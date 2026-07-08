#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
rollout_report="${repo_root}/reports/goal-009-governed-response-headers-rollout.md"
runtime_report="${repo_root}/reports/goal-009-governed-response-headers-runtime.md"
tmp_output="$(mktemp)"
tmp_body="$(mktemp)"
tmp_headers="$(mktemp)"
tmp_apply="$(mktemp)"
tmp_dryrun="$(mktemp)"
trap 'rm -f "${tmp_output}" "${tmp_body}" "${tmp_headers}" "${tmp_apply}" "${tmp_dryrun}"' EXIT
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
credential_source="environment variables"

write_rollout_report() {
  local status="$1"
  {
    echo "# Goal009 Governed Response Headers Rollout Evidence"
    echo
    echo "Status: ${status}"
    echo
    echo "Supported states: not run, pass, fail, blocked, partial"
    echo
    echo "Generated at: $(date -Iseconds)"
    echo
    echo "Kubernetes context: $(kubectl config current-context 2>/dev/null || true)"
    echo
    echo "Route/service affected: tenant-accounts/HTTPRoute/banklab-accounts"
    echo
    echo "Plugin applied: tenant-accounts/KongPlugin/banklab-goal009-security-headers"
    echo
    echo "Plugin type: response-transformer"
    echo
    echo "## Server dry-run output"
    cat "${tmp_dryrun}"
    echo
    echo "## Apply output"
    cat "${tmp_apply}"
    echo
    echo "## Convergence checks"
    cat "${tmp_output}"
  } >"${rollout_report}"
}

write_runtime_report() {
  local status="$1"
  {
    echo "# Goal009 Governed Response Headers Runtime Evidence"
    echo
    echo "Status: ${status}"
    echo
    echo "Supported states: not run, pass, fail, blocked, partial"
    echo
    echo "Generated at: $(date -Iseconds)"
    echo
    echo "Kubernetes context: $(kubectl config current-context 2>/dev/null || true)"
    echo
    echo "Credential source: ${credential_source}"
    echo
    echo "## Runtime smoke"
    cat "${tmp_output}"
  } >"${runtime_report}"
}

write_reports() {
  local status="$1"
  write_rollout_report "${status}"
  write_runtime_report "${status}"
}

fail() {
  echo "$1" | tee -a "${tmp_output}" >&2
  write_reports "fail"
  exit 1
}

blocked() {
  echo "$1" | tee -a "${tmp_output}" >&2
  write_reports "blocked"
  exit 1
}

load_secret_env() {
  local env_name="$1"
  local secret_name="$2"
  local field_name="$3"
  if [[ -n "${!env_name:-}" ]]; then
    return 0
  fi
  local encoded
  if ! encoded="$(kubectl -n synthetic-clients get secret "${secret_name}" -o "jsonpath={.data.${field_name}}" 2>/dev/null)" || [[ -z "${encoded}" ]]; then
    blocked "Missing required environment variable ${env_name}, and Secret synthetic-clients/${secret_name} field ${field_name} was not readable."
  fi
  local value
  if ! value="$(printf '%s' "${encoded}" | base64 -d 2>/dev/null)" || [[ -z "${value}" ]]; then
    blocked "Secret synthetic-clients/${secret_name} field ${field_name} could not be decoded."
  fi
  export "${env_name}=${value}"
  credential_source="environment variables plus runtime credential Secrets"
}

curl_accounts() {
  local expected="$1"
  shift
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
    fail "accounts request expected ${expected}, got ${status}; body=$(cat "${tmp_body}")"
  fi
  printf '%s' "${status}"
}

require_goal009_headers() {
  grep -Eiq '^X-Content-Type-Options:[[:space:]]*nosniff[[:space:]]*$' "${tmp_headers}" || return 1
  grep -Eiq '^X-Frame-Options:[[:space:]]*DENY[[:space:]]*$' "${tmp_headers}" || return 1
  grep -Eiq '^Referrer-Policy:[[:space:]]*no-referrer[[:space:]]*$' "${tmp_headers}" || return 1
  grep -Eiq '^X-BankLab-Response-Policy:[[:space:]]*goal009[[:space:]]*$' "${tmp_headers}" || return 1
}

