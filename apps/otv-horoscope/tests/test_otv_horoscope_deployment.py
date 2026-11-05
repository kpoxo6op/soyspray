"""Deployment safety and digest promotion for the horoscope recorder."""

import importlib.util
import shutil
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("promote", ROOT / "promote-image.py")
promote = importlib.util.module_from_spec(spec)
spec.loader.exec_module(promote)
DIGEST = "ghcr.io/kpoxo6op/otv-horoscope@sha256:" + "a" * 64


def deployment(root=ROOT):
    return yaml.safe_load((root / "manifests/deployment.yaml").read_text())


def test_recorder_runs_unprivileged_with_a_bounded_disposable_buffer():
    pod = deployment()["spec"]["template"]["spec"]
    (container,) = pod["containers"]
    security = container["securityContext"]
    assert security["runAsNonRoot"] and security["readOnlyRootFilesystem"]
    assert security["capabilities"]["drop"] == ["ALL"]
    assert not security["allowPrivilegeEscalation"]
    assert pod["automountServiceAccountToken"] is False
    volumes = {volume["name"]: volume for volume in pod["volumes"]}
    assert set(volumes) == {"work", "tmp", "recipients"}
    buffers = [volumes["work"], volumes["tmp"]]
    assert all("emptyDir" in volume and "sizeLimit" in volume["emptyDir"] for volume in buffers)
    assert container["resources"]["limits"]["ephemeral-storage"]


def test_telegram_identity_comes_only_from_the_bootstrap_secret():
    (container,) = deployment()["spec"]["template"]["spec"]["containers"]
    env = {item["name"]: item for item in container["env"]}
    ref = env["TELEGRAM_BOT_TOKEN"]["valueFrom"]["secretKeyRef"]
    assert (ref["name"], ref["key"]) == ("otv-horoscope-telegram", "bot-token")
    assert "value" not in env["TELEGRAM_BOT_TOKEN"]


def test_the_chat_list_is_a_mounted_secret_file_so_new_recipients_need_no_restart():
    pod = deployment()["spec"]["template"]["spec"]
    (container,) = pod["containers"]
    env = {item["name"]: item for item in container["env"]}
    assert "TELEGRAM_CHAT_IDS" not in env
    volume = next(v for v in pod["volumes"] if v["name"] == "recipients")
    assert volume["secret"]["secretName"] == "otv-horoscope-telegram"
    assert volume["secret"]["items"] == [{"key": "chat-ids", "path": "chat-ids"}]
    mount = next(m for m in container["volumeMounts"] if m["name"] == "recipients")
    assert mount["readOnly"] and "subPath" not in mount  # subPath mounts never refresh
    assert env["TELEGRAM_CHAT_IDS_FILE"]["value"] == f"{mount['mountPath']}/chat-ids"


def test_promotion_changes_only_the_image(tmp_path):
    app = tmp_path / "app"
    shutil.copytree(ROOT / "manifests", app / "manifests")
    before = deployment(app)
    promote.promote(DIGEST, app)
    after = deployment(app)
    assert after["spec"]["template"]["spec"]["containers"][0]["image"] == DIGEST
    after["spec"]["template"]["spec"]["containers"][0]["image"] = before["spec"]["template"][
        "spec"
    ]["containers"][0]["image"]
    assert after == before


def test_promotion_rejects_tags_and_command_overrides(tmp_path):
    app = tmp_path / "app"
    shutil.copytree(ROOT / "manifests", app / "manifests")
    with pytest.raises(ValueError):
        promote.promote("ghcr.io/kpoxo6op/otv-horoscope:latest", app)
    manifest = deployment(app)
    manifest["spec"]["template"]["spec"]["containers"][0]["command"] = ["sh"]
    (app / "manifests/deployment.yaml").write_text(yaml.safe_dump(manifest))
    with pytest.raises(ValueError):
        promote.promote(DIGEST, app)


def test_application_cannot_prune_or_cascade_and_follows_main():
    application = yaml.safe_load((ROOT / "argocd/application.yaml").read_text())
    assert (
        "Prune=false,Delete=false"
        in application["metadata"]["annotations"]["argocd.argoproj.io/sync-options"]
    )
    assert "finalizers" not in application["metadata"]
    assert application["spec"]["source"]["targetRevision"] == "main"
    project = yaml.safe_load((ROOT / "argocd/project.yaml").read_text())
    assert project["spec"]["clusterResourceWhitelist"] == []
    assert project["spec"]["namespaceResourceWhitelist"] == [
        {"group": "apps", "kind": "Deployment"}
    ]
