#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
report="${repo_root}/reports/goal-005-change-rollout.md"
tmp_output="$(mktemp)"
tmp_body="$(mktemp)"
tmp_headers="$(mktemp)"
tmp_apply="$(mktemp)"
trap 'rm -f "${tmp_output}" "${tmp_body}" "${tmp_headers}" "${tmp_apply}"' EXIT
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
    echo "# Goal005 Change Rollout Evidence"
    echo
    echo "Status: ${status}"
    echo
    echo "Supported states: not run, pass, fail, blocked, partial"
    echo
    echo "Generated at: $(date -Iseconds)"
    echo
    echo "Kubernetes context: $(kubectl config current-context 2>/dev/null || true)"
    echo
    echo "Sample change ID: goal-005-normal-change"
    echo
    echo "Tenant: retail-accounts"
    echo
    echo "API: accounts"
    echo
    echo "Route/service affected: tenant-accounts/HTTPRoute/banklab-accounts"
    echo
    echo "Manifest applied: scripts/render_goal005_change.py"
    echo
    echo "## Apply output"
    cat "${tmp_apply}"
    echo
    echo "## Runtime smoke"
    cat "${tmp_output}"
  } >"${report}"
}

fail() {
  echo "$1" | tee -a "${tmp_output}" >&2
  write_report "fail"
  exit 1
}

if [[ -z "${BANKLAB_MOBILE_BANKING_APP_API_KEY:-}" ]]; then
  echo "Missing required environment variable BANKLAB_MOBILE_BANKING_APP_API_KEY." | tee -a "${tmp_output}" >&2
  write_report "blocked"
  exit 1
fi

cd "${repo_root}"
platform/kong/scripts/require-cluster-mutation-permission.sh
"${python_bin}" scripts/render_goal005_change.py | kubectl apply -f - >"${tmp_apply}" 2>&1 || {
  cat "${tmp_apply}" >&2
  write_report "fail"
  exit 1
}
sleep 2

if ! proxy_ip="$(kubectl -n platform-kong get service banklab-kong-gateway-proxy -o jsonpath='{.status.loadBalancer.ingress[0].ip}')" || [[ -z "${proxy_ip}" ]]; then
  echo "Kong proxy LoadBalancer IP not available." | tee -a "${tmp_output}" >&2
  write_report "blocked"
  exit 1
fi

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

[[ "${status}" == "200" ]] || fail "HTTP smoke result: fail; expected 200, got ${status}; body=$(cat "${tmp_body}")"
grep -Fq "banklab-accounts-ok" "${tmp_body}" || fail "goal004 marker preservation: fail"
grep -Eiq '^X-Banklab-Correlation-ID:' "${tmp_headers}" || fail "goal004 correlation ID preservation: fail"
grep -Eiq '^(x-)?ratelimit-limit|^ratelimit-limit:' "${tmp_headers}" || fail "rate-limit header preservation: fail"
grep -Eiq '^X-Goal005-Change-Id:[[:space:]]*goal-005-normal-change' "${tmp_headers}" || fail "observed temporary header: fail"

echo "HTTP smoke result: pass; status=200" | tee -a "${tmp_output}"
echo "observed temporary header: pass; X-Goal005-Change-Id=goal-005-normal-change" | tee -a "${tmp_output}"
echo "goal004 marker/header preservation: pass; marker=banklab-accounts-ok; correlation-id=present" | tee -a "${tmp_output}"
echo "auth preservation: pass; valid API key accepted" | tee -a "${tmp_output}"
echo "rate-limit header preservation: pass" | tee -a "${tmp_output}"
write_report "pass"
echo "${report#${repo_root}/} generated."
