"""Factual alert contract and delivery behavior."""

import json
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

APP = Path(__file__).parents[1] / "app"
sys.path.insert(0, str(APP))
import diagnosis as diagnosis_module  # noqa: E402

NOW = datetime(2026, 9, 22, 12, tzinfo=timezone.utc)


def alert(
    name="KubePodCrashLooping",
    *,
    pod="immich-server-0",
    namespace="immich",
    description="A service alert",
    ends=None,
    annotations=None,
):
    return {
        "fingerprint": f"{name}-{namespace}-{pod}",
        "labels": {
            "alertname": name,
            "severity": "critical",
            "namespace": namespace,
            "pod": pod,
            "container": "server",
        },
        "annotations": annotations or {"description": description},
        "status": {"state": "active", "silencedBy": [], "inhibitedBy": []},
        "startsAt": (NOW - timedelta(minutes=10)).isoformat(),
        "endsAt": (ends or NOW + timedelta(minutes=5)).isoformat(),
    }


def pack(signals=None, *, status="observed"):
    signals = signals or {}
    return {
        "status": status,
        "collected_at": NOW.isoformat(),
        "window_seconds": 900,
        "targets": [
            {
                "id": "A",
                "lines": 4,
                "exported": 4,
                "signals": signals,
                "samples": [],
                "levels": {"error": 4},
            }
        ],
        "totals": {"lines": 4, "exported": 4},
        "gaps": [],
    }


class FakeTelegram:
    def __init__(self):
        self.messages = []
        self.fail = False

    def healthy(self):
        return True

    def send(self, message):
        self.messages.append(message)
        return {"status": "failed" if self.fail else "sent", "cause": ""}


class Harness:
    def __init__(self, root):
        self.root = root
        self.clock = [NOW]
        self.alerts = [alert()]
        self.pack = pack({"disk-full": 2})
        self.telegram = FakeTelegram()
        self.worker = diagnosis_module.Diagnosis(
            state_path=root / "state.json",
            lock_path=root / "state.lock",
            alertmanager_url="http://alertmanager",
            loki_url="http://loki",
            prometheus_url="http://prometheus",
            telegram=self.telegram,
            fetch=lambda _url: self.alerts,
            collect=lambda _summary, **_kwargs: self.pack,
            metrics_source=lambda _url: {"status": "unavailable", "series": {}},
            now=lambda: self.clock[0],
            poll_seconds=120,
        )
        self.worker.reload_state()

    def state(self):
        return json.loads((self.root / "state.json").read_text())


def test_distinct_observation_is_a_short_factual_update(tmp_path):
    case = Harness(tmp_path)
    assert case.worker.iterate() == "factual"
    assert len(case.telegram.messages) == 1
    message = case.telegram.messages[0]
    assert "KubePodCrashLooping immich/immich-server-0" in message
    assert (
        "Loki, last 15m: immich/immich-server-0 (server): disk-full (2 sampled log lines)."
        in message
    )
    assert "DeepSeek" not in message and "classifier" not in message
    assert "budget" not in case.state()


def test_existing_alert_fact_is_not_repeated(tmp_path):
    case = Harness(tmp_path)
    case.pack = pack({"crash-loop": 4})
    assert case.worker.iterate() == "no-finding"
    assert case.telegram.messages == []


def test_synthetic_probe_never_becomes_a_cluster_health_claim(tmp_path):
    case = Harness(tmp_path)
    case.alerts = [
        alert(
            "SoysprayDiagnosisAcceptanceProbe",
            description=("A synthetic trigger; it carries no meaning about the cluster."),
        )
    ]
    case.pack = pack({"network-timeout": 34, "unhealthy": 34})
    assert case.worker.iterate() == "no-finding"
    assert case.telegram.messages == []


def test_missing_or_withheld_evidence_stays_silent(tmp_path):
    case = Harness(tmp_path)
    case.pack = pack(status="unavailable")
    case.pack["targets"] = []
    case.pack["totals"] = {"lines": 0, "exported": 0}
    case.pack["gaps"] = [{"reason": "message-held-back", "target": "A"}]
    assert case.worker.iterate() == "no-finding"
    assert case.telegram.messages == []


