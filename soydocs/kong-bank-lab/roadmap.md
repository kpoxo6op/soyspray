# Kong OSS Bank Lab Roadmap

Created: 2026-07-06

This roadmap captures the agreed plan from the ChatGPT Pro Kong design
conversation and turns it into local execution structure for future Codex goals.

## Mission

Build a realistic small-scale bank API gateway platform on the home
Kubespray-managed Kubernetes cluster using Kong OSS.

The platform should demonstrate controlled change, clear ownership, audit
evidence, safe rollback, client onboarding, production-like incidents, and
measurable SLOs. It should feel like a platform team operating Kong for internal
and external API consumers, scaled down for a 3-node home cluster.

## Target Architecture

- Kong OSS pinned to an explicitly verified OSS-compatible version.
- Kubernetes-native deployment using Helm and Kong Ingress Controller.
- Gateway API and HTTPRoute as the primary API team interface.
- DB-less Kong as the first runtime model.
- Kong Admin API kept private and reachable only by platform automation.
- MetalLB for LoadBalancer semantics on the home LAN.
- Local DNS names for internal and external gateway hostnames.
- cert-manager for declarative TLS and rotation exercises.
- Argo CD as the first GitOps surface.
- Keycloak for SSO around platform tools such as Argo CD, Grafana, and the
  developer portal.
- Kubernetes namespaces, Git permissions, CODEOWNERS, Argo CD projects, and
  policy-as-code as the OSS replacement for Kong Enterprise RBAC and workspace
  governance.
- Synthetic bank APIs for accounts, payments, cards, customer profile, fraud
  decisions, and open banking partner access.
- Synthetic clients for mobile banking, internet banking, CRM, fraud platform,
  payments processor, and fintech partner flows.
- OSS gateway controls using Key Auth, JWT, ACL, Redis-backed rate limiting,
  correlation IDs, request size limiting, selected logging plugins, selected
  transformers, and CORS where required.
- Static developer portal using MkDocs or a Backstage-lite shape generated from
  OpenAPI specs and Git metadata.
- kube-prometheus-stack, Grafana, Alertmanager, Loki, and Kong Prometheus
  metrics for observability.
- Regression and failure-mode tests that prove positive and negative paths.

## OSS Boundaries

The lab must be honest about Kong OSS.

Do not claim these Enterprise capabilities are available in the OSS baseline:

- Kong Gateway RBAC.
- Enterprise workspace governance assumptions.
- Kong OIDC plugin.
- Request Validator plugin.
- MTLS Auth plugin.
- Kong Developer Portal.

For each gap, document the OSS replacement pattern and, where possible, add a
test that proves the replacement works.

## Programme Rules

- The roadmap is not an active goal.
- One `/goal` produces one PR-sized platform increment.
- Each goal must define scope, constraints, acceptance criteria, validation
  commands, evidence, and a stop condition.
- Every goal writes an evidence report under `reports/goal-NNN-summary.md`.
- Do not blend future phases into the current goal.
- Do not make cluster changes in `goal-000`.

## Goal Sequence

| Goal | Name | Purpose | Cluster changes | Evidence |
| --- | --- | --- | --- | --- |
| `goal-000` | `repo-foundation` | Repository skeleton, engineering standards, roadmap, docs, test placeholders, validation targets | No | `reports/goal-000-summary.md` |
| `goal-001` | `platform-prereqs` | Namespaces, Argo CD app structure, MetalLB/cert-manager/SOPS/network-policy base | Yes | `reports/goal-001-summary.md` |
| `goal-002` | `kong-oss-baseline` | Baseline Kong OSS, KIC, Gateway API, private Admin API, first route smoke | Yes | `reports/goal-002-summary.md` |
| `goal-003` | `synthetic-bank-apis` | Mock bank APIs, synthetic clients, OpenAPI specs, product metadata | Yes | `reports/goal-003-summary.md` |
| `goal-004` | `auth-rate-limit-security` | Key Auth, JWT, ACL, Redis rate limiting, correlation IDs, security tests | Yes | `reports/goal-004-summary.md` |
| `goal-005` | `tenancy-rbac-change-control` | OSS tenancy simulation, CODEOWNERS, policy checks, onboarding PR flow | Yes | `reports/goal-005-summary.md` |
| `goal-006` | `keycloak-sso-platform-tools` | Keycloak personas and SSO for platform surfaces, not Kong OSS SSO | Yes | `reports/goal-006-summary.md` |
| `goal-007` | `observability-alerting` | Metrics, logs, dashboards, alerts, SLO-style evidence | Yes | `reports/goal-007-summary.md` |
| `goal-008` | `secrets-certs-rotation` | SOPS/age, API key rotation, JWT key rotation, cert renewal workflows | Yes | `reports/goal-008-summary.md` |
| `goal-009` | `regression-failure-tests` | Full regression, failure-mode, and performance baseline suite | Yes | `reports/goal-009-summary.md` |
| `goal-010` | `day2-ops-runbooks` | Incident runbooks, backup/restore, upgrade rehearsal, rollback drills | Yes | `reports/goal-010-summary.md` |

## Goal Gate Template

Each goal should include:

- Objective.
- Non-goals.
- Repo and cluster constraints.
- Required deliverables.
- Required validation commands.
- Required evidence report path.
- Stop condition.
- Explicit instruction not to proceed to later goals.

## Saved Goal Bodies

The initial goal bodies saved from ChatGPT Pro are:

- `goals/goal-000-repo-foundation.md`
- `goals/goal-001-platform-prereqs.md`
- `goals/goal-002-kong-oss-baseline.md`

Future goal bodies should continue the same naming pattern under `goals/`.
