import importlib.util
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

MODULE_PATH = Path(__file__).parents[1] / "app" / "incident.py"
SPEC = importlib.util.spec_from_file_location("cluster_diagnosis_incident", MODULE_PATH)
incident = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(incident)

NOW = datetime(2026, 9, 21, 12, 0, tzinfo=timezone.utc)


def alert(
    alertname="KubePodCrashLooping",
    *,
    namespace="immich",
    node=None,
    pod=None,
    container=None,
    pvc=None,
    severity="critical",
    state="active",
    silenced=None,
    inhibited=None,
    starts=NOW - timedelta(minutes=10),
    ends=NOW + timedelta(minutes=5),
    fingerprint=None,
    summary="a symptom",
):
    labels = {"alertname": alertname, "severity": severity}
    if namespace:
        labels["namespace"] = namespace
    if node:
        labels["node"] = node
    if pod:
        labels["pod"] = pod
    if container:
        labels["container"] = container
    if pvc:
        labels["pvc"] = pvc
    return {
        "fingerprint": fingerprint or f"{alertname}-{namespace}-{pod}-{pvc}",
        "labels": labels,
        "annotations": {"summary": summary},
        "status": {
            "state": state,
            "silencedBy": silenced or [],
            "inhibitedBy": inhibited or [],
        },
        "startsAt": starts.isoformat().replace("+00:00", "Z"),
        "endsAt": ends.isoformat().replace("+00:00", "Z"),
    }


def refiring(*, minutes):
    """A currently firing alert for the same namespace, minutes after NOW."""
    return alert(
        pod="immich-server-0",
        starts=NOW + timedelta(minutes=minutes - 10),
        ends=NOW + timedelta(minutes=minutes + 5),
    )


def fresh_state():
    return incident._empty_state()


def applied(state, alerts, now=NOW):
    return incident.apply_alerts(state, alerts, now)


class AnchorTests(unittest.TestCase):
    def test_namespaced_alert_belongs_to_its_application(self):
        self.assertEqual(incident.anchor(alert()), ("app", "immich"))

    def test_node_alert_without_namespace_belongs_to_the_node(self):
        value = alert(alertname="KubeNodeNotReady", namespace=None, node="node-1")
        self.assertEqual(incident.anchor(value), ("node", "node-1"))

    def test_unnamed_alert_falls_back_to_its_alert_name(self):
        value = alert(alertname="Watchdog", namespace=None)
        self.assertEqual(incident.anchor(value), ("alert", "Watchdog"))

    def test_app_namespace_alias_is_used_when_namespace_is_absent(self):
        value = alert()
        del value["labels"]["namespace"]
        value["labels"]["app_namespace"] = "boys"
        self.assertEqual(incident.anchor(value), ("app", "boys"))

    def test_unsafe_label_value_is_not_an_anchor(self):
        value = alert(namespace="immich; drop")
        self.assertEqual(incident.anchor(value), ("alert", "KubePodCrashLooping"))


