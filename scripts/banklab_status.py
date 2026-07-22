#!/usr/bin/env python3
"""Print a concise, read-only health summary for the Kong bank lab."""

from __future__ import annotations

import json
import subprocess
import sys

EXPECTED_APPLICATIONS = {
    "banklab-customer-traffic",
    "banklab-docs",
    "banklab-kong",
    "banklab-kong-crds",
    "banklab-kong-gateway-api",
    "banklab-kong-operator-dashboard",
    "banklab-kong-security-controls",
    "banklab-kong-smoke",
    "synthetic-bank-apis",
}
PARKED_APPLICATIONS = {"banklab-kong-crds"}


def classify_applications(names: set[str]) -> str:
    if names == PARKED_APPLICATIONS:
        return "OFF"
    if names == EXPECTED_APPLICATIONS:
        return "ON"
    return "PARTIAL"


def kubectl(*args: str) -> dict:
    result = subprocess.run(
        ["kubectl", *args],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())
    return json.loads(result.stdout)


def main() -> int:
    try:
        nodes = kubectl("get", "nodes", "-o", "json")["items"]
        apps = kubectl(
            "-n",
            "argocd",
            "get",
            "applications.argoproj.io",
            "-l",
            "app.kubernetes.io/part-of=kong-bank-lab",
            "-o",
            "json",
        )["items"]
        runtime_pods = kubectl(
            "get",
            "pods",
            "--all-namespaces",
            "-l",
            "banklab.konghq.com/platform-layer",
            "-o",
            "json",
        )["items"]
    except (RuntimeError, json.JSONDecodeError) as exc:
        print(f"Cluster check failed: {exc}", file=sys.stderr)
        return 1

    failed = False
    print("NODES")
    for node in sorted(nodes, key=lambda item: item["metadata"]["name"]):
        ready = next(
            condition["status"] == "True"
            for condition in node["status"]["conditions"]
            if condition["type"] == "Ready"
        )
        print(f"  {node['metadata']['name']:<12} {'Ready' if ready else 'NotReady'}")
        failed |= not ready

    print("\nARGO APPLICATIONS")
    if not apps:
        print("  No bank-lab applications found.")
        return 1

    application_names = {app["metadata"]["name"] for app in apps}
    state = classify_applications(application_names)
    print(f"\nLAB STATE\n  {state}")
    failed |= state == "PARTIAL"

    for app in sorted(apps, key=lambda item: item["metadata"]["name"]):
        sync = app.get("status", {}).get("sync", {}).get("status", "Unknown")
        health = app.get("status", {}).get("health", {}).get("status", "Unknown")
        print(f"  {app['metadata']['name']:<36} {sync:<10} {health}")
        failed |= sync != "Synced" or health != "Healthy"

    print(f"\nRUNTIME PODS\n  {len(runtime_pods)}")
    if state == "OFF":
        failed |= bool(runtime_pods)
    elif state == "ON":
        failed |= not runtime_pods
        try:
            gateway = kubectl(
                "-n", "platform-kong", "get", "deployment", "banklab-kong-gateway", "-o", "json"
            )
        except (RuntimeError, json.JSONDecodeError) as exc:
            print(f"\nGATEWAY\n  unavailable: {exc}")
            failed = True
        else:
            desired = gateway["spec"].get("replicas", 0)
            available = gateway.get("status", {}).get("availableReplicas", 0)
            print(f"\nGATEWAY\n  {available}/{desired} replicas available")
            failed |= desired != 2 or available != desired

    return int(failed)


if __name__ == "__main__":
    raise SystemExit(main())
