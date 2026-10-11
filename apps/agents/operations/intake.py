#!/usr/bin/env python3
"""Reviewed data operation. Creates only a short-lived TokenRequest, never workloads."""

import argparse
import copy
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from evidence import digest, install


def assert_target(promotion, pvc, job, pod, allow_completed=False):
    expected_job = promotion["jobName"]
    image = promotion["image"]
    if not re.fullmatch(r"ghcr\.io/kpoxo6op/agents@sha256:[a-f0-9]{64}", image):
        raise ValueError("Image is not the approved digest-pinned repository")
    if (
        pvc["metadata"]["uid"] != promotion["pvcUid"]
        or pvc["metadata"]["name"] != promotion["claimName"]
    ):
        raise ValueError("PVC identity mismatch")
    if (
        pvc["status"]["phase"] != "Bound"
        or pvc["spec"]["storageClassName"] != "agents-evidence-rwx-retain"
    ):
        raise ValueError("PVC is not bound to the retained class")
    if job["metadata"]["name"] != expected_job:
        raise ValueError("Job identity mismatch")
    owner = [o for o in pod["metadata"].get("ownerReferences", []) if o.get("controller")]
    if (
        len(owner) != 1
        or owner[0]["kind"] != "Job"
        or owner[0]["uid"] != job["metadata"]["uid"]
        or owner[0]["name"] != expected_job
    ):
        raise ValueError("Pod owner mismatch")
    labels = pod["metadata"].get("labels", {})
    if (
        labels.get("app.kubernetes.io/name") != "agents-intake"
        or labels.get("agents.soyspray.vip/pack") != promotion["packHash"][:16]
    ):
        raise ValueError("Pod label mismatch")
    complete = (
        allow_completed
        and pod["status"]["phase"] == "Succeeded"
        and job.get("status", {}).get("succeeded") == 1
    )
    if (pod["status"]["phase"] != "Running" and not complete) or not pod["spec"].get("nodeName"):
        raise ValueError("Receiver pod is not running or a verified completed hook")
    if pod["spec"].get("serviceAccountName") != "agents-intake-operator":
        raise ValueError("Receiver service account identity mismatch")
    containers = pod["spec"]["containers"]
    if pod["spec"].get("initContainers") or pod["spec"].get("ephemeralContainers"):
        raise ValueError("Receiver unexpectedly has another execution path")
    if (
        len(containers) != 1
        or containers[0]["name"] != "receiver"
        or containers[0]["image"] != image
    ):
        raise ValueError("Pod digest mismatch")
    if containers[0]["command"] != ["python3", "/opt/evidence.py", "receive"]:
        raise ValueError("Receiver command mismatch")
    env = {e["name"]: e.get("value") for e in containers[0].get("env", [])}
    for key, field in [
        ("PACK_HASH", "packHash"),
        ("ARCHIVE_HASH", "archiveHash"),
        ("ARCHIVE_BYTES", "archiveBytes"),
    ]:
        if env.get(key) != str(promotion[field]):
            raise ValueError("Receiver pack identity mismatch")
    if pod["spec"].get("automountServiceAccountToken") is not False:
        raise ValueError("Receiver unexpectedly mounts a credential")
    volumes = [v for v in pod["spec"]["volumes"] if "persistentVolumeClaim" in v]
    if (
        len(volumes) != 1
        or volumes[0]["persistentVolumeClaim"]["claimName"] != promotion["claimName"]
    ):
        raise ValueError("Receiver claim mount mismatch")
    if any(set(v) - {"name", "persistentVolumeClaim", "emptyDir"} for v in pod["spec"]["volumes"]):
        raise ValueError("Receiver unexpectedly mounts another source or credential")
    evidence_mounts = [
        m for m in containers[0].get("volumeMounts", []) if m["mountPath"] == "/evidence"
    ]
    if (
        len(evidence_mounts) != 1
        or evidence_mounts[0]["name"] != volumes[0]["name"]
        or evidence_mounts[0].get("readOnly", False)
        or evidence_mounts[0].get("subPath")
        or evidence_mounts[0].get("subPathExpr")
        or containers[0].get("envFrom")
        or any("valueFrom" in e for e in containers[0].get("env", []))
    ):
        raise ValueError("Receiver evidence path or credential environment mismatch")


def pushed(root):
    def git(*args):
        return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()

    if git("status", "--porcelain", "--untracked-files=no"):
        raise ValueError("Tracked operation sources are not clean")
    head = git("rev-parse", "HEAD")
    if git("rev-parse", "@{upstream}") != head:
        raise ValueError("Push the reviewed commit before running this operation")
    return head


