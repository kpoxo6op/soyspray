#!/usr/bin/env python3
"""Read Application metadata and Argo observations without changing the cluster."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

PREFIX = "soyspray.vip/"


def unknown(cause):
    return {"value": "unknown", "cause": cause}


def observed(value, cause):
    return {"value": value} if value not in (None, "", [], {}) else unknown(cause)


def annotation(app, key):
    value = app.get("metadata", {}).get("annotations", {}).get(PREFIX + key)
    return observed(value, f"Application metadata has no {PREFIX}{key} annotation.")


def sources(spec):
    return spec.get("sources") or ([spec["source"]] if spec.get("source") else [])


def source_details(items, revisions=None):
    result = []
    for index, source in enumerate(items):
        item = {key: source[key] for key in ("repoURL", "path", "chart", "ref") if key in source}
        item["target_revision"] = observed(
            source.get("targetRevision"), "The Application source has no targetRevision."
        )
        if revisions is not None:
            item["resolved_revision"] = observed(
                revisions[index] if index < len(revisions) else None,
                "Argo has not reported a revision for this source.",
            )
        result.append(item)
    return result


def resolved_revisions(state):
    return state.get("revisions") or ([state["revision"]] if state.get("revision") else [])


def inventory(app):
    metadata, spec = app.get("metadata", {}), app.get("spec", {})
    return {
        "name": metadata.get("name", "unknown"),
        "owner": observed(
            metadata.get("labels", {}).get(PREFIX + "owner"),
            f"Application metadata has no {PREFIX}owner label.",
        ),
        "project": observed(spec.get("project"), "The Application has no project."),
        "namespace": observed(
            spec.get("destination", {}).get("namespace"),
            "The Application has no destination namespace.",
        ),
    }


def app_status(app):
    result = inventory(app)
    spec, state = app.get("spec", {}), app.get("status", {})
    sync = state.get("sync", {})
    compared = sync.get("comparedTo", {})
    operation = state.get("operationState", {})
    current_sources = sources(spec)
    compared_sources = sources(compared)
    result.update(
        desired_sources=observed(source_details(current_sources), "No Application source is set."),
        comparison_sources=observed(
            source_details(compared_sources, resolved_revisions(sync)),
            "Argo has not compared this Application.",
        ),
        reconciled_at=observed(
            state.get("reconciledAt"), "Argo has not reported its comparison time."
        ),
        health=observed(state.get("health", {}).get("status"), "Argo has not reported health."),
        sync=observed(sync.get("status"), "Argo has not reported sync status."),
        last_operation=observed(operation.get("phase"), "Argo has not reported a sync operation."),
    )
    if (
        sync.get("status") == "Synced"
        and current_sources
        and current_sources == compared_sources
        and spec.get("destination") == compared.get("destination")
        and operation.get("phase") not in {"Running", "Terminating"}
        and len(resolved_revisions(sync)) == len(current_sources)
        and all(resolved_revisions(sync))
    ):
        result["running_sources"] = {
            "value": source_details(compared_sources, resolved_revisions(sync)),
            "basis": "Argo reports the live resources match this comparison; no runtime probe was run.",
        }
    else:
        result["running_sources"] = unknown(
            "Argo has not confirmed that all live resources match the current desired sources. "
            "A partial or pending sync can contain more than one revision."
        )
    history = state.get("history", [])
    if history:
        last = max(history, key=lambda entry: (entry.get("deployedAt", ""), entry.get("id", -1)))
        result["last_successful_sync"] = {
            "value": {
                "at": observed(last.get("deployedAt"), "Argo has not reported the sync time."),
                "sources": source_details(sources(last), resolved_revisions(last)),
            },
            "basis": "Argo deployment history; this does not prove the current running revision.",
        }
    else:
        result["last_successful_sync"] = unknown("Argo has no successful deployment history.")
    declared_url = app.get("metadata", {}).get("annotations", {}).get(PREFIX + "access-url")
    urls = [declared_url] if declared_url else state.get("summary", {}).get("externalURLs")
    result["runtime"] = unknown("No Kubernetes workload observations were read.")
    result["access"] = {
        "urls": observed(urls, "Neither Application metadata nor Argo reports an access URL."),
        "method": annotation(app, "access-method"),
        "verified": unknown("No deployed user-journey check was run by this status command."),
    }
    result["recovery"] = {
        "declared_policy": annotation(app, "backup"),
        "policy_cause": annotation(app, "backup-cause"),
        "latest_backup": unknown(
            "Backup-system observations are not connected to this command yet."
        ),
        "last_restore": unknown("No restore evidence source is connected to this command yet."),
    }
    return result


def read_applications(input_path=None):
    if input_path:
        data = json.loads(Path(input_path).read_text())
    else:
        result = subprocess.run(
            [
                "kubectl",
                "--request-timeout=10s",
                "-n",
                "argocd",
                "get",
                "applications",
                "-o",
                "json",
            ],
            capture_output=True,
            text=True,
            timeout=20,
        )
        if result.returncode:
            raise RuntimeError(result.stderr.strip() or "kubectl did not return Applications.")
        data = json.loads(result.stdout)
    if not isinstance(data, dict):
        raise ValueError("The response is not a Kubernetes Application list.")
    items = [data] if data.get("kind") == "Application" else data.get("items")
    if not isinstance(items, list) or any(
        not isinstance(item, dict)
        or item.get("kind") != "Application"
        or not item.get("metadata", {}).get("name")
        for item in items
    ):
        raise ValueError("The response is not a Kubernetes Application list.")
    return sorted(items, key=lambda item: item["metadata"]["name"])


def display(value):
    if isinstance(value, dict) and "value" in value:
        if value["value"] == "unknown":
            return f"unknown ({value['cause']})"
        return display(value["value"])
    return value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("apps", "status"))
    parser.add_argument("--app")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--input", help="Read a saved kubectl JSON response for an offline check.")
    parser.add_argument(
        "--runtime-input",
        help="Read a saved Kubernetes workload list for offline image observations.",
    )
    parser.add_argument(
        "--backup-input", help="Read saved native backup observations for an offline status check."
    )
    parser.add_argument(
        "--restore-dir",
        help="Use private restore reports; required to enable report reads with offline input.",
    )
    args = parser.parse_args(argv)
    if args.command == "status" and not args.app:
        parser.error("status requires --app (make status APP=boys).")
    report = {
        "schema_version": 1,
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "source": str(args.input) if args.input else "Kubernetes Applications in argocd",
    }
    code = 0
    try:
        apps = read_applications(args.input)
        if args.app:
            apps = [app for app in apps if app["metadata"]["name"] == args.app]
            if not apps:
                raise ValueError(f"Argo returned no Application named {args.app}.")
        report["applications"] = [
            app_status(app) if args.command == "status" else inventory(app) for app in apps
        ]
        if args.command == "status":
            from scripts import app_runtime, backup_status

            try:
                runtime = (
                    json.loads(Path(args.runtime_input).read_text())
                    if args.runtime_input
                    else None
                    if args.input
                    else app_runtime.read_workloads(apps)
                )
                for app, row in zip(apps, report["applications"], strict=True):
                    row["runtime"] = (
                        unknown(
                            "Offline Application input has no workload observations; supply --runtime-input."
                        )
                        if runtime is None
                        else app_runtime.runtime_status(app, runtime)
                    )
            except (
                OSError,
                ValueError,
                TypeError,
                KeyError,
                AttributeError,
                subprocess.TimeoutExpired,
            ):
                for row in report["applications"]:
                    row["runtime"] = unknown(
                        "Workload observations are unavailable or invalid; check API access or the supplied runtime input."
                    )
                code = 2
            from scripts.app_recovery import app_recovery

            now = datetime.now(timezone.utc)
            try:
                if args.backup_input:
                    data = json.loads(Path(args.backup_input).read_text())
                elif args.input:
                    data = {}
                else:
                    data = backup_status.read_observations()
                backups = backup_status.build_report(data, now)
            except (OSError, ValueError):
                backups = {
                    "longhorn": unknown("The supplied native backup observations cannot be read.")
                }
                code = 2
            report["backup_source"] = args.backup_input or (
                "unavailable in offline Application input"
                if args.input
                else "Native Kubernetes backup records"
            )
            for app, row in zip(apps, report["applications"], strict=True):
                row["recovery"].update(
                    app_recovery(
                        app,
                        backups,
                        now,
                        args.restore_dir,
                        not (args.input or args.backup_input) or args.restore_dir is not None,
                    )
                )
            if not args.input and backups["longhorn"]["value"] == "unknown":
                code = 2
    except (OSError, RuntimeError, ValueError, subprocess.TimeoutExpired) as exc:
        report["applications"] = unknown(f"Cannot read the application inventory: {exc}")
        code = 2
    if args.format == "json":
        print(json.dumps(report, ensure_ascii=False, indent=2))
    elif code:
        print(display(report["applications"]))
    elif args.command == "apps":
        for app in report["applications"]:
            print(f"{app['name']:<28} {display(app['owner'])}")
    else:
        for key, value in report["applications"][0].items():
            print(f"{key}: {display(value)}")
    return code


if __name__ == "__main__":
    sys.exit(main())
