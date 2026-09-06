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


if __name__ == "__main__":
    unittest.main()
