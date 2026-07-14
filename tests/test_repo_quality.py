from __future__ import annotations

import re
import subprocess
import sys
from urllib.parse import unquote

from conftest import ROOT

NAVIGATION_DIRECTORIES = (
    ".agents",
    ".agents/skills",
    ".agents/skills/ansible-application-role",
    ".agents/skills/ansible-application-role/agents",
    ".agents/skills/argocd-kubernetes-application",
    ".agents/skills/argocd-kubernetes-application/agents",
    ".agents/skills/demo-lab-experience",
    ".agents/skills/demo-lab-experience/agents",
    ".agents/skills/playwright",
    ".agents/skills/playwright/agents",
    ".agents/skills/playwright/assets",
    ".agents/skills/playwright/references",
    ".agents/skills/playwright/scripts",
    ".agents/skills/security-best-practices",
    ".agents/skills/security-best-practices/agents",
    ".agents/skills/security-best-practices/references",
    ".agents/skills/security-threat-model",
    ".agents/skills/security-threat-model/agents",
    ".agents/skills/security-threat-model/references",
    ".agents/skills/systematic-debugging",
    ".agents/skills/test-driven-development",
    ".agents/skills/verification-before-completion",
    ".github",
    ".github/workflows",
    "apis",
    "apis/synthetic-bank",
    "apis/synthetic-bank/accounts",
    "apis/synthetic-bank/cards",
    "apis/synthetic-bank/customer-profile",
    "apis/synthetic-bank/fraud-decisions",
    "apis/synthetic-bank/open-banking",
    "apis/synthetic-bank/payments",
    "docs",
    "docs/runbooks",
    "docs/stylesheets",
    "kubernetes/banklab",
    "kubernetes/banklab/customer-web",
    "kubernetes/banklab/customer-web/app",
    "kubernetes/banklab/docs-site",
    "kubernetes/banklab/docs-site/config",
    "kubernetes/banklab/governance",
    "kubernetes/banklab/security",
    "kubernetes/banklab/tenancy",
    "platform",
    "platform/kong",
    "platform/kong/gateway-api",
    "platform/kong/helm",
    "platform/kong/network-policies",
    "platform/kong/smoke",
    "playbooks/argocd/applications/kong-bank-lab",
    "playbooks/argocd/applications/kong-bank-lab/operator-dashboard",
    "playbooks/argocd/applications/kong-bank-lab/operator-dashboard/dashboards",
    "roles/apps/kong-bank-lab",
    "roles/apps/kong-bank-lab/defaults",
    "roles/apps/kong-bank-lab/tasks",
    "tests",
)


def test_first_party_folders_have_navigation_readmes() -> None:
    missing = [path for path in NAVIGATION_DIRECTORIES if not (ROOT / path / "README.md").is_file()]
    assert not missing, "Missing navigation README.md files:\n" + "\n".join(missing)


def test_navigation_readme_links_resolve() -> None:
    broken: list[str] = []
    for path in NAVIGATION_DIRECTORIES:
        readme = ROOT / path / "README.md"
        for raw_target in re.findall(r"\]\(([^)]+)\)", readme.read_text()):
            if raw_target.startswith(("#", "http://", "https://")):
                continue
            target = unquote(raw_target.split("#", 1)[0])
            if target and not (readme.parent / target).exists():
                broken.append(f"{readme.relative_to(ROOT)} -> {raw_target}")
    assert not broken, "Broken navigation links:\n" + "\n".join(broken)


def test_root_readme_is_application_neutral() -> None:
    text = (ROOT / "README.md").read_text().lower()
    forbidden = [term for term in ("kong", "banklab", "bank lab") if term in text]
    assert not forbidden, f"Application-specific terms leaked into README.md: {forbidden}"


def test_project_skills_validate() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/validate_skills.py"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Validated 9 project skills" in result.stdout


def test_dead_goal_scaffolding_is_absent() -> None:
    dead_paths = (
        "platform/kong/gateway-api/crds/standard-install.yaml",
        "platform/kong/helm/render-kong-baseline.sh",
        "platform/kong/helm/values-kong-oss-baseline.schema.yaml",
        "platform/kong/versions.yaml",
        "apis/synthetic-bank/exposure-policy.yaml",
        "apis/synthetic-bank/versions.yaml",
        "clients/synthetic/client-catalog.yaml",
    )
    assert not [path for path in dead_paths if (ROOT / path).exists()]
