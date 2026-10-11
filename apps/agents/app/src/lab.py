#!/usr/bin/env python3
"""Offline, deterministic agent practice. Git subprocesses never use a remote."""

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

MARKER = ".agent-workshop-owner.json"


def command(root, *args, expected=0):
    result = subprocess.run(
        args,
        cwd=root,
        text=True,
        capture_output=True,
        env={**os.environ, "GIT_CONFIG_NOSYSTEM": "1", "GIT_TERMINAL_PROMPT": "0"},
    )
    if result.returncode != expected:
        raise RuntimeError(f"{args[0]} failed ({result.returncode}): {result.stderr[:200]}")
    return result.stdout.strip()


def ownership(root, create=False):
    if not root.is_absolute() or root == Path(root.anchor) or root == Path.home():
        raise RuntimeError(
            "Choose a dedicated absolute lab directory, not home or a filesystem root"
        )
    for part in [root, *root.parents]:
        if part.is_symlink():
            raise RuntimeError("Symlink in lab path")
        if (part / ".git").exists():
            remotes = command(part, "git", "remote")
            if remotes:
                raise RuntimeError("Repository with a remote is outside lab scope")
    marker = root / MARKER
    if root.exists():
        if not marker.is_file() or marker.is_symlink():
            raise RuntimeError("Existing directory is not owned by this lab")
        record = json.loads(marker.read_text())
        if record != {"version": 1, "path": str(root), "uid": os.getuid()}:
            raise RuntimeError("Lab ownership marker mismatch")
    elif create:
        if not root.parent.is_dir():
            raise RuntimeError("Lab parent must already exist")
        root.mkdir(mode=0o700)
        marker.write_text(json.dumps({"version": 1, "path": str(root), "uid": os.getuid()}))
    else:
        raise RuntimeError("Lab does not exist")
    # Refuse foreign/remotely connected repositories anywhere in an existing lab.
    if any(p.is_symlink() for p in root.rglob("*")):
        raise RuntimeError("Symlink inside owned lab; no writes permitted")
    for gitdir in root.rglob(".git"):
        if gitdir.is_symlink():
            raise RuntimeError("Symlinked Git metadata")
        if command(gitdir.parent, "git", "remote"):
            raise RuntimeError("Lab contains a repository with a remote")


