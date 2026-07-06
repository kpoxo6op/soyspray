#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
python_bin="${PYTHON:-${repo_root}/soyspray-venv/bin/python}"
if [[ ! -x "${python_bin}" ]]; then
  python_bin="python3"
fi

exec "${python_bin}" "${repo_root}/scripts/validate_kong_baseline.py" --admin-only
