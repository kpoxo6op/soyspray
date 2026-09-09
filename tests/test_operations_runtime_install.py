from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "apps/cluster-diagnosis/install.yml"


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
