from pathlib import Path

import yaml

APP = Path(__file__).resolve().parents[1]


def test_upstream_chart_keeps_dns_record_ownership_and_selection():
    app = yaml.safe_load((APP / "argocd/application.yaml").read_text())
    values = yaml.safe_load((APP / "values.yaml").read_text())
    chart, source = app["spec"]["sources"]
    assert chart["repoURL"] == "https://kubernetes-sigs.github.io/external-dns"
    assert chart["chart"] == "external-dns"
    assert chart["targetRevision"] == "1.14.0"
    assert chart["helm"]["valueFiles"] == ["$values/apps/external-dns/values.yaml"]
    assert source["ref"] == "values"
    assert source["targetRevision"] == "HEAD"
    assert values["domainFilters"] == ["soyspray.vip"]
    assert values["policy"] == "upsert-only"
    assert values["registry"] == "txt"
    assert values["txtOwnerId"] == "k8s"
    assert values["sources"] == ["ingress"]
    assert set(values["extraArgs"]) == {
        "--txt-prefix=external-dns-",
        "--ignore-ingress-tls-spec",
        "--ignore-ingress-rules-spec",
    }
    assert values["env"] == [
        {
            "name": "CF_API_TOKEN",
            "valueFrom": {"secretKeyRef": {"name": "cloudflare-api-token", "key": "api-token"}},
        }
    ]


def test_project_scope_keeps_bootstrap_secrets_outside_argo():
    project = yaml.safe_load((APP / "argocd/project.yaml").read_text())
    assert project["spec"]["destinations"] == [
        {"server": "https://kubernetes.default.svc", "namespace": "external-dns"}
    ]
    assert {item["kind"] for item in project["spec"]["namespaceResourceWhitelist"]} == {
        "Service",
        "ServiceAccount",
        "Deployment",
    }
    assert {item["kind"] for item in project["spec"]["clusterResourceWhitelist"]} == {
        "Namespace",
        "ClusterRole",
        "ClusterRoleBinding",
    }
