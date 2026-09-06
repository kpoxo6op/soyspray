#!/usr/bin/env python3
"""Run the monthly isolated restore checks and retain a private JSON summary."""

import argparse
import fcntl
import json
import os
import secrets
import signal
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from scripts.restore_common import RestoreInterrupted, capture_output, run_process


def revision(root):
    return capture_output(["git", "rev-parse", "HEAD"], cwd=root, text=True, timeout=10).strip()


APPS = ("boys", "vaultwarden", "obsidian-livesync")
SHARED_GATE_TIMEOUT = 1800
RESTORE_TIMEOUT = 6 * 60 * 60
ROOT = Path(__file__).resolve().parents[1]


def now():
    return datetime.now(timezone.utc)


def save_report(path, report):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(report, indent=2) + "\n")
    temporary.chmod(0o600)
    temporary.replace(path)
    path.chmod(0o600)


def parse_report(output):
    decoder = json.JSONDecoder()
    for offset in reversed([index for index, value in enumerate(output) if value == "{"]):
        try:
            report, _ = decoder.raw_decode(output[offset:])
        except json.JSONDecodeError:
            continue
        if isinstance(report, dict) and {"app", "check_id", "status", "cleanup"} <= report.keys():
            return report
    return None


def report_files(state_home, app):
    return (state_home / "soyspray/restores" / app).glob("*/report.json")


def latest_report(state_home, app, started):
    candidates = []
    for path in report_files(state_home, app):
        try:
            report = json.loads(path.read_text())
            report_started = datetime.fromisoformat(report["started_at"])
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
            continue
        if report_started >= started and path.parent.name == report.get("check_id"):
            candidates.append((report_started, path, report))
    return max(candidates, default=None, key=lambda item: item[0])


def validate_app_report(app, run_id, command_started, command, returncode, stdout, state_home):
    found = latest_report(state_home, app, command_started)
    report = found[2] if found else None
    printed = parse_report(stdout)
    path = str(found[1]) if found else None
    result = {
        "run_id": run_id,
        "app": app,
        "command": command,
        "command_returncode": returncode,
        "report_path": path,
        "report_check_id": report.get("check_id") if report else None,
        "report_status": report.get("status") if report else None,
        "cleanup": report.get("cleanup") if report else None,
        "passed": bool(
            returncode == 0
            and report
            and report.get("app") == app
            and printed
            and printed.get("app") == app
            and printed.get("check_id") == report.get("check_id")
            and report.get("status") == "passed"
            and report.get("cleanup") == "completed"
        ),
    }
    if not result["passed"]:
        result["error"] = (
            "The restore command did not produce a passed report with completed cleanup."
        )
    return result


def run_command(command, cwd, env, timeout, log_path, runner=run_process):
    try:
        result = runner(
            command,
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
            termination_grace=900,
        )
    except subprocess.TimeoutExpired:
        log_path.write_text("The command exceeded its time limit.\n")
        log_path.chmod(0o600)
        return None, "timeout"
    except OSError:
        log_path.write_text("The command could not be started.\n")
        log_path.chmod(0o600)
        return None, "start failure"
    log_path.write_text(result.stdout + result.stderr)
    log_path.chmod(0o600)
    return result, None


def run_schedule(root, state_home, runner=run_process):
    started = now()
    run_id = started.strftime("%Y%m%d%H%M%S") + "-" + secrets.token_hex(2)
    state = state_home / "soyspray/restores/schedule"
    state.mkdir(mode=0o700, parents=True, exist_ok=True)
    state.chmod(0o700)
    output = state / run_id
    output.mkdir(mode=0o700)
    report_path = output / "report.json"
    report = {
        "schema_version": 1,
        "run_id": run_id,
        "started_at": started.isoformat(),
        "status": "running",
        "apps": [],
    }
    lock_path = state / ".monthly.lock"
    with lock_path.open("a+") as lock:
        lock_path.chmod(0o600)
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            report.update(status="failed", error="Another monthly restore schedule is running.")
            save_report(report_path, report)
            return report, 2
        try:
            save_report(report_path, report)
            env = {
                **os.environ,
                "XDG_STATE_HOME": str(state_home),
                "SOYSPRAY_RESTORE_SCHEDULE_RUN_ID": run_id,
            }
            gate_revision = revision(root)
            report["git_revision"] = gate_revision
            gate_command = ["make", "--no-print-directory", "full-check"]
            gate, gate_error = run_command(
                gate_command, root, env, SHARED_GATE_TIMEOUT, output / "shared-check.log", runner
            )
            report["shared_gate"] = {
                "command": gate_command,
                "returncode": gate.returncode if gate else None,
                "status": "passed" if gate and gate.returncode == 0 else "failed",
            }
            if gate_error or not gate or gate.returncode != 0:
                report.update(
                    status="failed",
                    error="The shared repository gate failed or exceeded its time limit.",
                )
                save_report(report_path, report)
                return report, 2

            save_report(report_path, report)
            for app in APPS:
                if revision(root) != gate_revision:
                    report.update(
                        status="failed", error="The checkout changed after the full gate."
                    )
                    save_report(report_path, report)
                    return report, 2
                command = [
                    "make",
                    "--no-print-directory",
                    "restore-check",
                    f"APP={app}",
                ]
                command_started = now()
                result, command_error = run_command(
                    command, root, env, RESTORE_TIMEOUT, output / f"{app}.log", runner
                )
                app_result = validate_app_report(
                    app,
                    run_id,
                    command_started,
                    command,
                    result.returncode if result else None,
                    result.stdout if result else "",
                    state_home,
                )
                if command_error:
                    app_result["error"] = (
                        "The restore command exceeded its time limit."
                        if command_error == "timeout"
                        else "The restore command could not be started."
                    )
                report["apps"].append(app_result)
                save_report(report_path, report)
                if not app_result["passed"] and app_result.get("cleanup") != "completed":
                    report["status"] = "failed"
                    report["error"] = (
                        "The schedule stopped because cleanup evidence was not complete."
                    )
                    save_report(report_path, report)
                    return report, 2

            report["status"] = (
                "passed" if all(item["passed"] for item in report["apps"]) else "failed"
            )
            save_report(report_path, report)
            return report, 0 if report["status"] == "passed" else 2
        finally:
            if report["status"] == "running":
                report.update(status="failed", error="The schedule was interrupted.")
            report["finished_at"] = now().isoformat()
            save_report(report_path, report)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument(
        "--state-home",
        type=Path,
        default=Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state")),
    )
    args = parser.parse_args()
    os.umask(0o077)

    def interrupted(signum, frame):
        raise RestoreInterrupted

    signal.signal(signal.SIGTERM, interrupted)
    try:
        report, code = run_schedule(args.root.resolve(), args.state_home.resolve())
    except (RestoreInterrupted, KeyboardInterrupt):
        print("Restore schedule interrupted; inspect its private report.")
        return 2
    print(json.dumps(report, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
