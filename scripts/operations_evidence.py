"""Collect private backup evidence and expose numeric Prometheus metrics."""

from __future__ import annotations

import argparse
import json
import math
import os
import shlex
import shutil
import signal
import subprocess
import tempfile
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from shutil import which

import yaml

from scripts.restore_evidence import read_evidence

PROMETHEUS_RULE = "soyspray:critical_backup_age_seconds"
PROMETHEUS_URL = "http://10.233.4.158:9090/api/v1/query"
PROMETHEUS_SSH_HOST = "ubuntu@192.168.20.10"
RESTIC_PATH = "/home/boris/.local/bin/restic"
VAULT_FILE = "/home/boris/.config/soyspray/recovery/immich-backup.vault.yml"
VAULT_PASSWORD_FILE = "/home/boris/.config/soyspray/recovery/vault-password"
RESTORE_ROOT = Path.home() / ".local/state/soyspray/restores"
EVIDENCE_FILE = Path.home() / ".local/state/soyspray/evidence/operations.jsonl"
INTERVAL_SECONDS = 120
DEFAULT_BIND = "127.0.0.1"
DEFAULT_PORT = 9910
CRITICAL_BACKUPS = {
    "boys/boys-data": {"app_namespace": "boys", "pvc": "boys-data"},
    "obsidian/obsidian-livesync-couchdb-rescue-longhorn": {
        "app_namespace": "obsidian",
        "pvc": "obsidian-livesync-couchdb-rescue-longhorn",
    },
    "vaultwarden/vaultwarden-data": {"app_namespace": "vaultwarden", "pvc": "vaultwarden-data"},
}


def unknown(cause: str) -> dict:
    return {"value": "unknown", "cause": cause}


def timestamp(value: object) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    return parsed if parsed.tzinfo else None


def iso_now() -> datetime:
    return datetime.now(timezone.utc)


def run_command(argv: list[str], *, env: dict[str, str] | None = None, timeout: int = 30):
    """Run one bounded child and kill its process group if it does not finish."""

    process = subprocess.Popen(
        argv,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
        start_new_session=True,
    )
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGTERM)
        try:
            stdout, stderr = process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            stdout, stderr = process.communicate()
        return subprocess.CompletedProcess(argv, 124, stdout, stderr)
    return subprocess.CompletedProcess(argv, process.returncode, stdout, stderr)


def _recording_rule(result: dict, now: datetime) -> dict:
    if result.get("status") != "success" or not isinstance(result.get("data"), dict):
        return {
            key: unknown("Prometheus returned no successful query result.")
            for key in CRITICAL_BACKUPS
        }
    rows = result["data"].get("result")
    if not isinstance(rows, list):
        return {
            key: unknown("Prometheus returned no vector for the critical backup rule.")
            for key in CRITICAL_BACKUPS
        }
    observed: dict[str, dict] = {}
    for row in rows:
        metric = row.get("metric", {})
        key = f"{metric.get('app_namespace', '')}/{metric.get('pvc', '')}"
        if key not in CRITICAL_BACKUPS or key in observed:
            continue
        value = row.get("value")
        try:
            sample_time = float(value[0])
            age = float(value[1])
        except (IndexError, TypeError, ValueError):
            continue
        if not math.isfinite(age) or age < 0 or not -30 <= now.timestamp() - sample_time <= 300:
            continue
        observed[key] = {"value": int(age), "source": PROMETHEUS_RULE}
    return {
        key: observed.get(
            key, unknown("Prometheus has no valid current value for this critical backup.")
        )
        for key in CRITICAL_BACKUPS
    }


