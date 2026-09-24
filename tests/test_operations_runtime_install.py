from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "apps/cluster-diagnosis/install.yml"
RUNTIME_INSTALLER = ROOT / "playbooks/operations/runtime/install.yml"


def test_the_laptop_diagnosis_job_is_retired_not_installed() -> None:
    """Diagnosis runs in the cluster; the runtime must not install a laptop job."""
    installer = RUNTIME_INSTALLER.read_text()
    assert "cluster-diagnosis/install.yml" not in installer
    assert "openclaw cron add" not in installer
    assert not (ROOT / "apps/cluster-diagnosis/install.yml").exists()

    retirement = yaml.safe_load(
        (ROOT / "playbooks/operations/retirement/laptop-cluster-diagnosis.yml").read_text()
    )[0]
    names = [task["name"] for task in retirement["tasks"]]
    remove = retirement["tasks"][names.index("Stop and remove the laptop diagnosis job")]
    assert remove["ansible.builtin.command"]["argv"][:3] == ["openclaw", "cron", "rm"]
    assert remove["loop"] == "{{ cluster_diagnosis_matches | default([]) }}"


def test_the_saved_evidence_endpoint_survives_the_diagnosis_retirement() -> None:
    """The endpoint serves backup and restore evidence, so it must still install."""
    play = yaml.safe_load(
        (ROOT / "playbooks/operations/recovery/install-evidence-schedule.yml").read_text()
    )[0]
    names = [task["name"] for task in play["tasks"]]
    unit = play["tasks"][names.index("Install the saved evidence endpoint")][
        "ansible.builtin.template"
    ]
    assert unit["src"] == "systemd/soyspray-evidence-metrics.service.j2"
    template = (
        ROOT / "playbooks/operations/recovery/systemd/soyspray-evidence-metrics.service.j2"
    ).read_text()
    assert "X-Soyspray-Revision={{ evidence_revision }}" in template
    assert "--serve-only" in template
    service = play["tasks"][names.index("Enable the saved evidence endpoint")][
        "ansible.builtin.systemd_service"
    ]
    assert "restarted" in service["state"]
    route = play["tasks"][names.index("Enable the numeric endpoint reply route")][
        "ansible.builtin.systemd_service"
    ]
    assert route["enabled"] is True


def test_runtime_uses_the_minimal_recovery_dependencies() -> None:
    recovery = (ROOT / "requirements-recovery.txt").read_text().splitlines()
    development = (ROOT / "requirements-dev.txt").read_text().splitlines()
    installer = RUNTIME_INSTALLER.read_text()

    assert all("==" in requirement for requirement in recovery)
    assert {requirement.split("==", 1)[0].lower() for requirement in recovery} == {
        "ansible-core",
        "bcrypt",
        "cryptography",
        "jmespath",
        "netaddr",
        "passlib",
        "pyyaml",
    }
    assert development[0] == "-r requirements-recovery.txt"
    assert "requirements-recovery.txt" in installer
    assert "requirements-dev.txt" not in installer
    assert "- --force" in installer
    assert "npm" not in installer
    assert "playwright" not in installer
    assert "make, go" not in installer


def test_runtime_checks_the_exact_release_and_recovery_playbooks() -> None:
    play = yaml.safe_load(RUNTIME_INSTALLER.read_text())[0]
    tasks = play["tasks"]
    names = [task["name"] for task in tasks]

    status = tasks[names.index("Verify tracked files in the installed release")]
    assert status["ansible.builtin.command"]["argv"] == [
        "git",
        "status",
        "--porcelain",
        "--untracked-files=no",
    ]
    revision = tasks[names.index("Read the installed release revision")]
    assert revision["ansible.builtin.command"]["argv"] == ["git", "rev-parse", "HEAD"]

    ancestry = tasks[names.index("Require the exact revision to be part of the pushed branch")][
        "ansible.builtin.command"
    ]["argv"]
    assert isinstance(ancestry, list), ancestry
    assert ancestry[:3] == ["git", "merge-base", "--is-ancestor"], (
        "an older pushed revision must still be installable for rollback"
    )
    refuse = tasks[names.index("Refuse a revision that is not on the pushed branch")]
    assert refuse["ansible.builtin.assert"]["that"] == [
        "operations_remote_main.stdout | length > 0",
        "operations_ancestry.rc == 0",
    ]

    syntax = tasks[names.index("Check the emergency recovery playbooks")]
    assert "--syntax-check" in syntax["ansible.builtin.command"]["argv"]
    assert syntax["loop"] == [
        "playbooks/operations/recovery/restore-volume.yml",
        "playbooks/operations/recovery/validate-durable.yml",
        "apps/recovery-input-backup/collect.yml",
        "kubespray/remove-node.yml",
        "kubespray/cluster.yml",
    ]
