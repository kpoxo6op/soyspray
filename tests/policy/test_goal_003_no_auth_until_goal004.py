from scripts.synthetic_bank_config import ROOT


def test_no_auth_or_rate_limit_resources_until_goal004():
    if (ROOT / "soydocs/kong-bank-lab/goals/goal-004-auth-rate-limit-security.md").exists():
        from scripts.validate_synthetic_api_security import validate

        assert validate() == []
        return

    forbidden = ["KongPlugin", "KongClusterPlugin", "KongConsumer", "key-auth", "jwt", "acl", "rate-limiting", "openid-connect"]
    offenders = []
    for path in list((ROOT / "apis/synthetic-bank").rglob("*")) + list((ROOT / "clients/synthetic").rglob("*")):
        if path.is_file():
            text = path.read_text(encoding="utf-8")
            for term in forbidden:
                if term in text:
                    offenders.append((str(path.relative_to(ROOT)), term))
    assert offenders == []
