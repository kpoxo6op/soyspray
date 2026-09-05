import copy
import json
import subprocess

import pytest

from scripts import app_runtime, app_status


def workload(kind, name, uid, parent=None, namespace="crew", group="apps"):
    metadata = {"name": name, "namespace": namespace, "uid": uid}
    if parent:
        metadata["ownerReferences"] = [{"uid": parent, "controller": True}]
    return {"apiVersion": group + "/v1" if group else "v1", "kind": kind, "metadata": metadata}


@pytest.fixture
def observation():
    app = {
        "kind": "Application",
        "metadata": {"name": "crew"},
        "spec": {"destination": {"server": "https://kubernetes.default.svc", "namespace": "crew"}},
        "status": {
            "resources": [
                {"group": "apps", "kind": "Deployment", "namespace": "crew", "name": "web"}
            ]
        },
    }
    deployment = workload("Deployment", "web", "deployment")
    replica = workload("ReplicaSet", "web-new", "replica", "deployment")
    pod = workload("Pod", "web-new-one", "pod", "replica", group="")
    pod["spec"] = {
        "containers": [
            {
                "name": "web",
                "image": "example/web:mutable",
                "env": [{"name": "TOKEN", "value": "private-value"}],
            }
        ]
    }
    pod["status"] = {
        "phase": "Running",
        "containerStatuses": [
            {
                "name": "web",
                "ready": True,
                "imageID": "example/web@sha256:" + "a" * 64,
                "state": {"running": {"startedAt": "2026-09-06T00:00:00Z"}},
            }
        ],
    }
    return app, {"kind": "List", "items": [pod, replica, deployment]}


def test_uid_chain_reports_actual_image_without_environment(observation):
    app, data = observation
    result = app_runtime.runtime_status(app, data)
    container = result["value"][0]["containers"][0]
    assert container["pod_image"]["value"] == "example/web:mutable"
    assert container["image_id"]["value"].endswith("a" * 64)
    assert container["ready"]["value"] is True
    assert "private-value" not in json.dumps(result)


@pytest.mark.parametrize(
    "change", ["different-uid", "different-namespace", "non-controller", "labels-only"]
)
def test_unrelated_pods_are_not_claimed(observation, change):
    app, data = observation
    metadata = data["items"][0]["metadata"]
    if change == "different-uid":
        metadata["ownerReferences"][0]["uid"] = "unrelated"
    elif change == "different-namespace":
        metadata["namespace"] = "other"
    elif change == "non-controller":
        metadata["ownerReferences"][0]["controller"] = False
    else:
        metadata.pop("ownerReferences")
        metadata["labels"] = {"argocd.argoproj.io/instance": "crew"}
    assert app_runtime.runtime_status(app, data)["value"] == "unknown"


def test_rollout_keeps_old_pending_and_init_images_visible(observation):
    app, data = observation
    old = copy.deepcopy(data["items"][0])
    old["metadata"].update(name="web-old", uid="old", deletionTimestamp="2026-09-06T00:00:00Z")
    old["status"]["containerStatuses"][0]["imageID"] = "example/web@sha256:" + "b" * 64
    data["items"].append(old)
    pod = data["items"][0]
    pod["status"] = {
        "phase": "Pending",
        "initContainerStatuses": [
            {
                "name": "setup",
                "ready": False,
                "imageID": "example/setup@sha256:" + "c" * 64,
                "state": {"terminated": {"exitCode": 0}},
            }
        ],
    }
    pod["spec"]["initContainers"] = [{"name": "setup", "image": "example/setup:1"}]
    rows = app_runtime.runtime_status(app, data)["value"]
    assert len(rows) == 2
    pending = next(row for row in rows if not row["terminating"])
    assert pending["containers"][0]["image_id"]["value"] == "unknown"
    assert pending["containers"][1]["role"] == "init"
    assert pending["containers"][1]["ready"]["value"] is False
    assert pending["containers"][1]["state"]["value"] == "terminated"
    assert next(row for row in rows if row["terminating"])["containers"][0]["image_id"][
        "value"
    ].endswith("b" * 64)


def test_operator_owned_pods_follow_native_uids(observation):
    app, data = observation
    app["status"]["resources"] = [
        {"group": "postgresql.cnpg.io", "kind": "Cluster", "namespace": "crew", "name": "db"}
    ]
    data["items"] = [
        data["items"][0],
        workload("Cluster", "db", "database", group="postgresql.cnpg.io"),
    ]
    data["items"][0]["metadata"]["ownerReferences"][0]["uid"] = "database"
    assert len(app_runtime.runtime_status(app, data)["value"]) == 1
    app["spec"]["destination"]["server"] = "https://another-cluster"
    assert app_runtime.runtime_status(app, data)["value"] == "unknown"


def test_workload_read_uses_only_explicit_read_only_resource_kinds(observation, monkeypatch):
    app, data = observation
    app["status"]["resources"].append({"kind": "Secret", "name": "private", "namespace": "crew"})

    def run(command, **kwargs):
        assert command == [
            "kubectl",
            "--request-timeout=10s",
            "get",
            "deployments.apps,jobs.batch,pods,replicasets.apps,statefulsets.apps",
            "-A",
            "-o",
            "json",
        ]
        assert kwargs["timeout"] == 20
        return subprocess.CompletedProcess(command, 0, json.dumps(data), "")

    monkeypatch.setattr(app_runtime.subprocess, "run", run)
    assert app_runtime.read_workloads([app]) == data


def test_failed_workload_read_does_not_expose_command_output(observation, monkeypatch):
    app, _ = observation

    def run(command, **kwargs):
        return subprocess.CompletedProcess(command, 1, "private-output", "private-error")

    monkeypatch.setattr(app_runtime.subprocess, "run", run)
    with pytest.raises(ValueError) as error:
        app_runtime.read_workloads([app])
    assert "private" not in str(error.value)


@pytest.mark.parametrize("failure", [False, "bad-json", "bad-records"])
def test_offline_runtime_input_preserves_argo_status_without_api_calls(
    observation, tmp_path, monkeypatch, capsys, failure
):
    app, data = observation
    app["status"]["health"] = {"status": "Healthy"}
    source = tmp_path / "app.json"
    source.write_text(json.dumps(app))
    runtime = tmp_path / "runtime.json"
    runtime.write_text(
        "bad" if failure == "bad-json" else json.dumps({"items": [None]} if failure else data)
    )

    def forbidden(*args, **kwargs):
        raise AssertionError("Offline status must not call Kubernetes")

    monkeypatch.setattr(app_runtime.subprocess, "run", forbidden)
    code = app_status.main(
        [
            "status",
            "--app",
            "crew",
            "--format",
            "json",
            "--input",
            str(source),
            "--runtime-input",
            str(runtime),
        ]
    )
    row = json.loads(capsys.readouterr().out)["applications"][0]
    assert row["health"]["value"] == "Healthy"
    assert code == (2 if failure else 0)
    assert (row["runtime"]["value"] == "unknown") == bool(failure)