class LifecycleTests(unittest.TestCase):
    def test_one_alert_opens_one_incident(self):
        state = fresh_state()
        report = applied(state, [alert()])
        self.assertEqual([item["transition"] for item in report["transitions"]], ["opened"])
        self.assertEqual(len(state["incidents"]), 1)
        current = next(iter(state["incidents"].values()))
        self.assertEqual(current["anchor"], "app:immich")
        self.assertEqual(current["generation"], 1)

    def test_symptoms_in_one_namespace_share_one_incident(self):
        state = fresh_state()
        alerts = [
            alert(pod="immich-server-0"),
            alert(alertname="KubePodNotReady", pod="immich-server-0"),
            alert(alertname="SoysprayVolumeMountFailure", pod="immich-server-0", pvc="immich-data"),
        ]
        report = applied(state, alerts)
        self.assertEqual(len(report["transitions"]), 1)
        self.assertEqual(len(state["incidents"]), 1)
        current = incident.Incident(next(iter(state["incidents"].values())))
        self.assertEqual(len(current.symptoms), 3)
        self.assertEqual(current.highest_severity(), "critical")

    def test_independent_namespaces_stay_separate(self):
        state = fresh_state()
        report = applied(state, [alert(namespace="immich"), alert(namespace="boys")])
        self.assertEqual(len(report["transitions"]), 2)
        self.assertEqual(len(state["incidents"]), 2)

    def test_node_and_application_incidents_stay_separate(self):
        state = fresh_state()
        alerts = [
            alert(alertname="KubeNodeNotReady", namespace=None, node="node-1", severity="warning"),
            alert(namespace="immich", node="node-1", pod="immich-server-0"),
            alert(namespace="boys", node="node-1", pod="boys-0"),
        ]
        applied(state, alerts)
        anchors = {record["anchor"] for record in state["incidents"].values()}
        self.assertEqual(anchors, {"node:node-1", "app:immich", "app:boys"})

    def test_refresh_timestamps_do_not_change_the_incident(self):
        state = fresh_state()
        applied(state, [alert()])
        report = applied(state, [alert(ends=NOW + timedelta(minutes=4), summary="a symptom")])
        self.assertEqual(report["transitions"], [])
        self.assertGreaterEqual(len(state["incidents"]), 1)

    def test_new_symptom_is_a_material_update(self):
        state = fresh_state()
        applied(state, [alert(pod="immich-server-0")])
        report = applied(
            state,
            [alert(pod="immich-server-0"), alert(alertname="KubeJobFailed", pod="immich-backup-1")],
        )
        self.assertEqual([item["transition"] for item in report["transitions"]], ["updated"])

    def test_meaning_change_in_one_symptom_is_a_material_update(self):
        state = fresh_state()
        applied(state, [alert(pod="immich-server-0", container="server")])
        report = applied(
            state, [alert(pod="immich-server-0", container="server", summary="a new symptom")]
        )
        self.assertEqual([item["transition"] for item in report["transitions"]], ["updated"])

    def test_recovery_closes_once_and_does_not_repeat(self):
        state = fresh_state()
        applied(state, [alert(pod="immich-server-0")])
        resolved = alert(
            pod="immich-server-0",
            ends=NOW - timedelta(minutes=2),
            starts=NOW - timedelta(minutes=30),
        )
        report = applied(state, [resolved], NOW + timedelta(minutes=5))
        self.assertEqual([item["transition"] for item in report["transitions"]], ["recovered"])
        self.assertEqual(report["transitions"][0]["reason"], "resolved")
        closed = state["closed"][-1]
        self.assertEqual(closed["state"], "closed")
        again = applied(state, [resolved], NOW + timedelta(minutes=7))
        self.assertEqual(again["transitions"], [])
        self.assertEqual(len(state["closed"]), 1)

    def test_absent_alert_closes_the_incident_after_the_grace(self):
        state = fresh_state()
        applied(state, [alert(pod="immich-server-0")])
        early = applied(state, [], NOW + timedelta(minutes=1))
        self.assertEqual(early["transitions"], [])
        late = applied(state, [], NOW + timedelta(minutes=10))
        self.assertEqual([item["transition"] for item in late["transitions"]], ["recovered"])
        self.assertEqual(late["transitions"][0]["reason"], "not-observed")

    def test_reopen_inside_the_window_increments_the_generation(self):
        state = fresh_state()
        applied(state, [alert(pod="immich-server-0")])
        resolved = alert(
            pod="immich-server-0",
            ends=NOW - timedelta(minutes=2),
            starts=NOW - timedelta(minutes=30),
        )
        applied(state, [resolved], NOW + timedelta(minutes=5))
        report = applied(state, [refiring(minutes=30)], NOW + timedelta(minutes=30))
        self.assertEqual([item["transition"] for item in report["transitions"]], ["reopened"])
        current = incident.Incident(next(iter(state["incidents"].values())))
        self.assertEqual(current.generation, 2)
        self.assertIsNotNone(current.record["reopened_from"])

    def test_reopen_after_the_window_starts_a_new_generation_one(self):
        state = fresh_state()
        applied(state, [alert(pod="immich-server-0")])
        resolved = alert(
            pod="immich-server-0",
            ends=NOW - timedelta(minutes=2),
            starts=NOW - timedelta(minutes=30),
        )
        applied(state, [resolved], NOW + timedelta(minutes=5))
        report = applied(state, [refiring(minutes=9 * 60)], NOW + timedelta(hours=9))
        self.assertEqual([item["transition"] for item in report["transitions"]], ["opened"])
        current = incident.Incident(next(iter(state["incidents"].values())))
        self.assertEqual(current.generation, 1)

    def test_alerts_that_never_page_are_not_incidents(self):
        state = fresh_state()
        report = applied(
            state,
            [
                alert(
                    alertname="Watchdog", namespace=None, pod=None, container=None, severity="none"
                ),
                alert(alertname="InfoInhibitor", severity="info"),
                alert(alertname="CPUThrottlingHigh", severity="info"),
            ],
        )
        self.assertEqual(report["transitions"], [])
        self.assertEqual(state["incidents"], {})

    def test_suppressed_alert_does_not_open_an_incident(self):
        state = fresh_state()
        report = applied(state, [alert(inhibited=["KubeNodeNotReady"])])
        self.assertEqual(report["transitions"], [])
        self.assertEqual(state["incidents"], {})

    def test_resolved_page_history_does_not_open_an_incident(self):
        state = fresh_state()
        value = alert(ends=NOW - timedelta(minutes=2), starts=NOW - timedelta(minutes=30))
        report = applied(state, [value])
        self.assertEqual(report["transitions"], [])
        self.assertEqual(state["incidents"], {})

    def test_silenced_alert_does_not_open_an_incident(self):
        state = fresh_state()
        report = applied(state, [alert(silenced=["silence-1"])])
        self.assertEqual(report["transitions"], [])
        self.assertEqual(state["incidents"], {})

    def test_symptom_list_is_bounded(self):
        state = fresh_state()
        alerts = [alert(alertname=f"Alert{index}", pod=f"pod-{index}") for index in range(40)]
        applied(state, alerts)
        current = incident.Incident(next(iter(state["incidents"].values())))
        self.assertEqual(len(current.symptoms), incident.MAX_SYMPTOMS)

    def test_silent_incidents_are_discarded_after_the_stale_bound(self):
        state = fresh_state()
        applied(state, [alert()])
        applied(state, [], NOW + timedelta(hours=13))
        self.assertEqual(state["incidents"], {})
        self.assertEqual(len(state["closed"]), 1)

    def test_closed_history_is_bounded(self):
        state = fresh_state()
        for index in range(incident.MAX_CLOSED_INCIDENTS + 10):
            moment = NOW + timedelta(hours=index)
            applied(state, [alert(namespace=f"app{index}")], moment)
            applied(state, [], moment + timedelta(minutes=10))
        self.assertLessEqual(len(state["closed"]), incident.MAX_CLOSED_INCIDENTS)

    def test_content_hash_ignores_refresh_but_tracks_state(self):
        state = fresh_state()
        applied(state, [alert(pod="immich-server-0")])
        current = incident.Incident(next(iter(state["incidents"].values())))
        first = current.content_hash()
        applied(state, [alert(pod="immich-server-0", ends=NOW + timedelta(minutes=4))])
        self.assertEqual(current.content_hash(), first)
        applied(state, [alert(pod="immich-server-0"), alert(alertname="Extra", pod="other")])
        self.assertNotEqual(current.content_hash(), first)