def token_request(pod):
    from kubernetes import client

    return client.AuthenticationV1TokenRequest(
        spec=client.V1TokenRequestSpec(
            audiences=["https://kubernetes.default.svc.cluster.local"],
            expiration_seconds=1200,
            bound_object_ref=client.V1BoundObjectReference(
                api_version="v1",
                kind="Pod",
                name=pod["metadata"]["name"],
                uid=pod["metadata"]["uid"],
            ),
        )
    )


def operator_configuration(base, token):
    operator = copy.deepcopy(base)
    operator.debug = False
    operator.api_key = {"BearerToken": token}
    operator.api_key_prefix = {"BearerToken": "Bearer"}
    operator.cert_file = operator.key_file = None
    operator.username = operator.password = None
    operator.refresh_api_key_hook = None
    auth = operator.auth_settings().get("BearerToken", {})
    if auth.get("key") != "authorization" or auth.get("value") != "Bearer " + token:
        raise ValueError("Installed SDK does not attach the scoped credential correctly")
    return operator


def run(args):
    from kubernetes.stream import stream

    from kubernetes import client, config

    revision = pushed(Path(__file__).resolve().parents[3])
    promotion = json.loads(args.promotion.read_text())
    if promotion["claimName"] not in ("agents-evidence", "agents-restore-test") or not re.fullmatch(
        r"agents-(intake|restore)-[a-f0-9]{16}", promotion["jobName"]
    ):
        raise ValueError("Operation scope is outside the dedicated evidence claims")
    for key in ("packHash", "archiveHash"):
        if not re.fullmatch(r"[a-f0-9]{64}", promotion[key]):
            raise ValueError("Promotion hash invalid")
    if (
        args.archive.stat().st_size != promotion["archiveBytes"]
        or digest(args.archive) != promotion["archiveHash"]
    ):
        raise ValueError("Controller archive identity mismatch")
    with tempfile.TemporaryDirectory(prefix="agents-preflight-") as scratch:
        install(args.archive, Path(scratch), promotion["packHash"], promotion["archiveHash"])
    config.load_kube_config(config_file=args.kubeconfig, persist_config=False)
    admin_configuration = client.Configuration.get_default_copy()
    admin_core, admin_batch = client.CoreV1Api(), client.BatchV1Api()
    namespace = "agents"
    as_dict = client.ApiClient().sanitize_for_serialization
    pvc = as_dict(
        admin_core.read_namespaced_persistent_volume_claim(promotion["claimName"], namespace)
    )
    pv = admin_core.read_persistent_volume(pvc["spec"]["volumeName"])
    if pv.spec.persistent_volume_reclaim_policy != "Retain":
        raise ValueError("Live PV is not retained")
    job = as_dict(admin_batch.read_namespaced_job(promotion["jobName"], namespace))
    pods = admin_core.list_namespaced_pod(
        namespace, label_selector=f"batch.kubernetes.io/job-name={promotion['jobName']}"
    ).items
    if len(pods) != 1:
        raise ValueError("Expected exactly one bounded Job pod")
    pod = as_dict(pods[0])
    assert_target(promotion, pvc, job, pod, allow_completed=True)
    node = admin_core.read_node(pod["spec"]["nodeName"])
    if not any(c.type == "Ready" and c.status == "True" for c in node.status.conditions):
        raise ValueError("Receiver node is not Ready")
    start = time.monotonic()

    def report_completed(completed, matrix, token_expiration=None, noop=False):
        log = admin_core.read_namespaced_pod_log(
            pod["metadata"]["name"], namespace, container="receiver"
        )
        result = json.loads(log.strip().splitlines()[-1])
        if result.get("packHash") != promotion["packHash"] or result.get("status") not in (
            "installed",
            "already-identical",
        ):
            raise ValueError("Receiver completion log does not prove the pinned pack")
        if noop and result["status"] != "already-identical":
            raise ValueError("Completed hook is not an identical no-op")
        custom = client.CustomObjectsApi()
        app = None
        for _ in range(30):
            app = custom.get_namespaced_custom_object(
                "argoproj.io", "v1alpha1", "argocd", "applications", "agents"
            )
            operation = app.get("status", {}).get("operationState", {})
            hooks = operation.get("syncResult", {}).get("resources", [])
            if any(
                h.get("kind") == "Job"
                and h.get("name") == promotion["jobName"]
                and h.get("hookPhase") == "Succeeded"
                for h in hooks
            ):
                break
            time.sleep(1)
        else:
            raise ValueError("Argo has not recorded the hook's successful completion")
        report = {
            "sourceRevision": revision,
            "jobName": promotion["jobName"],
            "jobUid": job["metadata"]["uid"],
            "podUid": pod["metadata"]["uid"],
            "node": pod["spec"]["nodeName"],
            "image": promotion["image"],
            "pvcUid": pvc["metadata"]["uid"],
            "boundPV": pvc["spec"]["volumeName"],
            "pvReclaimPolicy": "Retain",
            "packHash": promotion["packHash"],
            "archiveHash": promotion["archiveHash"],
            "bytes": promotion["archiveBytes"],
            "tokenPersisted": False,
            "tokenExpiration": token_expiration,
            "rbac": matrix,
            "jobComplete": True,
            "noop": noop,
            "execPerformed": not noop,
            "startTime": completed.get("status", {}).get("startTime"),
            "completionTime": completed.get("status", {}).get("completionTime"),
            "receiverResult": result,
            "argoOperationState": operation,
            "elapsedSeconds": round(time.monotonic() - start, 2),
        }
        args.report.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2) + "\n")
        args.report.chmod(0o600)

    if job.get("status", {}).get("succeeded") == 1:
        report_completed(job, [], noop=True)
        return
    request = token_request(pod)
    issued = admin_core.create_namespaced_service_account_token(
        "agents-intake-operator", namespace, request
    )
    remaining = (issued.status.expiration_timestamp - datetime.now(timezone.utc)).total_seconds()
    if not 0 < remaining <= 1800:
        raise ValueError("Server-issued token lifetime exceeds the reviewed bound")
    operator = operator_configuration(admin_configuration, issued.status.token)
    api = client.ApiClient(operator)
    auth = client.AuthorizationV1Api(api)
    matrix = []
    checks = [
        ("agents", "", "pods", "get", "", True),
        ("agents", "batch", "jobs", "get", "", True),
        ("agents", "", "pods", "create", "exec", True),
        ("agents", "", "pods", "get", "exec", True),
        ("agents", "", "secrets", "get", "", False),
        ("agents", "", "pods", "list", "", False),
        ("agents", "", "pods", "create", "", False),
        ("agents", "apps", "deployments", "patch", "", False),
        ("default", "", "pods", "create", "exec", False),
        ("default", "", "pods", "get", "exec", False),
        ("argocd", "", "secrets", "get", "", False),
        ("", "", "nodes", "get", "", False),
    ]
    for ns, group, resource, verb, subresource, required in checks:
        response = auth.create_self_subject_access_review(
            client.V1SelfSubjectAccessReview(
                spec=client.V1SelfSubjectAccessReviewSpec(
                    resource_attributes=client.V1ResourceAttributes(
                        namespace=ns,
                        group=group,
                        resource=resource,
                        verb=verb,
                        subresource=subresource or None,
                    )
                )
            )
        )
        allowed = response.status.allowed is True
        matrix.append(
            {
                "namespace": ns,
                "group": group,
                "resource": resource,
                "subresource": subresource,
                "verb": verb,
                "allowed": allowed,
            }
        )
        if allowed != required:
            raise ValueError("Intake credential failed the least-privilege matrix")
    core, batch = client.CoreV1Api(api), client.BatchV1Api(api)
    current_pod = as_dict(core.read_namespaced_pod(pod["metadata"]["name"], namespace))
    current_job = as_dict(batch.read_namespaced_job(promotion["jobName"], namespace))
    assert_target(promotion, pvc, current_job, current_pod)
    channel = stream(
        core.connect_get_namespaced_pod_exec,
        pod["metadata"]["name"],
        namespace,
        container="receiver",
        command=["python3", "/opt/evidence.py", "send"],
        stdin=True,
        stdout=True,
        stderr=True,
        tty=False,
        _preload_content=False,
    )
    try:
        with args.archive.open("rb") as archive:
            for chunk in iter(lambda: archive.read(256 * 1024), b""):
                if not channel.is_open():
                    raise ValueError("Intake exec closed before transfer finished")
                channel.write_stdin(chunk)
                channel.update(timeout=0)
        deadline = time.monotonic() + 120
        while channel.is_open() and time.monotonic() < deadline:
            channel.update(timeout=1)
        if channel.is_open() or channel.returncode != 0:
            raise ValueError("Fixed intake sender did not exit successfully")
    finally:
        channel.close()
    # Credential goes out of scope; TokenRequest is pod-bound and expires within 30 minutes.
    for _ in range(120):
        completed = as_dict(batch.read_namespaced_job(promotion["jobName"], namespace))
        status = completed.get("status", {})
        if status.get("failed"):
            raise ValueError("Receiver rejected the transferred pack")
        if status.get("succeeded"):
            report_completed(completed, matrix, issued.status.expiration_timestamp.isoformat())
            return
        time.sleep(3)
    raise ValueError("Receiver did not complete within six minutes")


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--promotion", required=True, type=Path)
    cli.add_argument("--archive", required=True, type=Path)
    cli.add_argument("--report", required=True, type=Path)
    cli.add_argument("--kubeconfig", default=os.path.expanduser("~/.kube/config"))
    run(cli.parse_args())
