# ADR 0001: Platform Direction

## Status

Accepted

## Context

The lab needs to simulate a bank-style Kong platform on a small home Kubernetes
cluster. The first decision must make the baseline clear before any cluster
resources are deployed.

## Decision

Use Kong OSS as the baseline.

Use Kubernetes as the runtime.

Prefer Gateway API and Kong Ingress Controller in later implementation goals.

Use GitOps as the configuration model.

Avoid exposing the Kong Admin API as a human control plane.

Simulate Enterprise governance using Kubernetes, Git, GitOps, policy-as-code,
and SSO around platform tools.

Require automated validation and evidence for each future phase.

## Consequences

The lab will be honest about OSS limits and will not claim Enterprise features
as working baseline behaviour.

Governance will be implemented around Kong rather than inside Kong Enterprise
features.

Future goals need stronger tests and docs than a simple install demo.

## Alternatives Considered

Use Kong Enterprise or Konnect: rejected for the baseline because the lab goal
is OSS.

Use direct Kong Admin API changes: rejected because Git must be the source of
truth.

Use manual cluster checks as proof: rejected because the platform needs
repeatable evidence.

## Validation

Goal 000 validates the repository structure and documentation. Later goals must
add cluster validation, policy checks, smoke tests, negative tests, and evidence
reports.

## Rollback / Revisit Criteria

Revisit this decision if the project deliberately changes from OSS learning to
licensed Enterprise or Konnect evaluation.

