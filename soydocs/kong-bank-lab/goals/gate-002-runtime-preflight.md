# gate-002-runtime-preflight

## Assignment

Next assigned goal/gate name: `gate-002-runtime-preflight`

Gate type: repo-safe/local-only pre-cluster-apply gate.

This gate must not mutate the Kubernetes cluster. It exists because
`goal-003-synthetic-bank-apis` must wait until the Kong OSS baseline from
goal 002 has been applied to the cluster and proven through smoke tests.

## Objective

Prepare the repository for a controlled, auditable, explicitly approved runtime
validation of `goal-002-kong-oss-baseline`.

This gate sits between `goal-002-kong-oss-baseline` and
`goal-003-synthetic-bank-apis`.

Goal 002 is approved as local-only, but it is not yet approved as a working
runtime baseline because no cluster-mutating commands, cluster smoke tests, or
route smoke tests have been run.

This gate must make the next cluster step safe, explicit, repeatable, and
evidence-driven without changing the cluster.

The output of this gate is an apply-readiness package for the Kong OSS
baseline. It must include:

- explicit preconditions for cluster apply
- cluster mutation guardrails
- read-only preflight checks
- apply-plan documentation
- rollback-plan documentation
- runtime validation checklist
- smoke-test checklist
- evidence-report structure
- validation targets proving that dangerous commands are guarded
- confirmation that goal 003 remains blocked until runtime proof passes

This gate is complete when the repo can prove that:

- no cluster mutation can happen accidentally
- the Kong baseline apply path is documented
- the smoke validation path is documented
- the rollback path is documented
- the evidence model is ready
- goal 003 remains blocked until Kong runtime validation passes

## Current State Entering This Gate

- Goal 000: complete
- Goal 001: complete and approved
- Goal 002: corrected and approved as local-only
- Goal 002 evidence: `reports/goal-002-summary.md`
- Goal 002 status: `pass; local-only`
- Kong Gateway image: `kong:3.9.3`
- KIC image: `kong/kubernetes-ingress-controller:3.5.10`
- Gateway API version: `v1.3.0`
- Helm chart: `kong/ingress 0.24.0`
- Full local goal-002 gate: passed
- Cluster changes performed: none
- Cluster verification: not run
- Ready-for-next: no; run cluster apply and smoke tests before goal 003

This gate must preserve that state.

## Non-Goals

Do not run:

- `make kong-apply`
- `kubectl apply`
- `helm install`
- `helm upgrade`
- `argocd app sync`
- `kubectl delete`

Do not mutate the Kubernetes cluster in any way.

Do not install Kong, Gateway API CRDs, MetalLB, cert-manager, or Argo CD.

Do not run cluster smoke tests or route smoke tests as a required validation
step.

Do not create synthetic banking APIs.

Do not implement `goal-003-synthetic-bank-apis`.

Do not create accounts, payments, cards, customer profile, fraud, or
open-banking APIs.

Do not create Kong Consumers, API keys, Key Auth, JWT, ACL, rate limiting,
Redis, SSO, or the observability stack.

Do not add real secrets, kubeconfigs, private keys, generated certificates, API
keys, or passwords.

Do not alter goal 002's approved version pins unless a validation bug is found.

Do not mark goal 002 as runtime-approved.

Do not mark the programme ready for goal 003.

## Corrections And Preconditions

### Preserve Gateway API Compatibility

Goal 002 must still use:

- KIC: `3.5.10`
- Gateway API: `v1.3.0`

The KIC/Gateway API compatibility validation added after goal 002 must remain
active. Validation must reject KIC 3.5.x paired with Gateway API versions
greater than v1.3.x unless a newer official Kong compatibility source is
explicitly added to the repo and cited in evidence.

Do not revert to Gateway API `v1.6.0`.

### Keep Goal 002 Local-Only Status Accurate

`reports/goal-002-summary.md` must remain historically accurate. It must
continue to state:

- `Status: pass; local-only`
- `Cluster changes performed: none`
- `Cluster verification: not run`
- `Kong resources created: none applied; manifests/templates only`
- `Helm chart compatibility: local render passed; cluster behavior not verified`
- `Ready for next goal: no; run cluster apply and smoke tests before goal-003`

Do not overwrite this status unless runtime validation is actually performed in
a later explicitly approved cluster-apply gate.

### Enforce Explicit Permission For Cluster Mutation

Any existing or new cluster-mutating target must require an explicit guard.

The following targets must be guarded:

- `make kong-apply`
- `make kong-rollback`
- any future target that can mutate the cluster

The guard must require explicit operator intent:

