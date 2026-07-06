Goal 003 is approved as a local-only checkpoint. The next step is a guarded runtime apply/smoke gate, not goal 004, unless you explicitly accept a local-only exception.

Thought for 4m 22s
Review
Approval status
Approved as goal-003-synthetic-bank-apis local-only.

The reported state is consistent with the goal:

Status: pass; local-only
Branch: kong-goals-foundation
Commit: 976f5f5
Cluster changes performed: none
Runtime verification: not run
No auth/plugins/consumers/secrets/Enterprise/Konnect/rate limiting
Runtime-ready check fails closed
Full local gate passed
Corrections
No corrections required before the runtime gate.

Do not start goal-004-auth-rate-limit-security yet. The correct next checkpoint is guarded runtime apply and smoke for the synthetic APIs.

Decision
Do not accept local-only as sufficient for moving to goal 004.

Proceed to the guarded runtime apply/smoke gate only after explicit user permission and target Kubernetes context are provided.

Gate: gate-003-synthetic-api-runtime-apply-and-smoke
Classification
This is a cluster-apply gate for goal-003-synthetic-bank-apis.

It requires explicit user permission before any cluster-mutating command is run.

Do not assume permission is granted.

Required mutation guard variables before mutation:

export BANKLAB_ALLOW_CLUSTER_MUTATION=true
export BANKLAB_TARGET_CONTEXT=<expected-kubernetes-context>
If these variables are not set correctly, all cluster-mutating commands must fail closed.

Objective
Runtime-validate the synthetic banking API product layer created in goal-003-synthetic-bank-apis.

The purpose of this gate is to move goal 003 from:

Status: pass; local-only
Runtime verification: not run
Ready for goal004: no
to:

Status: pass; runtime-verified
Runtime verification: pass
Ready for goal004: yes
only if the synthetic APIs are actually applied to the Kubernetes cluster and proven through smoke and negative tests.

This gate must prove:

explicit mutation approval exists
expected Kubernetes context is targeted
goal 003 local validation still passes
synthetic API manifests dry-run successfully
synthetic API resources apply successfully
all six mock backends become ready
all intended HTTPRoutes are accepted
internal API routes work through the internal Gateway
external Open Banking route works through the external Gateway
internal APIs are not externally exposed
unknown host and unknown path fail safely
Kong Admin API remains externally unreachable
no authentication or rate limiting is introduced in goal 003
no KongPlugin, KongClusterPlugin, or KongConsumer resources are created
no real secrets are created
runtime evidence is recorded
goal 004 remains blocked unless this gate passes
Current state entering this gate
Known current state:

Goal 000: complete
Goal 001: complete
Goal 002: runtime-verified
Goal 003: pass; local-only
Branch: kong-goals-foundation
Commit: 976f5f5
Cluster changes for goal 003: none
Runtime verification for goal 003: not run
Goal 002 runtime baseline:

Kong Gateway image: kong:3.9.3
KIC image: kong/kubernetes-ingress-controller:3.5.10
Gateway API version: v1.3.0
GatewayClass/kong: Accepted=True
Gateway/kong-external: Programmed=True
Gateway/kong-internal: Programmed=True
Gateway address: 192.168.20.22
Admin API external exposure: negative
Goal 003 local state:

six synthetic APIs implemented
six synthetic clients implemented
Gateway API routes implemented
OpenAPI specs implemented
ownership metadata implemented
route matrix implemented
exposure policy implemented
temporary-no-auth markers implemented
guarded apply and rollback implemented
runtime-ready check fails closed before runtime evidence
Non-goals
Do not implement goal 004.

Do not configure authentication.

Do not create Kong Consumers.

Do not create API keys.

Do not configure Key Auth.

Do not configure JWT.

Do not configure ACL.

Do not configure rate limiting.

Do not configure Redis.

Do not configure SSO.

Do not install Keycloak.

Do not install Prometheus, Grafana, Loki, or Alertmanager.

Do not create KongPlugin.

Do not create KongClusterPlugin.

Do not create KongConsumer.

Do not create real secrets.

Do not commit kubeconfigs.

Do not commit private keys.

Do not use Kong Enterprise.

Do not use Konnect.

Do not expose Kong Admin API externally.

Do not make manual kubectl patch or manual one-off edits the success path.

