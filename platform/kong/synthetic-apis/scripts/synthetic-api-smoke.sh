#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
report="${repo_root}/reports/synthetic-api-route-smoke-results.md"
platform_report="${repo_root}/platform/kong/synthetic-apis/RUNTIME-SMOKE-RESULTS.md"
tmp_output="$(mktemp)"
trap 'rm -f "${tmp_output}"' EXIT
curl_connect_timeout="${BANKLAB_SYNTHETIC_API_CURL_CONNECT_TIMEOUT:-3}"
curl_max_time="${BANKLAB_SYNTHETIC_API_CURL_MAX_TIME:-10}"

write_report() {
  local status="$1"
  {
    echo "# Synthetic API Route Smoke Results"
    echo
    echo "Status: ${status}"
    echo
    echo "Supported states: not run, pass, fail, blocked, partial"
    echo
    echo "Generated at: $(date -Iseconds)"
    echo
    echo "Kubernetes context: $(kubectl config current-context 2>/dev/null || true)"
    echo
    echo "## Route checks"
    cat "${tmp_output}"
  } >"${report}"
  cp "${report}" "${platform_report}"
}

check_route() {
  local host="$1"
  local path="$2"
  local expected="$3"
  local body
  body="$(curl --silent --show-error --fail --connect-timeout "${curl_connect_timeout}" --max-time "${curl_max_time}" --resolve "${host}:80:${proxy_ip}" "http://${host}${path}")"
  if [[ "${body}" != *"${expected}"* ]]; then
    echo "${host}${path}: fail; expected marker ${expected}; body=${body}" | tee -a "${tmp_output}" >&2
    return 1
  fi
  echo "${host}${path}: pass; marker=${expected}" | tee -a "${tmp_output}"
}

if ! proxy_ip="$(kubectl -n platform-kong get service banklab-kong-gateway-proxy -o jsonpath='{.status.loadBalancer.ingress[0].ip}')" || [[ -z "${proxy_ip}" ]]; then
  echo "Kong proxy LoadBalancer IP not available." | tee -a "${tmp_output}" >&2
  write_report "blocked"
  exit 1
fi

if check_route api.internal.banklab.test /accounts/v1/health banklab-accounts-ok \
  && check_route api.internal.banklab.test /payments/v1/health banklab-payments-ok \
  && check_route api.internal.banklab.test /cards/v1/health banklab-cards-ok \
  && check_route api.internal.banklab.test /customers/v1/health banklab-customer-profile-ok \
  && check_route api.internal.banklab.test /fraud/v1/health banklab-fraud-decisions-ok \
  && check_route api.external.banklab.test /open-banking/v1/health banklab-open-banking-ok; then
  write_report "pass"
else
  write_report "fail"
  exit 1
fi

echo "${report#${repo_root}/} generated."