def collect_prometheus(
    *,
    now: datetime,
    prometheus_url: str = PROMETHEUS_URL,
    ssh_host: str = PROMETHEUS_SSH_HOST,
    runner=run_command,
) -> dict:
    command = [
        "ssh",
        "-o",
        "BatchMode=yes",
        "-o",
        "ConnectTimeout=10",
        ssh_host,
        "curl",
        "--fail",
        "--silent",
        "--show-error",
        "--get",
        "--data-urlencode",
        f"query={PROMETHEUS_RULE}",
        prometheus_url,
    ]
    try:
        result = runner(command[:6] + [shlex.join(command[6:])], timeout=25)
        if result.returncode != 0:
            return {
                key: unknown(f"Prometheus query failed with exit status {result.returncode}.")
                for key in CRITICAL_BACKUPS
            }
        payload = json.loads(result.stdout)
        return _recording_rule(payload, now)
    except (OSError, TypeError, ValueError, json.JSONDecodeError):
        return {
            key: unknown("Prometheus observation could not be read from the node.")
            for key in CRITICAL_BACKUPS
        }


def _vault_credentials(
    *,
    vault_file: str = VAULT_FILE,
    vault_password_file: str = VAULT_PASSWORD_FILE,
    runner=run_command,
) -> dict:
    ansible_vault = (
        which("ansible-vault") or "/home/boris/code/soyspray/soyspray-venv/bin/ansible-vault"
    )
    if not Path(vault_file).is_file() or not Path(vault_password_file).is_file():
        raise ValueError("The private Immich Vault input is unavailable.")
    result = runner(
        [ansible_vault, "view", "--vault-password-file", vault_password_file, vault_file],
        timeout=20,
    )
    if result.returncode != 0:
        raise ValueError("The private Immich Vault input could not be decrypted.")
    values = yaml.safe_load(result.stdout)
    if not isinstance(values, dict):
        raise ValueError("The private Immich Vault input is not a mapping.")
    credentials = values.get("immich_restic_credentials", values.get("restic", values))
    if isinstance(credentials, dict) and isinstance(credentials.get("restic"), dict):
        credentials = credentials["restic"]
    required = {
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_DEFAULT_REGION",
        "RESTIC_REPOSITORY",
        "RESTIC_PASSWORD",
    }
    if (
        not isinstance(credentials, dict)
        or set(credentials) != required
        or any(not isinstance(value, str) or not value.strip() for value in credentials.values())
    ):
        raise ValueError("The private Immich Restic identity is incomplete.")
    return credentials


def collect_restic(
    *,
    now: datetime,
    restic_path: str = RESTIC_PATH,
    vault_file: str = VAULT_FILE,
    vault_password_file: str = VAULT_PASSWORD_FILE,
    runner=run_command,
) -> dict:
    try:
        credentials = _vault_credentials(
            vault_file=vault_file, vault_password_file=vault_password_file, runner=runner
        )
        if not Path(restic_path).is_file():
            return unknown("The pinned Restic binary is unavailable.")
        with tempfile.NamedTemporaryFile(mode="w", prefix="soyspray-restic-", delete=False) as key:
            key.write(credentials["RESTIC_PASSWORD"])
            key_path = Path(key.name)
        key_path.chmod(0o600)
        try:
            env = {
                "PATH": "/usr/bin:/bin",
                "AWS_ACCESS_KEY_ID": credentials["AWS_ACCESS_KEY_ID"],
                "AWS_SECRET_ACCESS_KEY": credentials["AWS_SECRET_ACCESS_KEY"],
                "AWS_DEFAULT_REGION": credentials["AWS_DEFAULT_REGION"],
                "RESTIC_REPOSITORY": credentials["RESTIC_REPOSITORY"],
                "RESTIC_PASSWORD_FILE": str(key_path),
                "RESTIC_CACHE_DIR": tempfile.mkdtemp(prefix="soyspray-restic-cache-"),
            }
            result = runner(
                [
                    restic_path,
                    "snapshots",
                    "--json",
                    "--host",
                    "immich",
                    "--tag",
                    "restore-candidate",
                ],
                env=env,
                timeout=45,
            )
        finally:
            key_path.unlink(missing_ok=True)
            shutil.rmtree(env["RESTIC_CACHE_DIR"], ignore_errors=True)
        if result.returncode != 0:
            return unknown(f"Restic snapshot query failed with exit status {result.returncode}.")
        snapshots = json.loads(result.stdout)
        if not isinstance(snapshots, list):
            return unknown("Restic returned no snapshot list.")
        candidates = []
        for snapshot in snapshots:
            point = timestamp(snapshot.get("time"))
            if (
                snapshot.get("hostname") == "immich"
                and "restore-candidate" in (snapshot.get("tags") or [])
                and "pending" not in (snapshot.get("tags") or [])
                and point is not None
                and point <= now
                and isinstance(snapshot.get("id"), str)
            ):
                candidates.append((point, snapshot))
        if not candidates:
            return unknown("Restic has no completed immich restore-candidate snapshot.")
        point, snapshot = max(candidates, key=lambda item: item[0])
        return {
            "value": {
                "snapshot_id": snapshot["id"],
                "dump_started_at": point.isoformat(),
                "age_seconds": int((now - point).total_seconds()),
            },
            "basis": "Restic snapshot time is the paired PostgreSQL dump start time.",
        }
    except (OSError, TypeError, ValueError, json.JSONDecodeError):
        return unknown("The private Restic observation could not be read.")


