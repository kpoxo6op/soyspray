"""Protect the daily schedule and the explicit node-local input boundary."""

from __future__ import annotations

import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


class NodeBackupManifest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = yaml.safe_load((ROOT / "manifests/cronjob.yaml").read_text())

    def test_daily_schedule_preserves_single_runner(self) -> None:
        spec = self.manifest["spec"]
        self.assertFalse(spec["suspend"])
        self.assertEqual(spec["concurrencyPolicy"], "Forbid")
        self.assertEqual(spec["schedule"], "0 3 * * *")
        self.assertEqual(spec["timeZone"], "Pacific/Auckland")

    def test_only_proven_host_paths_are_mounted(self) -> None:
        pod = self.manifest["spec"]["jobTemplate"]["spec"]["template"]["spec"]
        paths = [volume["hostPath"]["path"] for volume in pod["volumes"] if "hostPath" in volume]
        self.assertEqual(paths, ["/srv/media/jellyfin-data", "/srv/media/downloads"])
        mounts = {mount["name"]: mount for mount in pod["containers"][0]["volumeMounts"]}
        self.assertTrue(mounts["jellyfin-data"]["readOnly"])
        self.assertTrue(mounts["media-downloads"]["readOnly"])

    def test_credentials_use_the_documented_secret_contract(self) -> None:
        container = self.manifest["spec"]["jobTemplate"]["spec"]["template"]["spec"]["containers"][0]
        names = {entry["name"] for entry in container["env"]}
        self.assertIn({"name": "TMPDIR", "value": "/work"}, container["env"])
        self.assertTrue(
            {
                "RESTIC_REPOSITORY",
                "RESTIC_PASSWORD_FILE",
                "AWS_ACCESS_KEY_ID",
                "AWS_SECRET_ACCESS_KEY",
                "AWS_REGION",
            }.issubset(names)
        )
        self.assertRegex(container["image"], r"^ghcr.io/kpoxo6op/node-backup@sha256:[0-9a-f]{64}$")


if __name__ == "__main__":
    unittest.main()
