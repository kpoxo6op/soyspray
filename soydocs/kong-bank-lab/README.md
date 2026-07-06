# Kong OSS Bank Lab

Source: distilled from the ChatGPT Pro conversation at
`https://chatgpt.com/g/g-p-6a40ea717f108191904f22479731671b/c/6a4a1df1-4568-83ec-aac0-6638c5568778`
on 2026-07-06.

This workspace is for the Kong OSS bank-lab programme: a realistic home
Kubernetes platform that simulates how a bank platform team would run Kong,
without pretending that Kong Enterprise features exist in OSS.

The target is not a one-off demo. The target is a bank-like platform product
with GitOps, ownership boundaries, policy gates, observability, regression
tests, runbooks, and day-2 evidence.

## Documents

- `roadmap.md` is the master programme roadmap. It is not an active Codex goal.
- `goals/` contains one Codex-ready goal body per implementation slice.

## Execution Rule

Use several small `/goal` bodies, not one giant goal.

Each goal must be PR-sized, testable, reviewable, reversible, and must stop
after its own evidence report is written. Do not proceed to the next goal until
the previous goal has been reviewed.

Every goal should preserve this stop condition:

> Do not proceed to the next phase. Stop when this phase is complete, tests
> pass, and the evidence report is written.

## Core Constraints

- Kong OSS only. Enterprise-only features must be rejected by policy or called
  out as documented gaps.
- Git is the source of truth for gateway config, policies, tests, docs, and
  runbooks.
- Kong Admin API must stay private; it is not the human control plane.
- SSO belongs around platform tools in this OSS lab, not inside Kong OSS.
- Kubernetes RBAC, namespaces, CODEOWNERS, Argo CD projects, and policy-as-code
  replace Kong Enterprise RBAC/workspace governance.
- Every deployed feature needs manifests, docs, a positive test, a negative
  test, rollback notes, and evidence.

