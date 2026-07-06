# Platform Principles

## Git Is The Source Of Truth

All gateway configuration, ownership metadata, policy definitions, tests, docs,
runbooks, and evidence should be represented in Git. The Kong Admin API is not a
human configuration surface for this lab.

## Kubernetes First

The lab runs on Kubernetes and should use Kubernetes-native interfaces where
practical. Later Kong phases should prefer Gateway API and Kong Ingress
Controller over direct manual gateway edits.

## OSS-Compatible Design

The baseline is Kong OSS. Enterprise-only features must be blocked, documented,
or represented by an OSS-compatible replacement pattern.

## Automated Validation

Each meaningful change needs automated validation. Static checks, policy tests,
unit tests, integration tests, negative tests, and failure-mode tests should be
added as the platform matures.

## Auditable Change

Change evidence should come from pull requests, CODEOWNERS, CI logs, GitOps
history, Kubernetes events where available, generated reports, and runbooks.

## Least Privilege

Human and automation access should be scoped to the narrowest practical role.
Later goals should model platform admins, operators, API teams, security
reviewers, auditors, and synthetic clients separately.

## Explicit Ownership

Every API, policy, tenant, and platform component should declare an owner. Work
that lacks ownership should fail validation once the relevant policy gates
exist.

## Safe Rollback

Every deployed platform change should include rollback notes and a testable way
to prove the rollback restored the expected behaviour.

## Synthetic But Realistic Banking

The services are synthetic, but the operating model should feel serious:
accounts, payments, cards, fraud, customer profile, and open-banking partner
flows should have owners, exposure models, SLOs, tests, and support paths.

## Day-2 From The Beginning

Operations are not a final polish pass. Upgrade, backup, restore, key rotation,
certificate rotation, incidents, evidence, and regression tests are part of the
platform design from the first phase.

