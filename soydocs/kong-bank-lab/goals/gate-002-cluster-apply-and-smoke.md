# gate-002-cluster-apply-and-smoke

## Classification

This is a cluster-apply gate.

It requires explicit user permission before any cluster-mutating command is
run. Do not assume permission is granted.

This gate may only mutate the Kubernetes cluster after the operator explicitly
approves cluster mutation and supplies the expected Kubernetes context.

Required mutation guard variables:

```bash
BANKLAB_ALLOW_CLUSTER_MUTATION=true
BANKLAB_TARGET_CONTEXT=<expected-kubernetes-context>
```

If these variables are not set correctly, all cluster-mutating commands must
fail closed.

## Objective

Apply and runtime-validate the `goal-002-kong-oss-baseline` implementation on
the home Kubernetes cluster.

The purpose of this gate is to move goal 002 from:

```text
Status: pass; local-only
```

to:

```text
Status: pass; runtime-verified
```

only if the Kong OSS baseline is actually applied, reconciled, smoke-tested,
and proven safe.

This gate must prove:

- cluster preconditions are satisfied
- explicit mutation approval exists
- the expected Kubernetes context is targeted
- Kong OSS baseline can be applied
- Kong Gateway pods become ready
- Kong Ingress Controller pods become ready
- Gateway API resources are accepted
- the smoke backend becomes ready
- internal smoke route works
- external smoke route works, or a documented MetalLB/DNS blocker exists with port-forward fallback evidence
- unknown route returns the expected failure
- Kong Admin API is not externally exposed
- rollback path exists and is safe
- evidence is updated accurately

This gate does not create business APIs and does not start
`goal-003-synthetic-bank-apis`.

## Current State Entering This Gate

- Goal 000: complete
- Goal 001: complete and approved
- Goal 002: corrected and approved as local-only
- `gate-002-runtime-preflight`: complete and approved as local-only pre-cluster-apply

Current goal 002 runtime state:

- Kong Gateway image: `kong:3.9.3`
- KIC image: `kong/kubernetes-ingress-controller:3.5.10`
- Gateway API version: `v1.3.0`
- Helm chart: `kong/ingress 0.24.0`
- Kong mode: DB-less
- Enterprise enabled: false
- PostgreSQL enabled: false
- Admin API external exposure: no, based on static validation
- Cluster changes performed: none
- Cluster verification: not run
- Kong runtime applied: no
- Kong route smoke passed: no

Current preflight state:

- Mutation guard: implemented
- Apply plan: `reports/kong-runtime-apply-plan.md`
- Runtime preflight evidence: `reports/gate-002-runtime-preflight-summary.md`
- Goal 003 blocked: yes

## Non-Goals

Do not create `goal-003-synthetic-bank-apis`.

Do not implement accounts, payments, cards, customer profile, fraud, or
open-banking APIs.

Do not create Kong Consumers, API keys, Key Auth, JWT, ACL, rate limiting,
Redis, SSO, Keycloak, observability stack, production TLS, real secrets,
kubeconfigs, private keys, or generated certificates.

Do not use Kong Enterprise, Konnect, Enterprise RBAC, Workspaces as a governance
boundary, Enterprise OIDC, Enterprise Request Validator, Enterprise MTLS Auth,
or Enterprise Developer Portal.

Do not expose Kong Admin API externally.

Do not make Kong Manager the platform UI.

Do not bypass Git as source of truth.

Do not manually patch resources as the success path.

Do not proceed if the selected Kubernetes context does not match
`BANKLAB_TARGET_CONTEXT`.

Do not run cluster-mutating commands unless explicit permission is present.

## Required Explicit Permission

Before any cluster-mutating command is run, the operator must explicitly approve
this gate.

The approval must identify:

- Branch
- Commit
- Target Kubernetes context
- Commands approved
- Expected resources to change
- Rollback command

The operator must export:

```bash
export BANKLAB_ALLOW_CLUSTER_MUTATION=true
export BANKLAB_TARGET_CONTEXT=<expected-kubernetes-context>
```

The mutation guard must verify:

- `BANKLAB_ALLOW_CLUSTER_MUTATION` is exactly `true`
- `BANKLAB_TARGET_CONTEXT` is not empty
- `kubectl` is available
- current Kubernetes context matches `BANKLAB_TARGET_CONTEXT`
- mutating command is guarded before it runs

If any condition fails, stop.

## Constraints

All cluster-mutating commands must be guarded, must print the current
Kubernetes context before mutation, and must fail closed if explicit permission
is absent.

CI must remain cluster-free. Do not add cluster mutation to CI.

Do not weaken goal 002 local validators, Admin API exposure tests,
KIC/Gateway API compatibility tests, or secret scanning.

