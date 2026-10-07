"""Back up and restore-check private recovery inputs, node configuration and unique voice models."""

import argparse
import base64
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
MODELS = {
    "gi-v7.tflite": (
        "openwakeword-gi-model-v7b",
        "e61dd9f2880f226b05b8f9885c053fa7ec7805170c3f3b4d56427c6294cb4be0",
    ),
    "gi-v2.tflite": (
        "openwakeword-gi-model-v2",
        "4b89c92d8500243404a77af30a7d8f8a618718403a355a3564e18108bc8f9739",
    ),
}


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def interrupted(signum, frame):
    raise InterruptedError("The backup was interrupted")


def live_model(configmap):
    value = subprocess.check_output(
        [
            "kubectl",
            "-n",
            "home-automation",
            "get",
            "configmap",
            configmap,
            "-o",
            "json",
        ],
        stderr=subprocess.PIPE,
        timeout=30,
    )
    return base64.b64decode(json.loads(value)["binaryData"]["gi.tflite"], validate=True)


def stable_models(seed=False):
    directory = Path.home() / ".config/soyspray/recovery/voice-models"
    if seed:
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    hashes = {}
    for name, (configmap, expected) in MODELS.items():
        active = live_model(configmap)
        if hashlib.sha256(active).hexdigest() != expected or active[4:8] != b"TFL3":
            raise ValueError(f"The live {name} model does not match its preservation contract")
        path = directory / name
        if seed and not path.exists():
            temporary = path.with_suffix(".tmp")
            temporary.write_bytes(active)
            temporary.chmod(0o600)
            temporary.replace(path)
        if not path.is_file() or digest(path) != expected:
            raise ValueError(f"The stable {name} recovery model is missing or differs")
        hashes[name] = {"active": expected, "stable": digest(path)}
    return directory, hashes


def local_inputs():
    """Explicit roots only: no CLI caches, source checkouts or browser state."""
    home = Path.home()
    roots = {
        "recovery": home / ".config/soyspray/recovery",
        "kubespray": ROOT / "inventory/soycluster/credentials",
        "kubeconfig": Path(os.environ.get("KUBECONFIG", home / ".kube/config")),
        "ssh/config": home / ".ssh/config",
        "ssh/known_hosts": home / ".ssh/known_hosts",
        "aws/config": home / ".aws/config",
    }
    if ":" in str(roots["kubeconfig"]):
        raise ValueError("Use a single recovery kubeconfig")
    config = yaml.safe_load(roots["kubeconfig"].read_text())
    for section, fields in (
        ("clusters", ("certificate-authority",)),
        ("users", ("client-certificate", "client-key")),
    ):
        for entry in config.get(section, []):
            for field in fields:
                value = entry[section[:-1]].get(field)
                if value:
                    source = Path(value).expanduser()
                    if not source.is_absolute():
                        source = roots["kubeconfig"].parent / source
                    roots[f"kube-files/{len(roots)}-{source.name}"] = source
    for node in ("192.168.20.10", "192.168.20.11", "192.168.20.12"):
        config = subprocess.check_output(
            ["ssh", "-G", f"ubuntu@{node}"], stderr=subprocess.PIPE, text=True, timeout=10
        )
        for line in config.splitlines():
            if line.startswith("identityfile "):
                source = Path(line.split(" ", 1)[1]).expanduser()
                if source.is_file():
                    roots[f"ssh/{source.name}"] = source
    if (home / ".aws/credentials").exists():
        roots["aws/credentials"] = home / ".aws/credentials"
    files = {}
    for label, root in roots.items():
        if not root.exists():
            raise ValueError("A required private input root is missing")
        candidates = sorted(root.rglob("*")) if root.is_dir() else [root]
        for source in candidates:
            if source.is_symlink():
                raise ValueError("Private input contains an unexpected symlink")
            if source.is_file():
                name = label + "/" + str(source.relative_to(root)) if root.is_dir() else label
                files[name] = source
    if not files or not any(name.startswith("kubespray/") for name in files):
        raise ValueError("Private Kubespray inputs are missing")
    return files


def stage_local_inputs(stage, originals):
    fingerprints = {}
    for name, source in originals.items():
        before = digest(source)
        destination = stage / "local" / name
        destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        shutil.copyfile(source, destination)
        destination.chmod(0o600)
        if digest(source) != before or digest(destination) != before:
            raise ValueError("A private input changed while being collected")
        fingerprints[name] = before
    return fingerprints


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed-models", action="store_true")
    args = parser.parse_args()
    signal.signal(signal.SIGTERM, interrupted)
    os.umask(0o077)
    model_source, model_hashes = stable_models(seed=args.seed_models)
    if args.seed_models:
        print(json.dumps({"model_hashes": model_hashes, "status": "passed"}))
        return 0
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
                    "inventory/soycluster/hosts.yml",
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
            originals = local_inputs()
            original_hashes = stage_local_inputs(stage, originals)
            voice = stage / "voice"
            voice.mkdir()
            for name in MODELS:
                original = model_source / name
                if original.read_bytes()[4:8] != b"TFL3":
                    raise ValueError("Expected the existing TFLite model format")
                shutil.copyfile(original, voice / name)
                if digest(original) != digest(voice / name):
                    raise ValueError("The model changed while being collected")
                model_hashes[name]["backed_up"] = digest(voice / name)
            for node in ("node-0", "node-1", "node-2"):
                if (stage / "nodes" / node / "hostname").read_text().strip() != node:
                    raise ValueError("The collected node identity differs")
            files = {
                str(p.relative_to(stage)): {"sha256": digest(p), "bytes": p.stat().st_size}
                for p in stage.rglob("*")
                if p.is_file()
            }
            if len([name for name in files if name.startswith("nodes/")]) != 12:
                raise ValueError("The node input set is incomplete")
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
            base = restored / stage.relative_to(stage.anchor)
            if json.loads((base / "manifest.json").read_text()) != files:
                raise ValueError("Restored manifest differs")
            for name, expected in files.items():
                path = base / name
                if digest(path) != expected["sha256"] or path.stat().st_size != expected["bytes"]:
                    raise ValueError("Restored input differs")
            for name, source in originals.items():
                if digest(source) != original_hashes[name]:
                    raise ValueError("An original private input changed before verification")
                if digest(base / "local" / name) != original_hashes[name]:
                    raise ValueError("Restored private input differs from its original")
            for name in MODELS:
                model_hashes[name]["restored"] = digest(base / "voice" / name)
                if len(set(model_hashes[name].values())) != 1:
                    raise ValueError(
                        f"The active, stable, backed-up, and restored {name} hashes differ"
                    )
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
                status="passed",
                snapshot=snapshot,
                verified_files=files,
                model_hashes=model_hashes,
                restored_real_content=True,
                original_checksum_matches=len(originals),
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
