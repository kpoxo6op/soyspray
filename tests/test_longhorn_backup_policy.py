import copy
from pathlib import Path

import pytest
import yaml
from ansible.parsing.dataloader import DataLoader
from ansible.playbook.conditional import Conditional
from ansible.template import Templar

RECOVERY = Path(__file__).resolve().parents[1] / "playbooks/operations/recovery"
CONFIGURE = yaml.safe_load((RECOVERY / "configure-longhorn.yml").read_text())[0]
RUN = yaml.safe_load((RECOVERY / "backup-daily-now.yml").read_text())[0]


def evaluate(expressions, variables):
    loader = DataLoader()
    condition = Conditional(loader=loader)
    condition.when = expressions if isinstance(expressions, list) else [expressions]
    return condition.evaluate_conditional(Templar(loader=loader, variables=variables), variables)


def test_explicit_groups_preserve_critical_retention_and_exclude_other_data():
    claims = CONFIGURE["vars"]["recovery_claims"]
    critical = {(c["namespace"], c["claim"]) for c in claims if c["group"] == "critical"}
    assert critical == {
        ("boys", "boys-data"),
        ("vaultwarden", "vaultwarden-data"),
        ("obsidian", "obsidian-livesync-couchdb-rescue-longhorn"),
    }
    assert all(c["group"] in {"critical", "durable-small"} for c in claims)
    selected = {(c["namespace"], c["claim"]) for c in claims}
    assert not selected & {
        ("media", "jellyfin-config"),
        ("media", "media-downloads"),
        ("immich", "immich-library"),
        ("home-automation", "piper-en-data-v1"),
        ("home-automation", "speech-to-phrase-data-v1"),
    }
    assert not any(c["namespace"] in {"monitoring", "postgresql", "authentik"} for c in claims)
    policies = list(yaml.safe_load_all((RECOVERY / "longhorn-jobs.yaml").read_text()))
    actual = {
        p["metadata"]["name"]: (p["spec"]["groups"], p["spec"]["cron"], p["spec"]["retain"])
        for p in policies
    }
    assert actual == {
        "critical-recent": (["critical"], "*/30 * * * *", 48),
        "critical-daily": (["critical"], "15 14 * * *", 30),
        "durable-small-daily": (["durable-small"], "45 15 * * *", 30),
    }
    assert all(p["spec"]["task"] == "backup-force-create" for p in policies)


@pytest.mark.parametrize("claim", CONFIGURE["vars"]["recovery_claims"], ids=lambda c: c["app"])
def test_group_patch_preserves_volume_identity_and_is_retryable(claim):
    task = next(t for t in CONFIGURE["tasks"] if "kubernetes.core.k8s_json_patch" in t)
    volume = {
        "metadata": {"uid": "original-volume", "labels": {"unrelated": "keep"}},
        "spec": {"backupTargetName": "default", "freezeFilesystemForSnapshot": "ignored"},
    }
    item = {"resources": [volume], "item": {"item": claim}}
    variables = {**CONFIGURE["vars"], "item": item}
    assert evaluate(task["when"], variables)
    patch = Templar(loader=DataLoader(), variables=variables).template(
        task["kubernetes.core.k8s_json_patch"]["patch"]
    )
    assert patch[:2] == [
        {"op": "test", "path": "/metadata/uid", "value": "original-volume"},
        {"op": "test", "path": "/spec", "value": volume["spec"]},
    ]
    assert patch[2:] == [
        {"op": "add", "path": "/spec/backupTargetName", "value": "critical-s3"},
        {"op": "add", "path": "/spec/freezeFilesystemForSnapshot", "value": "enabled"},
        {
            "op": "add",
            "path": "/metadata/labels/recurring-job-group.longhorn.io~1" + claim["group"],
            "value": "enabled",
        },
    ]
    changed = copy.deepcopy(volume)
    changed["metadata"]["labels"]["recurring-job-group.longhorn.io/" + claim["group"]] = "enabled"
    changed["spec"].update(backupTargetName="critical-s3", freezeFilesystemForSnapshot="enabled")
    item["resources"] = [changed]
    assert not evaluate(task["when"], variables)