class SymptomIdentityTests(unittest.TestCase):
    """Regression coverage for symptoms that used to share one key."""

    def test_sibling_containers_are_separate_symptoms(self):
        state = fresh_state()
        applied(
            state,
            [
                alert(pod="immich-server-0", container="server"),
                alert(pod="immich-server-0", container="sidecar"),
            ],
        )
        current = incident.Incident(next(iter(state["incidents"].values())))
        self.assertEqual(len(current.symptoms), 2)

    def test_a_resolved_sibling_container_does_not_hide_a_firing_one(self):
        state = fresh_state()
        applied(
            state,
            [
                alert(pod="immich-server-0", container="server"),
                alert(pod="immich-server-0", container="sidecar"),
            ],
        )
        report = applied(
            state,
            [
                alert(
                    pod="immich-server-0",
                    container="server",
                    starts=NOW,
                    ends=NOW + timedelta(minutes=30),
                ),
                alert(
                    pod="immich-server-0",
                    container="sidecar",
                    starts=NOW - timedelta(minutes=40),
                    ends=NOW + timedelta(minutes=9),
                ),
            ],
            NOW + timedelta(minutes=10),
        )
        current = incident.Incident(next(iter(state["incidents"].values())))
        self.assertEqual(len(current.active_symptoms()), 1)
        self.assertEqual(current.state, "open")
        self.assertEqual([item["transition"] for item in report["transitions"]], ["updated"])

    def test_event_object_is_part_of_the_symptom_identity(self):
        first = alert(alertname="SoysprayVolumeMountFailure", pod=None, container=None)
        first["labels"]["kubernetes_event_involved_object_name"] = "immich-server-0"
        second = alert(alertname="SoysprayVolumeMountFailure", pod=None, container=None)
        second["labels"]["kubernetes_event_involved_object_name"] = "immich-server-1"
        self.assertNotEqual(incident.symptom_name(first), incident.symptom_name(second))
        self.assertIn("immich-server-1", incident.symptom_name(second))
        self.assertIn("kubernetes_event_involved_object_name", incident.prompt_labels(second))

    def test_a_critical_symptom_replaces_a_warning_one_at_the_cap(self):
        state = fresh_state()
        warnings = [
            alert(alertname=f"Warning{index}", pod=f"pod-{index}", severity="warning")
            for index in range(incident.MAX_SYMPTOMS)
        ]
        applied(state, warnings)
        applied(state, [alert(alertname="KubePodCrashLooping", pod="critical-pod")])
        current = incident.Incident(next(iter(state["incidents"].values())))
        self.assertIn("KubePodCrashLooping(critical-pod)", current.symptoms)
        self.assertEqual(len(current.symptoms), incident.MAX_SYMPTOMS)

    def test_overflow_is_counted_and_reported(self):
        state = fresh_state()
        alerts = [alert(alertname=f"Critical{index}", pod=f"pod-{index}") for index in range(40)]
        applied(state, alerts)
        current = incident.Incident(next(iter(state["incidents"].values())))
        self.assertEqual(len(current.symptoms), incident.MAX_SYMPTOMS)
        self.assertGreater(current.record["symptom_overflow"], 0)
        self.assertGreater(incident.summarize(current)["symptom_overflow"], 0)

    def test_a_vanished_symptom_closes_while_a_sibling_stays_firing(self):
        state = fresh_state()
        applied(
            state,
            [
                alert(pod="pod-a", container="one"),
                alert(pod="pod-b", container="two"),
            ],
        )
        report = applied(
            state,
            [
                alert(
                    pod="pod-b",
                    container="two",
                    starts=NOW,
                    ends=NOW + timedelta(minutes=30),
                )
            ],
            NOW + timedelta(minutes=10),
        )
        current = incident.Incident(next(iter(state["incidents"].values())))
        states = {name: item["state"] for name, item in current.symptoms.items()}
        self.assertEqual(states["KubePodCrashLooping(pod-a, one)"], "closed")
        self.assertEqual(states["KubePodCrashLooping(pod-b, two)"], "firing")
        self.assertEqual(current.state, "open")
        self.assertEqual([item["transition"] for item in report["transitions"]], ["updated"])

    def test_suppression_is_not_reported_as_recovery(self):
        state = fresh_state()
        applied(state, [alert(pod="pod-a", container="one")])
        report = applied(
            state,
            [alert(pod="pod-a", container="one", inhibited=["KubeNodeNotReady"])],
            NOW + timedelta(minutes=10),
        )
        self.assertEqual([item["transition"] for item in report["transitions"]], ["recovered"])
        self.assertEqual(report["transitions"][0]["reason"], "suppressed")

    def test_alertmanager_resolution_is_reported_as_recovery(self):
        state = fresh_state()
        applied(state, [alert(pod="pod-a", container="one")])
        report = applied(
            state,
            [
                alert(
                    pod="pod-a",
                    container="one",
                    starts=NOW - timedelta(minutes=40),
                    ends=NOW - timedelta(minutes=2),
                )
            ],
            NOW + timedelta(minutes=10),
        )
        self.assertEqual(report["transitions"][0]["reason"], "resolved")


