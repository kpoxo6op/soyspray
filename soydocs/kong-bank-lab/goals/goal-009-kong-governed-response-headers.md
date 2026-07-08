# Goal 009: Kong governed response headers

Status: proposed

Goal id: goal-009-kong-governed-response-headers

## Objective

Add a small, reversible, GitOps-managed Kong response header control to the existing bank-lab API path.

The goal is to prove that an approved OSS KongPlugin can be safely attached through Kubernetes manifests, observed at runtime, and rolled back without changing authentication, rate limiting, routing, or application behavior.

This goal intentionally builds on the governance direction from goal008 by using an allowed plugin class, `response-transformer`, but it does not require re-running the full goal008 admission-policy rollout.

## Scope

Add one namespaced KongPlugin:

- Name: `banklab-goal009-security-headers`
- Plugin: `response-transformer`
- Attachment: the existing bank-lab route or service used by the goal004 positive smoke path
- Attachment method: Kubernetes/GitOps manifest only
- Runtime effect: add response headers without changing status code, body, upstream, routing, auth, or rate-limit behavior

Required headers:

```yaml
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
Referrer-Policy: no-referrer
X-BankLab-Response-Policy: goal009
```

The `X-BankLab-Response-Policy: goal009` header is a lab-only runtime marker. It exists to make rollout and rollback evidence unambiguous.

The implementation must preserve any existing `konghq.com/plugins` annotation values. If the target route or service already has plugins attached, append `banklab-goal009-security-headers` rather than replacing existing plugin references.

The implementation must be namespaced. Do not use a global KongPlugin or cluster-wide attachment.

## Non-goals

Do not add Kong Enterprise plugins.

Do not add WAF behavior, OIDC, mTLS, Vault integration, cert-manager, external DNS, or TLS/HSTS changes.

Do not change application code.

Do not change existing auth behavior.

Do not change existing Redis rate-limit thresholds.

Do not change existing route paths, service names, upstream ports, or ingress classes.

Do not reintroduce goal008 admission resources as part of this goal unless a later correction explicitly requires it.

Do not add request transformation.

Do not add body transformation.

Do not expose or modify the Kong Admin API.

## Required implementation

Add GitOps-managed Kubernetes manifests for the new KongPlugin and its attachment patch.

Add a dedicated validation target:

```sh
make validate-goal009-security-headers
```

The validation target must fail unless all of the following are true:

- The goal009 KongPlugin uses `plugin: response-transformer`.
- The plugin name is exactly `banklab-goal009-security-headers`.
- The manifest does not include `request-transformer`.
- The manifest does not include any Enterprise-only plugin.
- The manifest does not include global plugin attachment.
- The configured headers include the four required headers.
- The attachment preserves existing plugin annotations.
- The rollback overlay or rollback script removes the goal009 plugin attachment.
- Kustomize can render the rollout and rollback states.
- The goal009 manifests are compatible with the existing goal008 governance allowlist rules.

Add or extend local tests so that the response-header manifest, attachment patch, and rollback path are covered.

## Local validation

The local validation evidence must include these commands:

```sh
make validate
make validate-yaml
make validate-kustomize
make validate-goal008-governance
make validate-goal009-security-headers
make test
make policy-test
make docs
```

Expected result: all pass.

The local tests must include at least one negative assertion that an unsafe `request-transformer` version of the goal009 plugin would fail the goal009 validation path.

## Runtime readiness

Runtime execution must remain explicitly gated.

Required command:

```sh
BANKLAB_ALLOW_CLUSTER_MUTATION=true \
BANKLAB_TARGET_CONTEXT=kubernetes-admin@cluster.local \
make goal009-runtime-ready
```

The readiness target must verify:

- The active Kubernetes context is exactly `kubernetes-admin@cluster.local`.
- Cluster mutation is explicitly allowed through `BANKLAB_ALLOW_CLUSTER_MUTATION=true`.
- The target bank-lab namespace exists.
- Kong/KIC is reachable using the repo's existing runtime access pattern.
- The existing goal004 positive smoke path is reachable before rollout.
- The existing negative auth behavior is intact before rollout.
- The existing Redis rate-limit smoke is intact before rollout.
- The goal009 rollout manifests pass server-side dry-run.
- The goal009 rollback path is available.

Readiness must not apply the goal009 plugin.

## Runtime rollout evidence

Required command:

```sh
BANKLAB_ALLOW_CLUSTER_MUTATION=true \
BANKLAB_TARGET_CONTEXT=kubernetes-admin@cluster.local \
make evidence-goal-009
```

