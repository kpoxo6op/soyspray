"""Select application checks from changed paths; shared checks always run."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path

APP_PATHS = {
    "immich": (
        "apps/immich/",
        "roles/apps/immich/",
        "playbooks/argocd/applications/media/immich/",
        "playbooks/argocd/applications/backups/immich-offsite-backup/",
    ),
    "boys": ("apps/boys/",),
    "autism": ("apps/autism-traits/",),
}
SHARED_CONTROLS = {
    "Makefile",
    "requirements-dev.txt",
    "requirements-ansible.yml",
    "ruff.toml",
    "scripts/ci_scope.py",
    "scripts/argo_preview.py",
    "scripts/app_command.py",
    "scripts/app_diff.py",
    "scripts/argocd_cli.py",
    "playbooks/bootstrap-apps.yml",
    "playbooks/operations/recovery/restore-volume.yml",
    "playbooks/operations/recovery/cleanup-restore.yml",
}


def select(paths, full=False):
    all_apps = full or any(
        path in SHARED_CONTROLS or path.startswith((".github/workflows/", "argocd/"))
        for path in paths
    )
    return {
        app: all_apps or any(path.startswith(prefixes) for path in paths)
        for app, prefixes in APP_PATHS.items()
    }


def changed_paths(base):
    if not base:
        return None
    try:
        revision = subprocess.run(
            ["git", "rev-parse", "--verify", "--end-of-options", f"{base}^{{commit}}"],
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        ).stdout.strip()
        result = subprocess.run(
            ["git", "diff", "--name-only", "--no-renames", "-z", revision, "HEAD", "--"],
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return [path for path in result.stdout.split("\0") if path]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base")
    parser.add_argument("--full", action="store_true")
    args = parser.parse_args()
    paths = changed_paths(args.base) if not args.full else []
    result = select(paths or [], full=args.full or paths is None)
    if os.environ.get("GITHUB_OUTPUT"):
        with Path(os.environ["GITHUB_OUTPUT"]).open("a") as output:
            for app, required in result.items():
                output.write(f"{app}={str(required).lower()}\n")
    print(json.dumps({"checks": result, "full": all(result.values())}))


if __name__ == "__main__":
    main()
