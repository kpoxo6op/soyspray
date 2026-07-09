# Goal 010: Kong runtime drift guard and final readiness audit

Status: proposed

Goal id: goal-010-kong-runtime-drift-guard-final-readiness

## Objective

Add a read-only final readiness audit for the Kong bank-lab runtime.

The goal is to prove that the live Kubernetes and Kong state matches the approved GitOps baseline after Goal009 rollback, that no temporary governance or response-header resources remain, and that the approved bank-lab runtime behavior still works without mutating the cluster.

This goal is intentionally read-only. It must not apply, patch, delete, annotate, label, restart, scale, or otherwise mutate Kubernetes or Kong resources.

## Scope

Add a GitOps-compatible drift guard and runtime inventory audit for the existing bank-lab deployment.

The audit must verify the live runtime state against an expected inventory committed in the repo.

The expected inventory must include at least:

- The active Kubernetes context.
- The bank-lab namespaces that are expected to exist.
- The Kong-facing route resource used by the accounts smoke path.
- The expected `konghq.com/plugins` annotation on the accounts route.
- The expected namespaced KongPlugin resources.
- The expected plugin types.
- The expected absence of Goal008 admission resources after rollback.
- The expected absence of Goal009 response-header resources after rollback.
- The expected absence of unsafe or unapproved Kong plugins.
- The expected Kong Admin API exposure safety posture.

The live cluster state after Goal009 approval is expected to include:

```text
tenant-accounts/HTTPRoute/banklab-accounts
konghq.com/plugins: banklab-key-auth,banklab-acl,banklab-rate-limit,banklab-correlation-id
```

The live cluster state after Goal009 approval is expected not to include:

```text
banklab-goal009-security-headers
banklab-kong-plugin-governance
```

The audit must also verify that the runtime behavior from the approved goals still holds:

- Goal004 positive smoke path works.
- Missing API key remains denied.
- Wrong ACL key remains denied.
- Redis-backed rate-limit behavior remains intact.
- Correlation ID behavior remains intact.
- Kong Admin API exposure safety remains intact.
- No Goal009 response-header marker remains after rollback.

The runtime evidence must be collected using read-only Kubernetes and Kong inspection only.

## Non-goals

Do not add new Kong plugins.

Do not add new Kong routes.

Do not add new Kubernetes admission resources.

Do not reapply Goal008 admission policy resources.

Do not reapply Goal009 response-header resources.

Do not mutate cluster state.

Do not change application code.

Do not change authentication, ACL, rate-limit, correlation ID, routing, service, namespace, ingress class, or upstream configuration.

Do not change Kong Admin API exposure.

Do not add Kong Enterprise features.

Do not add WAF behavior, OIDC, mTLS, Vault integration, cert-manager, external DNS, TLS, or HSTS changes.

Do not print raw Secret values in reports.

Do not approve the whole project as part of this goal. Whole-project approval requires a separate final approval packet after Goal010 is approved.

## Required implementation

Add a machine-readable expected runtime inventory file.

Recommended path:

```text
soydocs/kong-bank-lab/goal-010-expected-runtime-inventory.yaml
```

The inventory must describe the approved post-Goal009 rollback baseline. It must be specific enough for automated checks to fail on drift.

Add a dedicated validation target:

```sh
make validate-goal010-drift-guard
```

The validation target must fail unless all of the following are true:

- The expected inventory file exists.
- The expected inventory includes `kubernetes-admin@cluster.local`.
- The expected inventory includes `tenant-accounts/HTTPRoute/banklab-accounts`.
- The expected accounts route plugin annotation is exactly `banklab-key-auth,banklab-acl,banklab-rate-limit,banklab-correlation-id`.
- The expected inventory includes the approved plugin types used by the accounts route.
- The expected inventory rejects `request-transformer`.
- The expected inventory rejects global KongPlugin attachment unless already approved elsewhere in the repo.
- The expected inventory rejects `banklab-goal009-security-headers`.
- The expected inventory rejects `banklab-kong-plugin-governance`.
- The Goal010 runtime scripts contain no mutating Kubernetes commands.
- The Goal010 runtime scripts contain no mutating Kong Admin API calls.
- The Goal010 report writers redact Secret values.
- The Goal010 rollback target is a read-only verification target.
- The Goal010 docs and handover paths are present or reserved.

Add a render target:

