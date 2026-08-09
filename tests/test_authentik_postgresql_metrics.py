from __future__ import annotations

from conftest import load_yaml


def test_kube_prometheus_stack_can_scrape_authentik_postgresql_metrics() -> None:
    policy = load_yaml(
        "playbooks/argocd/applications/security/authentik/database/networkpolicy.yaml"
    )

    assert {
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
    } in policy["spec"]["ingress"]
