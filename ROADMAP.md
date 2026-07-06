# Kong OSS Bank-Lab Roadmap

This roadmap defines the Kong OSS bank-lab programme at a high level. It is a
sequencing document, not an active implementation goal.

## Direction

The lab will model how a bank platform team could operate Kong OSS on a small
home Kubernetes cluster. The platform must stay honest about the OSS boundary:
Kong Enterprise features are not assumed, and replacement controls must be
implemented with Kubernetes, Git, GitOps, policy-as-code, SSO around platform
tools, automated tests, evidence, and runbooks.

## Phases

| Goal | Phase | Intent |
| --- | --- | --- |
| `goal-000` | Repository foundation | Create the repo structure, local validation gates, docs standards, templates, CI skeleton, and evidence pattern. |
| `goal-001` | Platform prerequisites | Define and locally validate namespaces, Argo CD app structure, MetalLB, cert-manager, SOPS/age, NetworkPolicy, rollback docs, and opt-in cluster smoke checks. |
| `goal-002` | Kong OSS baseline | Define and locally validate pinned Kong OSS with Kong Ingress Controller, Gateway API, private Admin API, smoke backend, route checks, and evidence. |
| `goal-003` | Synthetic bank APIs | Add mock accounts, payments, cards, customer profile, fraud, and open-banking APIs with synthetic clients. |
| `goal-004` | OSS auth, authorization, and rate limiting | Add Key Auth, JWT, ACL, Redis-backed rate limiting, correlation IDs, and security tests. |
| `goal-005` | Tenancy, RBAC simulation, and change control | Simulate bank governance with CODEOWNERS, namespaces, Argo CD projects, and policy checks. |
| `goal-006` | SSO-protected platform tools | Use Keycloak for SSO around platform surfaces such as Argo CD, Grafana, and docs. |
| `goal-007` | Observability, logging, alerting, and dashboards | Add metrics, logs, dashboards, alert rules, SLO evidence, and synthetic probes. |
| `goal-008` | Secrets, certificates, and rotation workflows | Add SOPS/age, API key rotation, JWT key rotation, certificate renewal checks, and recovery docs. |
| `goal-009` | Regression and failure-mode test suite | Build the wider pytest, k6, negative-path, failure-mode, and performance baseline suite. |
| `goal-010` | Day-2 operations and runbooks | Add incident drills, backup/restore, upgrade rehearsal, rollback drills, and runbook evidence. |

## Rules

- One goal should produce one reviewable, reversible platform increment.
- Each goal must include validation commands and an evidence report.
- Do not proceed to the next phase until the previous phase has been reviewed.
- Do not claim Enterprise-grade behaviour unless the lab can prove the OSS
  replacement pattern.
- Do not use the live cluster as the proof for `goal-000`; this phase is local
  repository structure only.
