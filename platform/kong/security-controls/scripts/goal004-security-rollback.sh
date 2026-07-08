#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
python_bin="${BANKLAB_PYTHON:-}"
if [[ -z "${python_bin}" ]]; then
  if [[ -x "${repo_root}/soyspray-venv/bin/python" ]]; then
    python_bin="${repo_root}/soyspray-venv/bin/python"
  else
    python_bin="python3"
  fi
fi

cd "${repo_root}"
platform/kong/scripts/require-cluster-mutation-permission.sh
kubectl -n synthetic-clients delete secret -l banklab.konghq.com/goal=goal-004 --ignore-not-found=true || true
"${python_bin}" scripts/render_goal004_security_controls.py | kubectl delete --ignore-not-found=true -f -
