#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
report="${repo_root}/reports/goal-007-consumer-onboarding-rollback.md"
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
credential_source="environment variables"
stable_plugins="banklab-key-auth,banklab-acl,banklab-rate-limit,banklab-correlation-id"

write_report() {
  local status="$1"
  {
    echo "# Goal007 Consumer Onboarding Rollback Evidence"
    echo
    echo "Status: ${status}"
    echo
    echo "Supported states: not run, pass, fail, blocked, partial"
    echo
    echo "Generated at: $(date -Iseconds)"
    echo
    echo "Kubernetes context: $(kubectl config current-context 2>/dev/null || true)"
    echo
    echo "Rollback command: make goal007-consumer-onboarding-rollback-and-smoke"
    echo
    echo "Resources removed: KongConsumer/synthetic-clients/branch-insights-app, Secret/synthetic-clients/banklab-branch-insights-app-key-auth, Secret/synthetic-clients/banklab-branch-insights-app-accounts-acl"
    echo
    echo "Resources preserved: tenant-accounts/HTTPRoute/banklab-accounts and baseline plugins ${stable_plugins}"
    echo
    echo "Credential source: ${credential_source}"
    echo
    echo "Credential values printed: no"
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

blocked() {
  echo "$1" | tee -a "${tmp_output}" >&2
  write_report "blocked"
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

wait_for_old_key_rejected() {
  local status
  for _ in $(seq 1 30); do
    status="$(
      curl --silent --show-error \
        --connect-timeout "${curl_connect_timeout}" \
        --max-time "${curl_max_time}" \
        --output "${tmp_body}" \
        --write-out '%{http_code}' \
        --header "apikey: ${BANKLAB_BRANCH_INSIGHTS_APP_API_KEY}" \
        --resolve "api.internal.banklab.test:80:${proxy_ip}" \
        "http://api.internal.banklab.test/accounts/v1/health"
    )"
    if [[ "${status}" == "401" ]]; then
      return 0
    fi
    sleep 2
  done
  fail "removed consumer key expected 401 after rollback, got ${status:-unknown}; body=$(cat "${tmp_body}")"
}

cd "${repo_root}"
platform/kong/scripts/require-cluster-mutation-permission.sh
load_secret_env BANKLAB_MOBILE_BANKING_APP_API_KEY banklab-mobile-banking-app-key-auth key
load_secret_env BANKLAB_INTERNET_BANKING_WEB_API_KEY banklab-internet-banking-web-key-auth key

"${python_bin}" scripts/render_goal007_consumer_onboarding.py --delete | kubectl delete --ignore-not-found=true -f - >"${tmp_rollback}" 2>&1 || {
  cat "${tmp_rollback}" >&2
  write_report "fail"
  exit 1
}

if ! proxy_ip="$(kubectl -n platform-kong get service banklab-kong-gateway-proxy -o jsonpath='{.status.loadBalancer.ingress[0].ip}')" || [[ -z "${proxy_ip}" ]]; then
  blocked "Kong proxy LoadBalancer IP not available."
fi

if kubectl -n synthetic-clients get kongconsumer branch-insights-app >/dev/null 2>&1; then
  fail "KongConsumer synthetic-clients/branch-insights-app still exists after rollback"
fi
if kubectl -n synthetic-clients get secret banklab-branch-insights-app-key-auth >/dev/null 2>&1; then
  fail "key-auth Secret still exists after rollback"
fi
if kubectl -n synthetic-clients get secret banklab-branch-insights-app-accounts-acl >/dev/null 2>&1; then
  fail "ACL Secret still exists after rollback"
fi
echo "consumer and runtime credential resources removed: pass" | tee -a "${tmp_output}"

if [[ -n "${BANKLAB_BRANCH_INSIGHTS_APP_API_KEY:-}" ]]; then
  wait_for_old_key_rejected
  echo "removed consumer key rejected after rollback: pass; status=401" | tee -a "${tmp_output}"
else
  echo "removed consumer key rejected after rollback: not checked; key env var absent" | tee -a "${tmp_output}"
fi

curl_accounts 200 --header "apikey: ${BANKLAB_MOBILE_BANKING_APP_API_KEY}" >/dev/null
grep -Fq "banklab-accounts-ok" "${tmp_body}" || fail "accounts marker preservation after rollback: fail"
grep -Eiq '^X-Banklab-Correlation-ID:' "${tmp_headers}" || fail "correlation ID preservation after rollback: fail"
grep -Eiq '^(x-)?ratelimit-limit:' "${tmp_headers}" || fail "rate-limit header preservation after rollback: fail"
if grep -Eiq '^X-Banklab-Product-Contract:' "${tmp_headers}"; then
  fail "goal006 product marker unexpectedly returned after goal007 rollback"
fi
echo "baseline accounts consumer still succeeds after rollback: pass; status=200" | tee -a "${tmp_output}"
echo "correlation ID and rate-limit headers preserved after rollback: pass" | tee -a "${tmp_output}"
echo "goal006 product marker remains absent after rollback: pass" | tee -a "${tmp_output}"

curl_accounts 401 >/dev/null
echo "missing API key remains unauthorized after rollback: pass; status=401" | tee -a "${tmp_output}"
curl_accounts 403 --header "apikey: ${BANKLAB_INTERNET_BANKING_WEB_API_KEY}" >/dev/null
echo "wrong ACL key remains forbidden after rollback: pass; status=403" | tee -a "${tmp_output}"

plugins="$(kubectl -n tenant-accounts get httproute banklab-accounts -o jsonpath='{.metadata.annotations.konghq\.com/plugins}')"
if [[ "${plugins}" != "${stable_plugins}" ]]; then
  fail "runtime route annotation mismatch after rollback; expected ${stable_plugins}; got ${plugins}"
fi
echo "runtime route annotation matches post-rollback baseline: pass; plugins=${plugins}" | tee -a "${tmp_output}"

write_report "pass"
echo "${report#${repo_root}/} generated."
