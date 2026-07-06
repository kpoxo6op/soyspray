#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
"${repo_root}/platform/kong/scripts/require-cluster-mutation-permission.sh"
python_bin="${PYTHON:-${repo_root}/soyspray-venv/bin/python}"
if [[ ! -x "${python_bin}" ]]; then
  python_bin="python3"
fi

"${python_bin}" "${repo_root}/scripts/render_synthetic_apis.py" | kubectl apply -f -
