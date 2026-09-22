import importlib.util
import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

APP = Path(__file__).parents[1] / "app"
sys.path.insert(0, str(APP))
for name in ("diagnosis", "deepseek", "telegram", "evidence", "incident", "store", "metrics"):
    spec = importlib.util.spec_from_file_location(f"cluster_diagnosis_{name}", APP / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)

import deepseek as deepseek_module  # noqa: E402
import diagnosis as diagnosis_module  # noqa: E402
import telegram as telegram_module  # noqa: E402

NOW = datetime(2026, 9, 22, 12, 0, tzinfo=timezone.utc)
DAY = "2026-09-22"


def alert(
    alertname="KubePodCrashLooping",
    *,
    namespace="immich",
    pod="immich-server-0",
    container="immich-server",
    severity="critical",
    state="active",
    starts=NOW - timedelta(minutes=10),
    ends=NOW + timedelta(minutes=5),
    inhibited=None,
):
    labels = {"alertname": alertname, "severity": severity, "namespace": namespace}
    if pod:
        labels["pod"] = pod
    if container:
        labels["container"] = container
    return {
        "fingerprint": f"{alertname}-{namespace}-{pod}",
        "labels": labels,
        "annotations": {"summary": "a symptom"},
        "status": {"state": state, "silencedBy": [], "inhibitedBy": inhibited or []},
        "startsAt": starts.isoformat().replace("+00:00", "Z"),
        "endsAt": ends.isoformat().replace("+00:00", "Z"),
    }


def pack(status="observed"):
    return {
        "status": status,
        "collected_at": NOW.isoformat(),
        "window_seconds": 900,
        "targets": [
            {
                "id": "A",
                "selector": '{namespace="immich", container="immich-server"}',
                "lines": 4,
                "exported": 4,
                "dropped": 0,
                "levels": {"error": 4},
                "signals": {"crash-loop": 4},
                "samples": [{"level": "error", "message": "panic: boot failed"}],
            }
        ],
        "gaps": [],
        "totals": {"lines": 4, "exported": 4, "dropped": 0, "samples": 1, "bytes": 200},
    }


def classification(status="ok", counts=None, model="jev-1.13.0"):
    return {
        "status": status,
        "model": model,
        "model_substitution": False,
        "counts": counts if counts is not None else {"application crash or resource exhaustion": 1},
        "results": [],
        "classifications": 1,
        "requests": 1,
        "skipped": 0,
        "cause": "",
        "unknown": 0,
    }


def answer(content="A narrative.", tokens=812, model="deepseek-flash", finish="stop"):
    return (
        200,
        {
            "model": model,
            "choices": [{"message": {"content": content}, "finish_reason": finish}],
            "usage": {"total_tokens": tokens},
        },
    )


class FakeTelegram:
    def __init__(self, results=None):
        self.results = list(results or [])
        self.messages = []

    def healthy(self):
        return True

    def send(self, message):
        self.messages.append(message)
        if self.results:
            return self.results.pop(0)
        return {"status": "sent", "cause": ""}


class FakeClassifier:
    def __init__(self, state, report=None):
        self.report = report or classification()

    def classify(self, _texts):
        return self.report


class Transmission:
    """Records each request and can inspect the state file at request time."""

    def __init__(self, responses, state_path=None):
        self.responses = list(responses)
        self.state_path = state_path
        self.budgets = []
        self.calls = []

    def __call__(self, payload, api_key, timeout):
        self.calls.append(payload)
        if self.state_path is not None:
            self.budgets.append(
                json.loads(Path(self.state_path).read_text())["budget"].get(DAY, {})
            )
        if not self.responses:
            return answer()
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