Do not change the approved version pins unless a runtime blocker proves a pin
is invalid. If a version change is required, stop and record a correction
instead of silently changing versions.

Approved baseline pins:

- Kong Gateway: `kong:3.9.3`
- KIC: `kong/kubernetes-ingress-controller:3.5.10`
- Gateway API: `v1.3.0`
- Helm chart: `kong/ingress 0.24.0`

The cluster apply path must remain auditable.

All evidence must distinguish clearly between not run, failed, passed, and
blocked.

Do not claim runtime success unless runtime checks actually pass.

If the cluster lacks prerequisites, record the blocker and stop.

If Gateway API CRDs are missing, record the blocker and stop unless this gate
explicitly applies them through a guarded approved path.

If MetalLB is missing or not assigning an external IP, use a documented
port-forward fallback for route smoke, but do not mark external LoadBalancer
exposure fully verified.

If NetworkPolicy blocks required smoke traffic, record the exact failed path
and stop or rollback.

If Admin API is externally reachable, this is a gate failure.

## Required Files

Create or update:

- `soydocs/kong-bank-lab/goals/gate-002-cluster-apply-and-smoke.md`
- `docs/runbooks/kong-cluster-apply-and-smoke.md`
- `docs/runbooks/kong-cluster-apply-failure.md`
- `docs/runbooks/kong-runtime-verification-evidence.md`
- `docs/decisions/goal-002-runtime-approval.md`
- `platform/kong/CLUSTER-APPLY-EXECUTION-LOG.md`
- `platform/kong/CLUSTER-SMOKE-RESULTS.md`
- `platform/kong/ROUTE-SMOKE-RESULTS.md`
- `platform/kong/ADMIN-API-EXPOSURE-RESULTS.md`
- `platform/kong/scripts/kong-cluster-apply-and-smoke.sh`
- `platform/kong/scripts/collect-kong-runtime-evidence.sh`
- `platform/kong/scripts/verify-goal002-runtime-ready.sh`
- `scripts/validate_cluster_apply_gate.py`
- `scripts/generate_evidence_report.py`
- `tests/unit/test_gate_002_cluster_apply_gate_structure.py`
- `tests/unit/test_gate_002_cluster_mutation_requires_permission.py`
- `tests/unit/test_gate_002_runtime_evidence_contract.py`
- `tests/policy/test_gate_002_cluster_apply_policy.py`
- `tests/policy/test_gate_002_no_unapproved_runtime_approval.py`
- `reports/gate-002-cluster-apply-and-smoke-summary.md`

Do not remove goal 000, goal 001, goal 002, or `gate-002-runtime-preflight`
files. Do not overwrite historical evidence reports.

## Deliverables

### Cluster Apply Runbook

Create `docs/runbooks/kong-cluster-apply-and-smoke.md`. It must document the
exact runtime sequence.

Required local sequence before permission:

```bash
make validate
make validate-yaml
make validate-kustomize
make validate-prereqs
make validate-kong-baseline
make render-kong-baseline
make kong-static-test
make kong-admin-exposure-test
make runtime-preflight-local
make kong-apply-plan
make mutation-guard-test
make test
make policy-test
make docs
```

Then, only after explicit permission and exported guard variables:

```bash
make cluster-readonly-preflight
make kong-readonly-preflight
make cluster-smoke
make cluster-prereq-smoke
make kong-install-dry-run
make kong-apply
make kong-cluster-smoke
make kong-route-smoke
make kong-admin-exposure-test
make evidence-gate-002-cluster-apply-and-smoke
```

The runbook must explain what each step proves.

### Failure Runbook

Create `docs/runbooks/kong-cluster-apply-failure.md`. It must cover failure
handling for wrong context, missing Kubernetes access, missing Gateway API CRDs,
missing MetalLB, missing cert-manager, failed render, failed dry-run, pod
readiness failures, Gateway and HTTPRoute acceptance failures, LoadBalancer
pending, smoke failures, Admin API exposure, and NetworkPolicy blockers.

For each failure, include symptom, likely cause, diagnostic commands, safe
mitigation, rollback decision, and evidence to collect.

### Runtime Evidence Documentation

Create `docs/runbooks/kong-runtime-verification-evidence.md`. It must define
evidence required to mark goal 002 runtime-verified:

- current branch and commit
- current Kubernetes context
- goal 002 version pins
- mutation approval present
- local validation passed
- cluster preflight passed
- dry-run passed
- apply completed
- Kong namespace exists
- Kong pods ready
- KIC pods ready
- proxy service exists and type verified
- LoadBalancer status recorded
- GatewayClass and Gateway status recorded
- smoke backend ready
- HTTPRoute status recorded
- internal route smoke result
- external route smoke result or documented blocker plus fallback
- unknown route negative test result
- Admin API external exposure negative test result
- rollback command documented

