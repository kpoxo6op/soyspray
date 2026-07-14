from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
from conftest import ROOT


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def traffic(monkeypatch):
    for name in (
        "ACCOUNTS_API_KEY",
        "PAYMENTS_API_KEY",
        "CARDS_API_KEY",
        "CUSTOMERS_API_KEY",
        "FRAUD_API_KEY",
    ):
        monkeypatch.setenv(name, "test-key")
    monkeypatch.setenv("JWT_KEY", "partner")
    monkeypatch.setenv("JWT_SECRET", "secret")
    return load_module("banklab_traffic", ROOT / "kubernetes/banklab/customer-web/app/traffic.py")


def test_traffic_profiles_are_domain_specific(traffic) -> None:
    assert {profile[1] for profile in traffic.PROFILES} == {
        "accounts",
        "payments",
        "cards",
        "customer-profile",
        "fraud",
    }
    assert all(profile[2].startswith("/") for profile in traffic.PROFILES)


@pytest.mark.parametrize(
    ("counter", "scenario", "status"),
    (
        (1, "steady", 200),
        (41, "missing-credential", 401),
        (67, "unknown-route", 404),
        (97, "partner", 200),
        (113, "planned-backend-error", 500),
    ),
)
def test_planned_traffic_scenarios(traffic, counter: int, scenario: str, status: int) -> None:
    item = traffic.event(counter, traffic.PROFILES[0])
    assert item["scenario"] == scenario
    assert item["expected"] == status


def test_traffic_closes_connection_after_request_error(traffic, monkeypatch, capsys) -> None:
    class BrokenConnection:
        closed = False

        def request(self, *_args, **_kwargs) -> None:
            raise OSError("test connection failure")

        def close(self) -> None:
            self.closed = True

    connection = BrokenConnection()
    monkeypatch.setattr(
        traffic.http.client,
        "HTTPConnection",
        lambda *_args, **_kwargs: connection,
    )

    traffic.send(
        {
            "client": "test-client",
            "api": "test-api",
            "path": "/health",
            "headers": {"X-Request-ID": "test-request"},
            "expected": 200,
            "scenario": "test",
        }
    )

    assert connection.closed is True
    assert '"ok":false' in capsys.readouterr().out


def test_customer_page_has_no_development_goal_language() -> None:
    app_dir = ROOT / "kubernetes/banklab/customer-web/app"
    page = (app_dir / "index.html").read_text().lower()
    script = (app_dir / "app.js").read_text()
    assert "goal0" not in page
    assert "harbour bank" in page
    assert "gateway trace" in page
    assert '<link rel="stylesheet" href="/styles.css">' in page
    assert '<script src="/app.js" defer></script>' in page
    assert "<style>" not in page
    assert "<script>" not in page
    assert ".innerHTML" not in script
    assert "textContent" in script
    assert 'aria-busy="true"' in page


def test_customer_page_formats_numeric_nzd_balances() -> None:
    page = (ROOT / "kubernetes/banklab/customer-web/app/app.js").read_text()
    response = (ROOT / "apis/synthetic-bank/cards/default.conf").read_text()

    assert 'new Intl.NumberFormat("en-NZ"' in page
    assert '"available":1850.75,"currency":"NZD"' in response
    assert '"available":"$' not in response


def test_customer_server_delivers_static_assets_and_security_headers() -> None:
    server = (ROOT / "kubernetes/banklab/customer-web/app/server.py").read_text()
    kustomization = (ROOT / "kubernetes/banklab/customer-web/kustomization.yaml").read_text()

    assert '"/app.js"' in server
    assert '"/styles.css"' in server
    assert "Content-Security-Policy" in server
    assert "X-Content-Type-Options" in server
    assert "Referrer-Policy" in server
    assert "app/app.js" in kustomization
    assert "app/styles.css" in kustomization
