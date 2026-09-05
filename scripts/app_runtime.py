"""Report observed container images through native Kubernetes ownership."""

import json
import subprocess

from scripts.app_status import observed, unknown

# Read only workload kinds; never use this list to fetch credentials or pod logs.
WORKLOADS = {
    ("", "Pod"): "pods",
    ("apps", "Deployment"): "deployments.apps",
    ("apps", "ReplicaSet"): "replicasets.apps",
    ("apps", "StatefulSet"): "statefulsets.apps",
    ("apps", "DaemonSet"): "daemonsets.apps",
    ("batch", "Job"): "jobs.batch",
    ("batch", "CronJob"): "cronjobs.batch",
    ("postgresql.cnpg.io", "Cluster"): "clusters.postgresql.cnpg.io",
    ("monitoring.coreos.com", "Prometheus"): "prometheuses.monitoring.coreos.com",
    ("monitoring.coreos.com", "Alertmanager"): "alertmanagers.monitoring.coreos.com",
}
BASE = {"pods", "replicasets.apps", "statefulsets.apps", "jobs.batch"}


def resource_key(item):
    api = item.get("apiVersion", "")
    group = api.split("/", 1)[0] if "/" in api else ""
    metadata = item.get("metadata", {})
    return group, item.get("kind"), metadata.get("namespace"), metadata.get("name")


def read_workloads(apps):
    kinds = BASE | {
        WORKLOADS[(resource.get("group", ""), resource["kind"])]
        for app in apps
        for resource in app.get("status", {}).get("resources", [])
        if (resource.get("group", ""), resource.get("kind")) in WORKLOADS
    }
    result = subprocess.run(
        ["kubectl", "--request-timeout=10s", "get", ",".join(sorted(kinds)), "-A", "-o", "json"],
        capture_output=True,
        text=True,
        timeout=20,
    )
    if result.returncode:
        raise ValueError(
            "The Kubernetes workload read failed; check cluster access and permissions."
        )
    return json.loads(result.stdout)


def runtime_status(app, data):
    destination = app.get("spec", {}).get("destination", {})
    if destination.get("server") != "https://kubernetes.default.svc":
        return unknown("The Application does not target the local Argo cluster.")
    if not isinstance(data, dict) or not isinstance(data.get("items"), list):
        raise ValueError("No valid Kubernetes workload list was supplied.")
    items = data["items"]
    if any(
        not isinstance(item, dict) or not isinstance(item.get("metadata"), dict) for item in items
    ):
        raise ValueError("The Kubernetes workload list contains invalid records.")
    roots = {
        (
            resource.get("group", ""),
            resource.get("kind"),
            resource.get("namespace"),
            resource.get("name"),
        )
        for resource in app.get("status", {}).get("resources", [])
        if (resource.get("group", ""), resource.get("kind")) in WORKLOADS
    }
    owned = {
        (item["metadata"].get("namespace"), item["metadata"]["uid"])
        for item in items
        if resource_key(item) in roots and item["metadata"].get("uid")
    }
    while True:
        children = {
            (item["metadata"].get("namespace"), item["metadata"]["uid"])
            for item in items
            if item["metadata"].get("uid")
            and any(
                owner.get("controller") is True
                and (item["metadata"].get("namespace"), owner.get("uid")) in owned
                for owner in item["metadata"].get("ownerReferences", [])
            )
        }
        if children <= owned:
            break
        owned |= children
    pods = []
    for item in items:
        metadata = item["metadata"]
        if (
            item.get("kind") != "Pod"
            or (metadata.get("namespace"), metadata.get("uid")) not in owned
        ):
            continue
        containers = []
        for spec_key, status_key, role in (
            ("containers", "containerStatuses", "app"),
            ("initContainers", "initContainerStatuses", "init"),
            ("ephemeralContainers", "ephemeralContainerStatuses", "ephemeral"),
        ):
            statuses = {
                entry["name"]: entry for entry in item.get("status", {}).get(status_key, [])
            }
            for container in item.get("spec", {}).get(spec_key, []):
                state = statuses.get(container["name"], {})
                containers.append(
                    {
                        "name": container["name"],
                        "role": role,
                        "pod_image": observed(container.get("image"), "The pod spec has no image."),
                        "image_id": observed(
                            state.get("imageID"),
                            "The kubelet has not reported a container image ID.",
                        ),
                        "ready": observed(
                            state.get("ready"), "The kubelet has not reported container readiness."
                        ),
                        "state": observed(
                            next(iter(state.get("state", {})), None),
                            "The kubelet has not reported container state.",
                        ),
                    }
                )
        pods.append(
            {
                "namespace": metadata.get("namespace"),
                "name": metadata.get("name"),
                "uid": metadata.get("uid"),
                "terminating": bool(metadata.get("deletionTimestamp")),
                "phase": observed(
                    item.get("status", {}).get("phase"), "The kubelet has not reported pod phase."
                ),
                "containers": containers,
            }
        )
    if not pods:
        return unknown(
            "No observed pods have a controller-UID ownership chain to an Argo-managed workload."
        )
    return {
        "value": sorted(pods, key=lambda pod: (pod["namespace"], pod["name"])),
        "basis": "Pod specs and kubelet container image IDs, linked by controller UIDs to Argo resources. Old, pending and terminating pods remain visible; this does not prove a user journey.",
    }
