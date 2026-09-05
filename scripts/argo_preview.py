"""Prepare native root parameters for a single adopted application's branch preview."""

import argparse
import copy
import json
import re
import subprocess
from pathlib import Path

import yaml

from scripts.app_status import sources

ROOT = Path(__file__).resolve().parents[1]


def prepare(root, children, revision, app_name=""):
    result = copy.deepcopy(root)
    source = result["spec"]["source"]
    source["targetRevision"] = revision
    if not app_name:
        return result
    if revision == "HEAD":
        raise ValueError(
            "A preview requires the pushed branch name; omit the app to return to HEAD."
        )
    matches = [
        child
        for child in children
        if child.get("kind") == "Application" and child["metadata"]["name"] == app_name
    ]
    if len(matches) != 1:
        raise ValueError(f"Application {app_name!r} is not uniquely declared in the native root.")
    app = matches[0]
    spec = app["spec"]
    if spec.get("source") and spec.get("sources"):
        raise ValueError("The child has ambiguous single and multiple sources.")
    operations = []
    for index, child_source in enumerate(sources(spec)):
        if child_source.get("repoURL") == source["repoURL"]:
            path = (
                f"/spec/sources/{index}/targetRevision"
                if spec.get("sources")
                else "/spec/source/targetRevision"
            )
            operations.append({"op": "add", "path": path, "value": revision})
    if operations:
        source.setdefault("kustomize", {}).setdefault("patches", []).append(
            {
                "target": {
                    "group": "argoproj.io",
                    "version": "v1alpha1",
                    "kind": "Application",
                    "name": re.escape(app_name),
                    "namespace": re.escape(app["metadata"]["namespace"]),
                },
                "patch": json.dumps(operations),
            }
        )
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--revision", default="HEAD")
    parser.add_argument("--app", default="")
    args = parser.parse_args()
    root = yaml.safe_load((ROOT / "argocd/bootstrap/application.yaml").read_text())
    children = []
    if args.app:
        subprocess.run(
            ["git", "check-ref-format", "--branch", args.revision],
            cwd=ROOT,
            check=True,
            stdout=subprocess.DEVNULL,
        )
        head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
        remote = subprocess.check_output(
            [
                "git",
                "ls-remote",
                "--exit-code",
                "--heads",
                root["spec"]["source"]["repoURL"],
                args.revision,
            ],
            cwd=ROOT,
            text=True,
        ).splitlines()
        if f"{head}\trefs/heads/{args.revision}" not in remote:
            raise SystemExit("Push this checkout to the requested branch before previewing it.")
        if subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT):
            raise SystemExit("Commit the working tree before previewing an application.")
        rendered = subprocess.check_output(
            ["kubectl", "kustomize", str(ROOT / "argocd")], text=True
        )
        children = list(yaml.safe_load_all(rendered))
    result = prepare(root, children, args.revision, args.app)
    reference = "HEAD" if args.revision == "HEAD" else f"refs/heads/{args.revision}"
    resolved = subprocess.check_output(
        ["git", "ls-remote", "--exit-code", root["spec"]["source"]["repoURL"], reference],
        text=True,
    ).splitlines()
    commits = [line.split("\t")[0] for line in resolved if line.endswith(f"\t{reference}")]
    if len(commits) != 1:
        raise SystemExit("The root revision must resolve to one remote Git commit.")
    if args.app and commits[0] != head:
        raise SystemExit(
            "The remote branch changed while preparing the preview; retry from its current checkout."
        )
    print(json.dumps({"application": result, "revision": commits[0]}))


if __name__ == "__main__":
    main()
