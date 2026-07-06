import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
GUARD = ROOT / "platform/kong/scripts/require-cluster-mutation-permission.sh"


def makefile_target_body(target: str) -> str:
    lines = (ROOT / "Makefile").read_text(encoding="utf-8").splitlines()
    body: list[str] = []
    in_target = False
    for line in lines:
        if line == f"{target}:":
            in_target = True
            continue
        if in_target and line and not line.startswith(("\t", " ")):
            break
        if in_target:
            body.append(line)
    return "\n".join(body)


def test_mutation_guard_fails_without_permission():
    env = os.environ.copy()
    env.pop("BANKLAB_ALLOW_CLUSTER_MUTATION", None)
    env.pop("BANKLAB_TARGET_CONTEXT", None)
    result = subprocess.run(["bash", str(GUARD)], cwd=ROOT, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    assert result.returncode != 0
    assert "BANKLAB_ALLOW_CLUSTER_MUTATION" in result.stdout


def test_mutation_guard_fails_without_target_context():
    env = os.environ.copy()
    env["BANKLAB_ALLOW_CLUSTER_MUTATION"] = "true"
    env.pop("BANKLAB_TARGET_CONTEXT", None)
    result = subprocess.run(["bash", str(GUARD)], cwd=ROOT, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    assert result.returncode != 0
    assert "BANKLAB_TARGET_CONTEXT" in result.stdout


def test_kong_mutating_targets_call_guard_before_mutation():
    guard_path = "platform/kong/scripts/require-cluster-mutation-permission.sh"
    for target in ("kong-apply", "kong-rollback"):
        body = makefile_target_body(target)
        assert guard_path in body
        guard_index = body.index(guard_path)
        mutating_index = min(
            index
            for marker in ("kubectl apply", "kubectl delete")
            if (index := body.find(marker)) != -1
        )
        assert guard_index < mutating_index
