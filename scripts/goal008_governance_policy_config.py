"""Goal008 Kong governance policy model."""

from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    from scripts.goal005_tenancy_config import load_yaml
    from scripts.synthetic_bank_config import ROOT
except ModuleNotFoundError:
    from goal005_tenancy_config import load_yaml
    from synthetic_bank_config import ROOT


GOAL_ID = "goal-008-kong-governance-policy-as-code"
GOAL_LABEL = "goal-008"
POLICY_PATH = ROOT / "platform/governance/kong/policies/kong-plugin-governance.yaml"


def load_policy() -> dict[str, Any]:
    return load_yaml(POLICY_PATH)


def relative(path: Path) -> str:
    return str(path.relative_to(ROOT))
