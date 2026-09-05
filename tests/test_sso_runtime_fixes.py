from __future__ import annotations

from conftest import load_all, load_yaml


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
        {
            "from": [
                {
                    "namespaceSelector": {
                        "matchLabels": {
                            "kubernetes.io/metadata.name": "monitoring",
                        },
                    },
                    "podSelector": {
                        "matchLabels": {
                            "app.kubernetes.io/name": "prometheus",
                            "prometheus": "kube-prometheus-stack-prometheus",
                        },
                    },
                },
            ],
            "ports": [{"protocol": "TCP", "port": 9187}],
        },
    ]


def test_authentik_database_has_cpu_for_blueprint_reconciliation() -> None:
    resources = load_all("playbooks/argocd/applications/security/authentik/database/cluster.yaml")
    cluster = next(item for item in resources if item["kind"] == "Cluster")

    assert cluster["spec"]["resources"]["limits"]["cpu"] == "1"


def test_authentik_serializes_blueprint_work_on_one_worker() -> None:
    values = load_yaml("playbooks/argocd/applications/security/authentik/values.yaml")

    assert values["worker"]["replicas"] == 1
    worker_env = {item["name"]: item["value"] for item in values["worker"]["env"]}
    assert worker_env["AUTHENTIK_WORKER__THREADS"] == "1"
