from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


REQUIRED_FILES = [
    "README.md",
    "ROADMAP.md",
    "Makefile",
    ".gitignore",
    ".editorconfig",
    ".pre-commit-config.yaml",
    "CODEOWNERS",
    ".github/workflows/ci.yml",
    "docs/index.md",
    "docs/architecture/platform-principles.md",
    "docs/architecture/oss-vs-enterprise.md",
    "docs/architecture/operating-model.md",
    "docs/architecture/testing-strategy.md",
    "docs/adr/adr-template.md",
    "docs/adr/0001-platform-direction.md",
    "docs/onboarding/api-onboarding-template.md",
    "docs/runbooks/runbook-template.md",
    "apis/api-template/openapi.yaml",
    "apis/api-template/ownership.yaml",
    "policies/conftest/placeholder.rego",
    "policies/examples/valid-api-metadata.yaml",
    "policies/examples/invalid-api-metadata.yaml",
    "scripts/validate_repo.py",
    "scripts/generate_evidence_report.py",
    "reports/goal-000-summary.md",
    "mkdocs.yml",
]


REQUIRED_DIRS = [
    "docs/architecture",
    "docs/adr",
    "docs/onboarding",
    "docs/runbooks",
    "docs/decisions",
    "platform/gitops",
    "platform/kong",
    "platform/identity",
    "platform/observability",
    "platform/security",
    "platform/networking",
    "tenants/tenant-template",
    "apis/api-template/tests",
    "policies/conftest",
    "policies/examples",
    "tests/unit",
    "tests/policy",
    "tests/integration",
    "tests/fixtures",
    "reports",
]


def test_required_files_exist():
    missing = [path for path in REQUIRED_FILES if not (ROOT / path).is_file()]
    assert missing == []


def test_required_directories_exist():
    missing = [path for path in REQUIRED_DIRS if not (ROOT / path).is_dir()]
    assert missing == []


def test_oss_boundary_document_mentions_enterprise_gaps():
    content = (ROOT / "docs/architecture/oss-vs-enterprise.md").read_text()
    expected = [
        "Kong RBAC",
        "Kong Workspaces",
        "Kong OIDC plugin",
        "Request Validator plugin",
        "MTLS Auth plugin",
        "Developer Portal",
        "Audit logs",
    ]
    missing = [term for term in expected if term not in content]
    assert missing == []


def test_kong_directory_has_readme():
    assert (ROOT / "platform/kong/README.md").is_file()