```sh
make render-goal010-inventory
```

The render target must produce a deterministic local artifact showing the expected inventory that will be compared to the live cluster.

Recommended output:

```text
reports/goal-010-expected-runtime-inventory-rendered.yaml
```

Add static and contract tests:

```sh
make goal010-static-test
make goal010-contract-test
```

The static tests must include negative fixtures proving that validation fails for:

- A route missing `banklab-key-auth`.
- A route missing `banklab-acl`.
- A route missing `banklab-rate-limit`.
- A route missing `banklab-correlation-id`.
- A route containing `banklab-goal009-security-headers`.
- A KongPlugin using `request-transformer`.
- A global KongPlugin fixture.
- A lingering `banklab-kong-plugin-governance` admission fixture.
- A Goal010 runtime script containing `kubectl apply`.
- A Goal010 runtime script containing `kubectl delete`.
- A Goal010 runtime script containing `kubectl patch`.
- A Goal010 runtime script containing `kubectl annotate`.
- A Goal010 runtime script containing `kubectl label`.
- A Goal010 runtime script containing a mutating Kong Admin API method.

The contract tests must prove that:

- The expected inventory schema is stable.
- The runtime report format is stable.
- The drift report format is stable.
- The no-mutation proof format is stable.
- Secret values are redacted in all report outputs.
- No report contains a raw API key value.

## Local validation commands

The local validation evidence must include these commands:

```sh
make validate
make validate-yaml
make validate-kustomize
make validate-goal008-governance
make validate-goal009-security-headers
make validate-goal010-drift-guard
make render-goal010-inventory
make goal010-static-test
make goal010-contract-test
make test
make policy-test
make docs
```

Expected result: all pass.

The local evidence must record the exact test counts for:

```sh
make test
make policy-test
```

## Runtime readiness

Runtime execution must remain explicitly gated and read-only.

Goal010 must fail if cluster mutation is enabled.

Required command:

```sh
BANKLAB_ALLOW_CLUSTER_MUTATION=false \
BANKLAB_TARGET_CONTEXT=kubernetes-admin@cluster.local \
make goal010-runtime-ready
```

The readiness target must verify:

- `BANKLAB_TARGET_CONTEXT` is set.
- `BANKLAB_TARGET_CONTEXT` is exactly `kubernetes-admin@cluster.local`.
- `BANKLAB_ALLOW_CLUSTER_MUTATION` is unset or exactly `false`.
- The current Kubernetes context is exactly `kubernetes-admin@cluster.local`.
- The target bank-lab namespaces exist.
- Kong or KIC is reachable using the repo’s existing runtime access pattern.
- The accounts route exists.
- The accounts route has the expected plugin annotation.
- The expected KongPlugin resources exist.
- `banklab-goal009-security-headers` is absent.
- `banklab-kong-plugin-governance` admission resources are absent.
- The existing Goal004 positive smoke path is reachable.
- The existing missing API key behavior is intact.
- The existing wrong ACL key behavior is intact.
- The existing Redis rate-limit smoke is intact.
- The existing correlation ID behavior is intact.
- Kong Admin API exposure safety is intact.
- The evidence target can run using read-only commands only.
- The rollback target can run using read-only commands only.

Readiness must not apply, patch, delete, annotate, label, restart, scale, or otherwise mutate any cluster resource.

Readiness must write:

```text
reports/goal-010-runtime-readiness.md
```

The readiness report must show:

```text
Status: pass
Mutation mode: disabled
Result: ready
```

## Runtime evidence commands

Required command:

```sh
BANKLAB_ALLOW_CLUSTER_MUTATION=false \
BANKLAB_TARGET_CONTEXT=kubernetes-admin@cluster.local \
make evidence-goal-010
```

The evidence target must be read-only.

It must write these files:

```text
reports/goal-010-summary.md
reports/goal-010-runtime-readiness.md
reports/goal-010-kong-runtime-inventory.md
reports/goal-010-kong-drift-audit.md
reports/goal-010-behavior-regression.md
reports/goal-010-no-mutation-proof.md
docs/decisions/goal-010-runtime-approval.md
```

The summary report must show:

```text
Status: pass
Result: runtime-verified locally
Goal: goal-010-kong-runtime-drift-guard-final-readiness
```

The runtime inventory report must show:

- Status: pass.
- Kubernetes context: `kubernetes-admin@cluster.local`.
- Runtime source commit.
- Expected inventory file path.
- Expected rendered inventory path.
- Live accounts route resource.
- Live accounts route plugin annotation.
- Live KongPlugin inventory.
- Live plugin type inventory.
- Live KongConsumer inventory with Secret values redacted.
- Live route or service attachment inventory.
- Confirmed absence of `banklab-goal009-security-headers`.
- Confirmed absence of `banklab-kong-plugin-governance`.
- Confirmed absence of unsafe `request-transformer`.
- Confirmed absence of unapproved global KongPlugin attachment.
- Confirmed Kong Admin API exposure safety posture.

The drift audit report must show:

- Status: pass.
- The expected inventory and live inventory were compared.
- No unexpected KongPlugin was found.
- No expected KongPlugin was missing.
- No unexpected plugin annotation was found.
- No expected plugin annotation was missing.
- No Goal009 annotation reference was found.
- No Goal009 KongPlugin resource was found.
- No Goal008 admission policy resource was found.
- No Goal008 admission policy binding resource was found.
- No unsafe plugin type was found.
- No unapproved global plugin attachment was found.
- No unexpected Kong-facing route was found for the bank-lab namespaces.
- No drift requiring cluster mutation was found.

The behavior regression report must show:

- Status: pass.
- Goal004 positive smoke path still returns the expected successful response.
- Missing API key still returns the expected denied response.
- Wrong ACL key still returns the expected denied response.
- Redis-backed rate-limit behavior still matches the approved expected behavior.
- Correlation ID behavior still matches the approved expected behavior.
- `X-BankLab-Response-Policy: goal009` is absent after Goal009 rollback.
- Account response body marker is preserved.
- Existing rate-limit headers are preserved.
- Kong Admin API exposure safety still passes.

The no-mutation proof report must show:

- Status: pass.
- Mutation mode: disabled.
- No mutating Kubernetes command was executed.
- No mutating Kong Admin API call was executed.
- Resource versions or generations for the audited resources were captured before and after the audit.
- Audited resource versions or generations did not change due to Goal010.
- The Goal010 evidence target made no cluster changes.

The approval file must be created with:

```text
Status: pending approval
```

## Runtime rollback evidence

Goal010 is a read-only audit goal. It must not create any runtime resource and therefore has no mutating rollback.

A rollback verification target is still required.

Required command:

```sh
BANKLAB_ALLOW_CLUSTER_MUTATION=false \
BANKLAB_TARGET_CONTEXT=kubernetes-admin@cluster.local \
make rollback-goal-010
```

The rollback target must be a read-only no-op verification.

It must write:

```text
reports/goal-010-readonly-rollback.md
```

The rollback report must show:

- Status: pass.
- Rollback type: read-only no-op.
- Kubernetes context: `kubernetes-admin@cluster.local`.
- Mutation mode: disabled.
- No Goal010 Kubernetes resource exists.
- No Goal010 KongPlugin exists.
- No Goal010 plugin annotation exists.
- No Goal010 admission resource exists.
- No `banklab-goal009-security-headers` KongPlugin exists.
- No annotation references `banklab-goal009-security-headers`.
- No `banklab-kong-plugin-governance` ValidatingAdmissionPolicy exists.
- No `banklab-kong-plugin-governance` ValidatingAdmissionPolicyBinding exists.
- The accounts route annotation remains `banklab-key-auth,banklab-acl,banklab-rate-limit,banklab-correlation-id`.
- Goal004 positive smoke still passes.
- Missing API key behavior still passes.
- Wrong ACL key behavior still passes.
- Redis rate-limit behavior still passes.
- Correlation ID behavior still passes.
- Kong Admin API exposure safety still passes.

Use these concrete checks inside the harness or their repo-equivalent implementations:

```sh
kubectl --context "$BANKLAB_TARGET_CONTEXT" get kongplugin -A \
  | grep -F banklab-goal010
```

Expected result: no match.

```sh
kubectl --context "$BANKLAB_TARGET_CONTEXT" get ingress,httproute,service -A -o yaml \
  | grep -F banklab-goal010
```

Expected result: no match.

```sh
kubectl --context "$BANKLAB_TARGET_CONTEXT" get kongplugin -A \
  | grep -F banklab-goal009-security-headers
```

Expected result: no match.

