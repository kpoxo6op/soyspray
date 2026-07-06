#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
exec "${repo_root}/platform/kong/synthetic-apis/scripts/verify-goal003-runtime-ready.sh"
