"""Shared checks and lifecycle helpers for isolated Longhorn recovery operations."""

import contextlib
import fcntl
import json
import os
import re
import secrets
import signal
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

import yaml

from scripts.backup_status import has_backup_error, timestamp


def require(value, cause):
    if not value:
        raise ValueError(cause)


def select_backup(backups, volume, now, requested=None):
    candidates = []
    for backup in backups:
        state = backup.get("status", {})
        point = timestamp(state.get("snapshotCreatedAt"))
        if (
            state.get("volumeName") == volume
            and state.get("backupTargetName") == "critical-s3"
            and state.get("state") == "Completed"
            and state.get("progress") == 100
            and not has_backup_error(state)
            and point is not None
            and 0 < point.timestamp() <= now.timestamp()
            and state.get("url", "").startswith("s3://")
            and (requested is None or backup["metadata"]["name"] == requested)
        ):
            candidates.append(backup)
    require(candidates, "No eligible completed backup has a valid recovery point.")
    return max(candidates, key=lambda item: timestamp(item["status"]["snapshotCreatedAt"]))


def verify_binding(claim, volume):
    require(
        claim.get("status", {}).get("phase") == "Bound"
        and claim["spec"].get("storageClassName") == "longhorn"
        and volume["spec"].get("claimRef", {}).get("uid") == claim["metadata"]["uid"]
        and volume["spec"].get("csi", {}).get("driver") == "driver.longhorn.io"
        and volume["spec"]["csi"].get("volumeHandle") == claim["spec"]["volumeName"],
        "The original claim and Longhorn volume binding do not match.",
    )


def identity(item):
    return {"uid": item["metadata"]["uid"], "spec": item.get("spec")}


def save_report(output, report):
    temporary = output / "report.tmp"
    temporary.write_text(json.dumps(report, indent=2) + "\n")
    temporary.chmod(0o600)
    temporary.replace(output / "report.json")
    (output / "report.json").chmod(0o600)


class RestoreInterrupted(Exception):
    """The restore process received SIGTERM."""


def _process_identity(pid):
    try:
        fields = Path(f"/proc/{pid}/stat").read_text().rsplit(") ", 1)[1].split()
        return int(fields[2]), int(fields[3]), int(fields[19]), fields[0]
    except (OSError, IndexError, ValueError):
        return None


def _group_members(process_group, session):
    members = []
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        identity = _process_identity(int(entry.name))
        if identity is not None and identity[:2] == (process_group, session) and identity[3] != "Z":
            members.append((int(entry.name), identity))
    return members


def _signal_members(members, signum):
    for pid, expected in members:
        current = _process_identity(pid)
        if current is None or current[:3] != expected[:3] or current[3] == "Z":
            continue
        try:
            os.kill(pid, signum)
        except ProcessLookupError:
            pass


def _stop_process_group(process, process_group, session, leader_identity, grace_seconds=5):
    leader = _process_identity(process.pid)
    if leader is not None and leader_identity is not None and leader[:3] == leader_identity[:3]:
        try:
            os.killpg(process_group, signal.SIGTERM)
        except ProcessLookupError:
            pass
    else:
        _signal_members(_group_members(process_group, session), signal.SIGTERM)

    deadline = time.monotonic() + grace_seconds
    while True:
        members = _group_members(process_group, session)
        if not members or time.monotonic() >= deadline:
            break
        try:
            process.wait(timeout=min(0.1, deadline - time.monotonic()))
        except subprocess.TimeoutExpired:
            pass
        time.sleep(0.05)

    if members:
        leader = _process_identity(process.pid)
        if leader is not None and leader_identity is not None and leader[:3] == leader_identity[:3]:
            try:
                os.killpg(process_group, signal.SIGKILL)
            except ProcessLookupError:
                pass
        else:
            _signal_members(members, signal.SIGKILL)
    process.wait()


