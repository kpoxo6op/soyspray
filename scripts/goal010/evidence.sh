#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
tmp_snapshot="$(mktemp)"
trap 'rm -f "${tmp_snapshot}"' EXIT
python_bin="${BANKLAB_PYTHON:-}"
if [[ -z "${python_bin}" ]]; then
  if [[ -x "${repo_root}/soyspray-venv/bin/python" ]]; then
    python_bin="${repo_root}/soyspray-venv/bin/python"
  else
    python_bin="python3"
  fi
fi

cd "${repo_root}"
scripts/goal010/require_readonly_runtime.sh

load_secret_env() {
  local env_name="$1"
  local secret_name="$2"
  local field_name="$3"
  if [[ -n "${!env_name:-}" ]]; then
    return 0
  fi
  local encoded
  encoded="$(kubectl -n synthetic-clients get secret "${secret_name}" -o "jsonpath={.data.${field_name}}" 2>/dev/null || true)"
  if [[ -z "${encoded}" ]]; then
    echo "Missing ${env_name}, and Secret synthetic-clients/${secret_name} field ${field_name} was not readable." >&2
    return 1
  fi
  local value
  value="$(printf '%s' "${encoded}" | base64 -d 2>/dev/null || true)"
  if [[ -z "${value}" ]]; then
    echo "Secret synthetic-clients/${secret_name} field ${field_name} could not be decoded." >&2
    return 1
  fi
  export "${env_name}=${value}"
}

load_runtime_credentials() {
  load_secret_env BANKLAB_MOBILE_BANKING_APP_API_KEY banklab-mobile-banking-app-key-auth key
  load_secret_env BANKLAB_PAYMENTS_PROCESSOR_API_KEY banklab-payments-processor-key-auth key
  load_secret_env BANKLAB_INTERNET_BANKING_WEB_API_KEY banklab-internet-banking-web-key-auth key
  load_secret_env BANKLAB_INTERNAL_CRM_API_KEY banklab-internal-crm-key-auth key
  load_secret_env BANKLAB_FRAUD_PLATFORM_API_KEY banklab-fraud-platform-key-auth key
  load_secret_env BANKLAB_EXTERNAL_FINTECH_PARTNER_JWT_KEY banklab-external-fintech-partner-jwt key
  load_secret_env BANKLAB_EXTERNAL_FINTECH_PARTNER_JWT_SECRET banklab-external-fintech-partner-jwt secret
}

run_step() {
  local label="$1"
  shift
  echo "## ${label}"
  "$@"
  echo
}

load_runtime_credentials
"${python_bin}" scripts/goal010/readonly_audit.py snapshot --output "${tmp_snapshot}"
run_step "goal010 runtime readiness" make goal010-runtime-ready
run_step "goal010 runtime inventory" "${python_bin}" scripts/goal010/readonly_audit.py inventory
run_step "goal010 drift audit" "${python_bin}" scripts/goal010/readonly_audit.py drift
run_step "goal004 positive smoke" make goal004-security-smoke
run_step "goal004 negative behavior" make goal004-security-negative-test
run_step "goal004 rate limit" make goal004-rate-limit-test
run_step "Kong Admin API exposure safety" make kong-admin-exposure-test
run_step "goal010 behavior report" "${python_bin}" scripts/goal010/readonly_audit.py behavior
run_step "goal010 no-mutation proof" "${python_bin}" scripts/goal010/readonly_audit.py no-mutation --before "${tmp_snapshot}"
run_step "goal010 read-only rollback verification" make rollback-goal-010
run_step "goal010 summary" "${python_bin}" scripts/goal010/readonly_audit.py summary
