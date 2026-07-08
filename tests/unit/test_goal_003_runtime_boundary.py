import re

from scripts.synthetic_bank_config import ROOT


def target_block(makefile: str, target: str) -> str:
    match = re.search(rf"^{re.escape(target)}:\n(?P<body>(?:\t.*\n|[ \t]*\n)*)", makefile, re.M)
    return match.group("body") if match else ""


def test_cluster_mutating_targets_are_guarded():
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    for target in ("synthetic-api-tenant-namespaces-apply", "synthetic-api-apply", "synthetic-api-rollback"):
        block = target_block(makefile, target)
        assert block
        assert "require-cluster-mutation-permission.sh" in block


def test_ci_keeps_runtime_targets_out():
    ci = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    for target in (
        "synthetic-api-install-dry-run",
        "synthetic-api-tenant-namespaces-dry-run",
        "synthetic-api-tenant-namespaces-apply",
        "synthetic-api-apply",
        "synthetic-api-smoke",
        "synthetic-api-negative-test",
        "synthetic-api-rollback",
        "synthetic-api-runtime-ready",
    ):
        assert not re.search(rf"run:\s+make\s+{target}(?:\s|$)", ci)
