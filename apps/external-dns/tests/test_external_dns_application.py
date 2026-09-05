from pathlib import Path

import yaml
from ansible.parsing.dataloader import DataLoader
from ansible.template import Templar

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


def test_adoption_patch_tests_the_observed_version_and_keeps_other_finalizers():
    play = yaml.safe_load((APP / "adopt.yml").read_text())[0]
    task = next(t for t in play["tasks"] if "kubernetes.core.k8s_json_patch" in t)
    variables = {
        "external_dns_existing_app": {
            "resources": [{"metadata": {"resourceVersion": "version-1"}}]
        },
        "external_dns_finalizers": [
            "another-controller/finalizer",
            "resources-finalizer.argocd.argoproj.io",
        ],
        "external_dns_cascading_finalizers": play["vars"]["external_dns_cascading_finalizers"],
    }
    templar = Templar(loader=DataLoader(), variables=variables)
    patch = templar.template(task["kubernetes.core.k8s_json_patch"]["patch"])
    assert patch == [
        {"op": "test", "path": "/metadata/resourceVersion", "value": "version-1"},
        {
            "op": "replace",
            "path": "/metadata/finalizers",
            "value": ["another-controller/finalizer"],
        },
    ]
