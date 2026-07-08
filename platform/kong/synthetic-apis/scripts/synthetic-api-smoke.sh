#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
report="${repo_root}/reports/goal004-security-smoke-results.md"
platform_report="${repo_root}/platform/kong/security-controls/RUNTIME-SMOKE-RESULTS.md"
legacy_report="${repo_root}/reports/synthetic-api-route-smoke-results.md"
legacy_platform_report="${repo_root}/platform/kong/synthetic-apis/RUNTIME-SMOKE-RESULTS.md"
tmp_output="$(mktemp)"
tmp_body="$(mktemp)"
tmp_headers="$(mktemp)"
trap 'rm -f "${tmp_output}" "${tmp_body}" "${tmp_headers}"' EXIT
curl_connect_timeout="${BANKLAB_SYNTHETIC_API_CURL_CONNECT_TIMEOUT:-3}"
curl_max_time="${BANKLAB_SYNTHETIC_API_CURL_MAX_TIME:-10}"

write_report() {
  local status="$1"
  {
    echo "# Goal004 Security Smoke Results"
    echo
    echo "Status: ${status}"
    echo
    echo "Supported states: not run, pass, fail, blocked, partial"
    echo
    echo "Generated at: $(date -Iseconds)"
    echo
    echo "Kubernetes context: $(kubectl config current-context 2>/dev/null || true)"
    echo
    echo "Credential source: local environment variables"
    echo
    echo "## Route checks"
    cat "${tmp_output}"
  } >"${report}"
  cp "${report}" "${platform_report}"
  cp "${report}" "${legacy_report}"
  cp "${report}" "${legacy_platform_report}"
}

require_env() {
  local name="$1"
  if [[ -z "${!name:-}" ]]; then
    echo "Missing required environment variable ${name}." | tee -a "${tmp_output}" >&2
    write_report "blocked"
    exit 1
  fi
  printf '%s' "${!name}"
}

make_jwt() {
  python3 - <<'PY'
import base64
import hashlib
import hmac
import json
import os
import time

key = os.environ["BANKLAB_EXTERNAL_FINTECH_PARTNER_JWT_KEY"]
secret = os.environ["BANKLAB_EXTERNAL_FINTECH_PARTNER_JWT_SECRET"].encode()

def b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

header = {"alg": "HS256", "typ": "JWT"}
payload = {"iss": key, "exp": int(time.time()) + 300}
signing_input = f"{b64(json.dumps(header, separators=(',', ':')).encode())}.{b64(json.dumps(payload, separators=(',', ':')).encode())}"
signature = hmac.new(secret, signing_input.encode(), hashlib.sha256).digest()
print(f"{signing_input}.{b64(signature)}")
PY
}

check_headers() {
  local label="$1"
  if ! grep -Eiq '^X-Banklab-Correlation-ID:' "${tmp_headers}"; then
    echo "${label}: fail; missing X-Banklab-Correlation-ID response header" | tee -a "${tmp_output}" >&2
    return 1
  fi
  if ! grep -Eiq '^(x-)?ratelimit-limit|^ratelimit-limit:' "${tmp_headers}" \
    || ! grep -Eiq '^(x-)?ratelimit-remaining|^ratelimit-remaining:' "${tmp_headers}"; then
    echo "${label}: fail; missing rate limit headers" | tee -a "${tmp_output}" >&2
    return 1
  fi
}

check_key_route() {
  local host="$1"
  local path="$2"
  local expected="$3"
  local client="$4"
  local env_name="$5"
  local key
  local status
  key="$(require_env "${env_name}")"
  status="$(
    curl --silent --show-error \
      --connect-timeout "${curl_connect_timeout}" \
      --max-time "${curl_max_time}" \
      --output "${tmp_body}" \
      --dump-header "${tmp_headers}" \
      --write-out '%{http_code}' \
      --header "apikey: ${key}" \
      --resolve "${host}:80:${proxy_ip}" \
      "http://${host}${path}"
  )"
  check_success "${host}${path}" "${client}" "${expected}" "${status}"
}

check_jwt_route() {
  local host="$1"
  local path="$2"
  local expected="$3"
  local client="$4"
  local token
  local status
  require_env BANKLAB_EXTERNAL_FINTECH_PARTNER_JWT_KEY >/dev/null
  require_env BANKLAB_EXTERNAL_FINTECH_PARTNER_JWT_SECRET >/dev/null
  token="$(make_jwt)"
  status="$(
    curl --silent --show-error \
      --connect-timeout "${curl_connect_timeout}" \
      --max-time "${curl_max_time}" \
      --output "${tmp_body}" \
      --dump-header "${tmp_headers}" \
      --write-out '%{http_code}' \
      --header "Authorization: Bearer ${token}" \
      --resolve "${host}:80:${proxy_ip}" \
      "http://${host}${path}"
  )"
  check_success "${host}${path}" "${client}" "${expected}" "${status}"
}

check_success() {
  local label="$1"
  local client="$2"
  local expected="$3"
  local status="$4"
  if [[ "${status}" != "200" ]]; then
    echo "${label}: fail; client=${client}; expected 200; got ${status}; body=$(cat "${tmp_body}")" | tee -a "${tmp_output}" >&2
    return 1
  fi
  if ! grep -Fq "${expected}" "${tmp_body}"; then
    echo "${label}: fail; client=${client}; expected marker ${expected}; body=$(cat "${tmp_body}")" | tee -a "${tmp_output}" >&2
    return 1
  fi
  check_headers "${label}" || return 1
  echo "${label}: pass; client=${client}; status=200; marker=${expected}; correlation-id=present; rate-limit-headers=present" | tee -a "${tmp_output}"
}

if ! proxy_ip="$(kubectl -n platform-kong get service banklab-kong-gateway-proxy -o jsonpath='{.status.loadBalancer.ingress[0].ip}')" || [[ -z "${proxy_ip}" ]]; then
  echo "Kong proxy LoadBalancer IP not available." | tee -a "${tmp_output}" >&2
  write_report "blocked"
  exit 1
fi

if check_key_route api.internal.banklab.test /accounts/v1/health banklab-accounts-ok mobile-banking-app BANKLAB_MOBILE_BANKING_APP_API_KEY \
  && check_key_route api.internal.banklab.test /payments/v1/health banklab-payments-ok payments-processor BANKLAB_PAYMENTS_PROCESSOR_API_KEY \
  && check_key_route api.internal.banklab.test /cards/v1/health banklab-cards-ok internet-banking-web BANKLAB_INTERNET_BANKING_WEB_API_KEY \
  && check_key_route api.internal.banklab.test /customers/v1/health banklab-customer-profile-ok internal-crm BANKLAB_INTERNAL_CRM_API_KEY \
  && check_key_route api.internal.banklab.test /fraud/v1/health banklab-fraud-decisions-ok fraud-platform BANKLAB_FRAUD_PLATFORM_API_KEY \
  && check_jwt_route api.external.banklab.test /open-banking/v1/health banklab-open-banking-ok external-fintech-partner; then
  write_report "pass"
else
  write_report "fail"
  exit 1
fi

echo "${report#${repo_root}/} generated."