def _kubectl_json(args: list[str], *, runner=run_command) -> dict:
    result = runner(["kubectl", "--request-timeout=10s", *args], timeout=20)
    if result.returncode != 0:
        raise ValueError("Kubernetes identity observation failed.")
    value = json.loads(result.stdout)
    if not isinstance(value, dict):
        raise ValueError("Kubernetes returned an invalid identity observation.")
    return value


def collect_validated_restore(
    *,
    now: datetime,
    restore_root: str | Path = RESTORE_ROOT,
    runner=run_command,
) -> dict:
    try:
        claim = _kubectl_json(
            ["get", "pvc", "immich-library", "-n", "immich", "-o", "json"], runner=runner
        )
        if claim.get("status", {}).get("phase") != "Bound":
            return unknown("The Immich library claim is not currently Bound.")
        claim_uid = claim.get("metadata", {}).get("uid")
        volume_name = claim.get("spec", {}).get("volumeName")
        if not claim_uid or not volume_name:
            return unknown("The Immich library claim has no verified UID and volume binding.")
        pv = _kubectl_json(["get", "pv", volume_name, "-o", "json"], runner=runner)
        pv_uid = pv.get("metadata", {}).get("uid")
        if pv.get("spec", {}).get("claimRef", {}).get("uid") != claim_uid or not pv_uid:
            return unknown("The Immich library PVC and PV identities do not match.")
        evidence = read_evidence("immich", claim_uid, pv_uid, now, root=restore_root)
        value = evidence.get("value", {}) if isinstance(evidence, dict) else {}
        if not isinstance(value, dict):
            return unknown(
                evidence.get("cause", "No validated Immich restore report is available.")
            )
        success = value.get("last_success", {}).get("value")
        if success == "unknown" or not isinstance(success, dict):
            return unknown(
                value.get("last_success", {}).get(
                    "cause", "No validated Immich restore report is available."
                )
            )
        finished = timestamp(success.get("finished_at"))
        point = timestamp(success.get("recovery_point"))
        if finished is None or finished > now or (point is not None and point > finished):
            return unknown("The latest Immich restore report has no valid completion time.")
        return {
            "value": {
                "finished_at": finished.isoformat(),
                "recovery_point": point.isoformat() if point else None,
                "age_seconds": int((now - finished).total_seconds()),
            },
            "basis": "A private restore report matched to the current Immich PVC and PV UIDs.",
        }
    except (OSError, TypeError, ValueError, json.JSONDecodeError):
        return unknown("The Immich restore identity or private report could not be read.")


def collect_once(
    *,
    now: datetime | None = None,
    prometheus_url: str = PROMETHEUS_URL,
    ssh_host: str = PROMETHEUS_SSH_HOST,
    restic_path: str = RESTIC_PATH,
    vault_file: str = VAULT_FILE,
    vault_password_file: str = VAULT_PASSWORD_FILE,
    restore_root: str | Path = RESTORE_ROOT,
    runner=run_command,
) -> dict:
    now = now or iso_now()
    return {
        "schema_version": 1,
        "observed_at": now.isoformat(),
        "critical_backups": collect_prometheus(
            now=now, prometheus_url=prometheus_url, ssh_host=ssh_host, runner=runner
        ),
        "immich_restic": collect_restic(
            now=now,
            restic_path=restic_path,
            vault_file=vault_file,
            vault_password_file=vault_password_file,
            runner=runner,
        ),
        "immich_last_validated_restore": collect_validated_restore(
            now=now, restore_root=restore_root, runner=runner
        ),
    }