def test_sliding_count_does_not_create_an_update(tmp_path):
    case = Harness(tmp_path)
    assert case.worker.iterate() == "factual"
    case.pack = pack({"disk-full": 9})
    case.clock[0] += timedelta(minutes=12)
    case.alerts = [alert(ends=NOW + timedelta(hours=2))]
    assert case.worker.iterate() == "no-news"
    assert len(case.telegram.messages) == 1


def test_new_observation_after_cooldown_is_delivered(tmp_path):
    case = Harness(tmp_path)
    case.worker.iterate()
    case.pack = pack({"mount-failure": 1})
    case.clock[0] += timedelta(minutes=11)
    case.alerts = [alert(ends=NOW + timedelta(hours=2))]
    assert case.worker.iterate() == "factual"
    assert "mount-failure" in case.telegram.messages[-1]


def test_correlated_alarms_name_the_shared_resource():
    summary = {
        "symptoms": [
            {"name": "A", "state": "firing", "labels": {"pod": "server-0", "namespace": "x"}},
            {"name": "B", "state": "firing", "labels": {"pod": "server-0", "namespace": "x"}},
        ]
    }
    assert diagnosis_module.finding_line(summary, pack()) == "2 alerts name server-0: A, B."


def test_log_finding_names_its_own_target_among_unrelated_alerts():
    summary = {
        "symptoms": [
            {"name": "A", "state": "firing", "labels": {"namespace": "x", "pod": "one"}},
            {"name": "B", "state": "firing", "labels": {"namespace": "x", "pod": "two"}},
        ]
    }
    evidence = pack()
    evidence["targets"] = [
        {"id": "A", "signals": {}},
        {"id": "B", "signals": {"disk-full": 2}},
    ]
    assert diagnosis_module.finding_line(summary, evidence) == (
        "Loki, last 15m: x/two: disk-full (2 sampled log lines)."
    )


def test_absence_is_not_reported_as_recovery(tmp_path):
    case = Harness(tmp_path)
    case.worker.iterate()
    case.alerts = []
    case.clock[0] += timedelta(minutes=10)
    assert "recovered" in case.worker.iterate()
    assert "recovery is unverified" in case.telegram.messages[-1]
    assert "RESOLVED" not in case.telegram.messages[-1]


def test_delivery_failure_retries_without_reexamining_the_incident(tmp_path):
    case = Harness(tmp_path)
    case.telegram.fail = True
    assert case.worker.iterate() == "factual"
    assert len(case.state()["outbox"]) == 1
    case.clock[0] += timedelta(minutes=2)
    case.alerts = [alert(ends=NOW + timedelta(hours=2))]
    assert case.worker.iterate() == "delivery-pending"
    assert len(case.state()["outbox"]) == 1
    case.telegram.fail = False
    case.clock[0] += timedelta(minutes=1)
    case.worker.iterate()
    assert case.state()["outbox"] == []
    assert case.state()["metrics"]["deliveries"]["sent"] == 1


def test_legacy_provider_message_is_not_delivered_after_upgrade(tmp_path):
    case = Harness(tmp_path)
    case.alerts = []
    case.worker.state["outbox"] = [{"message": "old provider prose", "queued_at": time.time()}]
    case.worker.iterate()
    assert case.telegram.messages == []
    assert case.state()["outbox"] == []
    assert case.state()["metrics"]["deliveries"]["legacy-dropped"] == 1


def test_legacy_delivery_does_not_trigger_an_orphan_close(tmp_path):
    case = Harness(tmp_path)
    case.worker.iterate()
    record = next(iter(case.worker.state["incidents"].values()))
    record.pop("delivered_format")
    case.alerts = []
    case.clock[0] += timedelta(minutes=10)
    case.worker.iterate()
    assert len(case.telegram.messages) == 1


def test_pending_outbox_is_bounded(tmp_path):
    case = Harness(tmp_path)
    for index in range(25):
        case.worker.enqueue(f"finding {index}")
    assert len(case.worker.state["outbox"]) == 20


def test_unreadable_state_is_not_overwritten(tmp_path):
    case = Harness(tmp_path)
    path = tmp_path / "state.json"
    path.write_text("{invalid")
    assert "unreadable" in case.worker.reload_state()
    assert case.worker.iterate() == "state-unusable"
    assert path.read_text() == "{invalid"
    assert "soyspray_diagnosis_state_usable 0" in case.worker.render_metrics()