class CorrelationTests(unittest.TestCase):
    def node_incident(self, state):
        applied(
            state,
            [
                alert(
                    alertname="KubeNodeNotReady", namespace=None, node="node-1", severity="warning"
                )
            ],
        )
        return incident.Incident(
            next(record for record in state["incidents"].values() if record["kind"] == "node")
        )

    def test_every_pod_on_the_failing_node_makes_a_consequence(self):
        state = fresh_state()
        node = self.node_incident(state)
        applied(
            state,
            [alert(namespace="immich", node="node-1", pod="immich-server-0")],
            NOW + timedelta(minutes=2),
        )
        app = incident.Incident(
            next(record for record in state["incidents"].values() if record["kind"] == "app")
        )
        mapping = {"node-1": [("immich", "immich-server-0")]}
        self.assertTrue(incident.related_to_node(app, node, mapping, NOW + timedelta(minutes=3)))

    def test_one_pod_outside_the_node_keeps_the_incident_independent(self):
        state = fresh_state()
        node = self.node_incident(state)
        applied(
            state,
            [
                alert(namespace="immich", node="node-1", pod="immich-server-0"),
                alert(namespace="immich", node="node-2", pod="immich-server-1"),
            ],
            NOW + timedelta(minutes=2),
        )
        app = incident.Incident(
            next(record for record in state["incidents"].values() if record["kind"] == "app")
        )
        mapping = {"node-1": [("immich", "immich-server-0")]}
        self.assertFalse(incident.related_to_node(app, node, mapping, NOW + timedelta(minutes=3)))

    def test_an_older_application_incident_stays_independent(self):
        state = fresh_state()
        app_alert = alert(
            namespace="immich",
            node="node-1",
            pod="immich-server-0",
            starts=NOW - timedelta(hours=2),
            ends=NOW + timedelta(minutes=5),
        )
        node_alert = alert(
            alertname="KubeNodeNotReady", namespace=None, node="node-1", severity="warning"
        )
        applied(state, [app_alert], NOW - timedelta(hours=2))
        applied(state, [app_alert, node_alert], NOW)
        node = incident.Incident(
            next(record for record in state["incidents"].values() if record["kind"] == "node")
        )
        app = incident.Incident(
            next(record for record in state["incidents"].values() if record["kind"] == "app")
        )
        mapping = {"node-1": [("immich", "immich-server-0")]}
        self.assertFalse(incident.related_to_node(app, node, mapping, NOW))

    def test_no_node_mapping_means_no_correlation(self):
        state = fresh_state()
        node = self.node_incident(state)
        applied(state, [alert(namespace="immich", node="node-1", pod="immich-server-0")], NOW)
        app = incident.Incident(
            next(record for record in state["incidents"].values() if record["kind"] == "app")
        )
        self.assertFalse(incident.related_to_node(app, node, {}, NOW))

    def test_symptom_without_a_pod_does_not_correlate(self):
        state = fresh_state()
        node = self.node_incident(state)
        applied(state, [alert(namespace="immich", pvc="immich-data")], NOW)
        app = incident.Incident(
            next(record for record in state["incidents"].values() if record["kind"] == "app")
        )
        mapping = {"node-1": [("immich", "immich-server-0")]}
        self.assertFalse(incident.related_to_node(app, node, mapping, NOW))

    def test_one_podless_symptom_blocks_correlation_for_the_whole_incident(self):
        state = fresh_state()
        node = self.node_incident(state)
        applied(
            state,
            [
                alert(namespace="immich", node="node-1", pod="immich-server-0"),
                alert(
                    alertname="CNPGBackupStale",
                    namespace="immich",
                    pod=None,
                    container=None,
                ),
            ],
            NOW,
        )
        app = incident.Incident(
            next(record for record in state["incidents"].values() if record["kind"] == "app")
        )
        mapping = {"node-1": [("immich", "immich-server-0")]}
        self.assertFalse(incident.related_to_node(app, node, mapping, NOW))

    def test_a_new_consequence_changes_the_parent_content_hash(self):
        parent = incident.new_incident("node", "node-1", NOW)
        before = parent.content_hash()
        parent.record["consequences"] = ["app:immich"]
        self.assertNotEqual(parent.content_hash(), before)