class Harness:
    def __init__(self, root, **kwargs):
        self.root = Path(root)
        self.state_path = self.root / "state.json"
        self.transmission = kwargs.pop("transmission", Transmission([], None))
        self.telegram = kwargs.pop("telegram", FakeTelegram())
        self.alerts = kwargs.pop("alerts", [alert()])
        self.pack = kwargs.pop("pack", pack())
        self.classifier_report = kwargs.pop("classifier_report", classification())
        self.clock = kwargs.pop("clock", [NOW])
        self.fail_fetch = kwargs.pop("fail_fetch", False)
        self.diagnosis = diagnosis_module.Diagnosis(
            state_path=self.state_path,
            lock_path=self.root / "state.lock",
            alertmanager_url="http://alertmanager",
            loki_url="http://loki",
            prometheus_url="http://prometheus",
            telegram=self.telegram,
            deepseek_factory=lambda: deepseek_module.DeepSeek("key", transport=self.transmission),
            classifier_factory=lambda state: FakeClassifier(state, self.classifier_report),
            fetch=self.fetch,
            collect=lambda summary, **rest: self.pack,
            metrics_source=lambda url: {"status": "unavailable", "series": {}},
            now=lambda: self.clock[0],
            poll_seconds=1,
            **kwargs,
        )

    def fetch(self, _url):
        if self.fail_fetch:
            raise OSError("alertmanager down")
        return self.alerts

    def open(self):
        self.diagnosis.state = self.diagnosis.store.load()
        self.diagnosis.state_usable = True
        return self.diagnosis

    def state(self):
        return json.loads(self.state_path.read_text())


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_one_incident_is_one_transmission_and_one_message(self):
        harness = Harness(self.root)
        harness.transmission = Transmission([answer()], harness.state_path)
        diagnosis = harness.open()
        self.assertEqual(diagnosis.iterate(), "diagnosed")
        self.assertEqual(len(harness.transmission.calls), 1)
        self.assertEqual(len(harness.telegram.messages), 1)
        message = harness.telegram.messages[0]
        self.assertIn("INCIDENT OPENED", message)
        self.assertIn("app:immich", message)
        self.assertIn("Evidence: 1 log target(s)", message)
        self.assertIn("Classifier hint (not proof)", message)
        self.assertIn("A narrative.", message)
        self.assertEqual(harness.state()["budget"][DAY]["attempts"], 1)

    def test_the_reservation_is_on_disk_before_the_request(self):
        harness = Harness(self.root)
        harness.transmission = Transmission([answer()], harness.state_path)
        diagnosis = harness.open()
        diagnosis.iterate()
        self.assertEqual(harness.transmission.budgets[0]["attempts"], 1)
        recorded = harness.transmission.budgets[0]["tokens"]
        self.assertGreaterEqual(recorded, deepseek_module.INPUT_TOKEN_RESERVE)

    def test_reported_usage_replaces_the_reservation(self):
        harness = Harness(self.root)
        harness.transmission = Transmission([answer(tokens=812)], harness.state_path)
        harness.open().iterate()
        self.assertEqual(harness.state()["budget"][DAY]["tokens"], 812)

    def test_a_duplicate_poll_spends_nothing(self):
        harness = Harness(self.root)
        harness.transmission = Transmission([answer()], harness.state_path)
        diagnosis = harness.open()
        diagnosis.iterate()
        self.assertEqual(diagnosis.iterate(), "unchanged")
        self.assertEqual(len(harness.transmission.calls), 1)
        self.assertEqual(len(harness.telegram.messages), 1)

    def test_a_material_change_is_a_second_transmission(self):
        harness = Harness(self.root)
        harness.transmission = Transmission([answer(), answer("second")], harness.state_path)
        diagnosis = harness.open()
        diagnosis.iterate()
        harness.alerts = [
            alert(ends=NOW + timedelta(minutes=40)),
            alert(
                alertname="KubeJobFailed",
                pod="immich-job-1",
                starts=NOW,
                ends=NOW + timedelta(minutes=40),
            ),
        ]
        harness.clock[0] = NOW + timedelta(minutes=10)
        self.assertEqual(diagnosis.iterate(), "diagnosed")
        self.assertEqual(len(harness.transmission.calls), 2)
        self.assertIn("INCIDENT UPDATED", harness.telegram.messages[-1])

    def test_recovery_delivers_without_a_transmission(self):
        harness = Harness(self.root)
        harness.transmission = Transmission([answer()], harness.state_path)
        diagnosis = harness.open()
        diagnosis.iterate()
        harness.alerts = [
            alert(starts=NOW - timedelta(minutes=40), ends=NOW + timedelta(minutes=9))
        ]
        harness.clock[0] = NOW + timedelta(minutes=10)
        self.assertEqual(diagnosis.iterate(), "recovered")
        self.assertEqual(len(harness.transmission.calls), 1)
        self.assertIn("INCIDENT RECOVERED", harness.telegram.messages[-1])
        self.assertEqual(harness.state()["budget"][DAY]["attempts"], 1)

    def test_suppression_is_reported_as_a_close_not_a_recovery(self):
        harness = Harness(self.root)
        harness.transmission = Transmission([answer()], harness.state_path)
        diagnosis = harness.open()
        diagnosis.iterate()
        harness.alerts = [alert(inhibited=["KubeNodeNotReady"])]
        harness.clock[0] = NOW + timedelta(minutes=10)
        diagnosis.iterate()
        closed = [message for message in harness.telegram.messages if "INCIDENT CLOSED" in message]
        self.assertEqual(len(closed), 1)
        self.assertIn("suppressed", closed[0])

    def test_the_narrative_reports_a_kept_local_gap(self):
        harness = Harness(self.root)
        harness.pack = pack()
        harness.pack["gaps"] = [{"reason": "text-format-not-exported", "target": "A", "lines": 3}]
        harness.transmission = Transmission([answer()], harness.state_path)
        harness.open().iterate()
        self.assertIn("text-format-not-exported", harness.telegram.messages[0])


class BudgetTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_the_daily_attempt_limit_stops_transmission(self):
        harness = Harness(self.root, attempt_limit=1)
        harness.transmission = Transmission([answer(), answer()], harness.state_path)
        diagnosis = harness.open()
        diagnosis.iterate()
        harness.alerts = [alert(namespace="boys", pod="boys-0")]
        self.assertEqual(diagnosis.iterate(), "daily-attempts")
        self.assertEqual(len(harness.transmission.calls), 1)

    def test_the_token_ceiling_stops_transmission(self):
        harness = Harness(self.root, token_limit=100)
        harness.transmission = Transmission([answer()], harness.state_path)
        diagnosis = harness.open()
        self.assertEqual(diagnosis.iterate(), "daily-tokens")
        self.assertEqual(harness.transmission.calls, [])

    def test_a_spent_token_budget_is_not_refilled_by_a_restart(self):
        harness = Harness(self.root, token_limit=1000)
        harness.transmission = Transmission([answer(tokens=990)], harness.state_path)
        harness.open().iterate()
        restarted = Harness(self.root, token_limit=1000)
        restarted.transmission = Transmission([answer()], restarted.state_path)
        diagnosis = restarted.open()
        self.assertEqual(diagnosis.iterate(), "daily-tokens")
        self.assertEqual(restarted.transmission.calls, [])

    def test_an_unusable_state_blocks_transmission(self):
        harness = Harness(self.root)
        harness.state_path.write_text("{ not json")
        diagnosis = harness.diagnosis
        detail = diagnosis.reload_state()
        self.assertIn("unreadable", detail)
        self.assertFalse(diagnosis.state_usable)
        self.assertEqual(diagnosis.iterate(), "state-unusable")
        self.assertEqual(harness.transmission.calls, [])
        self.assertIn("soyspray_diagnosis_state_usable 0", diagnosis.render_metrics())

    def test_a_missing_state_file_is_usable_and_starts_the_day_clean(self):
        harness = Harness(self.root)
        diagnosis = harness.open()
        self.assertEqual(diagnosis.iterate(), "diagnosed")
        self.assertEqual(harness.state()["budget"][DAY]["attempts"], 1)


class ProviderTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_a_rejected_key_stops_later_transmissions(self):
        harness = Harness(self.root)
        harness.transmission = Transmission([(401, {})], harness.state_path)
        diagnosis = harness.open()
        diagnosis.iterate()
        self.assertTrue(diagnosis.blocked)
        harness.alerts = [alert(namespace="boys", pod="boys-0")]
        self.assertEqual(diagnosis.iterate(), "provider-blocked")
        self.assertEqual(len(harness.transmission.calls), 1)
        self.assertIn("soyspray_diagnosis_provider_blocked 1", diagnosis.render_metrics())

    def test_a_temporary_failure_schedules_a_bounded_retry(self):
        harness = Harness(self.root)
        harness.transmission = Transmission([(429, {"retry_after": 120})], harness.state_path)
        diagnosis = harness.open()
        diagnosis.iterate()
        self.assertIn("Diagnosis stopped: http-429", harness.telegram.messages[0])
        self.assertEqual(diagnosis.iterate(), "backoff")
        self.assertEqual(len(harness.transmission.calls), 1)

    def test_the_backoff_expires_and_the_incident_is_retried(self):
        harness = Harness(self.root)
        harness.transmission = Transmission([(503, {}), answer("later")], harness.state_path)
        harness.alerts = [alert(ends=NOW + timedelta(minutes=40))]
        diagnosis = harness.open()
        diagnosis.iterate()
        harness.clock[0] = NOW + timedelta(minutes=10)
        self.assertEqual(diagnosis.iterate(), "diagnosed")
        self.assertEqual(len(harness.transmission.calls), 2)
        self.assertEqual(harness.state()["budget"][DAY]["attempts"], 2)

    def test_an_empty_answer_is_not_delivered_as_a_narrative(self):
        harness = Harness(self.root)
        harness.transmission = Transmission([answer(content="")], harness.state_path)
        harness.open().iterate()
        message = harness.telegram.messages[0]
        self.assertIn("Diagnosis stopped: empty-content", message)
        self.assertNotIn("A narrative.", message)

    def test_an_ambiguous_outcome_still_charges_the_attempt(self):
        harness = Harness(self.root)
        harness.transmission = Transmission([OSError("timeout")], harness.state_path)
        harness.open().iterate()
        self.assertEqual(harness.state()["budget"][DAY]["attempts"], 1)

    def test_the_model_and_profile_are_exposed(self):
        harness = Harness(self.root)
        harness.transmission = Transmission([answer(model="deepseek-flash")], harness.state_path)
        diagnosis = harness.open()
        diagnosis.iterate()
        self.assertIn(
            'soyspray_diagnosis_model_info{model="deepseek-flash",profile="flash"} 1',
            diagnosis.render_metrics(),
        )


class DeliveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_a_failed_delivery_is_retried_without_another_transmission(self):
        telegram = FakeTelegram([{"status": "unavailable", "cause": "network"}])
        harness = Harness(self.root, telegram=telegram)
        harness.transmission = Transmission([answer()], harness.state_path)
        diagnosis = harness.open()
        diagnosis.iterate()
        self.assertEqual(len(harness.state()["outbox"]), 1)
        self.assertEqual(len(harness.transmission.calls), 1)
        self.assertEqual(diagnosis.iterate(), "unchanged")
        self.assertEqual(len(harness.transmission.calls), 1)
        self.assertEqual(harness.state()["outbox"], [])
        self.assertEqual(len(telegram.messages), 2)

    def test_an_expired_outbox_entry_is_dropped(self):
        harness = Harness(self.root)
        harness.transmission = Transmission([answer()], harness.state_path)
        diagnosis = harness.open()
        diagnosis.iterate()
        diagnostics = harness.state()
        diagnostics["outbox"] = [{"message": "old", "queued_at": 0}]
        harness.state_path.write_text(json.dumps(diagnostics))
        diagnosis.state = harness.diagnosis.store.load()
        diagnosis.deliver_outbox()
        self.assertEqual(diagnosis.state["outbox"], [])

    def test_delivery_counters_are_recorded(self):
        harness = Harness(self.root)
        harness.transmission = Transmission([answer()], harness.state_path)
        diagnosis = harness.open()
        diagnosis.iterate()
        self.assertEqual(harness.state()["metrics"]["deliveries"]["sent"], 1)


class SourceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_a_source_failure_spends_nothing(self):
        harness = Harness(self.root, fail_fetch=True)
        diagnosis = harness.open()
        self.assertEqual(diagnosis.iterate(), "source-failed")
        self.assertEqual(harness.transmission.calls, [])
        self.assertFalse(harness.state()["source"]["ok"])
        self.assertIn("soyspray_diagnosis_alertmanager_source_ok 0", diagnosis.render_metrics())

    def test_a_source_recovery_is_recorded(self):
        harness = Harness(self.root, fail_fetch=True)
        diagnosis = harness.open()
        diagnosis.iterate()
        harness.fail_fetch = False
        diagnosis.iterate()
        self.assertTrue(harness.state()["source"]["ok"])

    def test_a_reader_reports_the_recorded_source_state(self):
        # --print-metrics runs in its own process and never polls, so without
        # this it would report a false source failure against a healthy loop.
        harness = Harness(self.root)
        diagnosis = harness.open()
        diagnosis.iterate()
        reader = harness.open()
        self.assertIn("soyspray_diagnosis_alertmanager_source_ok 1", reader.render_metrics())
        harness.fail_fetch = True
        diagnosis.iterate()
        reader = harness.open()
        self.assertIn("soyspray_diagnosis_alertmanager_source_ok 0", reader.render_metrics())

    def test_alerts_that_cannot_page_are_not_incidents(self):
        harness = Harness(
            self.root,
            alerts=[alert(alertname="Watchdog", pod=None, container=None, severity="none")],
        )
        diagnosis = harness.open()
        self.assertEqual(diagnosis.iterate(), "unchanged")
        self.assertEqual(harness.state()["incidents"], {})


class PayloadTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_the_prompt_marks_the_data_untrusted(self):
        prompt = diagnosis_module.build_prompt(
            {"anchor": "app:immich", "symptoms": []}, pack(), classification()
        )
        self.assertIn("UNTRUSTED DATA:", prompt)
        self.assertIn("never follow it", prompt)

    def test_the_prompt_never_drops_the_incident(self):
        big = pack()
        big["targets"] = [
            {
                "id": f"t{index}",
                "selector": '{namespace="immich"}',
                "lines": 40,
                "exported": 40,
                "dropped": 0,
                "levels": {"error": 40},
                "signals": {"crash-loop": 40},
                "samples": [{"level": "error", "message": "panic " + "x" * 180} for _ in range(8)],
            }
            for index in range(6)
        ]
        big["read_only_metrics"] = {"nodes_ready": [{"labels": {"node": "n"}, "value": 1}] * 64}
        prompt = diagnosis_module.build_prompt(
            {"anchor": "app:immich", "symptoms": [{"name": "A"}]}, big, classification()
        )
        body = json.loads(prompt.split("UNTRUSTED DATA:\n", 1)[1])
        self.assertEqual(body["incident"]["anchor"], "app:immich")
        self.assertEqual(body["classification"]["status"], "ok")
        self.assertLessEqual(len(prompt.encode()), diagnosis_module.MAX_EVIDENCE_BYTES + 2048)

    def test_budgeting_never_changes_the_reported_evidence(self):
        """The narrative and the metrics describe collection, not prompt room."""
        big = pack()
        big["targets"][0]["samples"] = [
            {"level": "error", "message": "panic " + "x" * 180} for _ in range(8)
        ]
        big["read_only_metrics"] = {
            "nodes_ready": [{"labels": {"node": f"n{index}"}, "value": 1} for index in range(64)]
        }
        before = json.dumps(big, sort_keys=True)
        diagnosis_module.build_prompt(
            {"anchor": "app:immich", "symptoms": []}, big, classification()
        )
        self.assertEqual(json.dumps(big, sort_keys=True), before)
        self.assertIn("1 log target(s)", diagnosis_module.evidence_line(big))

    def test_the_prompt_prefers_evidence_over_metrics(self):
        big = pack()
        big["read_only_metrics"] = {
            "nodes_ready": [{"labels": {"node": f"n{index}"}, "value": 1} for index in range(64)]
        }
        payload = diagnosis_module.budget_payload(
            diagnosis_module.build_payload(
                {"anchor": "app:immich", "symptoms": []}, big, classification()
            ),
            diagnosis_module.MAX_EVIDENCE_BYTES,
        )
        self.assertEqual(payload["incident"]["anchor"], "app:immich")
        # The small evidence sample survives; the bulky context goes first.
        self.assertTrue(payload["evidence"]["targets"][0]["samples"])

    def test_the_classifier_hint_is_labelled_as_a_hint(self):
        line = diagnosis_module.classifier_line(classification())
        self.assertIn("not proof", line)
        self.assertIn("jev-1.13.0", line)

    def test_an_unavailable_classifier_is_reported_without_stopping_diagnosis(self):
        line = diagnosis_module.classifier_line(classification(status="unavailable"))
        self.assertIn("unavailable", line)
        self.assertIn("native alerts continue", line)

    def test_a_no_input_classifier_says_so(self):
        self.assertIn(
            "no sanitized evidence line", diagnosis_module.classifier_line({"status": "no-input"})
        )

    def test_refresh_timestamps_do_not_change_the_incident(self):
        harness = Harness(self.root)
        harness.transmission = Transmission([answer()], harness.state_path)
        diagnosis = harness.open()
        diagnosis.iterate()
        harness.alerts = [alert(ends=NOW + timedelta(minutes=4))]
        self.assertEqual(diagnosis.iterate(), "unchanged")

    def test_a_bounded_message_is_always_produced(self):
        message = diagnosis_module.narrative(
            "opened",
            {"anchor": "app:immich", "generation": 1, "symptoms": []},
            pack(),
            classification(),
            "line\n" * 5000,
        )
        self.assertLessEqual(len(message), telegram_module.MAX_MESSAGE_CHARS)


