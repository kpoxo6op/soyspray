import base64
from pathlib import Path

import pytest
import yaml
from ansible.parsing.dataloader import DataLoader
from ansible.playbook.conditional import Conditional
from ansible.template import Templar

ROOT = Path(__file__).resolve().parents[3]
TASKS = yaml.safe_load((ROOT / "apps/cert-manager-config/bootstrap-tasks.yml").read_text())
TOKEN = "synthetic-token"


def allowed(expression, variables):
    loader = DataLoader()
    condition = Conditional(loader=loader)
    condition.when = expression if isinstance(expression, list) else [expression]
    return condition.evaluate_conditional(Templar(loader=loader, variables=variables), variables)


@pytest.mark.parametrize("existing", [True, False])
@pytest.mark.parametrize("namespace", [True, False])
@pytest.mark.parametrize("check_mode", [True, False])
@pytest.mark.parametrize("supplied", ["missing", TOKEN, "different", "", " ", None, 123, {}])
def test_provider_bootstrap_preserves_identity_and_creates_only_missing_secret(
    existing, namespace, check_mode, supplied
):
    variables = {
        "kubeconfig_path": "/test",
        "ansible_check_mode": check_mode,
        "cert_manager_namespace": {"resources": [{}] if namespace else []},
        "cert_manager_existing_token": {
            "resources": [{"data": {"api-token": base64.b64encode(TOKEN.encode()).decode()}}]
            if existing
            else []
        },
    }
    if supplied != "missing":
        variables["cert_manager_cloudflare_api_token"] = supplied
    writes = []
    passed = True
    for task in TASKS:
        templar = Templar(loader=DataLoader(), variables=variables)
        if "ansible.builtin.set_fact" in task:
            assert task["no_log"] is True
            variables.update(templar.template(task["ansible.builtin.set_fact"]))
        if "ansible.builtin.assert" in task and not allowed(
            task["ansible.builtin.assert"]["that"], variables
        ):
            passed = False
            break
        if "ansible.builtin.command" in task and allowed(task["when"], variables):
            command = templar.template(task["ansible.builtin.command"])
            assert task["no_log"] is True
            assert command["argv"] == ["kubectl", "--kubeconfig", "/test", "create", "-f", "-"]
            value = command["stdin"]
            writes.append(yaml.safe_load(value) if isinstance(value, str) else value)
        assert "kubernetes.core.k8s" not in task  # No namespace or existing Secret mutation.
    selected = (TOKEN if existing else "") if supplied == "missing" else supplied
    valid = isinstance(selected, str) and bool(selected.strip())
    expected = namespace and valid and (not existing or selected == TOKEN)
    assert passed == expected
    assert writes == (
        [
            {
                "apiVersion": "v1",
                "kind": "Secret",
                "metadata": {"name": "cloudflare-api-token", "namespace": "cert-manager"},
                "type": "Opaque",
                "stringData": {"api-token": selected},
            }
        ]
        if expected and not existing and not check_mode
        else []
    )


def test_public_repository_bootstrap_preserves_existing_chart_identity():
    tasks = yaml.safe_load((ROOT / "argocd/bootstrap/repositories.yml").read_text())
    templar = Templar(
        loader=DataLoader(),
        variables={
            "playbook_dir": str(ROOT / "playbooks"),
            "kubeconfig_path": "/test",
        },
    )
    resource = templar.template(tasks[0]["kubernetes.core.k8s"]["definition"])
    assert resource == {
        "apiVersion": "v1",
        "kind": "Secret",
        "type": "Opaque",
        "metadata": {
            "name": "bitnami-oci-helm",
            "namespace": "argocd",
            "labels": {"argocd.argoproj.io/secret-type": "repository"},
        },
        "stringData": {
            "name": "bitnami-oci",
            "url": "registry-1.docker.io",
            "type": "helm",
            "enableOCI": "true",
        },
    }
