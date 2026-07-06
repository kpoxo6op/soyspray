#!/usr/bin/env bash
set -euo pipefail

cat <<'MSG'
This example applies platform prerequisite resources to the current Kubernetes
context. It changes the cluster.

Do not run it unless you have reviewed the diff, selected the correct context,
and intentionally want to apply goal-001 prerequisites.

This script does not apply Kong resources.

Press Ctrl-C now to stop, or set APPLY_BANKLAB_PREREQS=1 to run non-interactively.
MSG

if [[ "${APPLY_BANKLAB_PREREQS:-}" != "1" ]]; then
  read -r -p "Type apply-prereqs to continue: " confirm
  if [[ "$confirm" != "apply-prereqs" ]]; then
    echo "Aborted."
    exit 1
  fi
fi

kubectl config current-context
kubectl apply -k platform/namespaces
kubectl apply -k platform/networking/network-policies

echo "Applied namespace and NetworkPolicy prerequisites only."

