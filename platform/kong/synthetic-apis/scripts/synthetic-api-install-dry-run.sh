#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
python_bin="${PYTHON:-${repo_root}/soyspray-venv/bin/python}"
if [[ ! -x "${python_bin}" ]]; then
  python_bin="python3"
fi

tenant_namespaces=(
  tenant-accounts
  tenant-payments
  tenant-cards
  tenant-customer-profile
  tenant-fraud
  tenant-open-banking
)

render() {
  "${python_bin}" "${repo_root}/scripts/render_synthetic_apis.py" "$@"
}

render --include-kind Namespace | kubectl apply --dry-run=server -f -

missing_namespaces=()
for namespace in "${tenant_namespaces[@]}"; do
  if ! kubectl get namespace "${namespace}" >/dev/null 2>&1; then
    missing_namespaces+=("${namespace}")
  fi
done

if [[ "${#missing_namespaces[@]}" -gt 0 ]]; then
  render | kubectl apply --dry-run=client -f - >/dev/null
  printf 'Synthetic tenant namespaces are absent: %s\n' "${missing_namespaces[*]}"
  echo "Namespace manifests passed server dry-run; full synthetic API render passed client dry-run."
  echo "Full server dry-run for namespaced synthetic API resources requires tenant namespaces to exist first."
  exit 0
fi

render | kubectl apply --dry-run=server -f -
