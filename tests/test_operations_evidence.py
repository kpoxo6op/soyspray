"""Reject stale observations and incomplete snapshots; preserve private evidence."""

import json
import subprocess
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from scripts import operations_evidence as evidence


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 9, 6, 8, tzinfo=timezone.utc)

    def test_source_failure_has_a_cause_for_each_claim(self):
        result = evidence._recording_rule({"status": "error"}, self.now)
        self.assertEqual(set(result), set(evidence.CRITICAL_BACKUPS))
        self.assertTrue(
            all(item["value"] == "unknown" and item["cause"] for item in result.values())
        )

    def test_stale_and_future_samples_are_unknown(self):
        labels = next(iter(evidence.CRITICAL_BACKUPS.values()))
        for offset in [-301, 60]:
            result = evidence._recording_rule(
                {
                    "status": "success",
                    "data": {
                        "result": [
                            {"metric": labels, "value": [self.now.timestamp() + offset, "60"]}
                        ]
                    },
                },
                self.now,
            )
            self.assertTrue(all(item["value"] == "unknown" for item in result.values()))

    def test_pending_candidate_is_excluded_and_private_workspace_is_removed(self):
        credentials = {
            key: "test"
            for key in [
                "AWS_ACCESS_KEY_ID",
                "AWS_SECRET_ACCESS_KEY",
                "AWS_DEFAULT_REGION",
                "RESTIC_REPOSITORY",
                "RESTIC_PASSWORD",
            ]
        }
        temporary = []

        def runner(argv, **kwargs):
            temporary.extend(
                [kwargs["env"]["RESTIC_PASSWORD_FILE"], kwargs["env"]["RESTIC_CACHE_DIR"]]
            )
            snapshots = [
                {
                    "id": "completed",
                    "hostname": "immich",
                    "tags": ["restore-candidate"],
                    "time": "2026-09-06T07:00:00Z",
                },
                {
                    "id": "incomplete",
                    "hostname": "immich",
                    "tags": ["restore-candidate", "pending"],
                    "time": "2026-09-06T07:30:00Z",
                },
            ]
            return subprocess.CompletedProcess(argv, 0, json.dumps(snapshots), "")

        with patch.object(evidence, "_vault_credentials", return_value=credentials):
            result = evidence.collect_restic(now=self.now, restic_path=__file__, runner=runner)
        self.assertEqual(result["value"]["snapshot_id"], "completed")
        self.assertEqual(result["value"]["age_seconds"], 3600)
        self.assertTrue(all(not Path(path).exists() for path in temporary))

    def test_append_is_private_and_does_not_follow_symlinks(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "records.jsonl"
            evidence.append_record(path, {"schema_version": 1})
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            link = Path(folder) / "link"
            link.symlink_to(path)
            with self.assertRaises(OSError):
                evidence.append_record(link, {})

    def test_saved_metrics_reject_incomplete_restore_schedules(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            directory = root / "schedule" / "test-run"
            directory.mkdir(parents=True)
            report = {
                "schema_version": 1,
                "run_id": "test-run",
                "status": "passed",
                "finished_at": "2026-09-06T05:10:39+00:00",
                "shared_gate": {"status": "passed", "returncode": 0},
                "apps": [
                    {
                        "app": name,
                        "passed": True,
                        "cleanup": "completed",
                        "command_returncode": 0,
                        "report_status": "passed",
                    }
                    for name in ("boys", "vaultwarden", "obsidian-livesync")
                ],
            }
            path = directory / "report.json"
            report["apps"][0]["cleanup"] = "failed"
            path.write_text(json.dumps(report))
            text = evidence.saved_metrics(
                root / "absent.jsonl", root, root / "absent-incidents.json"
            )
            self.assertNotIn("soyspray_critical_restore_last_success_timestamp_seconds 17", text)
            self.assertIn("soyspray_critical_restore_observed 0", text)
            report["apps"][0]["cleanup"] = "completed"
            path.write_text(json.dumps(report))
            text = evidence.saved_metrics(
                root / "absent.jsonl", root, root / "absent-incidents.json"
            )
            self.assertIn("soyspray_critical_restore_observed 1", text)
            self.assertIn("soyspray_critical_restore_last_success_timestamp_seconds 17", text)


class IncidentMetricTests(unittest.TestCase):
    """The endpoint must report bounded incident state, never raw evidence."""

    def snapshot(self, **overrides):
        value = {
            "schema_version": 1,
            "updated_at": "2026-09-21T12:00:00+00:00",
            "source_ok": True,
            "daily_limit": 3,
            "attempts_today": 1,
            "incidents": {
                "open": [
                    {
                        "anchor": "app:immich",
                        "kind": "app",
                        "generation": 1,
                        "state": "open",
                        "opened_at": "2026-09-21T01:00:00+00:00",
                        "consequences": ["app:boys"],
                        "symptoms": [{"name": "KubePodCrashLooping(p)", "labels": {"pod": "p"}}],
                    }
                ],
                "recently_closed": [],
            },
            "metrics": {
                "last_outcome": "diagnosed",
                "last_outcome_timestamp_seconds": 1789900000,
                "outcomes": {"diagnosed": 2, "unchanged": 40},
                "classifier_failure_total": 1,
                "classifier_unknown_total": 3,
                "classifier_last_success_timestamp_seconds": 1789900000,
            },
            "collector": {
                "status": "observed",
                "gaps": {"text-format-not-exported": 4},
                "targets": 2,
                "lines": 30,
                "exported": 12,
            },
            "classifier": {
                "status": "ok",
                "model": "jev-1.13.0",
                "counts": {"storage failure": 4},
                "model_substitution": False,
                "cause": "",
            },
        }
        value.update(overrides)
        return value

    def write(self, folder, value):
        path = Path(folder) / "metrics.json"
        path.write_text(json.dumps(value))
        return path

    def test_incident_state_is_exposed_as_bounded_numbers(self):
        with tempfile.TemporaryDirectory() as folder:
            path = self.write(folder, self.snapshot())
            text = evidence.incident_metrics(path)
        self.assertIn('soyspray_incident_open{anchor="app:immich",kind="app"} 1', text)
        self.assertIn(
            'soyspray_incident_consequence{anchor="app:boys",parent="app:immich"} 1', text
        )
        self.assertIn("soyspray_diagnosis_attempts_today 1", text)
        self.assertIn('soyspray_diagnosis_outcome_total{outcome="diagnosed"} 2', text)
        self.assertIn('soyspray_evidence_gap_total{reason="text-format-not-exported"} 4', text)
        self.assertIn("soyspray_evidence_collector_observed 1", text)
        self.assertIn("soyspray_classifier_up 1", text)
        self.assertIn('soyspray_classifier_model_info{model="jev-1.13.0"} 1', text)
        self.assertIn('soyspray_classifier_result_total{label="storage failure"} 4', text)
        self.assertIn("soyspray_classifier_failure_total 1", text)

    def test_missing_or_unknown_state_reports_no_series(self):
        def series(text):
            return [line for line in text.splitlines() if line and not line.startswith("#")]

        with tempfile.TemporaryDirectory() as folder:
            missing = Path(folder) / "absent.json"
            self.assertEqual(series(evidence.incident_metrics(missing)), [])
            wrong = self.write(folder, {"schema_version": 99})
            self.assertEqual(series(evidence.incident_metrics(wrong)), [])
            broken = Path(folder) / "broken.json"
            broken.write_text("{not json")
            self.assertEqual(series(evidence.incident_metrics(broken)), [])

    def test_classifier_failure_reports_zero_up(self):
        with tempfile.TemporaryDirectory() as folder:
            value = self.snapshot()
            value["classifier"]["status"] = "unavailable"
            value["classifier"]["cause"] = "network"
            path = self.write(folder, value)
            text = evidence.incident_metrics(path)
        self.assertIn("soyspray_classifier_up 0", text)

    def test_unreadable_collector_reports_zero_observed(self):
        with tempfile.TemporaryDirectory() as folder:
            value = self.snapshot()
            value["collector"]["status"] = "unavailable"
            path = self.write(folder, value)
            text = evidence.incident_metrics(path)
        self.assertIn("soyspray_evidence_collector_observed 0", text)

    def test_labels_are_bounded_and_escaped(self):
        with tempfile.TemporaryDirectory() as folder:
            value = self.snapshot()
            value["incidents"]["open"][0]["anchor"] = 'app:bad"anchor' + "\nrow"
            path = self.write(folder, value)
            text = evidence.incident_metrics(path)
        for line in text.splitlines():
            if line.startswith("soyspray_incident_open"):
                self.assertIn('anchor="app:bad_anchor_row"', line)
                break
        else:
            self.fail("the incident line is missing")

    def test_incident_list_is_bounded(self):
        with tempfile.TemporaryDirectory() as folder:
            value = self.snapshot()
            value["incidents"]["open"] = [
                {
                    "anchor": f"app:app{index}",
                    "kind": "app",
                    "opened_at": "2026-09-21T01:00:00+00:00",
                }
                for index in range(200)
            ]
            path = self.write(folder, value)
            text = evidence.incident_metrics(path)
        self.assertEqual(
            len([line for line in text.splitlines() if line.startswith("soyspray_incident_open{")]),
            evidence.MAX_INCIDENT_ANCHORS,
        )

    def test_saved_metrics_includes_the_incident_block(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            path = self.write(folder, self.snapshot())
            text = evidence.saved_metrics(root / "absent.jsonl", root, path)
        self.assertIn("soyspray_critical_restore_observed 0", text)
        self.assertIn('soyspray_incident_open{anchor="app:immich",kind="app"} 1', text)


if __name__ == "__main__":
    unittest.main()
