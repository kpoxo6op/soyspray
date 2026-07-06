# Kong Runtime Validation Gate

Goal 002 is approved as a local-only Kong OSS baseline. That approval means the
repository structure, version pins, local rendering, Admin API exposure checks,
and static tests passed. It does not mean Kong is running in the cluster.

`goal-003-synthetic-bank-apis` must wait until the Kong baseline is applied and
proved at runtime. Banking API work depends on a real gateway path, not only on
rendered manifests.

## Runtime Approval Threshold

Goal 002 becomes runtime-approved only after all of these are evidenced:

- Kong OSS baseline applied successfully.
- Kong and KIC pods are ready.
- Gateway API resources are accepted.
- The smoke backend is ready.
- The internal smoke route works.
- The external smoke route works, or a LoadBalancer blocker is documented.
- An unknown route returns the expected failure.
- Kong Admin API is not externally exposed.
- The evidence report is updated.

## Local Work Allowed Before Approval

These actions are local-only and safe inside `gate-002-runtime-preflight`:

- Validate repository, YAML, Kustomize, prerequisites, and Kong baseline files.
- Render local Kong baseline manifests.
- Run Kong static and Admin API exposure tests.
- Generate the runtime apply plan.
- Prove mutation guardrails fail closed.
- Update documentation, runbooks, and evidence templates.

## Work Requiring Explicit Cluster Permission

These actions require a later cluster-apply gate and explicit operator approval:

- Applying the Kong baseline.
- Rolling back the Kong baseline.
- Installing or upgrading Gateway API CRDs, MetalLB, cert-manager, or Argo CD.
- Running cluster smoke checks that depend on applied resources.
- Running route smoke checks against live Kong.

## Evidence Required Before Goal 003

Before `goal-003-synthetic-bank-apis` can start, evidence must show the applied
baseline, the smoke route results, the Admin API exposure negative test, the
exact branch and commit used, and any runtime blockers. Without that evidence,
goal 003 remains blocked.