def run(root):
    ownership(root, create=True)
    print("PREFLIGHT: owned root; no symlinks or Git remotes; stub agents only")
    repo = root / "repo"
    if repo.exists():
        # Only our disposable repo is reset; evidence logs are retained until this run finishes.
        shutil.rmtree(repo)
    for child in ("wt-a", "wt-b", "claims"):
        path = root / child
        if path.exists():
            if path.is_symlink():
                raise RuntimeError("Unexpected symlink in lab")
            shutil.rmtree(path)
    repo.mkdir()
    command(repo, "git", "init", "-q", "-b", "main")
    command(repo, "git", "config", "--local", "user.name", "lab")
    command(repo, "git", "config", "--local", "user.email", "lab@example.invalid")
    (repo / "config.txt").write_text("greeting=hi\n")
    (repo / "app.sh").write_text("cut -d= -f2 config.txt\n")
    command(repo, "git", "add", ".")
    command(repo, "git", "commit", "-qm", "init")
    results = []
    results.append({"step": "preflight", "result": "owned scratch repository; no remote"})
    print("WORKTREES: git worktree add; independent edits; git merge reports a conflict")
    command(repo, "git", "worktree", "add", "-q", str(root / "wt-a"), "-b", "agent-a")
    command(repo, "git", "worktree", "add", "-q", str(root / "wt-b"), "-b", "agent-b")
    for agent, greeting in [("a", "hi there"), ("b", "hello")]:
        tree = root / f"wt-{agent}"
        (tree / "config.txt").write_text(f"greeting={greeting}\n")
        command(tree, "git", "commit", "-qam", f"agent-{agent}: deterministic edit")
    command(repo, "git", "merge", "-q", "agent-a")
    command(repo, "git", "merge", "agent-b", expected=1)
    unmerged = command(repo, "git", "diff", "--name-only", "--diff-filter=U")
    if unmerged != "config.txt":
        raise RuntimeError("Expected integration conflict was not observed")
    command(repo, "git", "merge", "--abort")
    results.append({"step": "worktrees", "result": "CONFLICT-SURFACED: config.txt"})
    print("VERIFICATION: sh check.sh proves PASS on baseline and FAIL on a known-bad branch")
    # Restore the baseline so later exercises do not inherit an intentional conflicting edit.
    command(repo, "git", "reset", "--hard", "HEAD~1")
    (repo / "check.sh").write_text('set -eu\nvalue=$(sh app.sh)\n[ "$value" = hi ] && echo PASS\n')
    command(repo, "git", "add", "check.sh")
    command(repo, "git", "commit", "-qm", "user-boundary check")
    if command(repo, "sh", "check.sh") != "PASS":
        raise RuntimeError("Baseline user path failed")
    command(repo, "git", "switch", "-q", "-c", "agent-c")
    (repo / "config.txt").write_text("greeting=hey\n")
    command(repo, "git", "commit", "-qam", "claims fixed; deliberately wrong")
    command(repo, "sh", "check.sh", expected=1)
    command(repo, "git", "switch", "-q", "main")
    results.append(
        {"step": "verification", "result": "PASS baseline; REJECT claimed but wrong change"}
    )
    print("FEATURE MAP: check listed paths exist; billing.sh is the known stale entry")
    mapping = [("greeting", "config.txt"), ("app", "app.sh"), ("billing", "billing.sh")]
    (repo / "feature-map.txt").write_text("".join(f"{name}|{path}\n" for name, path in mapping))
    stale = [path for _, path in mapping if not (repo / path).exists()]
    if stale != ["billing.sh"]:
        raise RuntimeError("Feature-map check did not detect missing user path")
    results.append({"step": "feature-map", "result": "STALE: billing.sh; real paths exist"})
    print("BOUNDARY: execute check-boundary.py; allowed import passes, shortcut fails")
    (repo / "main").mkdir()
    (repo / "renderer").mkdir()
    (repo / "main/heavy.sh").write_text("echo heavy-work\n")
    (repo / "renderer/view.sh").write_text("echo draw\n")
    check = repo / "check-boundary.py"
    check.write_text(
        "from pathlib import Path\nimport sys\nbad=any('main/' in p.read_text() for p in Path('renderer').glob('*.sh'))\nprint('FAIL-boundary' if bad else 'PASS-boundary')\nsys.exit(1 if bad else 0)\n"
    )
    command(repo, sys.executable, str(check))
    (repo / "renderer/view.sh").write_text(". ../main/heavy.sh\necho draw\n")
    command(repo, sys.executable, str(check), expected=1)
    results.append({"step": "boundary", "result": "PASS allowed path; BLOCKED shortcut import"})
    print("RETRY: atomic mkdir claims/R7 succeeds once; repeated claim is skipped")
    claims = root / "claims"
    claims.mkdir()
    claim = claims / "R7"
    claim.mkdir()
    try:
        claim.mkdir()
    except FileExistsError:
        pass
    else:
        raise RuntimeError("Atomic claim allowed duplicate work")
    results.append({"step": "retry", "result": "claimed:R7 then skip:R7; one claim"})
    print("PROMOTION: git diff main promote -- contains only promotion.json")
    command(repo, "git", "switch", "-q", "-c", "promote")
    (repo / "promotion.json").write_text(
        json.dumps({"image": "sha256:offline-stub", "humanApproval": "required"})
    )
    command(repo, "git", "add", "promotion.json")
    command(repo, "git", "commit", "-qm", "separate human promotion rehearsal")
    command(repo, "git", "switch", "-q", "main")
    if command(repo, "git", "diff", "--name-only", "main", "promote", "--") != "promotion.json":
        raise RuntimeError("Promotion contains a source change")
    results.append({"step": "promotion", "result": "promotion.json only; source main unchanged"})
    (root / "results.json").write_text(json.dumps({"offline": True, "steps": results}, indent=2))
    verify(root)


def verify(root):
    ownership(root)
    repo = root / "repo"
    results = json.loads((root / "results.json").read_text())
    if len(results["steps"]) != 7 or command(repo, "sh", "check.sh") != "PASS":
        raise RuntimeError("Lab verification failed")
    if command(repo, "git", "diff", "--name-only", "main", "promote", "--") != "promotion.json":
        raise RuntimeError("Promotion boundary failed")
    print(json.dumps(results, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["run", "verify", "cleanup"])
    parser.add_argument("--root", required=True)
    args = parser.parse_args()
    root = Path(os.path.abspath(os.path.expanduser(args.root)))
    if args.action == "run":
        run(root)
    elif args.action == "verify":
        verify(root)
    else:
        ownership(root)
        shutil.rmtree(root)
        print("Removed the owned lab root only")


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, ValueError, OSError) as error:
        print(f"STOP: {error}", file=sys.stderr)
        sys.exit(1)
