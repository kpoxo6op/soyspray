from __future__ import annotations

import importlib.util
from pathlib import Path

from conftest import ROOT


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


def test_status_classifies_complete_lifecycle_states() -> None:
    status = load_module("banklab_status", ROOT / "scripts/banklab_status.py")

    assert status.classify_applications({"banklab-kong-crds"}) == "OFF"
    assert status.classify_applications(status.EXPECTED_APPLICATIONS) == "ON"
    assert status.classify_applications({"banklab-kong-crds", "banklab-kong"}) == "PARTIAL"


def test_smoke_proves_rate_limit_and_recovery(monkeypatch, capsys) -> None:
    smoke = load_module("banklab_smoke", ROOT / "scripts/banklab_smoke.py")
    responses = iter(
        [
            (200, "ok"),
            (200, "ok"),
            (200, "ok"),
            (429, "limited"),
            (200, "banklab-accounts-ok"),
        ]
    )
    monkeypatch.setattr(smoke, "request", lambda *_args, **_kwargs: next(responses))
    monkeypatch.setattr(smoke.time, "sleep", lambda _seconds: None)

    assert smoke.check_rate_limit("proxy", "key") is True
    output = capsys.readouterr().out
    assert "rate limit rejects a burst" in output
    assert "rate limit window recovers" in output