- `BANKLAB_ALLOW_CLUSTER_MUTATION=true`
- `BANKLAB_TARGET_CONTEXT=<expected-kubernetes-context>`

A cluster-mutating command must fail closed if the guard is not satisfied. Do
not rely only on documentation warnings.

### Separate Read-Only Checks From Mutating Checks

Read-only cluster checks must be named clearly. Acceptable targets:

- `make cluster-readonly-preflight`
- `make kong-readonly-preflight`

They may check cluster state with non-mutating commands such as:

- `kubectl config current-context`
- `kubectl version`
- `kubectl get ns`
- `kubectl get crd`
- `kubectl api-resources`
- `kubectl auth can-i`

They must not apply, delete, patch, annotate, label, scale, restart, sync,
install, upgrade, or otherwise mutate resources.

Required local validation must not require these read-only checks.

### Keep CI Cluster-Free

CI must not run cluster-mutating commands, cluster smoke commands, or optional
read-only cluster preflight commands unless they are explicitly manual, opt-in,
and skipped by default.

### Keep Goal 003 Blocked

Do not create the full `goal-003-synthetic-bank-apis` body in this gate.

At most, add a short placeholder note:

`goal-003-synthetic-bank-apis is blocked until goal-002 runtime validation passes.`

The real goal 003 body must be created only after Kong is applied and smoke
tests pass.

## Constraints

All required validation in this gate must be local-only.

This gate must not require Kubernetes access, internet access, Docker, or Helm
chart downloads unless already supported by the existing local render flow.

This gate must not weaken existing secret validation, OSS boundary validation,
Admin API exposure validation, or KIC/Gateway API compatibility validation.

All new scripts must be safe by default.

All cluster-mutating scripts must fail closed unless explicit mutation
permission is supplied.

All cluster-aware scripts must print the current Kubernetes context before
doing anything.

All cluster-mutating scripts must require the expected Kubernetes context to be
provided explicitly. No script may silently default to the current context for
mutation.

The repository must continue to support the bank-like operating model:

- Git as source of truth
- explicit approval before change
- auditable command path
- rollback plan
- evidence report
- no manual hidden state
- no "it probably works" assumptions

## Required Files

Create or update:

- `soydocs/kong-bank-lab/goals/gate-002-runtime-preflight.md`
- `docs/architecture/kong-runtime-validation-gate.md`
- `docs/architecture/cluster-mutation-guardrails.md`
- `docs/runbooks/kong-runtime-preflight.md`
- `docs/runbooks/kong-runtime-apply-checklist.md`
- `docs/runbooks/kong-runtime-smoke-checklist.md`
- `docs/runbooks/kong-runtime-rollback-checklist.md`
- `docs/decisions/goal-003-blocked-until-kong-runtime-validation.md`
- `platform/kong/PRE-CLUSTER-APPLY-CHECKLIST.md`
- `platform/kong/CLUSTER-APPLY-REQUEST.md`
- `platform/kong/RUNTIME-VALIDATION-CHECKLIST.md`
- `platform/kong/ROLLBACK-CHECKLIST.md`
- `platform/kong/scripts/require-cluster-mutation-permission.sh`
- `platform/kong/scripts/cluster-readonly-preflight.sh`
- `platform/kong/scripts/kong-readonly-preflight.sh`
- `platform/kong/scripts/generate-kong-apply-plan.sh`
- `scripts/validate_runtime_preflight.py`
- `scripts/generate_evidence_report.py`
- `tests/unit/test_gate_002_runtime_preflight_structure.py`
- `tests/unit/test_gate_002_mutation_guardrails.py`
- `tests/unit/test_gate_002_goal003_blocked.py`
- `tests/policy/test_gate_002_no_unapproved_cluster_mutation.py`
- `tests/policy/test_gate_002_runtime_preflight_policy.py`
- `reports/gate-002-runtime-preflight-summary.md`

Small path adjustments are allowed if needed to fit repository conventions, but
the intent must remain the same.

Do not remove goal 000, goal 001, or goal 002 files. Do not overwrite goal 000,
goal 001, or goal 002 evidence.

## Deliverables

### Runtime Validation Gate Documentation

Create `docs/architecture/kong-runtime-validation-gate.md`. It must explain:

- why goal 002 is approved as local-only but not runtime-approved
- why goal 003 must wait
- what runtime proof is required
- how cluster mutation permission works
- what evidence must exist before goal 003
- what can be done without cluster access
- what requires explicit cluster permission

It must define the runtime approval threshold:

- Kong OSS baseline applied successfully
- Kong and KIC pods ready
- Gateway API resources accepted
- smoke backend ready
- internal smoke route works
- external smoke route works, or LoadBalancer blocker is explicitly documented
- unknown route returns expected failure
- Kong Admin API is not externally exposed
- evidence report updated

