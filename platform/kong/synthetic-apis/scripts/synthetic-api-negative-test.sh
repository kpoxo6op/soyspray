#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
report="${repo_root}/reports/goal004-security-negative-test-results.md"
platform_report="${repo_root}/platform/kong/security-controls/RUNTIME-NEGATIVE-TEST-RESULTS.md"
legacy_report="${repo_root}/reports/synthetic-api-negative-test-results.md"
legacy_platform_report="${repo_root}/platform/kong/synthetic-apis/RUNTIME-NEGATIVE-TEST-RESULTS.md"
tmp_output="$(mktemp)"
tmp_body="$(mktemp)"
tmp_err="$(mktemp)"
trap 'rm -f "${tmp_output}" "${tmp_body}" "${tmp_err}"' EXIT
curl_connect_timeout="${BANKLAB_SYNTHETIC_API_CURL_CONNECT_TIMEOUT:-3}"
curl_max_time="${BANKLAB_SYNTHETIC_API_CURL_MAX_TIME:-10}"

write_report() {
  local status="$1"
  {
    echo "# Goal004 Security Negative Test Results"
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
    echo "## Negative checks"
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
  local expiry_offset="$1"
  python3 - "${expiry_offset}" <<'PY'
import base64
import hashlib
import hmac
import json
import os
import sys
import time

offset = int(sys.argv[1])
key = os.environ["BANKLAB_EXTERNAL_FINTECH_PARTNER_JWT_KEY"]
secret = os.environ["BANKLAB_EXTERNAL_FINTECH_PARTNER_JWT_SECRET"].encode()

def b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

header = {"alg": "HS256", "typ": "JWT"}
payload = {"iss": key, "exp": int(time.time()) + offset}
signing_input = f"{b64(json.dumps(header, separators=(',', ':')).encode())}.{b64(json.dumps(payload, separators=(',', ':')).encode())}"
signature = hmac.new(secret, signing_input.encode(), hashlib.sha256).digest()
print(f"{signing_input}.{b64(signature)}")
PY
}

expect_status() {
  local host="$1"
  local path="$2"
  local expected="$3"
  local label="$4"
  shift 4
  local status
  status="$(
    curl --silent --show-error \
      --connect-timeout "${curl_connect_timeout}" \
      --max-time "${curl_max_time}" \
      --output "${tmp_body}" \
      --write-out '%{http_code}' \
      --resolve "${host}:80:${proxy_ip}" \
      "$@" \
      "http://${host}${path}"
  )"
  if [[ "${status}" != "${expected}" ]]; then
    echo "${label}: fail; expected ${expected}; got ${status}; body=$(cat "${tmp_body}")" | tee -a "${tmp_output}" >&2
    return 1
  fi
  echo "${label}: pass; status=${status}" | tee -a "${tmp_output}"
}

require_env BANKLAB_MOBILE_BANKING_APP_API_KEY >/dev/null
require_env BANKLAB_INTERNET_BANKING_WEB_API_KEY >/dev/null
require_env BANKLAB_EXTERNAL_FINTECH_PARTNER_JWT_KEY >/dev/null
require_env BANKLAB_EXTERNAL_FINTECH_PARTNER_JWT_SECRET >/dev/null

if ! proxy_ip="$(kubectl -n platform-kong get service banklab-kong-gateway-proxy -o jsonpath='{.status.loadBalancer.ingress[0].ip}')" || [[ -z "${proxy_ip}" ]]; then
  echo "Kong proxy LoadBalancer IP not available." | tee -a "${tmp_output}" >&2
  write_report "blocked"
  exit 1
fi

valid_external_jwt="$(make_jwt 300)"
expired_external_jwt="$(make_jwt -300)"

status="pass"
expect_status api.internal.banklab.test /accounts/v1/health 401 "missing API key returns 401" || status="fail"
expect_status api.internal.banklab.test /accounts/v1/health 401 "invalid API key returns 401" --header "apikey: banklab-wrong-api-key-value" || status="fail"
expect_status api.internal.banklab.test /accounts/v1/health 403 "valid API key for wrong ACL group returns 403" --header "apikey: ${BANKLAB_INTERNET_BANKING_WEB_API_KEY}" || status="fail"
expect_status api.external.banklab.test /open-banking/v1/health 401 "missing JWT returns 401" || status="fail"
expect_status api.external.banklab.test /open-banking/v1/health 401 "invalid JWT signature returns 401" --header "Authorization: Bearer invalid.jwt.signature" || status="fail"
expect_status api.external.banklab.test /open-banking/v1/health 401 "expired JWT returns 401" --header "Authorization: Bearer ${expired_external_jwt}" || status="fail"
expect_status api.external.banklab.test /accounts/v1/health 404 "internal API unavailable through external hostname" || status="fail"
expect_status unknown.internal.banklab.test /accounts/v1/health 404 "unknown host remains 404" || status="fail"
expect_status api.internal.banklab.test /unknown/v1/health 404 "unknown path remains 404" || status="fail"

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