### Runtime Approval Decision Note

Create `docs/decisions/goal-002-runtime-approval.md`.

It must start as:

```text
Status: pending
```

It may only be changed to:

```text
Status: approved
```

if cluster apply and smoke tests pass.

### Execution Logs

Create or update:

- `platform/kong/CLUSTER-APPLY-EXECUTION-LOG.md`
- `platform/kong/CLUSTER-SMOKE-RESULTS.md`
- `platform/kong/ROUTE-SMOKE-RESULTS.md`
- `platform/kong/ADMIN-API-EXPOSURE-RESULTS.md`

Each file must clearly support these states: not run, pass, fail, blocked.

If commands are not run, record:

```text
Status: not run
Reason:
```

If commands are run, record status, command, result summary, evidence, and
timestamp. Do not claim pass unless the command actually passed.

### Guarded Execution Script

Create `platform/kong/scripts/kong-cluster-apply-and-smoke.sh`.

It must call `require-cluster-mutation-permission.sh` before any mutation,
print current branch and commit, print current Kubernetes context, run
pre-apply read-only checks, run dry-run, run guarded apply, run cluster smoke,
run route smoke, run Admin API exposure check, stop on first failure, write
evidence locations, and never bypass Makefile guardrails.

It must not be run by CI or by required local validation.

### Runtime Evidence Collection Script

Create `platform/kong/scripts/collect-kong-runtime-evidence.sh`.

It must collect read-only runtime evidence under `reports/` and must not mutate
the cluster.

### Runtime-Ready Verifier

Create `platform/kong/scripts/verify-goal002-runtime-ready.sh`.

It must verify that all required runtime result files indicate pass. It must
fail if any required result is not run, fail, or blocked. It must fail if goal
002 still says local-only only, cluster verification is not run, Kong runtime
applied is no, route smoke passed is no, or Admin API exposure check did not
pass.

### Validation Script

Create `scripts/validate_cluster_apply_gate.py`. It must validate repository
structure for this gate without requiring Kubernetes.

It must check required files, mutation guard, guarded mutating scripts,
cluster-free CI, pending runtime approval, result file state support, evidence
report availability, goal 003 blocked status, and sensitive-file hygiene.

### Makefile Targets

Preserve all existing targets and add:

- `validate-cluster-apply-gate`
- `evidence-gate-002-cluster-apply-and-smoke`
- `goal002-runtime-ready`

`make validate-cluster-apply-gate` must run local validation for this gate and
must not require Kubernetes.

`make evidence-gate-002-cluster-apply-and-smoke` must generate or update
`reports/gate-002-cluster-apply-and-smoke-summary.md`.

`make goal002-runtime-ready` must verify runtime approval evidence and fail
until cluster apply and smoke tests have actually passed. It must not mutate
the cluster.

Do not add cluster-mutating commands to CI.

## Evidence Report Requirements

Create or update `reports/gate-002-cluster-apply-and-smoke-summary.md`.

Default values before permission or execution:

- Status: pending explicit cluster mutation permission
- Explicit mutation permission required: yes
- Mutation permission granted: no
- Cluster changes performed: none
- Secrets created: none
- Kong runtime applied: no
- Kong route smoke passed: no
- Admin API externally exposed: not runtime-tested
- Runtime approval: pending
- Ready for goal 003: no

Values required for successful runtime approval:

- Status: pass; runtime-verified
- Explicit mutation permission required: yes
- Mutation permission granted: yes
- Cluster changes performed: Kong OSS baseline applied
- Secrets created: none
- Kong runtime applied: yes
- Kong route smoke passed: yes
- Admin API externally exposed: no
- Runtime approval: approved
- Ready for goal 003: yes

If external LoadBalancer smoke cannot pass because MetalLB is not installed or
not assigning an IP, but port-forward smoke passes, use:

- Status: blocked
- Kong runtime applied: yes
- Kong route smoke passed: partial
- Known limitations: external LoadBalancer smoke blocked by reason
- Runtime approval: pending
- Ready for goal 003: no

Do not mark runtime approval as approved with only partial route smoke unless
the operator explicitly accepts a reduced baseline and records the risk.

## Acceptance Criteria

### Local Acceptance Before Permission

- Gate body is saved.
- Required files exist.
- Mutation guard remains active.
- Cluster-mutating scripts are guarded.
- CI remains cluster-free.
- Runtime approval decision starts as pending.
- Runtime result files exist and are marked not run.
- Evidence report exists and says permission is not granted.
- Goal 003 remains blocked.
- Local validation passes.

### Runtime Acceptance After Explicit Permission