### Cluster Mutation Guardrails Documentation

Create `docs/architecture/cluster-mutation-guardrails.md`. It must explain:

- which commands are read-only
- which commands are mutating
- why mutation requires explicit permission
- how the expected Kubernetes context is supplied
- what environment variables are required
- how accidental mutation is prevented
- how CI avoids mutation
- how evidence records mutation

### Runtime Runbooks And Checklists

Create:

- `docs/runbooks/kong-runtime-preflight.md`
- `docs/runbooks/kong-runtime-apply-checklist.md`
- `docs/runbooks/kong-runtime-smoke-checklist.md`
- `docs/runbooks/kong-runtime-rollback-checklist.md`

The preflight runbook must cover branch, Git working tree, goal 002 local gate,
Gateway API compatibility, Helm render status, Admin API static exposure,
secret hygiene, and accidental mutation permission.

The apply checklist must cover explicit user approval, expected cluster
context, target namespaces, Gateway API CRDs, MetalLB, cert-manager, Argo CD,
exact apply command path, expected resources created, expected resources not
created, and evidence to collect.

The smoke checklist must cover namespace presence, Kong and KIC readiness,
proxy service, LoadBalancer or port-forward fallback, GatewayClass, internal
and external Gateway status, smoke backend, HTTPRoute status, smoke requests,
unknown-route negative test, and Admin API external exposure negative test.

The rollback checklist must cover when to rollback, rollback command path,
expected resources removed or reverted, resources that must not be removed,
post-rollback validation, evidence to collect, and follow-up action.

### Platform Kong Local Checklists

Create:

- `platform/kong/PRE-CLUSTER-APPLY-CHECKLIST.md`
- `platform/kong/CLUSTER-APPLY-REQUEST.md`
- `platform/kong/RUNTIME-VALIDATION-CHECKLIST.md`
- `platform/kong/ROLLBACK-CHECKLIST.md`

`CLUSTER-APPLY-REQUEST.md` must be a short approval template with:

- Requested by
- Date
- Branch
- Commit
- Target cluster context
- Commands requested
- Expected resources to change
- Expected resources not to change
- Rollback command
- Preflight evidence
- Approval

It must clearly state: do not run cluster-mutating commands until approval is
explicitly granted.

### Mutation Permission Script

Create `platform/kong/scripts/require-cluster-mutation-permission.sh`.

It must fail unless:

- `BANKLAB_ALLOW_CLUSTER_MUTATION=true`
- `BANKLAB_TARGET_CONTEXT=<expected-context>`

The script must:

- fail if `BANKLAB_ALLOW_CLUSTER_MUTATION` is not exactly `true`
- fail if `BANKLAB_TARGET_CONTEXT` is empty
- print the current Kubernetes context if `kubectl` is available
- fail if the current context does not match `BANKLAB_TARGET_CONTEXT`
- fail if `kubectl` is unavailable and the caller is attempting mutation
- print a clear warning before allowing mutation
- never default to a context silently
- not mutate the cluster

### Read-Only Preflight Scripts

Create:

- `platform/kong/scripts/cluster-readonly-preflight.sh`
- `platform/kong/scripts/kong-readonly-preflight.sh`

These scripts may read cluster state if a Kubernetes context is available. They
must not mutate the cluster, and they must not fail solely because Kong is not
installed yet.

### Apply-Plan Generation

Create `platform/kong/scripts/generate-kong-apply-plan.sh`.

It must generate or update `reports/kong-runtime-apply-plan.md` from repository
files only. It must not query or mutate the cluster.

The apply plan must include:

- branch and commit if detectable
- Kong version lock
- KIC version lock
- Gateway API version lock
- Helm chart version lock
- expected namespaces
- expected Gateway API resources
- expected smoke resources
- expected NetworkPolicy resources
- expected Argo CD templates
- expected Admin API exposure model
- commands that would be run during explicit cluster apply
- rollback commands
- known unresolved runtime dependencies

It must state that it does not prove runtime success. Runtime success requires
explicit cluster apply and smoke validation.

### Makefile Targets

Preserve existing targets and add:

- `runtime-preflight-local`
- `kong-apply-plan`
- `cluster-readonly-preflight`
- `kong-readonly-preflight`
- `mutation-guard-test`
- `evidence-gate-002-runtime-preflight`

`make runtime-preflight-local` must run all required local checks for this gate
without Kubernetes.

`make kong-apply-plan` must generate
`reports/kong-runtime-apply-plan.md` without cluster access.