cd "${repo_root}"
platform/kong/scripts/require-cluster-mutation-permission.sh
load_secret_env BANKLAB_MOBILE_BANKING_APP_API_KEY banklab-mobile-banking-app-key-auth key
load_secret_env BANKLAB_INTERNET_BANKING_WEB_API_KEY banklab-internet-banking-web-key-auth key

if "${python_bin}" scripts/render_goal009_response_headers.py | kubectl apply --dry-run=server -f - >"${tmp_dryrun}" 2>&1; then
  echo "server dry-run before apply: pass" | tee -a "${tmp_output}"
else
  cat "${tmp_dryrun}" >&2
  fail "goal009 server dry-run before apply failed"
fi

"${python_bin}" scripts/render_goal009_response_headers.py | kubectl apply -f - >"${tmp_apply}" 2>&1 || {
  cat "${tmp_apply}" >&2
  write_reports "fail"
  exit 1
}

if ! proxy_ip="$(kubectl -n platform-kong get service banklab-kong-gateway-proxy -o jsonpath='{.status.loadBalancer.ingress[0].ip}')" || [[ -z "${proxy_ip}" ]]; then
  blocked "Kong proxy LoadBalancer IP not available."
fi

wait_for_goal009_headers() {
  local status
  for _ in $(seq 1 30); do
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
    if [[ "${status}" == "200" ]] && require_goal009_headers; then
      return 0
    fi
    sleep 2
  done
  fail "goal009 response headers observed: fail; last_status=${status:-unknown}; body=$(cat "${tmp_body}")"
}

wait_for_goal009_headers
grep -Fq "banklab-accounts-ok" "${tmp_body}" || fail "accounts marker preservation: fail"
grep -Eiq '^X-Banklab-Correlation-ID:' "${tmp_headers}" || fail "correlation ID preservation: fail"
grep -Eiq '^(x-)?ratelimit-limit:' "${tmp_headers}" || fail "rate-limit header preservation: fail"

echo "positive governed response header smoke: pass; status=200" | tee -a "${tmp_output}"
echo "header X-Content-Type-Options=nosniff: pass" | tee -a "${tmp_output}"
echo "header X-Frame-Options=DENY: pass" | tee -a "${tmp_output}"
echo "header Referrer-Policy=no-referrer: pass" | tee -a "${tmp_output}"
echo "header X-BankLab-Response-Policy=goal009: pass" | tee -a "${tmp_output}"
echo "accounts marker preservation: pass; marker=banklab-accounts-ok" | tee -a "${tmp_output}"
echo "goal004 correlation ID preservation: pass" | tee -a "${tmp_output}"
echo "goal004 rate-limit header preservation: pass" | tee -a "${tmp_output}"

curl_accounts 401 >/dev/null
echo "missing API key remains unauthorized: pass; status=401" | tee -a "${tmp_output}"
curl_accounts 403 --header "apikey: ${BANKLAB_INTERNET_BANKING_WEB_API_KEY}" >/dev/null
echo "wrong ACL key remains forbidden: pass; status=403" | tee -a "${tmp_output}"

plugins="$(kubectl -n tenant-accounts get httproute banklab-accounts -o jsonpath='{.metadata.annotations.konghq\.com/plugins}')"
if [[ "${plugins}" != *"banklab-goal009-security-headers"* ]]; then
  fail "runtime route annotation missing goal009 plugin"
fi
echo "runtime route annotation includes goal009 plugin: pass" | tee -a "${tmp_output}"

kubectl -n tenant-accounts get kongplugin banklab-goal009-security-headers >/dev/null || fail "goal009 KongPlugin missing after apply"
echo "goal009 KongPlugin resource exists: pass" | tee -a "${tmp_output}"

write_reports "pass"
echo "${rollout_report#${repo_root}/} generated."
echo "${runtime_report#${repo_root}/} generated."
