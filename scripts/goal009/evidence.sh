#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
decision="${repo_root}/docs/decisions/goal-009-runtime-approval.md"
tmp_output="$(mktemp)"
trap 'rm -f "${tmp_output}"' EXIT
python_bin="${BANKLAB_PYTHON:-}"
if [[ -z "${python_bin}" ]]; then
  if [[ -x "${repo_root}/soyspray-venv/bin/python" ]]; then
    python_bin="${repo_root}/soyspray-venv/bin/python"
  else
    python_bin="python3"
  fi
fi

cd "${repo_root}"
platform/kong/scripts/require-cluster-mutation-permission.sh

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
  echo "## ${label}" >>"${tmp_output}"
  set +e
  "$@" >>"${tmp_output}" 2>&1
  local code=$?
  set -e
  if [[ "${code}" -ne 0 ]]; then
    echo "step failed: ${label}; exit=${code}" >>"${tmp_output}"
    cat "${tmp_output}"
    exit "${code}"
  fi
  echo >>"${tmp_output}"
}

load_runtime_credentials

run_step "goal009 runtime readiness" make goal009-runtime-ready
run_step "goal009 response headers apply and smoke" make goal009-security-headers-apply-and-smoke
sleep 2
run_step "goal009 response headers rollback and smoke" make rollback-goal-009
sleep 2
run_step "goal004 positive smoke after rollback" make goal004-security-smoke
run_step "goal004 negative auth behavior after rollback" make goal004-security-negative-test
run_step "goal004 Redis rate-limit behavior after rollback" make goal004-rate-limit-test
run_step "Kong Admin API exposure safety" make kong-admin-exposure-test

{
  echo "# Goal009 Runtime Approval"
  echo
  echo "Status: pending approval"
  echo
  echo "Generated at: $(date -Iseconds)"
  echo
  echo "Branch: $(git branch --show-current)"
  echo
  echo "Commit: $(git rev-parse --short HEAD)"
  echo
  echo "Kubernetes context: $(kubectl config current-context 2>/dev/null || true)"
  echo
  echo "## Summary"
  echo
  echo "Goal009 runtime acceptance passed locally and is ready for ChatGPT Pro review."
  echo
  echo "## Evidence links"
  echo
  echo "- reports/goal-009-runtime-readiness.md"
  echo "- reports/goal-009-governed-response-headers-rollout.md"
  echo "- reports/goal-009-governed-response-headers-runtime.md"
  echo "- reports/goal-009-governed-response-headers-rollback.md"
  echo "- reports/goal004-security-smoke-results.md"
  echo "- reports/goal004-security-negative-test-results.md"
  echo "- reports/goal004-rate-limit-results.md"
  echo
  echo "## Known issues"
  echo
  echo "- None from the runtime acceptance sequence."
  echo
  echo "## Rollback notes"
  echo
  echo "- Goal009 rollback reapplies the stable accounts route annotation and deletes only the governed response-header plugin."
  echo "- The cluster is expected to end with no Goal009 plugin resource and no Goal009 route annotation."
  echo
  echo "## Ready-for-approval statement"
  echo
  echo "Goal009 is ready for Pro approval after evidence is committed and pushed."
} >"${decision}"

"${python_bin}" scripts/generate_evidence_report.py --goal goal-009-kong-governed-response-headers

cat "${tmp_output}"
echo "${decision#${repo_root}/} generated."
