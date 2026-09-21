"""Keep the Alloy signal config and the Prometheus rules in step.

The Alloy selector is a River string that becomes a LogQL string that becomes an
RE2 pattern. Two unescaping levels means a single backslash can silently turn
into a backspace or an invalid escape. These checks run without a cluster.
"""

import json
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
MANIFESTS = ROOT / "apps/loki/manifests"
ALERTS = ROOT / "apps/prometheus/alerts"

CONFIGS = ("alloy-configmap.yaml", "alloy-events-configmap.yaml")

# Go string escapes, which is what a LogQL string literal accepts.
VALID_ESCAPES = set("abfnrtv\\\"'")
STRING_LITERAL = re.compile(r'"((?:[^"\\]|\\.)*)"')


def alloy_body(name):
    text = (MANIFESTS / name).read_text()
    return yaml.safe_load(text)["data"]["config.alloy"]


def river_decode(value):
    """Decode the River string escapes that surround a decoded selector."""
    return value.replace("\\\\", "\\").replace('\\"', '"')


def selectors():
    found = []
    for name in CONFIGS:
        for line in alloy_body(name).splitlines():
            match = re.match(r'^\s*selector = "(.*)"\s*$', line)
            if match:
                found.append((name, river_decode(match.group(1))))
    return found


def produced_metrics():
    names = set()
    for name in CONFIGS:
        names.update(re.findall(r'name\s*=\s*"(soyspray_[a-z0-9_]+)"', alloy_body(name)))
    return names


def rule_text():
    return "\n".join(path.read_text() for path in sorted(ALERTS.glob("*.yaml")))


def test_every_selector_decodes_to_a_well_formed_logql_query():
    found = selectors()
    assert len(found) == 6, [name for name, _ in found]
    for name, selector in found:
        assert selector.startswith("{") and "}" in selector, (name, selector)
        matcher, _, rest = selector.partition("}")
        assert matcher.count('"') % 2 == 0, (name, selector)
        # The line filter must be a single quoted string per operator.
        for operator in ("|~", "!~", "|=", "!="):
            rest = rest.replace(operator, " ")
        for literal in STRING_LITERAL.findall(rest):
            assert re.search(r"\S", literal) or literal == "", (name, selector)


def test_no_selector_uses_an_invalid_string_escape():
    """A stray backslash becomes a backspace or a LogQL parse error."""
    for name, selector in selectors():
        for literal in STRING_LITERAL.findall(selector):
            index = 0
            while index < len(literal):
                if literal[index] != "\\":
                    index += 1
                    continue
                following = literal[index + 1 : index + 2]
                assert following, f"{name}: trailing backslash in {literal!r}"
                if following in VALID_ESCAPES:
                    index += 2
                    continue
                if following == "x" and re.match(r"[0-9a-fA-F]{2}", literal[index + 2 : index + 4]):
                    index += 4
                    continue
                if following == "u" and re.match(r"[0-9a-fA-F]{4}", literal[index + 2 : index + 6]):
                    index += 6
                    continue
                if following == "U" and re.match(
                    r"[0-9a-fA-F]{8}", literal[index + 2 : index + 10]
                ):
                    index += 10
                    continue
                if following in "01234567" and re.match(
                    r"[0-7]{3}", literal[index + 1 : index + 4]
                ):
                    index += 4
                    continue
                raise AssertionError(
                    f"{name}: invalid LogQL string escape \\{following} in {literal!r}. "
                    "A regex backslash needs four backslashes in the Alloy file."
                )


def test_no_regex_relies_on_a_logql_backspace():
    """In a LogQL string `\b` is a backspace, not a word boundary.

    A word boundary needs `\\b` in the LogQL text, which is `\\\\b` in the Alloy
    file. A bare `\b` parses, matches nothing, and silently removes coverage.
    """
    for name, selector in selectors():
        for literal in STRING_LITERAL.findall(selector):
            for match in re.finditer(r"\\", literal):
                index = match.start()
                runs = 0
                while index - runs - 1 >= 0 and literal[index - runs - 1] == "\\":
                    runs += 1
                if runs % 2 == 0 and literal[index + 1 : index + 2] == "b":
                    raise AssertionError(
                        f"{name}: a bare backslash-b in {literal!r} is a LogQL backspace. "
                        "Write four backslashes in the Alloy file for a word boundary."
                    )


