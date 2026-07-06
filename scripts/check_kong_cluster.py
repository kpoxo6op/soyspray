#!/usr/bin/env python3
"""Read-only cluster smoke checks for the Kong baseline."""

from __future__ import annotations

import shutil
import subprocess
import sys


REQUIRED_API_RESOURCES = ["gatewayclasses.gateway.networking.k8s.io", "gateways.gateway.networking.k8s.io", "httproutes.gateway.networking.k8s.io"]


def run(command: list[str]) -> tuple[int, str]:
    result = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return result.returncode, result.stdout.strip()


def main() -> int:
    if not shutil.which("kubectl"):
        print("kubectl is required for Kong cluster smoke checks.")
        return 1

    errors: list[str] = []
    code, output = run(["kubectl", "version", "--client=true"])
    if code != 0:
        errors.append(f"kubectl client check failed: {output}")

    code, output = run(["kubectl", "get", "--raw=/readyz"])
    if code != 0:
        errors.append(f"Kubernetes API readyz failed: {output}")

    code, output = run(["kubectl", "api-resources"])
    if code != 0:
        errors.append(f"api-resources failed: {output}")
    else:
        for resource in REQUIRED_API_RESOURCES:
            short = resource.split(".", 1)[0]
            if short not in output:
                errors.append(f"Gateway API resource missing: {resource}")

    for namespace in ["platform-kong", "platform-kong-smoke"]:
        code, output = run(["kubectl", "get", "namespace", namespace])
        if code != 0:
            errors.append(f"namespace not present: {namespace}: {output}")

    if errors:
        print("Kong cluster smoke failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("Kong cluster smoke passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
