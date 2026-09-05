import copy
from pathlib import Path

import pytest
import yaml
from ansible.parsing.dataloader import DataLoader
from ansible.playbook.conditional import Conditional
from ansible.template import Templar

ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize("case", ["ready", "missing", "wrong-type", "missing-key", "wrong-source"])
def test_authentik_requires_the_native_tls_mirror_without_writing_certificates(case):
    tasks = yaml.safe_load((ROOT / "roles/apps/authentik/tasks/certificate.yml").read_text())
    secret = {
        "type": "kubernetes.io/tls",
        "data": {"tls.crt": "synthetic", "tls.key": "synthetic"},
        "metadata": {
            "annotations": {
                "reflector.v1.k8s.emberstack.com/reflects": "cert-manager/prod-cert-tls"
            }
        },
    }
    if case == "wrong-type":
        secret["type"] = "Opaque"
    elif case == "missing-key":
        secret["data"].pop("tls.key")
    elif case == "wrong-source":
        secret["metadata"]["annotations"].clear()
    variables = {
        "authentik_wildcard_certificate": {
            "resources": [] if case == "missing" else [copy.deepcopy(secret)]
        }
    }
    for task in tasks:
        modules = [key for key in task if "." in key]
        assert modules == ["kubernetes.core.k8s_info"]
        assert task[modules[0]]["kind"] == "Secret"
        assert task[modules[0]]["namespace"] == "authentik"
        assert task[modules[0]]["name"] == "prod-cert-tls"
        assert task["no_log"] is True
        loader = DataLoader()
        condition = Conditional(loader=loader)
        condition.when = task["until"]
        assert condition.evaluate_conditional(
            Templar(loader=loader, variables=variables), variables
        ) == (case == "ready")


def test_native_certificate_allows_the_authentik_mirror_to_be_created():
    cert = yaml.safe_load(
        (ROOT / "apps/cert-manager-config/manifests/prod-certificate.yaml").read_text()
    )
    annotations = cert["spec"]["secretTemplate"]["annotations"]
    prefix = "reflector.v1.k8s.emberstack.com/"
    assert annotations[prefix + "reflection-allowed"] == "true"
    assert annotations[prefix + "reflection-auto-enabled"] == "true"
    assert "authentik" in annotations[prefix + "reflection-allowed-namespaces"].split(",")
    assert "authentik" in annotations[prefix + "reflection-auto-namespaces"].split(",")