def daily_variables():
    template = {
        "metadata": {"labels": {"recurring-job.longhorn.io": "durable-small-daily"}},
        "spec": {"containers": [{"name": "native-manager", "image": "installed-manager"}]},
    }
    cron = {
        "metadata": {"uid": "cron-original"},
        "spec": {"jobTemplate": {"spec": {"template": template}}},
    }
    return {
        "recovery_daily": {"results": [{"resources": []}, {"resources": [cron]}]},
        "recovery_daily_job": "backup-durable-small-test",
        "kubeconfig_path": "/test",
    }


@pytest.mark.parametrize(
    "change",
    [
        {},
        {"claimRef": {"uid": "replacement", "namespace": "media", "name": "data"}},
        {"csi": {"driver": "other", "volumeHandle": "pv"}},
        {"csi": {"driver": "driver.longhorn.io", "volumeHandle": "other"}},
    ],
)
def test_backup_rejects_a_rebound_claim_or_different_storage(change):
    spec = {
        "claimRef": {"uid": "original", "namespace": "media", "name": "data"},
        "csi": {"driver": "driver.longhorn.io", "volumeHandle": "pv"},
        **change,
    }
    item = {
        "resources": [{"metadata": {}, "spec": spec}],
        "item": {
            "resources": [{"metadata": {"uid": "original"}, "spec": {"volumeName": "pv"}}],
            "item": {"namespace": "media", "claim": "data"},
        },
    }
    task = next(
        t
        for t in CONFIGURE["tasks"]
        if "ansible.builtin.assert" in t and "spec.claimRef.uid" in str(t["ansible.builtin.assert"])
    )
    assert evaluate(task["ansible.builtin.assert"]["that"], {"item": item}) is (not change)


@pytest.mark.parametrize(
    "check_mode,existing,creates",
    [(False, False, True), (True, False, False), (False, True, False)],
)
def test_daily_run_uses_native_template_and_never_overwrites_a_retry(check_mode, existing, creates):
    variables = daily_variables()
    variables.update(
        ansible_check_mode=check_mode,
        recovery_daily_existing={"resources": [{}] if existing else []},
    )
    task = next(t for t in RUN["tasks"] if "kubernetes.core.k8s" in t)
    assert evaluate(task["when"], variables) is creates
    rendered = Templar(loader=DataLoader(), variables=variables).template(
        task["kubernetes.core.k8s"]["definition"]
    )
    assert (
        rendered["spec"]["template"]
        == variables["recovery_daily"]["results"][1]["resources"][0]["spec"]["jobTemplate"]["spec"][
            "template"
        ]
    )
    assert rendered["metadata"]["annotations"]["soyspray.vip/cronjob-uid"] == "cron-original"


def test_daily_retry_allows_controller_labels_but_rejects_a_changed_template():
    variables = daily_variables()
    template = copy.deepcopy(
        variables["recovery_daily"]["results"][1]["resources"][0]["spec"]["jobTemplate"]["spec"][
            "template"
        ]
    )
    template["metadata"]["labels"].update(
        {"batch.kubernetes.io/job-name": "backup-durable-small-test", "controller-uid": "job-uid"}
    )
    job = {
        "metadata": {
            "labels": {"soyspray.vip/purpose": "backup-check"},
            "annotations": {"soyspray.vip/cronjob-uid": "cron-original"},
        },
        "spec": {"template": template},
    }
    variables["recovery_daily_existing"] = {"resources": [job]}
    task = next(
        t
        for t in RUN["tasks"]
        if "ansible.builtin.assert" in t
        and "when" in t
        and "recovery_daily_existing" in str(t["when"])
    )
    assert evaluate(task["ansible.builtin.assert"]["that"], variables)
    template["spec"]["containers"][0]["image"] = "unexpected-image"
    assert not evaluate(task["ansible.builtin.assert"]["that"], variables)