class MetricsTests(unittest.TestCase):
    def test_metrics_expose_bounded_labels_only(self):
        with tempfile.TemporaryDirectory() as folder:
            harness = Harness(Path(folder))
            harness.transmission = Transmission([answer()], harness.state_path)
            diagnosis = harness.open()
            diagnosis.iterate()
            text = diagnosis.render_metrics()
        self.assertIn("soyspray_incident_open", text)
        self.assertIn("soyspray_diagnosis_attempts_today", text)
        self.assertIn("soyspray_evidence_lines_exported_total", text)
        self.assertNotIn("panic: boot failed", text)
        self.assertNotIn("A narrative.", text)

    def test_never_attempted_work_reports_no_series(self):
        with tempfile.TemporaryDirectory() as folder:
            harness = Harness(Path(folder))
            diagnosis = harness.open()
            text = diagnosis.render_metrics()
        series = [line for line in text.splitlines() if line and not line.startswith("#")]
        self.assertFalse([line for line in series if line.startswith("soyspray_classifier_up")])
        self.assertFalse(
            [line for line in series if line.startswith("soyspray_evidence_collector_observed")]
        )

    def test_a_hostile_anchor_cannot_inject_a_series(self):
        with tempfile.TemporaryDirectory() as folder:
            harness = Harness(
                Path(folder),
                alerts=[alert(namespace="immich")],
            )
            diagnosis = harness.open()
            diagnosis.iterate()
            record = next(iter(diagnosis.state["incidents"].values()))
            record["anchor"] = 'app:x"}\nsoyspray_fake 1'
            text = diagnosis.render_metrics()
        series = [line for line in text.splitlines() if line.startswith("soyspray_incident_open{")]
        self.assertEqual(len(series), 1)
        for line in series:
            self.assertNotIn("\n", line)
            self.assertEqual(line.count('"'), 4, line)
            anchor = line.split('anchor="', 1)[1].split('"', 1)[0]
            self.assertNotIn('"', anchor)
            self.assertNotIn("}", anchor)


class ConsequenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def node_alerts(self):
        node = alert(
            alertname="KubeNodeNotReady",
            namespace=None,
            pod=None,
            container=None,
            severity="warning",
        )
        node["labels"]["node"] = "node-1"
        app = alert()
        app["labels"]["node"] = "node-1"
        return [node, app]

    def test_a_node_incident_owns_its_consequence(self):
        harness = Harness(self.root, alerts=self.node_alerts())
        harness.transmission = Transmission([answer()], harness.state_path)
        diagnosis = harness.open()
        diagnosis.metrics_source = lambda url: {
            "status": "observed",
            "series": {
                "pod_nodes": [
                    {
                        "labels": {
                            "node": "node-1",
                            "namespace": "immich",
                            "pod": "immich-server-0",
                        },
                        "value": 1,
                    }
                ]
            },
        }
        diagnosis.iterate()
        anchors = {record["anchor"]: record for record in diagnosis.state["incidents"].values()}
        self.assertIn("node:node-1", anchors)
        self.assertEqual(anchors["app:immich"]["consequence_of"], "node:node-1")
        self.assertEqual(len(harness.transmission.calls), 1)

    def test_without_a_node_map_nothing_is_merged(self):
        harness = Harness(self.root, alerts=self.node_alerts())
        harness.transmission = Transmission([answer()], harness.state_path)
        diagnosis = harness.open()
        diagnosis.iterate()
        anchors = {record["anchor"]: record for record in diagnosis.state["incidents"].values()}
        self.assertIsNone(anchors["app:immich"]["consequence_of"])


if __name__ == "__main__":
    unittest.main()
