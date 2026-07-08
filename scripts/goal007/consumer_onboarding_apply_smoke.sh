#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
report="${repo_root}/reports/goal-007-consumer-onboarding-rollout.md"
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
burst_count="${BANKLAB_GOAL007_RATE_LIMIT_BURST_COUNT:-20}"
credential_source="environment variable"
stable_plugins="banklab-key-auth,banklab-acl,banklab-rate-limit,banklab-correlation-id"

write_report() {
  local status="$1"
  {
    echo "# Goal007 Consumer Onboarding Rollout Evidence"
    echo
    echo "Status: ${status}"
    echo
    echo "Supported states: not run, pass, fail, blocked, partial"
    echo
    echo "Generated at: $(date -Iseconds)"
    echo
    echo "Kubernetes context: $(kubectl config current-context 2>/dev/null || true)"
    echo
    echo "Consumer: branch-insights-app"
    echo
    echo "Owning team: branch-insights"
    echo
    echo "Target product: accounts-self-service-health-v1"
    echo
    echo "Target route: tenant-accounts/HTTPRoute/banklab-accounts"
    echo
    echo "Expected baseline plugins: ${stable_plugins}"
    echo
    echo "Credential source: ${credential_source}"
    echo
    echo "Credential values printed: no"
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

ensure_consumer_key() {
  if [[ -n "${BANKLAB_BRANCH_INSIGHTS_APP_API_KEY:-}" ]]; then
    return 0
  fi
  local generated
  generated="$("${python_bin}" - <<'PY'
import secrets
print("goal007-" + secrets.token_urlsafe(32))
PY
)"
  export BANKLAB_BRANCH_INSIGHTS_APP_API_KEY="${generated}"
  credential_source="generated runtime environment variable plus runtime credential Secrets"
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

check_success_headers() {
  grep -Fq "banklab-accounts-ok" "${tmp_body}" || fail "accounts marker preservation: fail"
  grep -Eiq '^X-Banklab-Correlation-ID:' "${tmp_headers}" || fail "correlation ID preservation: fail"
  grep -Eiq '^(x-)?ratelimit-limit:' "${tmp_headers}" || fail "rate-limit header preservation: fail"
  if grep -Eiq '^X-Banklab-Product-Contract:' "${tmp_headers}"; then
    fail "goal006 product marker must remain absent after goal006 rollback"
  fi
}

wait_for_onboarded_consumer() {
  local status
  for _ in $(seq 1 30); do
    status="$(
      curl --silent --show-error \
        --connect-timeout "${curl_connect_timeout}" \
        --max-time "${curl_max_time}" \
        --output "${tmp_body}" \
        --dump-header "${tmp_headers}" \
        --write-out '%{http_code}' \
        --header "apikey: ${BANKLAB_BRANCH_INSIGHTS_APP_API_KEY}" \
        --resolve "api.internal.banklab.test:80:${proxy_ip}" \
        "http://api.internal.banklab.test/accounts/v1/health"
    )"
    if [[ "${status}" == "200" ]]; then
      return 0
    fi
    sleep 2
  done
  fail "onboarded consumer positive smoke: fail; last_status=${status:-unknown}; body=$(cat "${tmp_body}")"
}

cd "${repo_root}"
platform/kong/scripts/require-cluster-mutation-permission.sh
load_secret_env BANKLAB_INTERNET_BANKING_WEB_API_KEY banklab-internet-banking-web-key-auth key
ensure_consumer_key

{
  "${python_bin}" scripts/render_goal007_runtime_credentials.py | kubectl apply -f -
  "${python_bin}" scripts/render_goal007_consumer_onboarding.py | kubectl apply -f -
} >"${tmp_apply}" 2>&1 || {
  cat "${tmp_apply}" >&2
  write_report "fail"
  exit 1
}

if ! proxy_ip="$(kubectl -n platform-kong get service banklab-kong-gateway-proxy -o jsonpath='{.status.loadBalancer.ingress[0].ip}')" || [[ -z "${proxy_ip}" ]]; then
  blocked "Kong proxy LoadBalancer IP not available."
fi

wait_for_onboarded_consumer
check_success_headers
echo "onboarded consumer positive smoke: pass; status=200; consumer=branch-insights-app; marker=banklab-accounts-ok" | tee -a "${tmp_output}"
echo "goal004 correlation ID preservation: pass" | tee -a "${tmp_output}"
echo "goal004 rate-limit header preservation: pass" | tee -a "${tmp_output}"
echo "goal006 product marker remains absent: pass" | tee -a "${tmp_output}"

curl_accounts 401 >/dev/null
echo "missing API key remains unauthorized: pass; status=401" | tee -a "${tmp_output}"
curl_accounts 403 --header "apikey: ${BANKLAB_INTERNET_BANKING_WEB_API_KEY}" >/dev/null
echo "valid key without accounts ACL remains forbidden: pass; status=403" | tee -a "${tmp_output}"

sleep 2
statuses=()
for _ in $(seq 1 "${burst_count}"); do
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
  statuses+=("${status}")
done
if printf '%s\n' "${statuses[@]}" | grep -Fxq "429"; then
  echo "onboarded consumer rate-limit burst: pass; statuses=${statuses[*]}" | tee -a "${tmp_output}"
else
  fail "onboarded consumer rate-limit burst: fail; expected at least one 429; statuses=${statuses[*]}"
fi

kubectl -n synthetic-clients get kongconsumer branch-insights-app >/dev/null || fail "KongConsumer synthetic-clients/branch-insights-app missing after apply"
kubectl -n synthetic-clients get secret banklab-branch-insights-app-key-auth >/dev/null || fail "key-auth Secret missing after apply"
kubectl -n synthetic-clients get secret banklab-branch-insights-app-accounts-acl >/dev/null || fail "ACL Secret missing after apply"
echo "runtime consumer and credential resources exist: pass" | tee -a "${tmp_output}"

plugins="$(kubectl -n tenant-accounts get httproute banklab-accounts -o jsonpath='{.metadata.annotations.konghq\.com/plugins}')"
if [[ "${plugins}" != "${stable_plugins}" ]]; then
  fail "runtime route annotation mismatch; expected ${stable_plugins}; got ${plugins}"
fi
echo "runtime route annotation preserves baseline plugins: pass; plugins=${plugins}" | tee -a "${tmp_output}"

write_report "pass"
echo "${report#${repo_root}/} generated."
