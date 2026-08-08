from __future__ import annotations

from conftest import ROOT, load_yaml


def test_cnpg_operator_can_read_authentik_instance_status() -> None:
    policy = load_yaml(
        "playbooks/argocd/applications/security/authentik/database/networkpolicy.yaml"
    )

    assert policy["spec"]["ingress"] == [
        {
            "from": [{"podSelector": {}}],
            "ports": [{"protocol": "TCP", "port": 5432}],
        },
        {
            "from": [
                {
                    "namespaceSelector": {
                        "matchLabels": {
                            "kubernetes.io/metadata.name": "cnpg-system",
                        },
                    },
                },
            ],
            "ports": [{"protocol": "TCP", "port": 8000}],
        },
    ]


def test_authentik_role_points_cert_manager_at_the_branch_before_certificate_change() -> None:
    tasks = (ROOT / "roles/apps/authentik/tasks/main.yml").read_text()
    application_task = "Point cert-manager config at the Authentik revision"
    certificate_task = "Allow the wildcard certificate in the Authentik namespace"

    assert application_task in tasks
    assert "cert-manager/cert-manager-application.yaml" in tasks
    assert "authentik_target_revision" in tasks
    assert tasks.index(application_task) < tasks.index(certificate_task)
