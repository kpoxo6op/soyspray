#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
"${repo_root}/scripts/render_kong_baseline.py" >/dev/null
exec "${repo_root}/scripts/validate_kong_baseline.py"
