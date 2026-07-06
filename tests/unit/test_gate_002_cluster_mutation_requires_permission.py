import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CLUSTER_SCRIPT = ROOT / "platform/kong/scripts/kong-cluster-apply-and-smoke.sh"


def test_cluster_apply_script_fails_without_permission_before_mutation():
    env = os.environ.copy()
    env.pop("BANKLAB_ALLOW_CLUSTER_MUTATION", None)
    env.pop("BANKLAB_TARGET_CONTEXT", None)
    result = subprocess.run(["bash", str(CLUSTER_SCRIPT)], cwd=ROOT, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    assert result.returncode != 0
    assert "BANKLAB_ALLOW_CLUSTER_MUTATION" in result.stdout
    assert "Applying Kong OSS baseline" not in result.stdout


def test_cluster_apply_script_calls_guard_before_apply_target():
    content = CLUSTER_SCRIPT.read_text(encoding="utf-8")
    guard_index = content.index("platform/kong/scripts/require-cluster-mutation-permission.sh")
    apply_index = content.index("make kong-apply")
    assert guard_index < apply_index


def test_make_kong_apply_and_rollback_remain_guarded():
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    guard = "platform/kong/scripts/require-cluster-mutation-permission.sh"
    for target, command in (("kong-apply", "kubectl apply"), ("kong-rollback", "kubectl delete")):
        start = makefile.index(f"{target}:")
        end = makefile.find("\n\n", start)
        block = makefile[start:end]
        assert guard in block
        assert block.index(guard) < block.index(command)