Do not bypass Git-managed manifests.

Do not bypass mutation guardrails.

Do not proceed to goal 004 if runtime validation fails, is partial, or is not run.

Required explicit permission
Before any cluster-mutating command is run, the operator must explicitly approve this gate.

The approval must identify:

Branch:
Commit:
Target Kubernetes context:
Commands approved:
Expected resources to change:
Expected resources not to change:
Rollback command:
Approval:
Use this approval template:

I approve running gate-003-synthetic-api-runtime-apply-and-smoke cluster-mutating commands.

Branch: kong-goals-foundation
Commit: 976f5f5
Target Kubernetes context:
Commands approved:
- make synthetic-api-install-dry-run
- make synthetic-api-apply
- make synthetic-api-smoke
- make synthetic-api-negative-test
- make kong-admin-exposure-test
- platform/kong/synthetic-apis/scripts/collect-synthetic-api-evidence.sh
- make evidence-goal-003
- make synthetic-api-runtime-ready

Expected resources to change:
- tenant-accounts synthetic API resources
- tenant-payments synthetic API resources
- tenant-cards synthetic API resources
- tenant-customer-profile synthetic API resources
- tenant-fraud synthetic API resources
- tenant-open-banking synthetic API resources
- synthetic API Deployments
- synthetic API Services
- synthetic API ConfigMaps
- synthetic API HTTPRoutes
- synthetic API NetworkPolicies
- synthetic API Argo CD template resources only if explicitly included in the approved apply path

Expected resources not to change:
- Kong Gateway deployment
- Kong Ingress Controller deployment
- Kong GatewayClass except status reconciliation
- Kong internal and external Gateways except status reconciliation
- Kong Admin API service
- Kong CRDs
- Gateway API CRDs
- existing non-Kong workloads
- existing Booklore resources
- existing Immich resources
- Kubespray configuration
- unrelated namespaces
- unrelated secrets
- unrelated Gateway/HTTPRoute resources
- any production-like credentials

Rollback command:
- make synthetic-api-rollback

Approval:
- approved
After approval, export:

export BANKLAB_ALLOW_CLUSTER_MUTATION=true
export BANKLAB_TARGET_CONTEXT=<expected-kubernetes-context>
Before mutation, verify:

kubectl config current-context
The output must exactly match:

$BANKLAB_TARGET_CONTEXT
If the context does not match, stop.

Constraints
All cluster-mutating commands must be guarded.

All cluster-mutating commands must print the current Kubernetes context before mutation.

All cluster-mutating commands must fail closed if explicit permission is absent.

CI must remain cluster-free.

Do not add cluster mutation to CI.

Do not weaken existing goal 003 local validators.

Do not weaken existing goal 002 runtime guardrails.

Do not weaken Admin API exposure tests.

Do not weaken secret scanning.

Do not weaken policy checks that prevent auth/rate-limit resources in goal 003.

Do not change the synthetic API route model unless a runtime blocker proves it is invalid.

If a runtime blocker requires a repo change, commit the repo change, rerun the full local gate, then rerun the guarded runtime gate.

Do not manually patch cluster resources as the final solution.

If runtime testing reveals that allowedRoutes, namespace labels, ReferenceGrants, NetworkPolicies, backend ports, service names, or mock backend paths are incorrect, fix them declaratively in the repo.

All evidence must distinguish clearly between:

not run
failed
passed
blocked
partial
Do not claim runtime success unless runtime checks actually pass.

Required files
Create or update the following files.

soydocs/
└── kong-bank-lab/
    └── goals/
        └── gate-003-synthetic-api-runtime-apply-and-smoke.md

docs/
├── runbooks/
│   ├── synthetic-api-runtime-apply-and-smoke.md
│   ├── synthetic-api-runtime-failure.md
│   └── synthetic-api-runtime-verification-evidence.md
└── decisions/
    └── goal-003-runtime-approval.md

platform/
└── kong/
    └── synthetic-apis/
        ├── RUNTIME-APPLY-EXECUTION-LOG.md
        ├── RUNTIME-SMOKE-RESULTS.md
        ├── RUNTIME-NEGATIVE-TEST-RESULTS.md
        ├── RUNTIME-ADMIN-API-SAFETY-RESULTS.md
        └── scripts/
            ├── synthetic-api-runtime-apply-and-smoke.sh
            ├── verify-goal003-runtime-ready.sh
            └── collect-synthetic-api-runtime-state.sh

