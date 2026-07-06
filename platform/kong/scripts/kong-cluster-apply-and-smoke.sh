#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "${repo_root}"

echo "Branch: $(git branch --show-current 2>/dev/null || echo unknown)"
echo "Commit: $(git rev-parse --short HEAD 2>/dev/null || echo unknown)"

platform/kong/scripts/require-cluster-mutation-permission.sh

echo "Running pre-apply read-only checks."
make cluster-readonly-preflight
make kong-readonly-preflight
make cluster-smoke
make cluster-prereq-smoke

echo "Running server-side dry-run."
make kong-install-dry-run

echo "Applying Kong OSS baseline through guarded Make target."
make kong-apply

echo "Running Kong runtime smoke checks."
make kong-cluster-smoke
make kong-route-smoke
make kong-admin-exposure-test

echo "Collecting runtime evidence."
platform/kong/scripts/collect-kong-runtime-evidence.sh

echo "Refresh evidence with:"
echo "  make evidence-goal-002"
echo "  make evidence-gate-002-cluster-apply-and-smoke"
echo "  make goal002-runtime-ready"
