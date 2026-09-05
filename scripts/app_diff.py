"""Compare one app's local YAML with its live state using native Argo rendering."""

import argparse
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path, PurePosixPath

from scripts.argocd_cli import argocd

ROOT = Path(__file__).resolve().parents[1]


def stage_package(package, source_path, destination):
    path = PurePosixPath(source_path)
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise ValueError("Argo's source path must stay inside the temporary repository.")
    files = (
        subprocess.check_output(
            [
                "git",
                "ls-files",
                "--cached",
                "--others",
                "--exclude-standard",
                "-z",
                "--",
                str(package),
            ],
            cwd=ROOT,
            timeout=20,
        )
        .decode()
        .split("\0")
    )
    count = 0
    for name in set(filter(None, files)):
        file = ROOT / name
        if file.suffix not in (".yaml", ".yml") or not file.exists():
            continue
        if not file.resolve().is_relative_to(package):
            raise ValueError("A manifest links outside this app's package.")
        target = destination / path / file.relative_to(package)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(file.read_bytes())
        count += 1
    if not count:
        raise ValueError("The app package has no tracked or unignored YAML files.")


def compare(app, package, binary):
    application = json.loads(
        subprocess.check_output(
            [
                "kubectl",
                "--request-timeout=10s",
                "-n",
                "argocd",
                "get",
                "application",
                app,
                "-o",
                "json",
            ],
            stderr=subprocess.PIPE,
            timeout=20,
        )
    )
    source = application["spec"].get("source", {})
    if "path" not in source or source.get("chart") or application["spec"].get("sources"):
        raise ValueError("This operation needs one Git source with a YAML manifest package.")
    config = json.loads(
        subprocess.check_output(
            ["kubectl", "config", "view", "--raw", "--minify", "--flatten", "-o", "json"],
            stderr=subprocess.PIPE,
            timeout=20,
        )
    )
    config["contexts"][0]["context"]["namespace"] = "argocd"
    with tempfile.TemporaryDirectory(prefix="soyspray-diff-") as directory:
        work = Path(directory)
        checkout = work / "repo"
        stage_package(package, source["path"], checkout)
        kubeconfig = work / "kubeconfig.json"
        kubeconfig.touch(mode=0o600)
        kubeconfig.write_text(json.dumps(config))
        argo_config = work / "argocd.yml"
        argo_config.touch(mode=0o600)
        env = {**os.environ, "KUBECONFIG": str(kubeconfig)}
        cli = [str(binary), "--config", str(argo_config)]
        subprocess.run(
            [*cli, "login", "--core"], env=env, check=True, timeout=30, stdout=subprocess.DEVNULL
        )
        print(
            "Native Argo comparison of local workload YAML. Secrets are omitted.\n"
            "Removed objects still follow their Argo prune protections; this command does not sync.",
            flush=True,
        )
        result = subprocess.run(
            [
                *cli,
                "--core",
                "app",
                "diff",
                app,
                "--local",
                str(checkout),
                "--server-side-generate",
                "--local-include",
                "*.yaml",
                "--local-include",
                "*.yml",
                "--diff-exit-code",
                "10",
            ],
            env=env,
            timeout=180,
        )
        # Argo fatal connection failures can return 1. Use a distinct diff code.
        if result.returncode not in (0, 10):
            raise RuntimeError(f"Argo comparison failed with exit {result.returncode}.")
        if result.returncode == 0:
            print("No workload difference.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app", required=True)
    parser.add_argument("--package", required=True)
    args = parser.parse_args()
    package = (ROOT / args.package).resolve()
    if not re.fullmatch(
        r"[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?", args.app
    ) or not package.is_relative_to(ROOT):
        parser.error("Use an Application name and a package inside this checkout.")
    try:
        compare(args.app, package, argocd())
    except (
        OSError,
        ValueError,
        KeyError,
        IndexError,
        RuntimeError,
        subprocess.SubprocessError,
    ) as error:
        parser.exit(2, f"unknown: deployment comparison did not complete: {error}\n")


if __name__ == "__main__":
    main()