class SanitizationTests(unittest.TestCase):
    def test_prompt_labels_are_allowlisted_and_charset_checked(self):
        value = alert(pod="immich-server-0")
        value["labels"]["DB_URL"] = "postgres://user:password@host/db"
        value["labels"]["pod"] = "immich server 0"
        selected = incident.prompt_labels(value)
        self.assertEqual(
            selected,
            {"alertname": "KubePodCrashLooping", "namespace": "immich", "severity": "critical"},
        )

    def test_prompt_labels_keep_only_the_selected_keys(self):
        value = alert(pod="immich-server-0", container="server")
        value["labels"]["team"] = "platform"
        selected = incident.prompt_labels(value)
        self.assertIn("pod", selected)
        self.assertNotIn("team", selected)

    def test_evidence_targets_use_the_namespace_alias(self):
        value = alert()
        del value["labels"]["namespace"]
        value["labels"]["app_namespace"] = "boys"
        value["labels"]["pvc"] = "boys-data"
        self.assertEqual(
            incident.evidence_targets(value),
            {"app_namespace": "boys", "namespace": "boys", "pvc": "boys-data"},
        )

    def test_secret_shaped_labels_are_redacted(self):
        value = alert()
        value["labels"]["token"] = "opaque"
        self.assertEqual(incident.safe_map(value["labels"])["token"], "[redacted]")

    def test_summary_reports_consequences(self):
        state = fresh_state()
        applied(state, [alert()])
        record = next(iter(state["incidents"].values()))
        record["consequences"] = ["app:boys"]
        self.assertEqual(
            incident.summarize(incident.Incident(record))["consequences"], ["app:boys"]
        )


class StateTests(unittest.TestCase):
    def test_old_state_version_is_discarded(self):
        self.assertEqual(incident.load_incident_state(lambda: {"version": 1})["incidents"], {})

    def test_current_state_version_is_loaded(self):
        state = fresh_state()
        applied(state, [alert()])
        loaded = incident.load_incident_state(lambda: state)
        self.assertEqual(len(loaded["incidents"]), 1)

    def test_inventory_is_bounded_and_sanitized(self):
        state = fresh_state()
        applied(state, [alert(namespace="immich"), alert(namespace="boys")])
        value = incident.inventory(state)
        self.assertEqual(len(value["open"]), 2)
        self.assertEqual({item["anchor"] for item in value["open"]}, {"app:immich", "app:boys"})


if __name__ == "__main__":
    unittest.main()