def run_process(args, **kwargs):
    termination_grace = kwargs.pop("termination_grace", 5)
    check = kwargs.pop("check", False)
    timeout = kwargs.pop("timeout", None)
    input_data = kwargs.pop("input", None)
    if kwargs.pop("capture_output", False):
        kwargs["stdout"] = subprocess.PIPE
        kwargs["stderr"] = subprocess.PIPE
    if input_data is not None:
        kwargs.setdefault("stdin", subprocess.PIPE)
    process = subprocess.Popen(args, start_new_session=True, **kwargs)
    process_group = os.getpgid(process.pid)
    session = os.getsid(process.pid)
    leader_identity = _process_identity(process.pid)
    try:
        stdout, stderr = process.communicate(input=input_data, timeout=timeout)
    except BaseException:
        _stop_process_group(process, process_group, session, leader_identity, termination_grace)
        raise
    result = subprocess.CompletedProcess(args, process.returncode, stdout, stderr)
    if check and result.returncode:
        raise subprocess.CalledProcessError(result.returncode, args, output=stdout, stderr=stderr)
    return result


def capture_output(args, **kwargs):
    kwargs.setdefault("stdout", subprocess.PIPE)
    return run_process(args, check=True, **kwargs).stdout


def _handle_sigterm(signum, frame):
    raise RestoreInterrupted


def preflight_command(root, state, run_id):
    if not run_id:
        return ["make", "go"]
    require(bool(re.fullmatch(r"[0-9]{14}-[0-9a-f]{4}", run_id)), "Invalid schedule run ID.")
    report = json.loads((state.parent / "schedule" / run_id / "report.json").read_text())
    require(
        report.get("run_id") == run_id
        and report.get("status") == "running"
        and report.get("shared_gate", {}).get("status") == "passed"
        and report.get("git_revision")
        == capture_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip(),
        "The scheduled full check did not pass for this revision.",
    )
    return ["make", "-o", "check", "go"]


