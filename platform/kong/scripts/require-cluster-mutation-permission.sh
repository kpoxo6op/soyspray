#!/usr/bin/env bash
set -euo pipefail

if [[ "${BANKLAB_ALLOW_CLUSTER_MUTATION:-}" != "true" ]]; then
  echo "Refusing cluster mutation: BANKLAB_ALLOW_CLUSTER_MUTATION must be exactly true." >&2
  exit 1
fi

if [[ -z "${BANKLAB_TARGET_CONTEXT:-}" ]]; then
  echo "Refusing cluster mutation: BANKLAB_TARGET_CONTEXT must be set explicitly." >&2
  exit 1
fi

if ! command -v kubectl >/dev/null 2>&1; then
  echo "Refusing cluster mutation: kubectl is required and was not found." >&2
  exit 1
fi

current_context="$(kubectl config current-context 2>/dev/null || true)"
if [[ -z "${current_context}" ]]; then
  echo "Refusing cluster mutation: kubectl has no current context." >&2
  exit 1
fi

echo "Current Kubernetes context: ${current_context}" >&2
echo "Expected Kubernetes context: ${BANKLAB_TARGET_CONTEXT}" >&2

if [[ "${current_context}" != "${BANKLAB_TARGET_CONTEXT}" ]]; then
  echo "Refusing cluster mutation: current context does not match BANKLAB_TARGET_CONTEXT." >&2
  exit 1
fi

echo "Cluster mutation permission granted for context ${current_context}." >&2
echo "Proceed only for the explicitly approved command and evidence capture." >&2