`make mutation-guard-test` must prove guardrails fail closed when required
environment variables are absent.

`make cluster-readonly-preflight` and `make kong-readonly-preflight` are
optional read-only checks and must not be part of CI.

`make evidence-gate-002-runtime-preflight` must generate or update
`reports/gate-002-runtime-preflight-summary.md`.

Guard existing mutating Make targets so they call
`platform/kong/scripts/require-cluster-mutation-permission.sh` before doing
anything mutating. At minimum, guard `make kong-apply` and
`make kong-rollback`.

## Evidence Report

Create or update `reports/gate-002-runtime-preflight-summary.md`. It must
contain:

- Gate
- Status
- Branch
- Generated at
- Objective summary
- Current programme state
- Goal 002 local-only status verified
- Gateway API compatibility verified
- Mutation guardrails
- Read-only preflight scripts
- Apply plan
- Rollback plan
- Goal 003 blocked
- Validation commands run
- Optional read-only cluster commands run
- Cluster-mutating commands run
- Created files
- Updated files
- Cluster changes performed
- Secrets created
- Kong runtime applied
- Kong route smoke passed
- Admin API externally exposed
- Known limitations
- Next assigned gate

Required values:

- Cluster changes performed: none
- Secrets created: none
- Kong runtime applied: no
- Kong route smoke passed: no
- Admin API externally exposed: no, based on static validation only
- Next assigned gate: `gate-002-cluster-apply-and-smoke`, requiring explicit cluster mutation permission
- Optional read-only cluster checks: not run, unless actually run

Do not claim cluster readiness unless read-only cluster checks actually ran and
passed. Do not claim runtime readiness unless cluster apply and smoke checks
actually ran and passed in a later gate.

## Acceptance Criteria

- Goal 002 remains approved as local-only.
- Goal 002 evidence remains historically accurate.
- Gateway API remains pinned to `v1.3.0`.
- KIC remains pinned to `3.5.10`.
- Kong Gateway remains pinned to `kong:3.9.3`.
- KIC/Gateway API compatibility validation remains present.
- No cluster-mutating command is run.
- No cluster-mutating command can run accidentally through Makefile targets without explicit guard variables.
- `make kong-apply` is guarded.
- `make kong-rollback` is guarded.
- Any other cluster-mutating target is guarded.
- Read-only preflight scripts exist and contain no mutating commands.
- Apply-plan generation exists and is local-only.
- Rollback checklist exists.
- Runtime validation checklist exists.
- Goal 003 is explicitly blocked until runtime validation passes.
- CI remains cluster-free.
- Secret scanning remains active.
- No secrets are committed.
- No kubeconfigs are committed.
- No private keys are committed.
- Evidence report exists at `reports/gate-002-runtime-preflight-summary.md`.
- Apply plan exists at `reports/kong-runtime-apply-plan.md`.
- All required local validation commands pass.

## Required Local Gate

Run from the repository root:

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
make evidence-gate-002-runtime-preflight
```

Full required local gate:

```bash
make validate && make validate-yaml && make validate-kustomize && make validate-prereqs && make validate-kong-baseline && make render-kong-baseline && make kong-static-test && make kong-admin-exposure-test && make runtime-preflight-local && make kong-apply-plan && make mutation-guard-test && make test && make policy-test && make docs && make evidence-gate-002-runtime-preflight
```

Expected result: all required checks pass without cluster access and without
cluster mutation.

## Optional Read-Only Cluster Checks

Run only if the operator wants read-only cluster inspection:

```bash
make cluster-readonly-preflight
make kong-readonly-preflight
```

If run, record results in `reports/gate-002-runtime-preflight-summary.md`.

## Forbidden In This Gate

Do not run:

- `make kong-apply`
- `make kong-rollback`
- `kubectl apply`
- `helm install`
- `helm upgrade`
- `argocd app sync`
- any other cluster-mutating command

## Stop Condition

Stop after this repo-safe runtime preflight gate is implemented, local
validation passes, mutation guardrails are proven, the apply plan is generated,
and `reports/gate-002-runtime-preflight-summary.md` is updated.

Do not install Kong.

Do not mutate the cluster.

Do not run cluster smoke tests or route smoke tests.

Do not create goal 003.

Do not implement synthetic bank APIs.

After this gate, the next assigned gate should be
`gate-002-cluster-apply-and-smoke`. That next gate is a cluster-apply gate and
requires explicit user permission before any cluster-mutating command is run.

## Goal 003 Status

`goal-003-synthetic-bank-apis` must wait.

The repo-safe preparatory gate to run now is:

```text
gate-002-runtime-preflight
```
