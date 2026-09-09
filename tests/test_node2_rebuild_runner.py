import importlib.util
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "playbooks/operations/nodes/run-node2-rebuild.py"
SPEC = importlib.util.spec_from_file_location("node2_rebuild_runner", SCRIPT)
runner = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(runner)


def args(*values: str):
    return runner.parser().parse_args(values)


def test_remove_runs_guarded_preflight_before_exact_native_removal() -> None:
    parsed = args(
        "remove",
        "--apply",
        "--revision",
        "a" * 40,
        "--evacuation",
        "/private/evacuation.json",
        "--snapshot",
        "/private/etcd.db",
        "--snapshot-status",
        "/private/etcd.json",
        "--snapshot-sha256",
        "b" * 64,
        "--backup-evidence",
        "/private/backups.jsonl",
        "--immich-report",
        "/private/immich.json",
    )
    commands = runner.build_invocations(runner.parser(), parsed)
    assert len(commands) == 2
    assert commands[0][6].endswith("playbooks/operations/nodes/remove-node2.yml")
    assert commands[1][6].endswith("kubespray/remove-node.yml")
    native = commands[1][-1]
    assert '"node":"node-2"' in native
    assert '"allow_ungraceful_removal":false' in native
    assert '"flush_iptables":false' in native
    assert '"reset_restart_network":false' in native
    assert '"reset_nodes":true' in native


def test_runner_never_emits_cli_escape_hatches() -> None:
    parsed = args("evacuate", "--revision", "a" * 40, "--run-id", "20260909T000000Z-aaaaaaa")
    command = runner.build_invocations(runner.parser(), parsed)[0]
    joined = " ".join(command)
    assert "--check" in command
    assert "--limit" not in joined
    assert "--tags" not in joined
    assert "--skip-tags" not in joined
    assert "--start-at-task" not in joined


def test_pre_removal_rollback_restores_the_old_node_identity() -> None:
    parsed = args(
        "rollback-evacuation",
        "--apply",
        "--revision",
        "a" * 40,
        "--evacuation",
        "/private/evacuation.json",
    )
    command = runner.build_invocations(runner.parser(), parsed)[0]
    assert '"node2_restore_mode":"pre-removal-rollback"' in command[-1]
    assert "--check" not in command


def test_failed_preflight_never_starts_native_removal() -> None:
    calls = []

    def fail_first(command, **kwargs):
        calls.append(command)
        return subprocess.CompletedProcess(command, 2)

    result = runner.execute([["preflight"], ["native-remove"]], runner=fail_first)
    assert result == 2
    assert calls == [["preflight"]]
