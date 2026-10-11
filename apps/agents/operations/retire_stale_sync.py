#!/usr/bin/env python3
"""Two specific reviewed recoveries; never edit or delete workloads."""

import argparse
import json
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from operations.intake import assert_target, pushed


def termination_patch(app, expected, desired_revision):
    metadata, status = app["metadata"], app["status"]
    operation = status["operationState"]
    scenario = expected.get("scenario", "initial")
    incidents = {
        "initial": ("808c39d95657413ff3282f8d03edc17edb345d4e", 4),
        "writeback-fallback": (
            "0196736b88e5e7de4d57da4b4038d8a299806c48",
            expected.get("retryCount"),
        ),
    }
    if scenario not in incidents:
        raise ValueError("This is not a reviewed recovery incident")
    old_revision, retry_count = incidents[scenario]
    if type(retry_count) is not int or not 0 <= retry_count < 5:
        raise ValueError("No further obsolete retries remain")
    if (
        metadata["name"] != "agents"
        or metadata["namespace"] != "argocd"
        or metadata["uid"] != expected["applicationUid"]
        or metadata["resourceVersion"] != expected["applicationResourceVersion"]
        or app["spec"]["source"]
        != {
            "repoURL": "https://github.com/kpoxo6op/soyspray.git",
            "targetRevision": "main",
            "path": "apps/agents/manifests",
        }
        or status["sync"]["revision"] != desired_revision
        or operation["phase"] != "Running"
        or operation["startedAt"] != expected["operationStartedAt"]
        or operation["retryCount"] != retry_count
        or operation["syncResult"]["revision"] != old_revision
    ):
        raise ValueError("The obsolete initial operation identity changed")
    retry = app["spec"]["syncPolicy"].get("retry", {})
    limit = retry.get("limit", 5)  # Argo 2.14 automated-sync default.
    if limit != 5:
        raise ValueError("Unexpected retry policy; this recovery is not applicable")
    return {
        "metadata": {"resourceVersion": metadata["resourceVersion"]},
        "status": {"operationState": {"phase": "Terminating"}},
    }


