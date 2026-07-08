#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"

cd "${repo_root}"
platform/kong/scripts/require-cluster-mutation-permission.sh
kubectl -n synthetic-clients delete secret -l banklab.konghq.com/goal=goal-004 --ignore-not-found=true || true
scripts/render_goal004_security_controls.py | kubectl delete --ignore-not-found=true -f -
