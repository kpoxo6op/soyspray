"""Every rule and dashboard file must actually be part of the package.

`alerts/runtime-signals.yaml` was written and tested but never listed in the
Kustomization, so the replacement paging rules were validated locally and never
deployed. These checks close that gap without a cluster.
"""

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
PACKAGE = ROOT / "apps/prometheus"
KUSTOMIZATION = PACKAGE / "kustomization.yaml"


def kustomization():
    return yaml.safe_load(KUSTOMIZATION.read_text())


def listed_resources():
    return list(kustomization().get("resources") or [])


def test_every_alert_file_is_deployed():
    listed = set(listed_resources())
    for path in sorted((PACKAGE / "alerts").glob("*.yaml")):
        relative = str(path.relative_to(PACKAGE))
        assert relative in listed, f"{relative} is not in the Kustomization resources"


def test_every_listed_resource_exists():
    for relative in listed_resources():
        assert (PACKAGE / relative).is_file(), f"{relative} is listed but missing"


def test_every_generated_dashboard_exists_and_the_operations_view_is_wired():
    generated = set()
    for entry in kustomization().get("configMapGenerator") or []:
        generated.update(entry.get("files") or [])
    for relative in sorted(generated):
        assert (PACKAGE / relative).is_file(), f"{relative} is generated but missing"
    assert "dashboards/soyspray-operations.json" in generated


def test_every_prometheus_rule_name_is_unique():
    names = []
    for path in sorted((PACKAGE / "alerts").glob("*.yaml")):
        document = yaml.safe_load(path.read_text())
        assert document["kind"] == "PrometheusRule", path.name
        assert document["metadata"].get("labels", {}).get("release") == "kube-prometheus-stack", (
            f"{path.name} would not be selected by the stack"
        )
        names.append(document["metadata"]["name"])
    assert len(names) == len(set(names)), names


def test_every_alert_rule_has_a_severity_label():
    for path in sorted((PACKAGE / "alerts").glob("*.yaml")):
        document = yaml.safe_load(path.read_text())
        for group in document["spec"]["groups"]:
            for rule in group["rules"]:
                if "alert" not in rule:
                    continue
                assert rule.get("labels", {}).get("severity"), (
                    f"{rule['alert']} in {path.name} has no severity label, so it never reaches "
                    "the Telegram route"
                )


def test_every_rule_expression_is_a_string():
    for path in sorted((PACKAGE / "alerts").glob("*.yaml")):
        document = yaml.safe_load(path.read_text())
        for group in document["spec"]["groups"]:
            for rule in group["rules"]:
                assert isinstance(rule.get("expr"), str), (path.name, rule.get("alert") or rule)
                assert "\\" not in rule["expr"] or re.search(r"\\\\", rule["expr"]), (
                    f"{path.name}: a single backslash in a PromQL string is usually a mistake"
                )
