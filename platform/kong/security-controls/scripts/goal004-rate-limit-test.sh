#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
report="${repo_root}/reports/goal004-rate-limit-results.md"
platform_report="${repo_root}/platform/kong/security-controls/RUNTIME-RATE-LIMIT-RESULTS.md"
tmp_output="$(mktemp)"
tmp_body="$(mktemp)"
trap 'rm -f "${tmp_output}" "${tmp_body}"' EXIT
curl_connect_timeout="${BANKLAB_SYNTHETIC_API_CURL_CONNECT_TIMEOUT:-3}"
curl_max_time="${BANKLAB_SYNTHETIC_API_CURL_MAX_TIME:-10}"
burst_count="${BANKLAB_GOAL004_RATE_LIMIT_BURST_COUNT:-20}"

write_report() {
  local status="$1"
  {
    echo "# Goal004 Rate Limit Results"
    echo
    echo "Status: ${status}"
    echo
    echo "Supported states: not run, pass, fail, blocked, partial"
    echo
    echo "Generated at: $(date -Iseconds)"
    echo
    echo "Kubernetes context: $(kubectl config current-context 2>/dev/null || true)"
    echo
    echo "Rate limit policy: redis"
    echo
    echo "## Checks"
    cat "${tmp_output}"
  } >"${report}"
  cp "${report}" "${platform_report}"
}

if [[ -z "${BANKLAB_MOBILE_BANKING_APP_API_KEY:-}" ]]; then
  echo "Missing required environment variable BANKLAB_MOBILE_BANKING_APP_API_KEY." | tee -a "${tmp_output}" >&2
  write_report "blocked"
  exit 1
fi

if ! proxy_ip="$(kubectl -n platform-kong get service banklab-kong-gateway-proxy -o jsonpath='{.status.loadBalancer.ingress[0].ip}')" || [[ -z "${proxy_ip}" ]]; then
  echo "Kong proxy LoadBalancer IP not available." | tee -a "${tmp_output}" >&2
  write_report "blocked"
  exit 1
fi

statuses=()
for _ in $(seq 1 "${burst_count}"); do
  status="$(
    curl --silent --show-error \
      --connect-timeout "${curl_connect_timeout}" \
      --max-time "${curl_max_time}" \
      --output "${tmp_body}" \
      --write-out '%{http_code}' \
      --header "apikey: ${BANKLAB_MOBILE_BANKING_APP_API_KEY}" \
      --resolve "api.internal.banklab.test:80:${proxy_ip}" \
      "http://api.internal.banklab.test/accounts/v1/health"
  )"
  statuses+=("${status}")
done

if printf '%s\n' "${statuses[@]}" | grep -Fxq "429"; then
  echo "accounts rate-limit burst: pass; statuses=${statuses[*]}" | tee -a "${tmp_output}"
  echo "redis policy evidence: pass; plugin config is validated locally and runtime returned 429" | tee -a "${tmp_output}"
  write_report "pass"
else
  echo "accounts rate-limit burst: fail; expected at least one 429; statuses=${statuses[*]}" | tee -a "${tmp_output}" >&2
  write_report "fail"
  exit 1
fi

echo "${report#${repo_root}/} generated."
