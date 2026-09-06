import copy
import importlib
import json
import ssl
import subprocess
from datetime import UTC, datetime

import pytest

smoke = importlib.import_module("apps.cert-manager-config.smoke")
NOW = datetime(2026, 9, 6, tzinfo=UTC)
RESOURCE = {
    "kind": "Certificate",
    "metadata": {"name": "prod-cert", "generation": 2},
    "status": {
        "conditions": [{"type": "Ready", "status": "True", "observedGeneration": 2}],
        "notBefore": "2026-09-01T00:00:00Z",
        "notAfter": "2026-10-01T00:00:00Z",
    },
}


@pytest.mark.parametrize(
    "change, expected",
    [
        ("ready", "passed"),
        ("stale", "unknown"),
        ("no-observation", "unknown"),
        ("not-ready", "failed"),
        ("expired", "failed"),
        ("future", "failed"),
        ("missing-date", "unknown"),
        ("no-timezone", "unknown"),
    ],
)
def test_readiness_requires_current_observation_and_valid_dates(change, expected):
    resource = copy.deepcopy(RESOURCE)
    status = resource["status"]
    if change == "stale":
        resource["metadata"]["generation"] = 3
    elif change == "no-observation":
        status["conditions"] = []
    elif change == "not-ready":
        status["conditions"][0]["status"] = "False"
    elif change == "expired":
        status["notAfter"] = NOW.isoformat()
    elif change == "future":
        status["notBefore"] = "2026-09-07T00:00:00Z"
    elif change == "missing-date":
        del status["notAfter"]
    elif change == "no-timezone":
        status["notAfter"] = "2026-10-01T00:00:00"
    assert smoke.resource_check(resource, NOW)["status"] == expected


def reader(kind, names, namespace):
    results = []
    for name in names:
        resource = copy.deepcopy(RESOURCE)
        resource["metadata"]["name"] = name
        if namespace is None:
            resource["kind"] = "ClusterIssuer"
            resource["status"].pop("notBefore")
            resource["status"].pop("notAfter")
        results.append(resource)
    return results


@pytest.mark.parametrize(
    "failure, expected",
    [
        (None, "passed"),
        (ssl.SSLCertVerificationError(), "failed"),
        (TimeoutError(), "unknown"),
        (ConnectionRefusedError(), "unknown"),
    ],
)
def test_tls_failure_is_visible_without_stopping_other_checks(failure, expected):
    seen = []

    def tls(host):
        seen.append(host)
        if failure and len(seen) == 1:
            raise failure
        return {"target": host, "status": "passed"}

    result = smoke.run(reader=reader, tls=tls, now=NOW)
    assert result["status"] == expected
    assert seen == list(smoke.HOSTS)
    assert result["renewal_and_recovery"]["status"] == "unknown"
    assert result["application_login"]["status"] == "unknown"


def test_unavailable_api_is_not_reported_as_healthy():
    def unavailable(*args):
        raise subprocess.TimeoutExpired("kubectl", 20)

    result = smoke.run(
        reader=unavailable, tls=lambda host: {"target": host, "status": "passed"}, now=NOW
    )
    assert result["status"] == "unknown"
    assert [c["status"] for c in result["checks"][:2]] == ["unknown", "unknown"]


def test_kubectl_reads_only_requested_certificate_resources_with_deadlines(monkeypatch):
    def output(argv, **kwargs):
        assert argv == [
            "kubectl",
            "--request-timeout=15s",
            "get",
            "certificates.cert-manager.io",
            "prod-cert",
            "-o",
            "json",
            "-n",
            "cert-manager",
        ]
        assert kwargs["timeout"] == 20
        return json.dumps({"items": [RESOURCE]})

    monkeypatch.setattr(smoke.subprocess, "check_output", output)
    assert smoke.read_resources("certificates.cert-manager.io", ["prod-cert"], "cert-manager") == [
        RESOURCE
    ]
    monkeypatch.setattr(smoke.subprocess, "check_output", lambda *a, **kw: b'{"items": []}')
    with pytest.raises(ValueError):
        smoke.read_resources("certificates.cert-manager.io", ["prod-cert"], "cert-manager")


@pytest.mark.parametrize("status, exit_code", [("passed", 0), ("failed", 1), ("unknown", 2)])
def test_json_output_and_exit_status(monkeypatch, capsys, status, exit_code):
    monkeypatch.setattr(smoke, "run", lambda: {"status": status})
    assert smoke.main() == exit_code
    assert json.loads(capsys.readouterr().out)["status"] == status


def test_missing_generation_does_not_appear_current():
    resource = copy.deepcopy(RESOURCE)
    del resource["metadata"]["generation"]
    del resource["status"]["conditions"][0]["observedGeneration"]
    assert smoke.resource_check(resource, NOW)["status"] == "unknown"


def test_make_smoke_stdout_is_json(tmp_path):
    import sys
    from pathlib import Path

    runner = tmp_path / "python"
    runner.write_text(f'#!{sys.executable}\nprint(\'{"{"}"status": "passed"{"}"}\')\n')
    runner.chmod(0o700)
    result = subprocess.run(
        [
            "make",
            "--no-print-directory",
            "-f",
            "apps/cert-manager-config/Makefile",
            "smoke",
            f"PYTHON={runner}",
        ],
        cwd=Path(__file__).resolve().parents[3],
        check=True,
        capture_output=True,
        text=True,
    )
    assert json.loads(result.stdout)["status"] == "passed"