```sh
kubectl --context "$BANKLAB_TARGET_CONTEXT" get ingress,httproute,service -A -o yaml \
  | grep -F banklab-goal009-security-headers
```

Expected result: no match.

```sh
kubectl --context "$BANKLAB_TARGET_CONTEXT" get validatingadmissionpolicy,validatingadmissionpolicybinding \
  | grep -F banklab-kong-plugin-governance
```

Expected result: no match.

The harness must treat no-match as pass for these checks.

## Documentation requirements

Add the Goal010 goal body at:

```text
soydocs/kong-bank-lab/goals/goal-010-kong-runtime-drift-guard-final-readiness.md
```

Update:

```text
soydocs/kong-bank-lab/current-state.md
```

Add a post-Goal010 handover after runtime evidence is captured:

```text
soydocs/kong-bank-lab/handover-2026-07-09-post-goal-010.md
```

Add a final approval candidate file, but do not mark it approved:

```text
docs/decisions/kong-bank-lab-final-approval-candidate.md
```

The final approval candidate file must have:

```text
Status: pending final approval
```

The docs must record:

- Goal id.
- Runtime source commit.
- Evidence commit.
- Kubernetes context.
- Local validation commands and results.
- Runtime readiness command and result.
- Runtime evidence command and result.
- Runtime rollback verification command and result.
- Evidence files.
- Expected runtime inventory path.
- Current cluster state after Goal010.
- Confirmed no-mutation result.
- Confirmed absence of Goal008 runtime admission resources.
- Confirmed absence of Goal009 runtime response-header resources.
- Known non-goals.
- Recommended next action: submit Goal010 evidence for formal approval, then submit the final whole-project approval packet.

The current-state document must clearly state that Goal010 is read-only and that the cluster should remain in the approved post-Goal009 rollback baseline.

## Completion gate

Goal010 is complete only when all of the following are true:

- Local validation passes.
- Runtime readiness passes.
- Runtime evidence passes.
- Runtime rollback verification passes.
- Evidence is committed.
- `reports/goal-010-summary.md` says `Status: pass`.
- `reports/goal-010-summary.md` says `Result: runtime-verified locally`.
- `reports/goal-010-runtime-readiness.md` says `Status: pass`.
- `reports/goal-010-kong-runtime-inventory.md` says `Status: pass`.
- `reports/goal-010-kong-drift-audit.md` says `Status: pass`.
- `reports/goal-010-behavior-regression.md` says `Status: pass`.
- `reports/goal-010-no-mutation-proof.md` says `Status: pass`.
- `reports/goal-010-readonly-rollback.md` says `Status: pass`.
- `docs/decisions/goal-010-runtime-approval.md` exists with `Status: pending approval`.
- `docs/decisions/kong-bank-lab-final-approval-candidate.md` exists with `Status: pending final approval`.
- The live accounts route annotation is exactly `banklab-key-auth,banklab-acl,banklab-rate-limit,banklab-correlation-id`.
- The live cluster has no `banklab-goal009-security-headers` KongPlugin.
- The live cluster has no annotation reference to `banklab-goal009-security-headers`.
- The live cluster has no `banklab-kong-plugin-governance` ValidatingAdmissionPolicy.
- The live cluster has no `banklab-kong-plugin-governance` ValidatingAdmissionPolicyBinding.
- No unsafe `request-transformer` KongPlugin is present.
- No unapproved global KongPlugin attachment is present.
- Existing positive smoke, negative auth, Redis rate-limit, correlation ID, and Kong Admin API safety behavior remain intact.
- Goal010 evidence proves that no cluster mutation was performed.

## Approval gate

Formal approval for Goal010 must wait for the pushed evidence commit.

The approval request must include:

- Repo path.
- Branch name.
- Current pushed HEAD.
- Runtime source commit.
- Runtime evidence commit.
- Kubernetes context.
- Goal body path.
- Evidence file list.
- Local validation results.
- Runtime readiness result.
- Runtime evidence result.
- Runtime rollback verification result.
- No-mutation proof result.
- Current live cluster state summary.

Goal010 may be approved only if the pushed evidence shows that the read-only drift guard passed, the live runtime matches the approved baseline, the behavior regression checks passed, rollback verification passed, and no cluster mutation was performed.

Whole-project approval must not be granted automatically with Goal010 approval. After Goal010 is formally approved, submit a separate final approval packet that cites all approved goals and their evidence commits.