#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
report="${repo_root}/reports/kong-runtime-apply-plan.md"
mkdir -p "${repo_root}/reports"
python_bin="${PYTHON:-}"
if [[ -z "${python_bin}" ]]; then
  if [[ -x "${repo_root}/soyspray-venv/bin/python" ]]; then
    python_bin="${repo_root}/soyspray-venv/bin/python"
  else
    python_bin="python3"
  fi
fi

cd "${repo_root}"

"${python_bin}" - <<'PY'
from __future__ import annotations

import datetime as dt
import subprocess
from pathlib import Path

import yaml

root = Path.cwd()
versions = yaml.safe_load((root / "platform/kong/versions.yaml").read_text(encoding="utf-8"))


def git(args: list[str]) -> str:
    result = subprocess.run(["git", *args], cwd=root, text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    return result.stdout.strip() if result.returncode == 0 else "unknown"


branch = git(["branch", "--show-current"]) or "unknown"
commit = git(["rev-parse", "--short", "HEAD"]) or "unknown"
now = dt.datetime.now(dt.timezone.utc).astimezone().isoformat(timespec="seconds")

report = f"""# Kong Runtime Apply Plan

Generated at: {now}

Branch: {branch}

Commit: {commit}

This plan is generated from repository files only. It does not query the
cluster and it does not mutate the cluster.

## Version Locks

- Kong Gateway: `{versions["kong_gateway"]["image_repository"]}:{versions["kong_gateway"]["image_tag"]}`
- Kong mode: `{versions["kong_gateway"]["mode"]}`
- Kong Enterprise enabled: `{versions["kong_gateway"]["enterprise_enabled"]}`
- KIC: `{versions["kong_ingress_controller"]["image_repository"]}:{versions["kong_ingress_controller"]["image_tag"]}`
- Gateway API: `{versions["gateway_api"]["version"]}`
- Helm chart: `{versions["helm"]["chart_name"]} {versions["helm"]["chart_version"]}`

## Expected Namespaces

- `platform-kong`
- `platform-kong-smoke`

## Expected Gateway API Resources

- `GatewayClass/kong`
- `Gateway/platform-kong/kong-external`
- `Gateway/platform-kong/kong-internal`
- `HTTPRoute/platform-kong-smoke/kong-smoke-external`
- `HTTPRoute/platform-kong-smoke/kong-smoke-internal`

## Expected Smoke Resources

- `Namespace/platform-kong-smoke`
- `Deployment/platform-kong-smoke/kong-smoke-backend`
- `Service/platform-kong-smoke/kong-smoke-backend`

## Expected NetworkPolicy Resources

- `NetworkPolicy/platform-kong/kong-default-deny`
- `NetworkPolicy/platform-kong/kong-allow-dns`
- `NetworkPolicy/platform-kong/kong-allow-kube-api-placeholder`
- `NetworkPolicy/platform-kong/kong-allow-proxy-ingress`
- `NetworkPolicy/platform-kong/kong-allow-smoke-upstream`

## Expected Argo CD Templates

- `platform/kong/argocd/kong-baseline-app.yaml`
- `platform/kong/argocd/kong-gateway-api-app.yaml`
- `platform/kong/argocd/kong-smoke-app.yaml`
- `platform/gitops/app-of-apps/kong-baseline-app.yaml`

## Admin API Exposure Model

The Kong Admin API must remain private. Static validation requires the Admin
service to be ClusterIP-only and rejects Ingress, Gateway, or HTTPRoute paths
that expose Admin API traffic externally.

## Explicit Cluster Apply Commands

Do not run these commands without explicit user permission and the mutation
guard variables:

```bash
BANKLAB_ALLOW_CLUSTER_MUTATION=true BANKLAB_TARGET_CONTEXT=<expected-context> make kong-apply
```

Rollback command:

```bash
BANKLAB_ALLOW_CLUSTER_MUTATION=true BANKLAB_TARGET_CONTEXT=<expected-context> make kong-rollback
```

## Known Runtime Dependencies

- Kubernetes API access and the expected context must be confirmed.
- Gateway API CRDs must exist before Gateway resources can be accepted.
- MetalLB or another LoadBalancer implementation is needed for external proxy
  service IP assignment.
- NetworkPolicy behavior depends on the live CNI.
- Route smoke tests require an applied Kong baseline.

## Runtime Proof Boundary

This plan does not prove runtime success. Runtime success requires explicit
cluster apply and smoke validation in a later approved gate.
"""

(root / "reports/kong-runtime-apply-plan.md").write_text(report, encoding="utf-8")
print("reports/kong-runtime-apply-plan.md generated.")
PY
