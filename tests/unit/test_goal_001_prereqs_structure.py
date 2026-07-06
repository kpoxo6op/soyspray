from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


REQUIRED_FILES = [
    "platform/namespaces/kustomization.yaml",
    "platform/gitops/app-of-apps/root-app.yaml",
    "platform/gitops/app-of-apps/platform-prereqs-app.yaml",
    "platform/gitops/app-of-apps/namespaces-app.yaml",
    "platform/gitops/app-of-apps/networking-app.yaml",
    "platform/gitops/app-of-apps/security-app.yaml",
    "platform/gitops/app-of-apps/cert-manager-app.yaml",
    "platform/gitops/app-of-apps/metallb-app.yaml",
    "platform/gitops/projects/platform-project.yaml",
    "platform/gitops/projects/security-project.yaml",
    "platform/gitops/projects/tenant-project-template.yaml",
    "platform/networking/metallb/kustomization.yaml",
    "platform/networking/metallb/ip-address-pool.example.yaml",
    "platform/certificates/cert-manager/kustomization.yaml",
    "platform/certificates/cert-manager/cluster-issuer-selfsigned.example.yaml",
    "platform/certificates/cert-manager/cluster-issuer-banklab-ca.example.yaml",
    "platform/security/sops/.sops.yaml.example",
    "platform/security/sops/encrypted-secret.example.yaml",
    "platform/networking/network-policies/platform-default-deny.yaml",
    "platform/networking/network-policies/tenants-default-deny.yaml",
    "platform/networking/network-policies/allow-dns.yaml",
    "platform/bootstrap/apply-prereqs.example.sh",
    "platform/bootstrap/check-cluster-prereqs.sh",
    "reports/goal-001-summary.md",
]


def test_goal_001_required_files_exist():
    missing = [path for path in REQUIRED_FILES if not (ROOT / path).is_file()]
    assert missing == []


def test_argocd_templates_use_obvious_repo_placeholder():
    for path in (ROOT / "platform/gitops").rglob("*.yaml"):
        content = path.read_text()
        assert "REPLACE_WITH_REPO_URL" in content


def test_examples_are_visibly_non_production():
    metallb = (ROOT / "platform/networking/metallb/ip-address-pool.example.yaml").read_text()
    sops = (ROOT / "platform/security/sops/.sops.yaml.example").read_text()
    secret_example = (ROOT / "platform/security/sops/encrypted-secret.example.yaml").read_text()
    assert "example-only" in metallb
    assert "REPLACE_WITH_LAB_LAN_LOADBALANCER_RANGE" in metallb
    assert "REPLACE_WITH_AGE_PUBLIC_RECIPIENT" in sops
    assert "REPLACE_WITH_SOPS_ENCRYPTED_VALUE" in secret_example

