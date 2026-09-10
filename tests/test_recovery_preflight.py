import subprocess
from pathlib import Path

import pytest

from scripts import recovery_preflight

ROOT = Path(__file__).resolve().parents[1]


def result(argv, code=0, output=""):
    return subprocess.CompletedProcess(argv, code, stdout=output, stderr="")


def runner_for(*, head="revision", main="revision", dirty=False, syntax=0):
    def run(argv, root):
        if argv[:3] == ["git", "rev-parse", "HEAD"]:
            return result(argv, output=head + "\n")
        if argv[:3] == ["git", "rev-parse", "origin/main"]:
            return result(argv, output=main + "\n")
        if argv[:2] == ["git", "status"]:
            return result(argv, output=" M tracked\n" if dirty else "")
        if argv[:2] == ["git", "ls-files"]:
            return result(argv)
        if argv[:4] == ["git", "-C", "kubespray", "ls-files"]:
            return result(argv)
        if "--syntax-check" in argv:
            return result(argv, code=syntax)
        raise AssertionError(argv)

    return run


def test_preflight_uses_only_recovery_runtime_and_delivered_source(monkeypatch) -> None:
    monkeypatch.setattr(recovery_preflight.shutil, "which", lambda tool: f"/usr/bin/{tool}")
    monkeypatch.setattr(recovery_preflight.importlib.util, "find_spec", lambda module: object())

    assert (
        recovery_preflight.validate(ROOT, ["boys"], runner=runner_for(), is_file=lambda path: True)
        == "revision"
    )


def test_durable_preflight_checks_its_shared_runner_not_a_fake_app_folder() -> None:
    assert recovery_preflight.operation_sources(["durable"]) == ["scripts/restore_durable.py"]


@pytest.mark.parametrize(
    "runner,message",
    [
        (runner_for(main="other"), "exact delivered main"),
        (runner_for(dirty=True), "tracked changes"),
        (runner_for(syntax=2), "syntax validation"),
    ],
)
def test_preflight_rejects_unvalidated_recovery_source(monkeypatch, runner, message) -> None:
    monkeypatch.setattr(recovery_preflight.shutil, "which", lambda tool: f"/usr/bin/{tool}")
    monkeypatch.setattr(recovery_preflight.importlib.util, "find_spec", lambda module: object())

    with pytest.raises(ValueError, match=message):
        recovery_preflight.validate(ROOT, ["boys"], runner=runner, is_file=lambda path: True)