def append_record(path: str | Path, record: dict) -> None:
    destination = Path(path).expanduser()
    destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    destination.parent.chmod(0o700)
    descriptor = os.open(destination, os.O_APPEND | os.O_CREAT | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    destination.chmod(0o600)


def last_record(path: str | Path) -> dict | None:
    try:
        lines = Path(path).expanduser().read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    for line in reversed(lines):
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and value.get("schema_version") == 1:
            return value
    return None


def _labels(labels: dict[str, str]) -> str:
    return ",".join(
        f'{key}="{str(value).replace("\\", "\\\\").replace('"', '\\"')}"'
        for key, value in labels.items()
    )


def _metric(name: str, value: object, labels: dict[str, str] | None = None) -> str:
    suffix = f"{{{_labels(labels)}}}" if labels else ""
    return f"{name}{suffix} {value}"


def metrics_text(record: dict | None) -> str:
    lines = [
        "# HELP soyspray_critical_backup_age_seconds Age of the latest critical Longhorn backup.",
        "# TYPE soyspray_critical_backup_age_seconds gauge",
        "# HELP soyspray_critical_backup_observed Whether a current critical backup age was observed.",
        "# TYPE soyspray_critical_backup_observed gauge",
        "# HELP soyspray_critical_backup_observation_timestamp_seconds Time of the collector observation.",
        "# TYPE soyspray_critical_backup_observation_timestamp_seconds gauge",
        "# HELP soyspray_immich_restic_restore_candidate_age_seconds Age of the latest Immich Restic candidate.",
        "# TYPE soyspray_immich_restic_restore_candidate_age_seconds gauge",
        "# HELP soyspray_immich_restic_restore_candidate_observed Whether an Immich Restic candidate was observed.",
        "# TYPE soyspray_immich_restic_restore_candidate_observed gauge",
        "# HELP soyspray_immich_last_validated_restore_timestamp_seconds Completion time of the latest validated Immich restore.",
        "# TYPE soyspray_immich_last_validated_restore_timestamp_seconds gauge",
        "# HELP soyspray_immich_last_validated_restore_observed Whether a validated Immich restore was observed.",
        "# TYPE soyspray_immich_last_validated_restore_observed gauge",
    ]
    if not record:
        return "\n".join(lines) + "\n"
    observed_at = timestamp(record.get("observed_at"))
    if observed_at:
        lines.append(
            _metric(
                "soyspray_critical_backup_observation_timestamp_seconds", observed_at.timestamp()
            )
        )
    for key, labels in CRITICAL_BACKUPS.items():
        item = record.get("critical_backups", {}).get(
            key, unknown("No collector observation exists.")
        )
        known = isinstance(item.get("value"), (int, float)) and not isinstance(
            item.get("value"), bool
        )
        lines.append(_metric("soyspray_critical_backup_observed", int(known), labels))
        if known:
            lines.append(_metric("soyspray_critical_backup_age_seconds", item["value"], labels))
    restic = record.get("immich_restic", {})
    restic_value = restic.get("value") if isinstance(restic, dict) else None
    restic_known = isinstance(restic_value, dict) and isinstance(
        restic_value.get("age_seconds"), int
    )
    lines.append(_metric("soyspray_immich_restic_restore_candidate_observed", int(restic_known)))
    if restic_known:
        lines.append(
            _metric(
                "soyspray_immich_restic_restore_candidate_age_seconds",
                restic_value["age_seconds"],
            )
        )
    restore = record.get("immich_last_validated_restore", {})
    restore_value = restore.get("value") if isinstance(restore, dict) else None
    finished = (
        timestamp(restore_value.get("finished_at")) if isinstance(restore_value, dict) else None
    )
    lines.append(
        _metric("soyspray_immich_last_validated_restore_observed", int(finished is not None))
    )
    if finished:
        lines.append(
            _metric(
                "soyspray_immich_last_validated_restore_timestamp_seconds", finished.timestamp()
            )
        )
    return "\n".join(lines) + "\n"


class MetricsHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        if self.path != "/metrics":
            self.send_error(404)
            return
        body = self.server.metrics_supplier().encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; version=0.0.4")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args) -> None:
        return


def run_service(
    *,
    output: str | Path = EVIDENCE_FILE,
    interval: int = INTERVAL_SECONDS,
    bind: str = DEFAULT_BIND,
    port: int = DEFAULT_PORT,
    collector_kwargs: dict | None = None,
) -> None:
    state = {"record": last_record(output)}
    lock = threading.Lock()
    stop = threading.Event()
    server = ThreadingHTTPServer((bind, port), MetricsHandler)
    server.metrics_supplier = lambda: metrics_text(state["record"])
    collector_kwargs = collector_kwargs or {}

    def collect_loop() -> None:
        while not stop.is_set():
            try:
                record = collect_once(**collector_kwargs)
                append_record(output, record)
                with lock:
                    state["record"] = record
            except Exception:
                stop.set()
                threading.Thread(target=server.shutdown, daemon=True).start()
                raise
            stop.wait(interval)

    worker = threading.Thread(target=collect_loop, name="evidence-collector", daemon=False)
    worker.start()

    def terminate(_signum, _frame) -> None:
        stop.set()
        threading.Thread(target=server.shutdown, daemon=True).start()

    signal.signal(signal.SIGTERM, terminate)
    signal.signal(signal.SIGINT, terminate)
    try:
        server.serve_forever()
    finally:
        stop.set()
        worker.join(timeout=max(interval, 30))
        server.server_close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true", help="Collect one record and exit.")
    parser.add_argument(
        "--output", default=os.environ.get("SOYSPRAY_EVIDENCE_OUTPUT", str(EVIDENCE_FILE))
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=int(os.environ.get("SOYSPRAY_EVIDENCE_INTERVAL", INTERVAL_SECONDS)),
    )
    parser.add_argument("--bind", default=os.environ.get("SOYSPRAY_EVIDENCE_BIND", DEFAULT_BIND))
    parser.add_argument(
        "--port", type=int, default=int(os.environ.get("SOYSPRAY_EVIDENCE_PORT", DEFAULT_PORT))
    )
    parser.add_argument(
        "--prometheus-url",
        default=os.environ.get("SOYSPRAY_EVIDENCE_PROMETHEUS_URL", PROMETHEUS_URL),
    )
    parser.add_argument(
        "--ssh-host",
        default=os.environ.get("SOYSPRAY_EVIDENCE_PROMETHEUS_SSH_HOST", PROMETHEUS_SSH_HOST),
    )
    parser.add_argument(
        "--restic-path", default=os.environ.get("SOYSPRAY_EVIDENCE_RESTIC_PATH", RESTIC_PATH)
    )
    parser.add_argument(
        "--vault-file", default=os.environ.get("SOYSPRAY_EVIDENCE_VAULT_FILE", VAULT_FILE)
    )
    parser.add_argument(
        "--vault-password-file",
        default=os.environ.get("SOYSPRAY_EVIDENCE_VAULT_PASSWORD_FILE", VAULT_PASSWORD_FILE),
    )
    parser.add_argument(
        "--restore-root",
        default=os.environ.get("SOYSPRAY_EVIDENCE_RESTORE_ROOT", str(RESTORE_ROOT)),
    )
    args = parser.parse_args(argv)
    if args.interval <= 0 or not 1 <= args.port <= 65535:
        parser.error("interval must be positive and port must be between 1 and 65535")
    collector_kwargs = {
        "prometheus_url": args.prometheus_url,
        "ssh_host": args.ssh_host,
        "restic_path": args.restic_path,
        "vault_file": args.vault_file,
        "vault_password_file": args.vault_password_file,
        "restore_root": args.restore_root,
    }
    if args.once:
        append_record(args.output, collect_once(**collector_kwargs))
    else:
        run_service(
            output=args.output,
            interval=args.interval,
            bind=args.bind,
            port=args.port,
            collector_kwargs=collector_kwargs,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
