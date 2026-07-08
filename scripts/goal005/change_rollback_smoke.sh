#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
report="${repo_root}/reports/goal-005-change-rollback.md"
tmp_output="$(mktemp)"
tmp_body="$(mktemp)"
tmp_headers="$(mktemp)"
tmp_rollback="$(mktemp)"
trap 'rm -f "${tmp_output}" "${tmp_body}" "${tmp_headers}" "${tmp_rollback}"' EXIT
python_bin="${BANKLAB_PYTHON:-}"
if [[ -z "${python_bin}" ]]; then
  if [[ -x "${repo_root}/soyspray-venv/bin/python" ]]; then
    python_bin="${repo_root}/soyspray-venv/bin/python"
  else
    python_bin="python3"
  fi
fi
curl_connect_timeout="${BANKLAB_SYNTHETIC_API_CURL_CONNECT_TIMEOUT:-3}"
curl_max_time="${BANKLAB_SYNTHETIC_API_CURL_MAX_TIME:-10}"

write_report() {
  local status="$1"
  {
    echo "# Goal005 Change Rollback Evidence"
    echo
    echo "Status: ${status}"
    echo
    echo "Supported states: not run, pass, fail, blocked, partial"
    echo
    echo "Generated at: $(date -Iseconds)"
    echo
    echo "Kubernetes context: $(kubectl config current-context 2>/dev/null || true)"
    echo
    echo "Rollback command: make goal005-change-rollback-and-smoke"
    echo
    echo "Resources removed or reverted: KongPlugin/tenant-accounts/goal005-normal-change-header removed; HTTPRoute/tenant-accounts/banklab-accounts reverted to stable goal005 annotation set."
    echo
    echo "## Rollback output"
    cat "${tmp_rollback}"
    echo
    echo "## Runtime smoke after rollback"
    cat "${tmp_output}"
  } >"${report}"
}

fail() {
  echo "$1" | tee -a "${tmp_output}" >&2
  write_report "fail"
  exit 1
}

if [[ -z "${BANKLAB_MOBILE_BANKING_APP_API_KEY:-}" || -z "${BANKLAB_INTERNET_BANKING_WEB_API_KEY:-}" ]]; then
  echo "Missing required environment variables BANKLAB_MOBILE_BANKING_APP_API_KEY and/or BANKLAB_INTERNET_BANKING_WEB_API_KEY." | tee -a "${tmp_output}" >&2
  write_report "blocked"
  exit 1
fi

cd "${repo_root}"
platform/kong/scripts/require-cluster-mutation-permission.sh
{
  "${python_bin}" scripts/render_goal005_change.py --rollback | kubectl apply -f -
  "${python_bin}" scripts/render_goal005_change.py --plugin-only | kubectl delete --ignore-not-found=true -f -
} >"${tmp_rollback}" 2>&1 || {
  cat "${tmp_rollback}" >&2
  write_report "fail"
  exit 1
}
sleep 2

if ! proxy_ip="$(kubectl -n platform-kong get service banklab-kong-gateway-proxy -o jsonpath='{.status.loadBalancer.ingress[0].ip}')" || [[ -z "${proxy_ip}" ]]; then
  echo "Kong proxy LoadBalancer IP not available." | tee -a "${tmp_output}" >&2
  write_report "blocked"
  exit 1
fi

curl_status() {
  local label="$1"
  local expected="$2"
  shift 2
  local status
  status="$(
    curl --silent --show-error \
      --connect-timeout "${curl_connect_timeout}" \
      --max-time "${curl_max_time}" \
      --output "${tmp_body}" \
      --dump-header "${tmp_headers}" \
      --write-out '%{http_code}' \
      --resolve "api.internal.banklab.test:80:${proxy_ip}" \
      "$@" \
      "http://api.internal.banklab.test/accounts/v1/health"
  )"
  if [[ "${status}" != "${expected}" ]]; then
    fail "${label}: fail; expected ${expected}, got ${status}; body=$(cat "${tmp_body}")"
  fi
  echo "${label}: pass; status=${status}" | tee -a "${tmp_output}"
}

wait_for_temporary_header_absent() {
  local status
  for _ in $(seq 1 15); do
    status="$(
      curl --silent --show-error \
        --connect-timeout "${curl_connect_timeout}" \
        --max-time "${curl_max_time}" \
        --output "${tmp_body}" \
        --dump-header "${tmp_headers}" \
        --write-out '%{http_code}' \
        --header "apikey: ${BANKLAB_MOBILE_BANKING_APP_API_KEY}" \
        --resolve "api.internal.banklab.test:80:${proxy_ip}" \
        "http://api.internal.banklab.test/accounts/v1/health"
    )"
    if [[ "${status}" == "200" ]] && ! grep -Eiq '^X-Goal005-Change-Id:' "${tmp_headers}"; then
      echo "HTTP smoke result after rollback: pass; status=200" | tee -a "${tmp_output}"
      return 0
    fi
    sleep 2
  done
  fail "temporary header absence: fail; last_status=${status:-unknown}; body=$(cat "${tmp_body}")"
}

wait_for_temporary_header_absent
grep -Fq "banklab-accounts-ok" "${tmp_body}" || fail "goal004 marker preservation after rollback: fail"
grep -Eiq '^X-Banklab-Correlation-ID:' "${tmp_headers}" || fail "goal004 correlation ID preservation after rollback: fail"
grep -Eiq '^(x-)?ratelimit-limit|^ratelimit-limit:' "${tmp_headers}" || fail "rate-limit header preservation after rollback: fail"
echo "temporary header absence: pass" | tee -a "${tmp_output}"
echo "goal004 marker/header behavior remains: pass; marker=banklab-accounts-ok; correlation-id=present" | tee -a "${tmp_output}"

curl_status "missing API key remains unauthorized" 401
curl_status "wrong ACL key remains forbidden" 403 --header "apikey: ${BANKLAB_INTERNET_BANKING_WEB_API_KEY}"
echo "goal004 authentication and authorization still behave correctly: pass" | tee -a "${tmp_output}"

write_report "pass"
echo "${report#${repo_root}/} generated."
