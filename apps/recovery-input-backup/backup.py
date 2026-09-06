"""Back up and restore-check explicit node configuration and unique voice models."""

import hashlib
import json
import os
import shutil
import signal
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
MODELS = ("gi-v7.tflite", "gi-v2.tflite")


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def interrupted(signum, frame):
    raise InterruptedError("The backup was interrupted")


def main():
    signal.signal(signal.SIGTERM, interrupted)
    os.umask(0o077)
    started = datetime.now(timezone.utc)
    state = Path.home() / ".local/state/soyspray/recovery-input-backup"
    state.mkdir(parents=True, exist_ok=True, mode=0o700)
    report = {"started_at": started.isoformat(), "status": "failed", "cleanup": "pending"}
    recovery = Path.home() / ".config/soyspray/recovery"
    try:
        credentials = subprocess.check_output(
            [
                str(ROOT / "soyspray-venv/bin/ansible-vault"),
                "view",
                "--vault-password-file",
                str(recovery / "vault-password"),
                str(recovery / "node-backup.vault.yml"),
            ],
            stderr=subprocess.PIPE,
            timeout=30,
        )
        env = {
            **os.environ,
            **yaml.safe_load(credentials)["node_backup_credentials"],
            "RESTIC_CACHE_DIR": str(state / "cache"),
        }

        def restic(*args):
            return subprocess.run(
                [str(Path.home() / ".local/bin/restic"), *args],
                env=env,
                check=True,
                capture_output=True,
                text=True,
                timeout=900,
            ).stdout

        with tempfile.TemporaryDirectory(prefix="working-", dir=state) as temporary:
            work = Path(temporary)
            stage = work / "inputs"
            stage.mkdir()
            subprocess.run(
                [
                    str(ROOT / "soyspray-venv/bin/ansible-playbook"),
                    "-i",
                    "kubespray/inventory/soycluster/hosts.yml",
                    "--become",
                    "--become-user=root",
                    "--user",
                    "ubuntu",
                    "apps/recovery-input-backup/collect.yml",
                    "-e",
                    "recovery_input_stage=" + str(stage),
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                timeout=180,
            )
            voice = stage / "voice"
            voice.mkdir()
            source = Path.home() / "pCloudDrive/docs/soyspray/home-assistant-voice"
            for name in MODELS:
                original = source / name
                if original.read_bytes()[4:8] != b"TFL3":
                    raise ValueError("Expected the existing TFLite model format")
                shutil.copyfile(original, voice / name)
                if digest(original) != digest(voice / name):
                    raise ValueError("The model changed while being collected")
            for node in ("node-0", "node-1", "node-2"):
                if (stage / "nodes" / node / "hostname").read_text().strip() != node:
                    raise ValueError("The collected node identity differs")
            files = {
                str(p.relative_to(stage)): {"sha256": digest(p), "bytes": p.stat().st_size}
                for p in stage.rglob("*")
                if p.is_file()
            }
            if len(files) != 14:
                raise ValueError("The explicit input set is incomplete")
            (stage / "manifest.json").write_text(json.dumps(files, indent=2))
            output = restic(
                "backup",
                "--retry-lock",
                "5m",
                "--json",
                "--host",
                "soyspray-recovery-inputs",
                "--tag",
                "recovery-inputs",
                str(stage),
            )
            summary = [
                json.loads(line)
                for line in output.splitlines()
                if json.loads(line).get("message_type") == "summary"
            ]
            if len(summary) != 1:
                raise ValueError("Missing snapshot summary")
            snapshot = summary[0]["snapshot_id"]
            restored = work / "restored"
            restic("restore", snapshot, "--target", str(restored))
            manifests = list(restored.rglob("manifest.json"))
            if len(manifests) != 1 or json.loads(manifests[0].read_text()) != files:
                raise ValueError("Restored manifest differs")
            base = manifests[0].parent
            for name, expected in files.items():
                path = base / name
                if digest(path) != expected["sha256"] or path.stat().st_size != expected["bytes"]:
                    raise ValueError("Restored input differs")
            restic(
                "forget",
                "--retry-lock",
                "5m",
                "--host",
                "soyspray-recovery-inputs",
                "--tag",
                "recovery-inputs",
                "--group-by",
                "host",
                "--keep-daily",
                "30",
                "--prune",
            )
            report.update(
                status="passed", snapshot=snapshot, verified_files=files, restored_real_content=True
            )
        report["cleanup"] = "completed"
    except BaseException as error:
        report["cause"] = type(error).__name__ + ": " + str(error)
    if not list(state.glob("working-*")):
        report["cleanup"] = "completed"
    report["finished_at"] = datetime.now(timezone.utc).isoformat()
    path = state / (started.strftime("%Y%m%d%H%M%S") + ".json")
    path.write_text(json.dumps(report, indent=2) + "\n")
    print(
        json.dumps({"report": str(path), "status": report["status"], "cleanup": report["cleanup"]})
    )
    return 0 if report["status"] == "passed" and report["cleanup"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
