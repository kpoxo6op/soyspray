"""Goal010 read-only runtime drift guard configuration."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

try:
    from scripts.synthetic_bank_config import ROOT
except ModuleNotFoundError:
    from synthetic_bank_config import ROOT


GOAL_ID = "goal-010-kong-runtime-drift-guard-final-readiness"
GOAL_LABEL = "goal-010"
EXPECTED_CONTEXT = "kubernetes-admin@cluster.local"
INVENTORY_PATH = ROOT / "soydocs/kong-bank-lab/goal-010-expected-runtime-inventory.yaml"
RENDERED_INVENTORY_PATH = ROOT / "reports/goal-010-expected-runtime-inventory-rendered.yaml"
GOAL_BODY_PATH = ROOT / "soydocs/kong-bank-lab/goals/goal-010-kong-runtime-drift-guard-final-readiness.md"
HANDOVER_PATH = ROOT / "soydocs/kong-bank-lab/handover-2026-07-09-post-goal-010.md"
FINAL_APPROVAL_CANDIDATE_PATH = ROOT / "docs/decisions/kong-bank-lab-final-approval-candidate.md"
RUNTIME_APPROVAL_PATH = ROOT / "docs/decisions/goal-010-runtime-approval.md"

ACCOUNTS_ROUTE_PLUGINS = "banklab-key-auth,banklab-acl,banklab-rate-limit,banklab-correlation-id"
ACCOUNTS_ROUTE = {"namespace": "tenant-accounts", "name": "banklab-accounts", "kind": "HTTPRoute"}
GOAL009_PLUGIN_NAME = "banklab-goal009-security-headers"
GOAL008_POLICY_NAME = "banklab-kong-plugin-governance"
DENIED_PLUGIN_TYPE = "request-transformer"

REPORT_PATHS = {
    "summary": ROOT / "reports/goal-010-summary.md",
    "readiness": ROOT / "reports/goal-010-runtime-readiness.md",
    "inventory": ROOT / "reports/goal-010-kong-runtime-inventory.md",
    "drift": ROOT / "reports/goal-010-kong-drift-audit.md",
    "behavior": ROOT / "reports/goal-010-behavior-regression.md",
    "no_mutation": ROOT / "reports/goal-010-no-mutation-proof.md",
    "rollback": ROOT / "reports/goal-010-readonly-rollback.md",
}

RUNTIME_SCRIPT_PATHS = (
    ROOT / "scripts/goal010/require_readonly_runtime.sh",
    ROOT / "scripts/goal010/runtime_ready.sh",
    ROOT / "scripts/goal010/evidence.sh",
    ROOT / "scripts/goal010/readonly_rollback.sh",
    ROOT / "scripts/goal010/readonly_audit.py",
)


def load_inventory(path: Path = INVENTORY_PATH) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def relative(path: Path) -> str:
    return str(path.relative_to(ROOT))