class RestoreOperation:
    """Own the private workspace and common isolated restore lifecycle."""

    def __init__(self, app, root, vault_file, vault_password_file):
        self.app = app
        self.root = root
        self.vault_file = vault_file
        self.vault_password_file = vault_password_file
        self.started = datetime.now(timezone.utc)
        self.check_id = self.started.strftime("%Y%m%d%H%M%S") + "-" + secrets.token_hex(2)
        state_home = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state"))
        self.state = state_home / "soyspray/restores" / app
        self.output = self.state / self.check_id
        self.report = {
            "schema_version": 1,
            "app": app,
            "check_id": self.check_id,
            "started_at": self.started.isoformat(),
            "status": "running",
            "cleanup": "not started",
        }
        self.stage = "preflight"
        self.created_output = False
        self.lock = None
        self.workspace = None
        self.work = None
        self.env = None

    @staticmethod
    def now():
        return datetime.now(timezone.utc)

    def prepare(self):
        require(
            not self.output.resolve().is_relative_to(self.root),
            "Restore evidence must stay outside the checkout.",
        )
        self.output.mkdir(mode=0o700, parents=True)
        self.created_output = True
        self.state.chmod(0o700)
        lock_path = self.state / ".lock"
        self.lock = lock_path.open("a+")
        lock_path.chmod(0o600)
        try:
            fcntl.flock(self.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError(f"Another {self.app} restore check is running.") from None
        save_report(self.output, self.report)
        print(f"Checking {self.app} recovery. Private logs: {self.output}", flush=True)
        preflight_log = self.output / "preflight.log"
        with preflight_log.open("w") as log:
            preflight_log.chmod(0o600)
            run_process(
                preflight_command(
                    self.root, self.state, os.environ.get("SOYSPRAY_RESTORE_SCHEDULE_RUN_ID")
                ),
                cwd=self.root,
                stdout=log,
                stderr=subprocess.STDOUT,
                check=True,
                timeout=1200,
            )
        self.report["git_revision"] = capture_output(
            ["git", "rev-parse", "HEAD"], cwd=self.root, text=True
        ).strip()
        for path in (self.vault_file, self.vault_password_file):
            require(
                path.is_file() and not path.resolve().is_relative_to(self.root),
                "Use existing off-cluster Vault inputs and password files outside this checkout.",
            )
        require(
            self.vault_file.read_bytes().startswith(b"$ANSIBLE_VAULT;"),
            f"The {self.app} input file must use Ansible Vault encryption.",
        )
        self.workspace = tempfile.TemporaryDirectory(prefix="working-", dir=self.output)
        self.work = Path(self.workspace.name)
        config = capture_output(
            ["kubectl", "config", "view", "--raw", "--minify", "--flatten", "-o", "json"],
            timeout=20,
            stderr=subprocess.PIPE,
        )
        kubeconfig = self.work / "kubeconfig.json"
        kubeconfig.write_bytes(config)
        kubeconfig.chmod(0o600)
        self.env = {**os.environ, "KUBECONFIG": str(kubeconfig)}

    def kube(self, *args):
        return json.loads(
            capture_output(
                ["kubectl", "--request-timeout=15s", *args, "-o", "json"],
                env=self.env,
                stderr=subprocess.PIPE,
                timeout=30,
            )
        )

    def vault(self):
        return yaml.safe_load(
            capture_output(
                [
                    str(self.root / "soyspray-venv/bin/ansible-vault"),
                    "view",
                    "--vault-password-file",
                    str(self.vault_password_file.resolve()),
                    str(self.vault_file.resolve()),
                ],
                stderr=subprocess.PIPE,
                timeout=30,
            )
        )

    def run(self, args, **kwargs):
        kwargs.setdefault("env", self.env)
        return run_process(args, **kwargs)

    def ansible(self, playbook, variables, log_name):
        variable_file = self.work / "operation-inputs.json"
        variable_file.write_text(json.dumps(variables))
        variable_file.chmod(0o600)
        log_path = self.output / log_name
        with log_path.open("w") as log:
            log_path.chmod(0o600)
            run_process(
                [
                    str(self.root / "soyspray-venv/bin/ansible-playbook"),
                    "-i",
                    "kubespray/inventory/soycluster/hosts.yml",
                    "--become",
                    "--become-user=root",
                    "--user",
                    "ubuntu",
                    "playbooks/operations/recovery/" + playbook,
                    "-e",
                    "@" + str(variable_file),
                ],
                cwd=self.root,
                env=self.env,
                stdout=log,
                stderr=subprocess.STDOUT,
                check=True,
                timeout=3600,
            )

    @contextlib.contextmanager
    def isolated_restore(self, namespace, variables):
        self.report["scratch_namespace"] = namespace
        self.report["cleanup"] = "pending"
        save_report(self.output, self.report)
        print(f"Restoring {self.report['backup']['name']} into {namespace}.", flush=True)
        try:
            yield
        finally:
            try:
                self.ansible("cleanup-restore.yml", variables, "cleanup.log")
                self.report["cleanup"] = "completed"
            except BaseException:
                self.stage = "isolated resource cleanup"
                self.report["cleanup"] = "failed - inspect the guarded cleanup log"
                raise

    def fail(self, error):
        self.report["status"] = "failed"
        self.report["failed_stage"] = self.stage
        if isinstance(error, RestoreInterrupted):
            self.report["cause"] = "The restore operation was interrupted by SIGTERM."
        elif isinstance(error, ValueError):
            self.report["cause"] = str(error)
        elif isinstance(error, subprocess.CalledProcessError):
            self.report["cause"] = f"{Path(error.cmd[0]).name} failed with exit {error.returncode}."
        elif isinstance(error, subprocess.TimeoutExpired):
            self.report["cause"] = f"{Path(error.cmd[0]).name} exceeded its time limit."
        elif isinstance(error, OSError):
            self.report["cause"] = error.strerror
        else:
            self.report["cause"] = (
                "The operation did not complete because of an unexpected local error."
            )

    def finish(self):
        try:
            if self.workspace is not None:
                self.workspace.cleanup()
        except BaseException as error:
            self.stage = "private workspace cleanup"
            self.fail(error)
        try:
            if self.lock is not None:
                self.lock.close()
        except BaseException as error:
            self.stage = "restore lock cleanup"
            self.fail(error)
        self.report["finished_at"] = datetime.now(timezone.utc).isoformat()
        self.report["duration_seconds"] = int(
            (datetime.now(timezone.utc) - self.started).total_seconds()
        )
        if self.created_output:
            save_report(self.output, self.report)
        print(json.dumps(self.report, indent=2))
        return 0 if self.report["status"] == "passed" else 2


def run_restore(app, root, vault_file, vault_password_file, worker):
    operation = RestoreOperation(app, root, vault_file, vault_password_file)
    previous_sigterm = signal.getsignal(signal.SIGTERM)
    signal.signal(signal.SIGTERM, _handle_sigterm)
    try:
        operation.prepare()
        worker(operation)
        operation.report["status"] = "passed"
    except BaseException as error:
        operation.fail(error)
    try:
        return operation.finish()
    finally:
        signal.signal(signal.SIGTERM, previous_sigterm)