def test_every_regex_filter_compiles():
    for name, selector in selectors():
        for literal in STRING_LITERAL.findall(selector):
            try:
                re.compile(literal)
            except re.error as error:  # pragma: no cover - failure path
                raise AssertionError(f"{name}: {literal!r} does not compile: {error}") from None


def test_every_produced_metric_is_used_by_a_rule():
    rules = rule_text()
    for metric in sorted(produced_metrics()):
        assert metric in rules, f"{metric} is produced by Alloy but no rule reads it"


def test_every_soyspray_counter_in_a_rule_is_produced():
    produced = produced_metrics()
    referenced = set(re.findall(r"\bsoyspray_(?:log|event)_[a-z0-9_]+_total\b", rule_text()))
    assert referenced, "no Alloy-derived counter is referenced by a rule"
    missing = referenced - produced
    assert not missing, f"rules read counters Alloy does not produce: {sorted(missing)}"


def test_signal_metric_names_do_not_collide():
    names = []
    for name in CONFIGS:
        names.extend(re.findall(r'name\s*=\s*"(soyspray_[a-z0-9_]+)"', alloy_body(name)))
    assert len(names) == len(set(names)), names


def test_metrics_stages_come_after_label_stages():
    """A stage after stage.metrics can add unexpected labels to the metric."""
    for name in CONFIGS:
        lines = alloy_body(name).splitlines()
        seen_metrics = False
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("stage.metrics"):
                seen_metrics = True
            if seen_metrics and stripped.startswith(("stage.labels", "stage.static_labels")):
                raise AssertionError(f"{name}: {stripped} follows a stage.metrics block")


def test_retired_loki_rules_and_ruler_are_gone():
    kustomization = (MANIFESTS / "kustomization.yaml").read_text()
    config = (MANIFESTS / "loki-configmap.yaml").read_text()
    statefulset = (MANIFESTS / "loki-statefulset.yaml").read_text()
    assert "loki-rules" not in kustomization
    assert not (MANIFESTS / "loki-rules-kubernetes.yaml").exists()
    assert not (MANIFESTS / "loki-rules-backup.yaml").exists()
    assert "ruler:" not in config
    assert "alertmanager-operated" not in config
    assert "loki-rules" not in statefulset


def test_retired_alert_names_are_not_reintroduced():
    retired = (
        "ApplicationErrorBurst",
        "BackupErrorBurst",
        "KubernetesPodCrashLoopingLogs",
        "VolumeMountAttachFailures",
        "ImmichMediaBackupFailureImmediate",
        "ObsidianBackupFailureImmediate",
        "ImmichMediaBackupBackoffLimitExceeded",
        "ObsidianBackupBackoffLimitExceeded",
        "CNPGBackupBarmanError",
        "CNPGWalArchiveFailure",
    )
    live = "\n".join(
        path.read_text() for path in list(ALERTS.glob("*.yaml")) + sorted(MANIFESTS.glob("*.yaml"))
    )
    for name in retired:
        for line in live.splitlines():
            stripped = line.lstrip()
            if stripped.startswith(("#", "//")):
                continue
            if name in line:
                raise AssertionError(f"{name} still appears as active configuration: {stripped}")


def test_every_retired_rule_has_a_named_replacement():
    """Every retired Loki rule must be mapped in the pipeline document."""
    document = (MANIFESTS / "docs/ALERT-PIPELINE.md").read_text()
    assert "Retired rules" in document
    for keyword in ("ApplicationErrorBurst", "BackupErrorBurst"):
        assert keyword in document
    replacements = set(re.findall(r"`(Soyspray[A-Za-z]+)`", document))
    assert {
        "SoysprayPodCrashLooping",
        "SoysprayVolumeMountFailure",
        "SoysprayBackupToolFailure",
        "SoysprayDatabaseBackupFailure",
        "SoysprayBackupJobBackoff",
    } <= replacements


