#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
report="${repo_root}/reports/goal-006-product-contract-rollout.md"
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
credential_source="environment variables"

write_report() {
  local status="$1"
  {
    echo "# Goal006 Product Contract Rollout Evidence"
    echo
    echo "Status: ${status}"
    echo
    echo "Supported states: not run, pass, fail, blocked, partial"
    echo
    echo "Generated at: $(date -Iseconds)"
    echo
    echo "Kubernetes context: $(kubectl config current-context 2>/dev/null || true)"
    echo
    echo "Product ID: accounts-self-service-health-v1"
    echo
    echo "Tenant: retail-accounts"
    echo
    echo "API: accounts"
    echo
    echo "Route/service affected: tenant-accounts/HTTPRoute/banklab-accounts"
    echo
    echo "Plugin applied: tenant-accounts/KongPlugin/goal006-product-contract-header"
    echo
    echo "Credential source: ${credential_source}"
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

cd "${repo_root}"
platform/kong/scripts/require-cluster-mutation-permission.sh
load_secret_env BANKLAB_MOBILE_BANKING_APP_API_KEY banklab-mobile-banking-app-key-auth key
load_secret_env BANKLAB_INTERNET_BANKING_WEB_API_KEY banklab-internet-banking-web-key-auth key

"${python_bin}" scripts/render_goal006_product_contract.py | kubectl apply -f - >"${tmp_apply}" 2>&1 || {
  cat "${tmp_apply}" >&2
  write_report "fail"
  exit 1
}

if ! proxy_ip="$(kubectl -n platform-kong get service banklab-kong-gateway-proxy -o jsonpath='{.status.loadBalancer.ingress[0].ip}')" || [[ -z "${proxy_ip}" ]]; then
  blocked "Kong proxy LoadBalancer IP not available."
fi

wait_for_product_header() {
  local status
  for _ in $(seq 1 20); do
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
    if [[ "${status}" == "200" ]] && grep -Eiq '^X-Banklab-Product-Contract:[[:space:]]*accounts-self-service-health-v1' "${tmp_headers}"; then
      return 0
    fi
    sleep 2
  done
  fail "product contract header observed: fail; last_status=${status:-unknown}; body=$(cat "${tmp_body}")"
}

wait_for_product_header
grep -Fq "banklab-accounts-ok" "${tmp_body}" || fail "accounts marker preservation: fail"
grep -Eiq '^X-Banklab-Correlation-ID:' "${tmp_headers}" || fail "correlation ID preservation: fail"
grep -Eiq '^(x-)?ratelimit-limit:' "${tmp_headers}" || fail "rate-limit header preservation: fail"

echo "positive product smoke: pass; status=200; product_header=accounts-self-service-health-v1" | tee -a "${tmp_output}"
echo "accounts marker preservation: pass; marker=banklab-accounts-ok" | tee -a "${tmp_output}"
echo "goal004 correlation ID preservation: pass" | tee -a "${tmp_output}"
echo "goal004 rate-limit header preservation: pass" | tee -a "${tmp_output}"

curl_accounts 401 >/dev/null
echo "missing API key remains unauthorized: pass; status=401" | tee -a "${tmp_output}"
curl_accounts 403 --header "apikey: ${BANKLAB_INTERNET_BANKING_WEB_API_KEY}" >/dev/null
echo "wrong ACL key remains forbidden: pass; status=403" | tee -a "${tmp_output}"

plugins="$(kubectl -n tenant-accounts get httproute banklab-accounts -o jsonpath='{.metadata.annotations.konghq\.com/plugins}')"
if [[ "${plugins}" != *"goal006-product-contract-header"* ]]; then
  fail "runtime route annotation missing goal006 plugin"
fi
echo "runtime route annotation includes goal006 plugin: pass" | tee -a "${tmp_output}"

write_report "pass"
echo "${report#${repo_root}/} generated."
