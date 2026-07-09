#!/usr/bin/env bash
set -euo pipefail

if [[ "${BANKLAB_ALLOW_CLUSTER_MUTATION:-false}" == "true" ]]; then
  echo "Refusing Goal010: BANKLAB_ALLOW_CLUSTER_MUTATION must be unset or exactly false." >&2
  exit 1
fi

if [[ -z "${BANKLAB_TARGET_CONTEXT:-}" ]]; then
  echo "Refusing Goal010: BANKLAB_TARGET_CONTEXT must be set explicitly." >&2
  exit 1
fi

if [[ "${BANKLAB_TARGET_CONTEXT}" != "kubernetes-admin@cluster.local" ]]; then
  echo "Refusing Goal010: BANKLAB_TARGET_CONTEXT must be kubernetes-admin@cluster.local." >&2
  exit 1
fi

current_context="$(kubectl config current-context 2>/dev/null || true)"
if [[ "${current_context}" != "${BANKLAB_TARGET_CONTEXT}" ]]; then
  echo "Refusing Goal010: current context ${current_context:-missing} does not match BANKLAB_TARGET_CONTEXT." >&2
  exit 1
fi

echo "Goal010 read-only runtime guard passed for context ${current_context}." >&2
