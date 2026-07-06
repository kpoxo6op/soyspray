import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

FORBIDDEN_READONLY_PATTERNS = [
    r"\bkubectl\s+apply\b",
    r"\bkubectl\s+delete\b",
    r"\bkubectl\s+patch\b",
    r"\bkubectl\s+label\b",
    r"\bkubectl\s+annotate\b",
    r"\bkubectl\s+scale\b",
    r"\bkubectl\s+rollout\s+restart\b",
    r"\bhelm\s+install\b",
    r"\bhelm\s+upgrade\b",
    r"\bhelm\s+uninstall\b",
    r"\bargocd\s+app\s+sync\b",
]


def test_readonly_preflight_scripts_do_not_mutate_cluster():
    for relative in (
        "platform/kong/scripts/cluster-readonly-preflight.sh",
        "platform/kong/scripts/kong-readonly-preflight.sh",
    ):
        content = (ROOT / relative).read_text(encoding="utf-8")
        matches = [
            pattern
            for pattern in FORBIDDEN_READONLY_PATTERNS
            if re.search(pattern, content)
        ]
        assert matches == []


def test_ci_does_not_run_cluster_targets():
    ci = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    forbidden_targets = [
        "cluster-readonly-preflight",
        "kong-readonly-preflight",
        "cluster-smoke",
        "cluster-prereq-smoke",
        "kong-install-dry-run",
        "kong-apply",
        "kong-cluster-smoke",
        "kong-route-smoke",
        "kong-rollback",
    ]
    for target in forbidden_targets:
        assert f"run: make {target}\n" not in ci
