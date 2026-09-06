import sqlite3
from pathlib import Path

import pytest
import yaml

from scripts.check_durable_data import check

ROOT = Path(__file__).resolve().parents[1]


def test_catalog_preserves_critical_identities_and_daily_claims():
    catalog = yaml.safe_load(
        (ROOT / "playbooks/operations/recovery/recovery-claims.yml").read_text()
    )["recovery_claims"]
    configured = yaml.safe_load(
        (ROOT / "playbooks/operations/recovery/configure-longhorn.yml").read_text()
    )[0]["vars"]["recovery_claims"]
    for row in configured:
        assert (row["namespace"], row["claim"]) in {
            (value["namespace"], value["claim"]) for value in catalog.values()
        }
    assert catalog["boys"] == {"namespace": "boys", "claim": "boys-data"}
    assert catalog["vaultwarden"] == {"namespace": "vaultwarden", "claim": "vaultwarden-data"}
    assert catalog["obsidian"]["claim"] == "obsidian-livesync-couchdb-rescue-longhorn"


def test_restored_sqlite_checks_real_rows(tmp_path):
    with sqlite3.connect(tmp_path / "app.db") as db:
        db.execute("create table records (value text)")
        db.execute("insert into records values ('restore fixture')")
    result = check(tmp_path)
    assert result["file_count"] == 1
    assert result["files"][0]["sqlite_rows"] == {"records": 1}


def test_invalid_restored_json_is_rejected(tmp_path):
    (tmp_path / "config.json").write_text("{broken")
    with pytest.raises(ValueError):
        check(tmp_path)


def test_empty_volume_is_explicit(tmp_path):
    assert check(tmp_path)["content"] == "empty volume"


@pytest.mark.parametrize(
    "app,uid",
    [
        ("booklore-mariadb", 1000),
        ("dispatcharr-data", 1000),
        ("redis-data-redis-master-0", 1001),
        ("mosquitto-data", 1883),
    ],
)
def test_native_restore_security_context_keeps_numeric_uid(app, uid):
    from ansible.parsing.dataloader import DataLoader
    from ansible.template import Templar

    play = yaml.safe_load(
        (ROOT / "playbooks/operations/recovery/validate-durable.yml").read_text()
    )[0]
    job = next(
        t["kubernetes.core.k8s"]["definition"] for t in play["tasks"] if "kubernetes.core.k8s" in t
    )
    context = Templar(loader=DataLoader(), variables={"recovery_app": app}).template(
        job["spec"]["template"]["spec"]["securityContext"]
    )
    assert type(context["runAsUser"]) is int
    assert context["runAsUser"] == context["runAsGroup"] == uid
    assert job["spec"]["template"]["spec"]["automountServiceAccountToken"] is False


@pytest.mark.parametrize(
    "app,read_only",
    [("boys", False), ("vaultwarden", False), ("obsidian", False), ("dispatcharr-data", True)],
)
def test_daily_inspector_reads_mixed_owners_without_changing_critical_pods(app, read_only):
    from ansible.parsing.dataloader import DataLoader
    from ansible.template import Templar

    play = yaml.safe_load((ROOT / "playbooks/operations/recovery/restore-volume.yml").read_text())[
        0
    ]
    pod = next(
        t["kubernetes.core.k8s"]["definition"]
        for t in play["tasks"]
        if isinstance(t.get("kubernetes.core.k8s", {}).get("definition"), dict)
        and t["kubernetes.core.k8s"]["definition"].get("kind") == "Pod"
    )
    container = pod["spec"]["containers"][0]
    template = Templar(loader=DataLoader(), variables={"recovery_app": app})
    caps = template.template(container["securityContext"]["capabilities"])
    mount = template.template(container["volumeMounts"])[0]
    assert caps == (
        {"drop": ["ALL"], "add": ["DAC_READ_SEARCH"]} if read_only else {"drop": ["ALL"]}
    )
    assert mount["readOnly"] is read_only


def test_mariadb_uses_the_writable_temporary_mount():
    import shlex

    command = (
        (ROOT / "playbooks/operations/recovery/validators/booklore-mariadb.sh")
        .read_text()
        .splitlines()[2]
    )
    assert "--tmpdir=/tmp" in shlex.split(command)
