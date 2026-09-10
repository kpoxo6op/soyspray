#!/usr/bin/env python3
"""Run node-2 recovery stages without Ansible CLI escape hatches."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
ANSIBLE_PLAYBOOK = ROOT / "soyspray-venv/bin/ansible-playbook"
INVENTORY = ROOT / "kubespray/inventory/soycluster/hosts.yml"
BASE = [
    str(ANSIBLE_PLAYBOOK),
    "-i",
    str(INVENTORY),
    "--become",
    "--become-user=root",
    "--user=ubuntu",
]


def require(parser: argparse.ArgumentParser, args: argparse.Namespace, *names: str) -> None:
    missing = [name.replace("_", "-") for name in names if not getattr(args, name)]
    if missing:
        parser.error("required for this stage: " + ", ".join(f"--{name}" for name in missing))


def invocation(playbook: str, variables: dict, *, check: bool) -> list[str]:
    command = [*BASE, str(ROOT / playbook)]
    if check:
        command.append("--check")
    command.extend(["-e", json.dumps(variables, separators=(",", ":"), sort_keys=True)])
    return command


def build_invocations(parser: argparse.ArgumentParser, args: argparse.Namespace) -> list[list[str]]:
    common = {"node2_recovery_git_revision": args.revision}
    if args.stage == "evacuate":
        require(parser, args, "revision", "run_id")
        return [
            invocation(
                "playbooks/operations/storage/evacuate-node2.yml",
                {**common, "node2_evacuation_run_id": args.run_id},
                check=not args.apply,
            )
        ]
    if args.stage in ("rollback-evacuation", "restore"):
        require(parser, args, "revision", "evacuation")
        mode = "pre-removal-rollback" if args.stage == "rollback-evacuation" else "post-rejoin"
        return [
            invocation(
                "playbooks/operations/storage/restore-node2-replicas.yml",
                {
                    **common,
                    "node2_evacuation_evidence_file": args.evacuation,
                    "node2_restore_mode": mode,
                },
                check=not args.apply,
            )
        ]
    if args.stage == "remove":
        require(
            parser,
            args,
            "revision",
            "evacuation",
            "snapshot",
            "snapshot_status",
            "snapshot_sha256",
            "backup_evidence",
            "immich_report",
        )
        evidence = {
            **common,
            "node2_removal_authorization": "destroy-node-2-retain-os-and-filesystems",
            "node2_evacuation_evidence_file": args.evacuation,
            "node2_etcd_snapshot_file": args.snapshot,
            "node2_etcd_snapshot_status_file": args.snapshot_status,
            "node2_etcd_snapshot_sha256": args.snapshot_sha256,
            "node2_backup_evidence_file": args.backup_evidence,
            "node2_immich_restore_report": args.immich_report,
        }
        commands = [
            invocation(
                "playbooks/operations/nodes/remove-node2.yml", evidence, check=not args.apply
            )
        ]
        if args.apply:
            commands.append(
                invocation(
                    "kubespray/remove-node.yml",
                    {
                        "node": "node-2",
                        "reset_nodes": True,
                        "allow_ungraceful_removal": False,
                        "skip_confirmation": True,
                        "flush_iptables": False,
                        "reset_restart_network": False,
                    },
                    check=False,
                )
            )
        return commands
    if args.stage == "clean":
        require(parser, args, "revision", "evacuation")
        return [
            invocation(
                "playbooks/operations/nodes/clean-node2-baseline.yml",
                {
                    **common,
                    "node2_baseline_cleanup_authorization": "clean-reset-node-2-cluster-state",
                    "node2_evacuation_evidence_file": args.evacuation,
                },
                check=not args.apply,
            )
        ]
    if args.stage == "rejoin":
        require(parser, args, "revision", "evacuation")
        return [
            invocation(
                "playbooks/operations/nodes/rejoin-node2.yml",
                {
                    **common,
                    "node2_rejoin_authorization": "rejoin-node-2-retained-os",
                    "node2_evacuation_evidence_file": args.evacuation,
                    "node2_rejoin_apply": args.apply,
                },
                check=not args.apply,
            )
        ]
    raise AssertionError(args.stage)


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser()
    result.add_argument(
        "stage", choices=("evacuate", "rollback-evacuation", "remove", "clean", "rejoin", "restore")
    )
    result.add_argument(
        "--apply", action="store_true", help="Apply this stage; the default is check mode."
    )
    result.add_argument("--revision")
    result.add_argument("--run-id")
    result.add_argument("--evacuation")
    result.add_argument("--snapshot")
    result.add_argument("--snapshot-status")
    result.add_argument("--snapshot-sha256")
    result.add_argument("--backup-evidence")
    result.add_argument("--immich-report")
    return result


def execute(commands: list[list[str]], runner=subprocess.run) -> int:
    for command in commands:
        completed = runner(command, cwd=ROOT, check=False)
        if completed.returncode:
            return completed.returncode
    return 0


def main() -> int:
    argument_parser = parser()
    args = argument_parser.parse_args()
    return execute(build_invocations(argument_parser, args))


if __name__ == "__main__":
    raise SystemExit(main())