def test_alloy_pods_roll_when_the_pipeline_changes():
    """Alloy reads its config at start; a mounted ConfigMap change is not reloaded."""
    for name, kind in (
        ("alloy-daemonset.yaml", "DaemonSet"),
        ("alloy-events-deployment.yaml", "Deployment"),
    ):
        document = yaml.safe_load((MANIFESTS / name).read_text())
        assert document["kind"] == kind
        annotations = document["spec"]["template"]["metadata"].get("annotations") or {}
        assert annotations.get("soyspray.dev/signal-config"), name


# Go text/template builtins plus every function Alertmanager adds (v0.28.1
# template/template.go). Anything else fails at reload time, which keeps the old
# configuration running and raises AlertmanagerFailedReload.
TEMPLATE_FUNCTIONS = {
    "and",
    "call",
    "html",
    "index",
    "slice",
    "js",
    "len",
    "not",
    "or",
    "print",
    "printf",
    "println",
    "urlquery",
    "eq",
    "ne",
    "lt",
    "le",
    "gt",
    "ge",
    "date",
    "humanizeDuration",
    "join",
    "match",
    "reReplaceAll",
    "safeHtml",
    "since",
    "stringSlice",
    "title",
    "toLower",
    "toUpper",
    "trimSpace",
    "tz",
    "template",
    "define",
    "block",
    "range",
    "with",
    "if",
    "else",
    "end",
    "nil",
    "true",
    "false",
}


def test_alert_manager_template_uses_only_defined_functions():
    values = yaml.safe_load((ROOT / "apps/prometheus/values.yaml").read_text())
    template = values["alertmanager"]["templateFiles"]["soy-telegram.tmpl"]
    called = set(re.findall(r"{{\s*-?\s*([a-zA-Z_][a-zA-Z0-9_]*)", template))
    unknown = {name for name in called if name not in TEMPLATE_FUNCTIONS}
    assert not unknown, f"Alertmanager does not define these template functions: {sorted(unknown)}"


def test_alert_manager_template_cannot_be_truncated():
    """Alertmanager cuts the rendered message at 4096 runes.

    A cut in the middle of an auto-escaped entity leaves an unparseable message
    and Telegram rejects the whole group, which is what happened on 2026-09-13.
    The template must bound its own length instead of relying on that cut.
    """
    values = yaml.safe_load((ROOT / "apps/prometheus/values.yaml").read_text())
    template = values["alertmanager"]["templateFiles"]["soy-telegram.tmpl"]
    assert "<b>" not in template and "<a href" not in template

    limit = int(re.search(r"\$limit := (\d+)", template).group(1))
    capped = re.findall(
        r'reReplaceAll "\[<&\]" " " \| reReplaceAll "\(\?s\)\^\(\.\{0,(\d+)\}\)\.\*\$" "\$1"',
        template,
    )
    caps = sorted(int(value) for value in capped)
    # Every rendered field that carries alert text: the alert name, the label
    # line, the summary, the description and the runbook URL.
    assert caps == [80, 200, 200, 300, 300], caps

    # Removing "<" and "&" first means auto-escaping cannot expand the text, so
    # the rendering is bounded by the caps themselves.
    header = 21 + 80 + 8
    per_alert = 2 + 200 + 1 + 2 + 300 + 1 + 2 + 300 + 1
    footer = 80 + 2 + 200
    worst = header + limit * per_alert + footer
    assert worst < 4096, f"worst-case rendering is {worst} runes"
    assert limit >= 2, "a group must show more than one alert"


def test_alert_manager_receiver_does_not_claim_an_ineffective_setting():
    """The Prometheus Operator omits an empty parse_mode from the config."""
    values = yaml.safe_load((ROOT / "apps/prometheus/values.yaml").read_text())
    telegram = values["alertmanager"]["config"]["receivers"][1]["telegram_configs"][0]
    assert "parse_mode" not in telegram, (
        "an empty parse_mode is dropped by the operator and would only look effective"
    )


if __name__ == "__main__":
    import sys

    failures = 0
    for name, function in sorted(globals().items()):
        if name.startswith("test_") and callable(function):
            try:
                function()
            except AssertionError as error:
                failures += 1
                print(f"FAIL {name}: {error}")
    print(json.dumps({"failures": failures}))
    sys.exit(1 if failures else 0)