- Explicit permission was provided.
- Expected Kubernetes context was supplied.
- Actual Kubernetes context matched expected context.
- Pre-mutation local validation passed.
- Read-only cluster preflight passed.
- Cluster prerequisite smoke passed.
- Kong install dry-run passed.
- Kong apply completed.
- Kong namespace exists.
- Kong Gateway pods are ready.
- KIC pods are ready.
- Proxy service exists.
- Admin API is not exposed as LoadBalancer or NodePort.
- No Gateway or HTTPRoute exposes the Admin API.
- GatewayClass exists and is accepted, or status is recorded with a non-blocking reason.
- Internal and external Gateways exist and are accepted.
- Smoke backend is ready.
- Internal and external HTTPRoutes are accepted.
- Internal smoke route returns expected success.
- External smoke route returns expected success, or a documented blocker is recorded and runtime approval remains pending.
- Unknown route returns expected failure.
- Admin API is not externally reachable through the proxy.
- Runtime evidence is collected.
- Goal 002 evidence is updated from local-only to runtime-verified only if all runtime checks pass.
- `docs/decisions/goal-002-runtime-approval.md` is updated to approved only if all runtime checks pass.
- `make goal002-runtime-ready` passes only after runtime evidence is complete.
- Evidence says whether goal 003 is allowed.

## Validation Commands

Required local validation before asking for permission:

```bash
make validate
make validate-yaml
make validate-kustomize
make validate-prereqs
make validate-kong-baseline
make render-kong-baseline
make kong-static-test
make kong-admin-exposure-test
make runtime-preflight-local
make kong-apply-plan
make mutation-guard-test
make validate-cluster-apply-gate
make test
make policy-test
make docs
make evidence-gate-002-cluster-apply-and-smoke
```

Full local gate:

```bash
make validate && make validate-yaml && make validate-kustomize && make validate-prereqs && make validate-kong-baseline && make render-kong-baseline && make kong-static-test && make kong-admin-exposure-test && make runtime-preflight-local && make kong-apply-plan && make mutation-guard-test && make validate-cluster-apply-gate && make test && make policy-test && make docs && make evidence-gate-002-cluster-apply-and-smoke
```

Expected result before permission:

- all local checks pass
- cluster changes performed: none
- runtime approval: pending
- ready for goal 003: no

## Required Permission Before Mutation

Do not continue unless the operator explicitly approves cluster mutation.

Then export:

```bash
export BANKLAB_ALLOW_CLUSTER_MUTATION=true
export BANKLAB_TARGET_CONTEXT=<expected-kubernetes-context>
```

Verify:

```bash
kubectl config current-context
```

The output must match `$BANKLAB_TARGET_CONTEXT`.

## Runtime Validation Sequence After Explicit Permission

Run:

```bash
make cluster-readonly-preflight
make kong-readonly-preflight
make cluster-smoke
make cluster-prereq-smoke
make kong-install-dry-run
make kong-apply
make kong-cluster-smoke
make kong-route-smoke
make kong-admin-exposure-test
platform/kong/scripts/collect-kong-runtime-evidence.sh
make evidence-goal-002
make evidence-gate-002-cluster-apply-and-smoke
make goal002-runtime-ready
```

## Optional Rollback

Run rollback only if apply fails or the operator intentionally tests rollback.
Rollback requires explicit mutation permission.

```bash
make kong-rollback
make kong-readonly-preflight
make evidence-gate-002-cluster-apply-and-smoke
```

## Stop Condition

Stop after one of these outcomes.

### Outcome A: No Explicit Permission Granted

Stop after local gate files, validation, and evidence are complete.

Required final state:

- Status: pending explicit cluster mutation permission
- Cluster changes performed: none
- Kong runtime applied: no
- Kong route smoke passed: no
- Runtime approval: pending
- Ready for goal 003: no

### Outcome B: Explicit Permission Granted And Runtime Validation Passes

Stop after Kong apply, cluster smoke, route smoke, Admin API exposure test,
evidence collection, and runtime-ready verification pass.

Required final state:

- Status: pass; runtime-verified
- Cluster changes performed: Kong OSS baseline applied
- Kong runtime applied: yes
- Kong route smoke passed: yes
- Admin API externally exposed: no
- Runtime approval: approved
- Ready for goal 003: yes

Do not create goal 003 in this gate.

### Outcome C: Explicit Permission Granted But Runtime Validation Fails

Stop after recording the failure, collecting evidence, and either leaving the
cluster state as-is for investigation or running guarded rollback if approved.

Required final state:

- Status: failed or blocked
- Cluster changes performed: recorded
- Kong runtime applied: recorded
- Kong route smoke passed: no or partial
- Runtime approval: pending
- Ready for goal 003: no

Do not continue to goal 003. Do not hide or bypass failed runtime checks.

## Permission Boundary

`gate-002-cluster-apply-and-smoke` requires explicit user permission before any
cluster-mutating command.

Permission is not assumed granted.