def run(args):
    from kubernetes import client, config

    root = Path(__file__).resolve().parents[3]
    revision = pushed(root)
    if (
        subprocess.check_output(
            ["git", "-C", str(root), "rev-parse", "origin/main"], text=True
        ).strip()
        != revision
    ):
        raise ValueError("Recovery requires the clean, pushed main revision")
    if args.report.exists():
        raise ValueError("This one-time recovery already has a report")
    declared = list(yaml.safe_load_all((root / "apps/agents/manifests/intake.yaml").read_text()))
    if any(
        d["spec"]["template"]["spec"]["containers"][0]["resources"]["limits"]["memory"] != "1Gi"
        for d in declared
    ):
        raise ValueError("Main does not declare the reviewed memory correction")
    expected = json.loads(args.expected.read_text())
    promotion = json.loads(args.promotion.read_text())
    fallback = expected.get("scenario", "initial") == "writeback-fallback"
    claim = "agents-restore-test" if fallback else "agents-evidence"
    if promotion["claimName"] != claim:
        raise ValueError("Claim does not match the specific recovery incident")
    if fallback:
        api_evidence = json.loads(Path(expected["nativeApiAvailabilityEvidence"]).read_text())
        age = (
            datetime.now(timezone.utc) - datetime.fromisoformat(api_evidence["UTC"])
        ).total_seconds()
        if api_evidence.get("HTTPStatus") != 401 or not 0 <= age <= 300:
            raise ValueError("Fresh native Argo API 401 evidence is required")
        for declared_job in declared:
            receiver = declared_job["spec"]["template"]["spec"]["containers"][0]
            if (
                receiver["image"] != expected["newImage"]
                or receiver["env"][0]["value"] != expected["newPackHash"]
            ):
                raise ValueError("Main does not declare the reviewed fallback pair")
        if (
            expected["newImage"] == promotion["image"]
            or expected["newPackHash"] == promotion["packHash"]
        ):
            raise ValueError("Fallback must use the new reviewed image and provenance pack")
    for proc in Path("/proc").iterdir():
        if not proc.name.isdigit():
            continue
        try:
            if b"/apps/agents/operations/intake.py" in (proc / "cmdline").read_bytes():
                raise ValueError("An intake sender is active on the controller")
        except (FileNotFoundError, PermissionError, ProcessLookupError):
            continue
    config.load_kube_config()
    client.Configuration.get_default_copy().debug = False
    custom, core, batch, apps = (
        client.CustomObjectsApi(),
        client.CoreV1Api(),
        client.BatchV1Api(),
        client.AppsV1Api(),
    )
    serialize = client.ApiClient().sanitize_for_serialization
    application = custom.get_namespaced_custom_object(
        "argoproj.io", "v1alpha1", "argocd", "applications", "agents"
    )
    patch = termination_patch(application, expected, revision)
    job = serialize(batch.read_namespaced_job(promotion["jobName"], "agents"))
    pods = core.list_namespaced_pod(
        "agents", label_selector=f"batch.kubernetes.io/job-name={promotion['jobName']}"
    ).items
    if len(pods) != 1:
        raise ValueError("Expected exactly the stale hook Pod")
    pod = serialize(pods[0])
    pvc = serialize(core.read_namespaced_persistent_volume_claim(claim, "agents"))
    old_memory = "1Gi" if fallback else "192Mi"
    assert_target(promotion, pvc, job, pod, memory_limit=old_memory)
    if job["metadata"]["uid"] != expected["jobUid"] or pod["metadata"]["uid"] != expected["podUid"]:
        raise ValueError("Hook identity changed")
    if pod["spec"]["containers"][0]["resources"]["limits"]["memory"] != old_memory:
        raise ValueError("Hook is not the obsolete memory configuration")
    production = {
        "deployments": serialize(apps.list_namespaced_deployment("agents")),
        "pods": serialize(
            core.list_namespaced_pod("agents", label_selector="app.kubernetes.io/name=agents")
        ),
    }
    prior_production_hook = None
    if fallback:
        prior_production_hook = serialize(
            batch.read_namespaced_job("agents-intake-" + promotion["packHash"][:16], "agents")
        )
        if prior_production_hook.get("status", {}).get("succeeded") != 1:
            raise ValueError("The earlier production intake is still running or failed")
    if not fallback and (production["deployments"]["items"] or production["pods"]["items"]):
        raise ValueError("A production web workload exists")
    if (
        fallback
        and [d["metadata"]["uid"] for d in production["deployments"]["items"]]
        != expected["productionDeploymentUids"]
    ):
        raise ValueError("Recorded production state changed")
    node, uid = pod["spec"]["nodeName"], pod["metadata"]["uid"]
    container = pod["status"]["containerStatuses"][0]["containerID"].removeprefix("containerd://")
    if node not in {"node-0", "node-1", "node-2"} or not re.fullmatch(r"[a-f0-9]{64}", container):
        raise ValueError("Unexpected node or container identity")
    # Fixed read-only host inspection: no receiver exec, shell, or host writes.
    inspect = f"""import json,time
from pathlib import Path
root=Path('/var/lib/kubelet/pods/{uid}/volumes/kubernetes.io~csi/pvc-{promotion["pvcUid"]}/mount/staging')
assert root.parent.is_dir() and (not root.exists() or root.is_dir())
def snapshot():
    for p in Path('/proc').iterdir():
        if not p.name.isdigit(): continue
        try:
            if '{container}' in (p/'cgroup').read_text() and b'/opt/evidence.py\\x00send' in (p/'cmdline').read_bytes():
                raise RuntimeError('Receiver sender is active')
        except (FileNotFoundError,PermissionError,ProcessLookupError): pass
    return sorted((str(p.relative_to(root)),p.stat().st_size,p.stat().st_mtime_ns) for p in root.rglob('*') if p.is_file())
first=snapshot();time.sleep(3);last=snapshot();assert first==last
print(json.dumps({{'stagingUnchanged':True,'fileCount':len(first),'bytes':sum(x[1] for x in first),'receiverSenderAbsent':True}}))
"""
    inspection = json.loads(
        subprocess.check_output(
            ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", node, "sudo", "python3", "-"],
            input=inspect,
            text=True,
        )
    )
    # Re-read immediately: resourceVersion in the patch also rejects an API race.
    fresh = custom.get_namespaced_custom_object(
        "argoproj.io", "v1alpha1", "argocd", "applications", "agents"
    )
    if fresh["metadata"]["resourceVersion"] != application["metadata"]["resourceVersion"]:
        raise ValueError("Application changed during the idle check")
    events = [
        serialize(
            core.list_namespaced_event("agents", field_selector=f"involvedObject.uid={object_uid}")
        )
        for object_uid in [uid, job["metadata"]["uid"]]
    ]
    report = {
        "UTC": datetime.now(timezone.utc).isoformat(),
        "sourceRevision": revision,
        "applicationBefore": application,
        "job": job,
        "pod": pod,
        "productionState": production,
        "priorProductionHook": prior_production_hook,
        "nativeApi401Evidence": api_evidence if fallback else None,
        "events": events,
        "idleInspection": inspection,
        "patch": patch,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n")
    result = custom.patch_namespaced_custom_object(
        "argoproj.io", "v1alpha1", "argocd", "applications", "agents", patch
    )
    report["applicationAfterRequest"] = result
    report["observedPhases"] = []
    for _ in range(240):
        current = custom.get_namespaced_custom_object(
            "argoproj.io", "v1alpha1", "argocd", "applications", "agents"
        )
        state = current.get("status", {}).get("operationState", {})
        report["observedPhases"].append(
            {
                "phase": state.get("phase"),
                "revision": state.get("syncResult", {}).get("revision"),
                "message": state.get("message"),
            }
        )
        args.report.write_text(json.dumps(report, indent=2) + "\n")
        if (
            state.get("phase") in {"Failed", "Error", "Succeeded"}
            or state.get("syncResult", {}).get("revision") == revision
        ):
            break
        time.sleep(0.5)
    else:
        raise ValueError("Argo did not finish its native termination")
    print("Obsolete initial sync retired by Argo; no workload or storage writes")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected", type=Path, required=True)
    parser.add_argument("--promotion", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    run(parser.parse_args())
