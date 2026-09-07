import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch
from urllib.error import URLError

MODULE_PATH = Path(__file__).parents[1] / "app" / "adapter.py"
SPEC = importlib.util.spec_from_file_location("cluster_diagnosis_adapter", MODULE_PATH)
adapter = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(adapter)


def alert(
    *,
    fingerprint="a",
    state="active",
    severity="critical",
    silenced=None,
    changed="one",
    ends="old",
):
    return {
        "fingerprint": fingerprint,
        "labels": {"alertname": "NodeDown", "severity": severity},
        "annotations": {"summary": changed},
        "status": {"state": state, "silencedBy": silenced or [], "inhibitedBy": []},
        "startsAt": "2026-09-06T00:00:00Z",
        "endsAt": ends,
        "updatedAt": changed,
    }


class AdapterTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.state = root / "state.json"
        self.lock = root / "lock"
        self.run = Mock(return_value=SimpleNamespace(returncode=0, stdout="", stderr=""))
        self.now = datetime.fromisoformat("2026-09-06T12:00:00+12:00")

    def tearDown(self):
        self.tmp.cleanup()

    def call(self, alerts, *, now=None, fetch=None, usage=0, diagnose=None):
        return adapter.run_once(
            alertmanager_url="http://alertmanager",
            state_path=self.state,
            lock_path=self.lock,
            openclaw="openclaw",
            agent="cluster-diagnosis",
            telegram_target="12345",
            now=now or self.now,
            fetch=fetch or (lambda _: alerts),
            run=self.run,
            usage_gate=lambda: usage,
            diagnose=diagnose or (lambda _: "diagnosed"),
        )

    def read_state(self):
        return json.loads(self.state.read_text())

    def test_restart_and_duplicate_alert_do_not_rediagnose(self):
        self.assertEqual(self.call([alert()]), "diagnosed")
        self.assertEqual(self.call([alert()]), "unchanged")
        self.assertEqual(self.read_state()["alerts"]["a"]["last_result"], "diagnosed")
        self.assertEqual(self.state.stat().st_mode & 0o777, 0o600)

    def test_refresh_timestamps_do_not_change_incident(self):
        self.assertEqual(self.call([alert(ends="first", changed="one")]), "diagnosed")
        self.assertEqual(self.call([alert(ends="second", changed="one")]), "unchanged")

    def test_unchanged_alert_invokes_no_model(self):
        self.assertEqual(self.call([alert(state="inactive")]), "unchanged")
        self.assertEqual(self.run.call_count, 0)

    def test_timeout_is_recorded_and_counts_as_one_attempt(self):
        self.assertEqual(self.call([alert()], diagnose=lambda _: "timeout"), "timeout")
        record = self.read_state()["alerts"]["a"]
        self.assertEqual(record["last_result"], "timeout")
        self.assertEqual(self.read_state()["attempts"]["2026-09-06"], 1)

    def test_daily_limit_pending_alert_retries_next_day(self):
        alerts = [alert(fingerprint=f"incident-{index}") for index in range(3)]
        for item in alerts:
            self.assertEqual(self.call([item]), "diagnosed")
        self.assertEqual(self.call([alert(fingerprint="incident-4")]), "daily-limit")
        self.assertEqual(
            self.call(
                [alert(fingerprint="incident-4")],
                now=datetime.fromisoformat("2026-09-07T00:01:00+12:00"),
            ),
            "diagnosed",
        )
        self.assertEqual(self.read_state()["attempts"], {"2026-09-06": 3, "2026-09-07": 1})

    def test_usage_gate_closes_at_55_and_stops_at_60(self):
        self.assertEqual(self.call([alert()], usage=55), "usage-closing")
        self.assertEqual(self.call([alert()], usage=60), "usage-limit")
        self.assertEqual(self.read_state()["attempts"], {})

    def test_unavailable_usage_does_not_start_model(self):
        result = adapter.run_once(
            alertmanager_url="http://alertmanager",
            state_path=self.state,
            lock_path=self.lock,
            openclaw="openclaw",
            agent="cluster-diagnosis",
            telegram_target="12345",
            now=self.now,
            fetch=lambda _: [alert()],
            run=self.run,
            usage_gate=lambda: None,
            diagnose=Mock(),
        )
        self.assertEqual(result, "usage-unavailable")
        self.assertFalse(self.read_state()["attempts"])

    def test_in_progress_is_marked_interrupted_without_duplicate(self):
        self.state.write_text(
            json.dumps(
                {
                    "version": 1,
                    "source": {"ok": True},
                    "alerts": {
                        "a": {
                            "last_hash": adapter.alert_hash(alert()),
                            "last_attempt_hash": adapter.alert_hash(alert()),
                            "last_result": "in-progress",
                        }
                    },
                    "attempts": {},
                }
            )
        )
        self.assertEqual(self.call([alert()]), "unchanged")
        self.assertEqual(self.read_state()["alerts"]["a"]["last_result"], "interrupted")

    def test_process_group_timeout_kills_children(self):
        with self.assertRaises(subprocess.TimeoutExpired):
            adapter._run_process_group(["/bin/sh", "-c", "sleep 60 & wait"], timeout=0.05)

    @unittest.skipUnless(shutil.which("bwrap"), "bubblewrap unavailable")
    def test_bwrap_permission_boundary_hides_host_tmp(self):
        marker = Path(self.tmp.name) / "host-only"
        marker.write_text("secret")
        result = subprocess.run(
            [
                "bwrap",
                "--die-with-parent",
                "--new-session",
                "--clearenv",
                "--ro-bind",
                "/usr",
                "/usr",
                "--ro-bind",
                "/bin",
                "/bin",
                "--ro-bind",
                "/lib",
                "/lib",
                "--ro-bind",
                "/lib64",
                "/lib64",
                "--ro-bind",
                "/etc",
                "/etc",
                "--proc",
                "/proc",
                "--dev",
                "/dev",
                "--tmpfs",
                "/tmp",
                "/bin/sh",
                "-c",
                f"test ! -e {marker}",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_source_failure_is_reported_only_on_state_change(self):
        def fail(_):
            raise URLError("http://user:password@example.invalid:9093 refused")

        self.assertEqual(self.call([], fetch=fail), "source-failed")
        self.assertEqual(self.call([], fetch=fail), "source-failed")
        sends = [
            call for call in self.run.call_args_list if call.args[0][1:3] == ["message", "send"]
        ]
        self.assertEqual(len(sends), 1)
        self.assertNotIn("password", sends[0].args[0][-1])

    def test_suppressed_and_noncritical_alerts_are_skipped(self):
        alerts = [
            alert(fingerprint="suppressed", silenced=["silence-1"]),
            alert(fingerprint="warning", severity="warning"),
        ]
        self.assertEqual(self.call(alerts), "unchanged")
        self.assertEqual(self.run.call_count, 0)

    def test_lock_serializes_runs(self):
        store = adapter.StateStore(self.state, self.lock)
        with store.lock() as acquired:
            self.assertTrue(acquired)
            self.assertEqual(self.call([alert()]), "busy")

    def test_model_payload_excludes_workload_credentials_and_free_text(self):
        value = alert()
        value["annotations"]["summary"] = "inline-database-password"
        value["labels"]["DB_URL"] = "opaque-database-credential"
        value["labels"]["pod"] = "unexpected free text"
        prompt = adapter._prompt(value)
        self.assertIn("NodeDown", prompt)
        self.assertNotIn("inline-database-password", prompt)
        self.assertNotIn("opaque-database-credential", prompt)
        self.assertNotIn("unexpected free text", prompt)

    def test_redacts_sensitive_keys_and_nested_values(self):
        value = adapter._safe_map({"password": "opaque-value", "nested": {"token": "opaque-token"}})
        self.assertNotIn("opaque", json.dumps(value))

    def test_usage_checks_both_windows_and_rounds_up(self):
        response = {
            "result": {
                "rateLimits": {"primary": {"usedPercent": 20}, "secondary": {"usedPercent": 54.5}}
            }
        }
        with (
            patch.object(adapter.subprocess, "Popen") as process,
            patch.object(adapter, "_rpc", return_value=response),
            patch.object(adapter.os, "killpg"),
        ):
            process.return_value.communicate.return_value = ("", "")
            self.assertEqual(adapter.read_usage_limit("codex"), 55)

    @unittest.skipUnless(shutil.which("bwrap"), "bubblewrap unavailable")
    def test_actual_sandbox_hides_home_credentials_and_host_processes(self):
        root = Path(self.tmp.name)
        (root / "auth.json").write_text("{}")
        (root / "config.toml").write_text("private fixture")
        workspace = root / "workspace"
        workspace.mkdir()
        argv = adapter._sandbox_argv(
            sys.executable, workspace, workspace / ".diagnosis-output", None, str(root)
        )
        self.assertIsNotNone(argv)
        executable_index = len(argv) - 1 - argv[::-1].index("/opt/diagnosis/codex")
        check = "import os,pathlib; p=pathlib.Path; assert not p('/home/boris').exists(); assert not p('/home/diagnosis/.codex/config.toml').exists(); assert not p('/home/diagnosis/.kube').exists(); assert not os.environ.get('AWS_SECRET_ACCESS_KEY'); assert len([x for x in p('/proc').iterdir() if x.name.isdigit()]) < 10; p('/workspace/probe').write_text('ok')"
        result = adapter._run_process_group(
            argv[:executable_index] + ["/opt/diagnosis/codex", "-c", check], timeout=5
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((workspace / "probe").read_text(), "ok")
        self.assertIsNone(
            adapter._sandbox_argv(
                sys.executable, workspace, workspace / "output", "/any/kubeconfig", str(root)
            )
        )

    @unittest.skipUnless(
        shutil.which("bwrap") and shutil.which("codex"), "native launcher unavailable"
    )
    def test_installed_codex_accepts_actual_sandbox_arguments(self):
        root = Path(self.tmp.name)
        (root / "auth.json").write_text("{}")
        workspace = root / "workspace"
        workspace.mkdir()
        argv = adapter._sandbox_argv(
            "codex", workspace, workspace / ".diagnosis-output", None, str(root)
        )
        self.assertIsNotNone(argv)
        result = adapter._run_process_group(argv[:-1] + ["--help"], timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Run Codex non-interactively", result.stdout)

    def test_result_delivery_retries_without_another_model_call(self):
        self.run.return_value.returncode = 1
        diagnosis = Mock(return_value="diagnosed")
        with self.assertRaises(RuntimeError):
            self.call([alert()], diagnose=diagnosis)
        self.assertEqual(self.read_state()["alerts"]["a"]["delivery_pending"], "diagnosed")
        self.run.return_value.returncode = 0
        self.assertEqual(self.call([alert()], diagnose=diagnosis), "unchanged")
        diagnosis.assert_called_once()
        self.assertNotIn("delivery_pending", self.read_state()["alerts"]["a"])

    def test_failed_telegram_delivery_is_not_silently_accepted(self):
        self.run.return_value.returncode = 1
        with self.assertRaisesRegex(RuntimeError, "Telegram delivery failed"):
            self.call([], fetch=lambda _: (_ for _ in ()).throw(URLError("offline")))
        self.assertFalse(self.state.exists())

    def test_metrics_use_fixed_queries_and_exclude_extra_labels(self):
        payload = {
            "nodes_ready": [
                {
                    "metric": {"node": "node-0", "password": "private-value"},
                    "value": [time.time(), "1"],
                }
            ]
        }
        with patch.object(
            adapter,
            "_run_process_group",
            return_value=SimpleNamespace(returncode=0, stdout=json.dumps(payload)),
        ) as run:
            result = adapter.metric_evidence()
        self.assertEqual(result["series"]["nodes_ready"][0]["value"], 1)
        self.assertNotIn("private-value", json.dumps(result))
        self.assertEqual(run.call_args.args[0][-2:], ["python3", "-"])

    def test_native_timeout_removes_children_that_start_a_new_session(self):
        if not shutil.which("bwrap"):
            self.skipTest("bubblewrap unavailable")
        root = Path(self.tmp.name)
        (root / "auth.json").write_text("{}")
        workspace = root / "workspace"
        workspace.mkdir()
        argv = adapter._sandbox_argv(
            sys.executable, workspace, workspace / "output", None, str(root)
        )
        end = len(argv) - 1 - argv[::-1].index("/opt/diagnosis/codex")
        with self.assertRaises(subprocess.TimeoutExpired):
            adapter._run_process_group(
                argv[:end]
                + [
                    "/bin/sh",
                    "-c",
                    "setsid /bin/sh -c 'sleep 0.3; touch /workspace/orphan' & wait",
                ],
                timeout=0.1,
            )
        time.sleep(0.4)
        self.assertFalse((workspace / "orphan").exists())

    def test_active_process_stops_when_usage_check_closes(self):
        with self.assertRaises(adapter.UsageStopped):
            adapter._run_process_group(
                ["/bin/sh", "-c", "sleep 60 & wait"],
                timeout=2,
                stop=lambda: True,
                poll_interval=0.01,
            )

    def test_scheduler_runs_only_one_model_per_invocation(self):
        diagnosis = Mock(return_value="diagnosed")
        self.assertEqual(
            self.call([alert(fingerprint="one"), alert(fingerprint="two")], diagnose=diagnosis),
            "diagnosed",
        )
        diagnosis.assert_called_once()


if __name__ == "__main__":
    unittest.main()
