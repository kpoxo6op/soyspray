from __future__ import annotations

import json
import subprocess

from conftest import ROOT

RUNNER = ROOT / "scripts/hays-open-submitted-timesheet"


def test_hays_runner_reports_only_safe_submitted_timesheet_proof() -> None:
    result = subprocess.run(
        ["node", RUNNER, "--check-proof"],
        cwd=ROOT,
        input="Timesheet Details\nTimesheet Received on 26/08/2026\n40 hours\n"
        "PRIVATE_ACCOUNT 1234567 PASSWORD=synthetic\n",
        check=True,
        capture_output=True,
        text=True,
    )

    assert json.loads(result.stdout) == {
        "status": "opened",
        "page": "submitted-timesheet",
        "receivedOn": "26/08/2026",
    }


def test_hays_runner_keeps_its_dedicated_browser_and_secret_helper() -> None:
    # The live browser and credential path cannot be exercised in repository CI.
    source = RUNNER.read_text()
    assert 'path.join(stateRoot, "hays-agent-chrome")' in source
    assert 'path.join(__dirname, "agent-secret")' in source
    assert "google-chrome-codex" not in source


def test_hays_runner_rejects_a_page_that_is_not_submitted_timesheet_details() -> None:
    page_text = "Job List\nNo submitted timesheet is open\n"
    result = subprocess.run(
        ["node", RUNNER, "--check-proof"],
        cwd=ROOT,
        input=page_text,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "submitted timesheet details" in result.stderr
    assert page_text not in result.stderr
