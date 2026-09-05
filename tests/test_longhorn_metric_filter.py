import re

import pytest
from conftest import load_yaml


@pytest.mark.parametrize(
    ("error", "reconcile_error", "retained"),
    [
        ("", "", True),
        ("backup failed", "", False),
        ("", "cannot inspect backup", False),
        ("first\nsecond", "", False),
        ("", "\n", False),
    ],
)
def test_failed_backup_timestamps_are_not_ingested(error, reconcile_error, retained):
    settings = load_yaml("playbooks/argocd/applications/observability/prometheus/values.yaml")[
        "kube-state-metrics"
    ]
    labels = {
        "__name__": "soyspray_longhorn_backup_snapshot_timestamp_seconds",
        "backup_error": error,
        "backup_reconcile_error": reconcile_error,
        "backup": "example",
    }
    keep = True
    for rule in settings["prometheus"]["monitor"]["http"]["metricRelabelings"]:
        # Prometheus relabel regexes are anchored and match newlines.
        pattern = re.compile(rule["regex"], re.DOTALL)
        if rule["action"] == "drop":
            value = ";".join(labels.get(key, "") for key in rule["sourceLabels"])
            if pattern.fullmatch(value):
                keep = False
                break
        elif rule["action"] == "labeldrop":
            labels = {k: v for k, v in labels.items() if not pattern.fullmatch(k)}
    assert keep is retained
    if keep:
        assert "backup_error" not in labels
        assert "backup_reconcile_error" not in labels
        assert labels["backup"] == "example"
