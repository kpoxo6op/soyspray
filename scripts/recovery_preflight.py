"""Validate the minimal installed recovery runtime and selected Git source."""

import argparse
import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path

from scripts.app_command import command as app_command

ROOT = Path(__file__).resolve().parents[1]
COMMON_PLAYBOOKS = (
    "playbooks/operations/recovery/restore-volume.yml",
    "playbooks/operations/recovery/cleanup-restore.yml",
    "playbooks/operations/recovery/validate-durable.yml",
)
PYTHON_MODULES = ("ansible", "bcrypt", "cryptography", "jmespath", "netaddr", "passlib", "yaml")


def run(argv, root=ROOT):
    return subprocess.run(argv, cwd=root, capture_output=True, text=True, check=False)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def command(root, apps):
    return [
        str(Path(root) / "soyspray-venv/bin/python"),
        "-m",
        "scripts.recovery_preflight",
        *[value for app in apps for value in ("--app", app)],
    ]


def operation_sources(apps):
    return [
        "scripts/restore_durable.py" if app == "durable" else f"apps/{app}/Makefile" for app in apps
    ]


def validate(root, apps, runner=run, is_file=lambda path: path.is_file()):
    root = Path(root).resolve()
    head = runner(["git", "rev-parse", "HEAD"], root)
    main = runner(["git", "rev-parse", "origin/main"], root)
    status = runner(["git", "status", "--porcelain", "--untracked-files=no"], root)
    require(
        head.returncode == 0 and main.returncode == 0, "The selected Git revision is unavailable."
    )
    require(
        head.stdout.strip() == main.stdout.strip(),
        "Recovery requires the exact delivered main revision.",
    )
    require(
        status.returncode == 0 and not status.stdout.strip(), "Recovery source has tracked changes."
    )

    required = [
        "requirements-recovery.txt",
        "requirements-ansible.yml",
        "scripts/restore_common.py",
        *COMMON_PLAYBOOKS,
        *operation_sources(apps),
    ]
    inventory = "kubespray/inventory/soycluster/hosts.yml"
    tracked = runner(["git", "ls-files", "--error-unmatch", "--", *required], root)
    inventory_tracked = runner(
        [
            "git",
            "-C",
            "kubespray",
            "ls-files",
            "--error-unmatch",
            "--",
            "inventory/soycluster/hosts.yml",
        ],
        root,
    )
    require(tracked.returncode == 0, "A required recovery source file is not tracked.")
    require(
        inventory_tracked.returncode == 0,
        "The recovery inventory is not tracked by the pinned Kubespray source.",
    )
    require(
        all(is_file(root / path) for path in [*required, inventory]),
        "A recovery source file is missing.",
    )

    require(
        all(shutil.which(tool) for tool in ("git", "kubectl", "ssh")),
        "A recovery command is missing.",
    )
    for tool in ("ansible-playbook", "ansible-vault"):
        require(is_file(root / "soyspray-venv/bin" / tool), f"The recovery runtime lacks {tool}.")
    require(
        all(importlib.util.find_spec(module) is not None for module in PYTHON_MODULES),
        "A pinned recovery Python dependency is missing.",
    )
    for app in apps:
        if app != "durable":
            app_command(app, "restore-check", str(root / "soyspray-venv/bin/python"), root=root)

    syntax = runner(
        [
            str(root / "soyspray-venv/bin/ansible-playbook"),
            "--syntax-check",
            "-i",
            "kubespray/inventory/soycluster/hosts.yml",
            *COMMON_PLAYBOOKS,
        ],
        root,
    )
    require(syntax.returncode == 0, "Recovery playbook syntax validation failed.")
    return head.stdout.strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app", action="append", required=True)
    args = parser.parse_args()
    try:
        revision = validate(ROOT, args.app)
    except ValueError as error:
        parser.exit(2, f"unsafe: {error}\n")
    print(f"Recovery preflight passed for {revision}.")


if __name__ == "__main__":
    sys.exit(main())