scripts/
├── validate_synthetic_api_runtime_gate.py
└── generate_evidence_report.py

tests/
├── unit/
│   ├── test_gate_003_runtime_gate_structure.py
│   ├── test_gate_003_runtime_evidence_contract.py
│   └── test_gate_003_runtime_ready_fails_before_evidence.py
└── policy/
    ├── test_gate_003_runtime_apply_policy.py
    └── test_gate_003_no_unapproved_goal004_start.py

reports/
└── gate-003-synthetic-api-runtime-apply-and-smoke-summary.md
Small path adjustments are allowed if they fit the existing repository conventions, but the intent must remain the same.

Do not overwrite historical reports from prior goals.

Deliverables
Saved gate body
Save this gate body at:

soydocs/kong-bank-lab/goals/gate-003-synthetic-api-runtime-apply-and-smoke.md
Runtime apply runbook
Create:

docs/runbooks/synthetic-api-runtime-apply-and-smoke.md
It must document:

purpose of this runtime gate
required explicit permission
required Kubernetes context check
pre-apply local validation
dry-run
guarded apply
runtime smoke tests
negative tests
Admin API safety check
evidence collection
runtime-ready verification
rollback path
Required command sequence before mutation:

make validate
make validate-yaml
make validate-kustomize
make validate-synthetic-apis
make openapi-lint
make render-synthetic-apis
make synthetic-api-static-test
make synthetic-api-contract-test
make synthetic-api-smoke-plan
make test
make policy-test
make docs
Required command sequence after explicit permission:

make synthetic-api-install-dry-run
make synthetic-api-apply
make synthetic-api-smoke
make synthetic-api-negative-test
make kong-admin-exposure-test
platform/kong/synthetic-apis/scripts/collect-synthetic-api-evidence.sh
make evidence-goal-003
make synthetic-api-runtime-ready
Runtime failure runbook
Create:

docs/runbooks/synthetic-api-runtime-failure.md
It must cover failure handling for:

wrong Kubernetes context
missing tenant namespace
HTTPRoute not accepted
Gateway parent not found
allowedRoutes rejects tenant route
backend Service not found
backend pods not ready
NetworkPolicy blocks Kong-to-upstream
mock backend returns wrong marker
internal route returns 404
internal route returns 5xx
external open-banking route returns 404
external route has LoadBalancer/DNS issue
internal API is reachable through external Gateway
unknown host does not return expected failure
Admin API is externally reachable
synthetic API rollback fails
For each failure, include:

symptom
likely cause
diagnostic commands
repo-safe correction path
rollback decision
evidence to collect
Runtime evidence documentation
Create:

docs/runbooks/synthetic-api-runtime-verification-evidence.md
It must define evidence required to mark goal 003 runtime-verified:

branch
commit
target Kubernetes context
actual Kubernetes context
explicit mutation approval
goal 003 local validation result
dry-run result
apply result
tenant namespace state
backend Deployment readiness
backend Service state
HTTPRoute accepted status
Gateway parent attachment status
NetworkPolicy state
internal route smoke results
external route smoke results
negative test results
Admin API safety result
runtime-created secrets summary
rollback command
goal 003 evidence status
Runtime approval decision
Create:

docs/decisions/goal-003-runtime-approval.md
Initial state:

Status: pending
It may only be changed to:

Status: approved
if runtime apply, smoke tests, negative tests, and Admin API safety checks pass.

Execution logs
Create or update:

platform/kong/synthetic-apis/RUNTIME-APPLY-EXECUTION-LOG.md
platform/kong/synthetic-apis/RUNTIME-SMOKE-RESULTS.md
platform/kong/synthetic-apis/RUNTIME-NEGATIVE-TEST-RESULTS.md
platform/kong/synthetic-apis/RUNTIME-ADMIN-API-SAFETY-RESULTS.md
Each file must support these states:

not run
pass
fail
blocked
partial
If not run, record:

Status: not run
Reason:
If run, record:

Status:
Command:
Result summary:
Evidence:
Timestamp:
Guarded runtime script
Create:

platform/kong/synthetic-apis/scripts/synthetic-api-runtime-apply-and-smoke.sh
It must:

call the existing mutation guard before mutation
print current branch and commit if available
print current Kubernetes context
verify target context
run pre-apply local checks
run dry-run
run guarded apply
run synthetic-api-smoke
run synthetic-api-negative-test
run kong-admin-exposure-test
collect runtime evidence
stop on first failure
never bypass Makefile guardrails
It must not be run by CI.

Runtime state collection
Create:

platform/kong/synthetic-apis/scripts/collect-synthetic-api-runtime-state.sh
It must collect read-only runtime state for:

tenant namespaces
synthetic API Deployments
synthetic API pods
synthetic API Services
synthetic API ConfigMaps
synthetic API HTTPRoutes
synthetic API NetworkPolicies
GatewayClass
internal Gateway
external Gateway
Kong proxy service
Kong Admin service
It must not mutate the cluster.

Runtime-ready verifier
Create:

platform/kong/synthetic-apis/scripts/verify-goal003-runtime-ready.sh
It must fail if any required runtime result is:

not run
fail
blocked
partial
It must fail if:

goal 003 evidence still says local-only only
cluster verification is not run
synthetic APIs were not applied
route smoke did not pass
negative tests did not pass
Admin API safety check did not pass
goal 003 runtime approval decision is not approved
Validation script
Create:

scripts/validate_synthetic_api_runtime_gate.py
It must validate:

required gate files exist
runtime approval decision starts as pending unless runtime evidence proves pass
runtime result files support not run/pass/fail/blocked/partial
runtime apply script is guarded
runtime rollback remains guarded
CI does not run cluster-mutating commands
goal 004 remains blocked before runtime approval
no secrets are committed
no kubeconfigs are committed
no private keys are committed
Makefile targets
Preserve all existing targets.

Add:

validate-synthetic-api-runtime-gate
evidence-gate-003-synthetic-api-runtime
goal003-runtime-ready
Target behavior:

validate-synthetic-api-runtime-gate:
  local-only
  validates runtime gate structure and guardrails

evidence-gate-003-synthetic-api-runtime:
  local-only
  creates or updates reports/gate-003-synthetic-api-runtime-apply-and-smoke-summary.md

goal003-runtime-ready:
  local/read-only evidence check
  fails until runtime evidence proves apply and smoke passed
Do not add cluster-mutating commands to CI.

Tests
Add tests:

tests/unit/test_gate_003_runtime_gate_structure.py
tests/unit/test_gate_003_runtime_evidence_contract.py
tests/unit/test_gate_003_runtime_ready_fails_before_evidence.py
tests/policy/test_gate_003_runtime_apply_policy.py
tests/policy/test_gate_003_no_unapproved_goal004_start.py
The tests must verify:

required runtime gate files exist
runtime apply script is guarded
synthetic-api-apply remains guarded
synthetic-api-rollback remains guarded
CI remains cluster-free
runtime approval starts pending
goal003-runtime-ready fails before runtime evidence
goal 004 remains blocked before runtime approval
runtime result files support required states
no secrets are committed
no kubeconfigs are committed
no private keys are committed
Tests must run locally.

Tests must not require Kubernetes.

Tests must not require Docker.

Tests must not require internet access.

CI
Update CI to include local-only validation for this gate.

CI may run:

make validate-synthetic-api-runtime-gate
CI must not run:

make synthetic-api-install-dry-run
make synthetic-api-apply
make synthetic-api-smoke
make synthetic-api-negative-test
make synthetic-api-rollback
make synthetic-api-runtime-ready
make goal003-runtime-ready
platform/kong/synthetic-apis/scripts/synthetic-api-runtime-apply-and-smoke.sh
unless the target is explicitly a negative unit test proving failure before runtime evidence.

CI must remain cluster-free.

Runtime validation sequence
Run only after explicit permission is granted.

Pre-mutation local validation
make validate
make validate-yaml
make validate-kustomize
make validate-synthetic-apis
make openapi-lint
make render-synthetic-apis
make synthetic-api-static-test
make synthetic-api-contract-test
make synthetic-api-smoke-plan
make test
make policy-test
make docs
make validate-synthetic-api-runtime-gate
make evidence-gate-003-synthetic-api-runtime
Expected result:

all local checks pass
cluster changes performed: none
runtime approval: pending
goal004 ready: no
Permission and context check
export BANKLAB_ALLOW_CLUSTER_MUTATION=true
export BANKLAB_TARGET_CONTEXT=<expected-kubernetes-context>
kubectl config current-context
Expected result:

actual context equals BANKLAB_TARGET_CONTEXT
Dry-run
make synthetic-api-install-dry-run
Expected result:

synthetic API manifests dry-run successfully
no cluster mutation occurs except API-server dry-run validation if implemented that way
Apply
make synthetic-api-apply
Expected result:

synthetic API resources are applied
mutation guard runs before mutation
Smoke
make synthetic-api-smoke
Required success cases:

GET http://api.internal.banklab.test/accounts/v1/health -> banklab-accounts-ok
GET http://api.internal.banklab.test/payments/v1/health -> banklab-payments-ok
GET http://api.internal.banklab.test/cards/v1/health -> banklab-cards-ok
GET http://api.internal.banklab.test/customers/v1/health -> banklab-customer-profile-ok
GET http://api.internal.banklab.test/fraud/v1/health -> banklab-fraud-decisions-ok
GET http://api.external.banklab.test/open-banking/v1/health -> banklab-open-banking-ok
Smoke may use:

LoadBalancer IP
Host headers
curl --resolve
documented port-forward fallback
If fallback is used, record it.

Negative tests
make synthetic-api-negative-test
Required negative cases:

unknown host returns Kong 404
unknown route returns expected failure
accounts is not reachable through api.external.banklab.test
payments is not reachable through api.external.banklab.test
cards is not reachable through api.external.banklab.test
customer-profile is not reachable through api.external.banklab.test
fraud-decisions is not reachable through api.external.banklab.test
open-banking is not reachable through api.internal.banklab.test unless explicitly documented otherwise
Admin API is not reachable through proxy
Admin API service is not LoadBalancer
Admin API service is not NodePort
no KongPlugin resources exist
no KongConsumer resources exist
no KongClusterPlugin resources exist
Admin API safety
make kong-admin-exposure-test
Expected result:

Admin API external exposure remains negative
Evidence and readiness
platform/kong/synthetic-apis/scripts/collect-synthetic-api-evidence.sh
platform/kong/synthetic-apis/scripts/collect-synthetic-api-runtime-state.sh
make evidence-goal-003
make evidence-gate-003-synthetic-api-runtime
make goal003-runtime-ready
Expected result:

goal 003 runtime evidence is complete
goal003-runtime-ready passes
goal 004 may be assigned next
Evidence report
Create or update:

reports/gate-003-synthetic-api-runtime-apply-and-smoke-summary.md
It must include:

Gate: gate-003-synthetic-api-runtime-apply-and-smoke
Status:
Branch:
Commit:
Generated at:

Gate classification:
Explicit mutation permission required:
Mutation permission granted:
Target Kubernetes context:
Actual Kubernetes context:

Current programme state:
- Goal 000:
- Goal 001:
- Goal 002:
- Goal 003 local-only:

Pre-mutation local validation:
- make validate:
- make validate-yaml:
- make validate-kustomize:
- make validate-synthetic-apis:
- make openapi-lint:
- make render-synthetic-apis:
- make synthetic-api-static-test:
- make synthetic-api-contract-test:
- make synthetic-api-smoke-plan:
- make test:
- make policy-test:
- make docs:
- make validate-synthetic-api-runtime-gate:

Dry-run:
- make synthetic-api-install-dry-run:

Mutation:
- make synthetic-api-apply:

Runtime smoke:
- make synthetic-api-smoke:

Runtime negative tests:
- make synthetic-api-negative-test:

Admin API safety:
- make kong-admin-exposure-test:

Runtime evidence:
- accounts backend:
- payments backend:
- cards backend:
- customer-profile backend:
- fraud-decisions backend:
- open-banking backend:
- accounts route:
- payments route:
- cards route:
- customer-profile route:
- fraud-decisions route:
- open-banking route:
- unknown host:
- unknown route:
- external exposure policy:
- Admin API exposure:

Cluster changes performed:

Secrets created:

Kong Enterprise features used:

