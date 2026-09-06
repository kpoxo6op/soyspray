import subprocess
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "backup" / "paired-backup.yaml"
SECRET_KEYS = {
    "PGHOST",
    "PGPORT",
    "PGDATABASE",
    "PGUSER",
    "PGPASSWORD",
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "AWS_DEFAULT_REGION",
    "RESTIC_REPOSITORY",
    "RESTIC_PASSWORD",
}


class PairedBackupManifestTest(unittest.TestCase):
    def test_job_is_scheduled_and_runs_ordered_pinned_stages(self):
        job = yaml.safe_load(MANIFEST.read_text())
        spec = job["spec"]
        pod = spec["jobTemplate"]["spec"]["template"]["spec"]
        init = pod["initContainers"]

        self.assertFalse(spec["suspend"])
        self.assertEqual(spec["schedule"], "*/30 * * * *")
        self.assertEqual(spec["concurrencyPolicy"], "Forbid")
        self.assertEqual([item["name"] for item in init], ["script-bundle", "pg-dump"])
        self.assertEqual([item["name"] for item in pod["containers"]], ["restic-backup"])
        self.assertEqual(init[0]["image"], "immich-backup-scripts")
        self.assertIn(
            "@sha256:38471f330eb885e04de130b768d6db4e10469e2311879c7e5c699f6d2d8a1c74",
            init[1]["image"],
        )
        self.assertIn(
            "@sha256:39d9072fb5651c80d75c7a811612eb60b4c06b32ffe87c2e9f3c7222e1797e76",
            pod["containers"][0]["image"],
        )
        self.assertEqual(init[1]["command"], ["/scripts/dump.sh"])
        self.assertEqual(pod["containers"][0]["command"], ["/scripts/backup.sh"])

    def test_secret_contract_mounts_and_library_affinity_are_restricted(self):
        job = yaml.safe_load(MANIFEST.read_text())
        pod = job["spec"]["jobTemplate"]["spec"]["template"]["spec"]
        dump = pod["initContainers"][1]
        restic = pod["containers"][0]
        secret_refs = [
            env["valueFrom"]["secretKeyRef"]
            for env in dump["env"] + restic["env"]
            if "valueFrom" in env
        ]
        env_keys = {ref["key"] for ref in secret_refs}
        password = next(volume for volume in pod["volumes"] if volume["name"] == "restic-password")
        password_item = password["secret"]["items"][0]

        self.assertTrue(pod["automountServiceAccountToken"] is False)
        self.assertNotIn("serviceAccountName", pod)
        self.assertEqual({ref["name"] for ref in secret_refs}, {"immich-paired-backup"})
        self.assertEqual(env_keys | {password_item["key"]}, SECRET_KEYS)
        self.assertNotIn("DB_HOSTNAME", MANIFEST.read_text())
        self.assertNotIn("RESTIC_PASSWORD", {env["name"] for env in restic["env"]})
        self.assertEqual(
            pod["affinity"]["podAffinity"]["requiredDuringSchedulingIgnoredDuringExecution"][0][
                "labelSelector"
            ]["matchLabels"],
            {"app.kubernetes.io/instance": "immich", "app.kubernetes.io/name": "server"},
        )
        library = next(volume for volume in pod["volumes"] if volume["name"] == "library")
        self.assertEqual(
            library["persistentVolumeClaim"], {"claimName": "immich-library", "readOnly": True}
        )
        mount = next(mount for mount in restic["volumeMounts"] if mount["name"] == "library")
        self.assertEqual(mount["mountPath"], "/usr/src/app/upload")
        self.assertTrue(mount["readOnly"])
        password = next(volume for volume in pod["volumes"] if volume["name"] == "restic-password")
        self.assertEqual(password["secret"]["secretName"], "immich-paired-backup")
        self.assertEqual(
            password["secret"]["items"], [{"key": "RESTIC_PASSWORD", "path": "RESTIC_PASSWORD"}]
        )
        password_mount = next(
            mount for mount in restic["volumeMounts"] if mount["name"] == "restic-password"
        )
        self.assertEqual(password_mount["subPath"], "RESTIC_PASSWORD")
        password_env = next(env for env in restic["env"] if env["name"] == "RESTIC_PASSWORD_FILE")
        self.assertEqual(password_env["value"], "/run/secrets/restic-password")


if __name__ == "__main__":
    unittest.main()


def test_script_digest_is_selected_by_kustomize():
    rendered = list(
        yaml.safe_load_all(
            subprocess.check_output(["kubectl", "kustomize", str(ROOT / "backup")], text=True)
        )
    )
    image = rendered[0]["spec"]["jobTemplate"]["spec"]["template"]["spec"]["initContainers"][0][
        "image"
    ]
    setting = yaml.safe_load((ROOT / "backup/kustomization.yaml").read_text())["images"][0]
    assert image == setting["newName"] + "@" + setting["digest"]
