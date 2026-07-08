#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
report="${repo_root}/reports/synthetic-api-negative-test-results.md"
platform_report="${repo_root}/platform/kong/synthetic-apis/RUNTIME-NEGATIVE-TEST-RESULTS.md"
tmp_output="$(mktemp)"
tmp_body="$(mktemp)"
tmp_err="$(mktemp)"
trap 'rm -f "${tmp_output}" "${tmp_body}" "${tmp_err}"' EXIT
curl_connect_timeout="${BANKLAB_SYNTHETIC_API_CURL_CONNECT_TIMEOUT:-3}"
curl_max_time="${BANKLAB_SYNTHETIC_API_CURL_MAX_TIME:-10}"

write_report() {
  local status="$1"
  {
    echo "# Synthetic API Negative Test Results"
    echo
    echo "Status: ${status}"
    echo
    echo "Supported states: not run, pass, fail, blocked, partial"
    echo
    echo "Generated at: $(date -Iseconds)"
    echo
    echo "Kubernetes context: $(kubectl config current-context 2>/dev/null || true)"
    echo
    echo "## Negative checks"
    cat "${tmp_output}"
  } >"${report}"
  cp "${report}" "${platform_report}"
}

expect_status() {
  local host="$1"
  local path="$2"
  local expected="$3"
  local status
  status="$(curl --silent --show-error --connect-timeout "${curl_connect_timeout}" --max-time "${curl_max_time}" --output "${tmp_body}" --write-out '%{http_code}' --resolve "${host}:80:${proxy_ip}" "http://${host}${path}")"
  if [[ "${status}" != "${expected}" ]]; then
    echo "${host}${path}: fail; expected ${expected}; got ${status}; body=$(cat "${tmp_body}")" | tee -a "${tmp_output}" >&2
    return 1
  fi
  echo "${host}${path}: pass; status=${status}" | tee -a "${tmp_output}"
}

if ! proxy_ip="$(kubectl -n platform-kong get service banklab-kong-gateway-proxy -o jsonpath='{.status.loadBalancer.ingress[0].ip}')" || [[ -z "${proxy_ip}" ]]; then
  echo "Kong proxy LoadBalancer IP not available." | tee -a "${tmp_output}" >&2
  write_report "blocked"
  exit 1
fi

status="pass"
expect_status unknown.internal.banklab.test /accounts/v1/health 404 || status="fail"
expect_status api.internal.banklab.test /unknown/v1/health 404 || status="fail"
expect_status api.external.banklab.test /accounts/v1/health 404 || status="fail"
expect_status api.external.banklab.test /payments/v1/health 404 || status="fail"
expect_status api.external.banklab.test /cards/v1/health 404 || status="fail"
expect_status api.external.banklab.test /customers/v1/health 404 || status="fail"
expect_status api.external.banklab.test /fraud/v1/health 404 || status="fail"

if curl --silent --show-error --connect-timeout 3 --max-time 5 "http://${proxy_ip}:8444/status" >"${tmp_body}" 2>"${tmp_err}"; then
  echo "admin API negative probe: fail; Admin API unexpectedly reachable on ${proxy_ip}:8444" | tee -a "${tmp_output}" >&2
  status="fail"
else
  echo "admin API negative probe: pass" | tee -a "${tmp_output}"
fi

write_report "${status}"
if [[ "${status}" != "pass" ]]; then
  exit 1
fi

echo "${report#${repo_root}/} generated."