The evidence target must apply the goal009 GitOps state, wait for Kong/KIC convergence, and write these files:

```text
reports/goal-009-summary.md
reports/goal-009-governed-response-headers-rollout.md
reports/goal-009-governed-response-headers-runtime.md
docs/decisions/goal-009-runtime-approval.md
```

The rollout report must show:

- Status: pass
- Kubernetes context: `kubernetes-admin@cluster.local`
- The rollout source commit
- The rendered manifest path or kustomize target used
- The applied KongPlugin name
- The Kubernetes resource that carries the plugin attachment
- Server-side dry-run passed before apply
- Apply completed successfully
- Kong/KIC convergence completed successfully

The runtime report must show:

- Status: pass
- Positive smoke endpoint still returns the expected successful response
- Negative auth endpoint still returns the expected denied response
- Redis rate-limit behavior still matches the existing expected behavior
- The positive smoke response includes:

```text
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
Referrer-Policy: no-referrer
X-BankLab-Response-Policy: goal009
```

- The denied auth response includes `X-BankLab-Response-Policy: goal009` unless the existing route topology proves the plugin is intentionally attached only after auth processing
- Kong Admin API or equivalent repo-approved inspection shows `banklab-goal009-security-headers` is enabled
- No unsafe `request-transformer` KongPlugin is present
- No goal008 admission resources are required for the goal009 runtime proof

The summary report must show:

```text
Status: pass
Result: runtime-verified locally
Goal: goal-009-kong-governed-response-headers
```

The approval file must be created with:

```text
Status: pending approval
```

## Runtime rollback evidence

Required command:

```sh
BANKLAB_ALLOW_CLUSTER_MUTATION=true \
BANKLAB_TARGET_CONTEXT=kubernetes-admin@cluster.local \
make rollback-goal-009
```

The rollback target must remove the goal009 plugin attachment and the goal009 KongPlugin using the repo's GitOps-compatible rollback path.

It must write:

```text
reports/goal-009-governed-response-headers-rollback.md
```

The rollback report must show:

- Status: pass
- Kubernetes context: `kubernetes-admin@cluster.local`
- The rollback source commit
- The rendered rollback manifest path or rollback target used
- The plugin attachment was removed
- The `banklab-goal009-security-headers` KongPlugin was removed
- Kong/KIC convergence completed successfully
- Positive smoke still passes after rollback
- Negative auth behavior still passes after rollback
- Redis rate-limit behavior still passes after rollback
- Kong Admin API safety check still passes after rollback
- `X-BankLab-Response-Policy: goal009` is absent after rollback
- No `banklab-goal009-security-headers` resource remains in the cluster
- No Kubernetes annotation still references `banklab-goal009-security-headers`

Use these concrete post-rollback checks inside the harness or their repo-equivalent implementations:

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

The harness should treat no-match as pass for both checks.

## Documentation requirements

Update:

```text
soydocs/kong-bank-lab/current-state.md
```

Add a goal009 handover after runtime evidence is captured:

```text
soydocs/kong-bank-lab/handover-2026-07-09-post-goal-009.md
```

Add or update the goal documentation in the repo's existing goal-doc location.

The docs must record:

- Goal id
- Runtime source commit
- Evidence commit
- Kubernetes context
- Local validation commands and results
- Runtime readiness command and result
- Runtime rollout command and result
- Runtime rollback command and result
- Evidence files
- Current cluster state after rollback
- Known non-goals
- Next recommended goal

## Completion gate

Goal009 is complete only when all of the following are true:

- Local validation passes.
- Runtime readiness passes.
- Runtime rollout evidence passes.
- Runtime rollback evidence passes.
- Evidence is committed.
- `reports/goal-009-summary.md` says `Status: pass`.
- `reports/goal-009-summary.md` says `Result: runtime-verified locally`.
- `reports/goal-009-governed-response-headers-rollout.md` says `Status: pass`.
- `reports/goal-009-governed-response-headers-runtime.md` says `Status: pass`.
- `reports/goal-009-governed-response-headers-rollback.md` says `Status: pass`.
- `docs/decisions/goal-009-runtime-approval.md` exists with `Status: pending approval`.
- Current cluster has no `banklab-goal009-security-headers` KongPlugin after rollback.
- Current cluster has no annotation reference to `banklab-goal009-security-headers` after rollback.
- Existing auth, smoke, rate-limit, and Admin API safety behavior remain intact after rollback.

Formal approval for goal009 must wait for the pushed evidence commit.
