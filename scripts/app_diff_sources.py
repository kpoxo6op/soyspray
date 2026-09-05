"""Resolve pushed native Git and chart revisions without changing an Application."""

import copy
import re
import subprocess

import yaml


def revision_arguments(live, desired, repo, commit):
    """Revision overrides cannot change value paths, parameters, or deployment policy."""
    before, after = copy.deepcopy(live["spec"]), copy.deepcopy(desired["spec"])
    if before.get("source") and after.get("source"):
        old, new = before["source"], after["source"]
        if (
            before.get("sources")
            or after.get("sources")
            or new.get("repoURL") != repo
            or not new.get("path")
            or new.get("chart")
            or new.get("targetRevision") != "HEAD"
        ):
            raise ValueError("Single-source comparison needs this repository's Git path at HEAD.")
        old.pop("targetRevision", None)
        new.pop("targetRevision", None)
        if before != after:
            raise ValueError(
                "Application settings changed; revision-only comparison cannot apply new "
                "source paths, parameters, destination, project, or policy. Review these separately."
            )
        return ["--revision", commit]
    old_sources, new_sources = before.get("sources", []), after.get("sources", [])
    if before.get("source") or after.get("source") or len(new_sources) < 2:
        raise ValueError("Pushed comparison needs native chart and Git values sources.")
    if len(old_sources) != len(new_sources):
        raise ValueError("Source membership changed; revision-only comparison cannot render it.")
    args = []
    charts = git_sources = 0
    for position, (old, new) in enumerate(zip(old_sources, new_sources, strict=True), 1):
        revision = new.get("targetRevision", "")
        if new.get("chart"):
            if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+(?:[-+][A-Za-z0-9.-]+)?", revision):
                raise ValueError("Chart versions must be explicitly pinned.")
            charts += 1
        elif new.get("repoURL") == repo and new.get("ref") and not new.get("path"):
            if revision != "HEAD":
                raise ValueError(
                    "Declare Git values at HEAD; the comparison uses this pushed commit."
                )
            revision = commit
            git_sources += 1
        else:
            raise ValueError(
                "Only upstream charts and this repository as a Git values source are supported."
            )
        args.extend(["--source-positions", str(position), "--revisions", revision])
        old.pop("targetRevision", None)
        new.pop("targetRevision", None)
    # Argo drops these false fields when serializing Applications.
    for spec in (before, after):
        automated = spec.get("syncPolicy", {}).get("automated", {})
        for key in ("prune", "allowEmpty"):
            if automated.get(key) is False:
                automated.pop(key)
    if not charts or not git_sources or before != after:
        raise ValueError(
            "Application settings changed; revision-only comparison cannot render the proposed "
            "source paths, Helm parameters, destination, project, or policy. Review these separately."
        )
    return args


def pushed_sources(app, live, root):
    def git(*args):
        return subprocess.check_output(["git", *args], cwd=root, text=True, timeout=30).strip()

    if git("status", "--porcelain"):
        raise ValueError("Commit and push the working tree before comparing workloads.")
    commit = git("rev-parse", "HEAD")
    branch = git("symbolic-ref", "--short", "HEAD")
    declaration = yaml.safe_load((root / "argocd/bootstrap/application.yaml").read_text())
    repo = declaration["spec"]["source"]["repoURL"]
    remote = git("ls-remote", "--exit-code", "--heads", repo, f"refs/heads/{branch}")
    if remote != f"{commit}\trefs/heads/{branch}":
        raise ValueError("Push this exact commit to the current branch before comparing workloads.")
    rendered = subprocess.check_output(
        ["kubectl", "kustomize", str(root / "argocd")], text=True, timeout=30
    )
    matches = [
        item
        for item in yaml.safe_load_all(rendered)
        if item and item.get("kind") == "Application" and item["metadata"]["name"] == app
    ]
    if len(matches) != 1:
        raise ValueError("The Application must be uniquely declared in the native root.")
    args = revision_arguments(live, matches[0], repo, commit)
    print(
        f"Compare pushed Git content at {commit}; declared chart versions stay explicit.",
        flush=True,
    )
    return args