KongPlugin resources created:

KongConsumer resources created:

KongClusterPlugin resources created:

Authentication configured:

Rate limiting configured:

Runtime verification:

Runtime approval:

Ready for goal 004:

Known limitations:
Default values before permission or execution:

Status: pending explicit cluster mutation permission
Explicit mutation permission required: yes
Mutation permission granted: no
Cluster changes performed: none
Secrets created: none
Kong Enterprise features used: none
KongPlugin resources created: none
KongConsumer resources created: none
KongClusterPlugin resources created: none
Authentication configured: no
Rate limiting configured: no
Runtime verification: not run
Runtime approval: pending
Ready for goal 004: no
Required values after successful runtime validation:

Status: pass; runtime-verified
Explicit mutation permission required: yes
Mutation permission granted: yes
Cluster changes performed: synthetic bank APIs applied
Secrets created: none
Kong Enterprise features used: none
KongPlugin resources created: none
KongConsumer resources created: none
KongClusterPlugin resources created: none
Authentication configured: no; deferred to goal-004
Rate limiting configured: no; deferred to goal-004
Runtime verification: pass
Runtime approval: approved
Ready for goal 004: yes
If runtime is partial or failed:

Status: failed or blocked
Runtime verification: failed or partial
Runtime approval: pending
Ready for goal 004: no
Update goal 003 evidence
After runtime execution, update:

reports/goal-003-summary.md
If runtime validation passes, update it to:

Status: pass; runtime-verified
Cluster changes performed: synthetic bank APIs applied
Runtime verification: pass
Ready for next goal: goal-004-auth-rate-limit-security
If runtime validation is not run, failed, partial, or blocked, do not mark goal 003 runtime-verified.

Acceptance criteria
Local gate acceptance before permission
The runtime gate body is saved.

Runtime gate docs exist.

Runtime failure runbook exists.

Runtime evidence documentation exists.

Runtime approval decision exists and starts as pending.

Runtime result files exist and support required states.

Runtime apply script is guarded.

Existing synthetic-api-apply remains guarded.

Existing synthetic-api-rollback remains guarded.

CI remains cluster-free.

Goal 004 remains blocked before runtime approval.

goal003-runtime-ready fails before runtime evidence.

Local validation passes.

Runtime acceptance after permission
Explicit mutation permission was provided.

Expected Kubernetes context was supplied.

Actual Kubernetes context matched expected context.

Pre-mutation local validation passed.

Dry-run passed.

Synthetic API apply completed.

All six mock backends are ready.

All six intended HTTPRoutes are accepted.

Internal route smoke passed for:

accounts
payments
cards
customer-profile
fraud-decisions
External route smoke passed for:

open-banking
Unknown host negative test passed.

Unknown route negative test passed.

External exposure negative tests passed for internal APIs.

Admin API external exposure test passed.

No KongPlugin resources exist.

No KongClusterPlugin resources exist.

No KongConsumer resources exist.

No real secrets are created.

No authentication is configured.

No rate limiting is configured.

Runtime evidence is collected.

Goal 003 evidence is updated.

Runtime approval decision is approved.

goal003-runtime-ready passes.

Goal 004 is allowed next.

Stop condition
Outcome A: no explicit permission granted
Stop after the local runtime gate package, validation, and evidence are complete.

Required final state:

Status: pending explicit cluster mutation permission
Cluster changes performed: none
Runtime verification: not run
Runtime approval: pending
Ready for goal 004: no
Outcome B: explicit permission granted and runtime validation passes
Stop after apply, smoke, negative tests, Admin API safety check, evidence collection, and runtime-ready verification pass.

Required final state:

Status: pass; runtime-verified
Cluster changes performed: synthetic bank APIs applied
Runtime verification: pass
Runtime approval: approved
Ready for goal 004: yes
Do not create goal 004 in this gate.

Outcome C: explicit permission granted but runtime validation fails
Stop after recording the failure, collecting evidence, and either leaving the cluster state for investigation or running guarded rollback if explicitly approved.

Required final state:

Status: failed or blocked
Runtime verification: failed or partial
Runtime approval: pending
Ready for goal 004: no
Do not continue to goal 004.

Do not hide failed runtime checks.

Do not bypass failed runtime checks.
