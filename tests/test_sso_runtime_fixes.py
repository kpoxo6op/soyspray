from __future__ import annotations

from conftest import ROOT, load_all, load_yaml


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


def test_authentik_database_has_cpu_for_blueprint_reconciliation() -> None:
    resources = load_all("playbooks/argocd/applications/security/authentik/database/cluster.yaml")
    cluster = next(item for item in resources if item["kind"] == "Cluster")

    assert cluster["spec"]["resources"]["limits"]["cpu"] == "1"


def test_authentik_requests_a_tls_mirror_after_updating_the_allowlist() -> None:
    tasks = (ROOT / "roles/apps/authentik/tasks/main.yml").read_text()
    allowlist_task = "Allow the wildcard certificate in the Authentik namespace"
    mirror_task = "Request the Authentik wildcard certificate mirror"

    assert mirror_task in tasks
    assert "Read the wildcard certificate for Authentik" in tasks
    assert "register: authentik_wildcard_certificate" in tasks
    assert "reflector.v1.k8s.emberstack.com/reflects" in tasks
    assert "cert-manager/prod-cert-tls" in tasks
    assert 'data: "{{ authentik_wildcard_certificate.resources[0].data }}"' in tasks
    assert tasks.index(allowlist_task) < tasks.index(mirror_task)
