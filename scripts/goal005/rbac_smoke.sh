#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
report="${repo_root}/reports/goal-005-rbac-runtime.md"
tmp_table="$(mktemp)"
tmp_output="$(mktemp)"
trap 'rm -f "${tmp_table}" "${tmp_output}"' EXIT

cd "${repo_root}"

status="pass"
{
  echo "| Actor | Namespace | Verb | Resource | Expected | Actual | Result |"
  echo "| --- | --- | --- | --- | --- | --- | --- |"
} >"${tmp_table}"

record_can_i() {
  local actor="$1"
  local namespace="$2"
  local verb="$3"
  local resource="$4"
  local expected="$5"
  local actual
  if [[ "${namespace}" == "-" ]]; then
    actual="$(kubectl auth can-i "${verb}" "${resource}" --as="${actor}" 2>/dev/null || true)"
  else
    actual="$(kubectl auth can-i "${verb}" "${resource}" -n "${namespace}" --as="${actor}" 2>/dev/null || true)"
  fi
  if [[ "${actual}" != "yes" ]]; then
    actual="no"
  fi
  local result="PASS"
  if [[ "${actual}" != "${expected}" ]]; then
    result="FAIL"
    status="fail"
  fi
  echo "| \`${actor}\` | \`${namespace}\` | \`${verb}\` | \`${resource}\` | \`${expected}\` | \`${actual}\` | ${result} |" >>"${tmp_table}"
}

dry_run_plugin() {
  local actor="$1"
  local namespace="$2"
  local name="$3"
  if cat <<YAML | kubectl apply --server-side --dry-run=server --as="${actor}" -f - >"${tmp_output}" 2>&1
apiVersion: configuration.konghq.com/v1
kind: KongPlugin
metadata:
  name: goal005-rbac-dry-run-${name}
  namespace: ${namespace}
  annotations:
    kubernetes.io/ingress.class: kong
  labels:
    platform.soyspray.io/managed-by: gitops
    platform.soyspray.io/goal: goal-005
plugin: response-transformer
config:
  add:
    headers:
      - X-Goal005-Rbac-Dry-Run:true
YAML
  then
    echo "- ${actor} server-side dry-run apply in ${namespace}: PASS" >>"${tmp_output}.summary"
  else
    echo "- ${actor} server-side dry-run apply in ${namespace}: FAIL" >>"${tmp_output}.summary"
    cat "${tmp_output}" >>"${tmp_output}.summary"
    status="fail"
  fi
}

retail_actor="system:serviceaccount:tenant-accounts:retail-accounts-api-applier"
payments_actor="system:serviceaccount:tenant-payments:payments-api-applier"
risk_actor="system:serviceaccount:tenant-fraud:risk-compliance-api-applier"
platform_actor="system:serviceaccount:platform-kong:kong-platform-change-applier"

for namespace in tenant-accounts tenant-cards tenant-customer-profile; do
  record_can_i "${retail_actor}" "${namespace}" get httproutes.gateway.networking.k8s.io yes
  record_can_i "${retail_actor}" "${namespace}" create kongplugins.configuration.konghq.com yes
done
for namespace in tenant-payments tenant-open-banking; do
  record_can_i "${payments_actor}" "${namespace}" get httproutes.gateway.networking.k8s.io yes
  record_can_i "${payments_actor}" "${namespace}" create kongplugins.configuration.konghq.com yes
done
record_can_i "${risk_actor}" tenant-fraud get httproutes.gateway.networking.k8s.io yes
record_can_i "${risk_actor}" tenant-fraud create kongplugins.configuration.konghq.com yes
record_can_i "${platform_actor}" platform-kong get configmaps yes

dry_run_plugin "${retail_actor}" tenant-accounts retail
dry_run_plugin "${payments_actor}" tenant-payments payments
dry_run_plugin "${risk_actor}" tenant-fraud risk

for actor in "${retail_actor}" "${payments_actor}" "${risk_actor}"; do
  case "${actor}" in
    *tenant-accounts*) own_ns="tenant-accounts"; other_ns="tenant-payments" ;;
    *tenant-payments*) own_ns="tenant-payments"; other_ns="tenant-accounts" ;;
    *) own_ns="tenant-fraud"; other_ns="tenant-accounts" ;;
  esac
  record_can_i "${actor}" "${own_ns}" get secrets no
  record_can_i "${actor}" "${own_ns}" list secrets no
  record_can_i "${actor}" "${other_ns}" get secrets no
  record_can_i "${actor}" "${other_ns}" list secrets no
  record_can_i "${actor}" "${own_ns}" create networkpolicies.networking.k8s.io no
  record_can_i "${actor}" "${own_ns}" patch networkpolicies.networking.k8s.io no
  record_can_i "${actor}" "-" create kongclusterplugins.configuration.konghq.com no
  record_can_i "${actor}" "-" patch clusterroles.rbac.authorization.k8s.io no
  record_can_i "${actor}" "-" patch clusterrolebindings.rbac.authorization.k8s.io no
  record_can_i "${actor}" "-" patch validatingwebhookconfigurations.admissionregistration.k8s.io no
  record_can_i "${actor}" "${other_ns}" get httproutes.gateway.networking.k8s.io no
  record_can_i "${actor}" "${other_ns}" get services no
  record_can_i "${actor}" "${other_ns}" get kongplugins.configuration.konghq.com no
  record_can_i "${actor}" platform-kong get service/banklab-kong-gateway-admin no
done

{
  echo "# Goal005 RBAC Runtime Evidence"
  echo
  echo "Status: ${status}"
  echo
  echo "Supported states: not run, pass, fail, blocked, partial"
  echo
  echo "Generated at: $(date -Iseconds)"
  echo
  echo "Kubernetes context: $(kubectl config current-context 2>/dev/null || true)"
  echo
  echo "## kubectl auth can-i checks"
  cat "${tmp_table}"
  echo
  echo "## Server-side dry-run apply checks"
  if [[ -f "${tmp_output}.summary" ]]; then
    cat "${tmp_output}.summary"
  fi
} >"${report}"

if [[ "${status}" != "pass" ]]; then
  cat "${report}"
  exit 1
fi

cat "${report}"
echo "${report#${repo_root}/} generated."
