from scripts.synthetic_bank_config import ROOT


def test_goal003_does_not_create_secrets_or_credentials():
    forbidden_names = {".env", "id_rsa", "id_ed25519", "kubeconfig", "admin.conf"}
    offenders = []
    for root in ("apis/synthetic-bank", "clients/synthetic", "platform/kong/synthetic-apis"):
        for path in (ROOT / root).rglob("*"):
            name = path.name.lower()
            if path.is_file() and (name in forbidden_names or name.endswith((".key", ".pem", ".p12", ".pfx"))):
                offenders.append(str(path.relative_to(ROOT)))
            if path.is_file() and path.suffix in {".yaml", ".yml"} and "kind: Secret" in path.read_text(encoding="utf-8"):
                offenders.append(str(path.relative_to(ROOT)))
    assert offenders == []
