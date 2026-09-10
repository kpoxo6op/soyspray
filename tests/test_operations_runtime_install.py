from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "apps/cluster-diagnosis/install.yml"
RUNTIME_INSTALLER = ROOT / "playbooks/operations/runtime/install.yml"


def test_diagnosis_reinstall_preserves_private_target_and_enabled_state() -> None:
    play = yaml.safe_load(INSTALLER.read_text())[0]
    tasks = play["tasks"]
    names = [task["name"] for task in tasks]
    preserve = tasks[names.index("Preserve the existing private target and schedule state")]
    values = preserve["ansible.builtin.set_fact"]

    assert (
        "diagnosis_matches[0].payload.env.TELEGRAM_TARGET"
        in values["diagnosis_effective_telegram_target"]
    )
    assert "diagnosis_matches[0].enabled" in values["diagnosis_effective_enabled"]
    options = tasks[names.index("Prepare the native command arguments")][
        "ansible.builtin.set_fact"
    ]["diagnosis_job_options"]
    assert "TELEGRAM_TARGET={{ diagnosis_effective_telegram_target }}" in options
    edit = tasks[names.index("Apply the requested command job state")]["ansible.builtin.command"][
        "argv"
    ]
    assert "diagnosis_effective_enabled" in edit


def test_runtime_uses_the_minimal_recovery_dependencies() -> None:
    recovery = (ROOT / "requirements-recovery.txt").read_text().splitlines()
    development = (ROOT / "requirements-dev.txt").read_text().splitlines()
    installer = RUNTIME_INSTALLER.read_text()

    assert recovery == [
        "ansible-core==2.18.18",
        "cryptography==46.0.7",
        "jmespath==1.1.0",
        "netaddr==1.3.0",
        "passlib==1.7.4",
        "PyYAML==6.0.3",
    ]
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

    syntax = tasks[names.index("Check the emergency recovery playbooks")]
    assert "--syntax-check" in syntax["ansible.builtin.command"]["argv"]
    assert syntax["loop"] == [
        "playbooks/operations/recovery/restore-volume.yml",
        "playbooks/operations/recovery/validate-durable.yml",
        "apps/recovery-input-backup/collect.yml",
        "playbooks/operations/storage/evacuate-node2.yml",
        "playbooks/operations/storage/restore-node2-replicas.yml",
        "playbooks/operations/nodes/remove-node2.yml",
        "playbooks/operations/nodes/clean-node2-baseline.yml",
        "playbooks/operations/nodes/rejoin-node2.yml",
    ]
