# goal-000-repo-foundation

Source: requested from ChatGPT Pro on 2026-07-06 from the agreed Kong OSS
bank-lab plan.

## Objective

Create the initial repository foundation for a Kong OSS bank-lab platform.

This repository will become the source of truth for a realistic home-lab
simulation of how a regulated bank platform team could operate Kong OSS on
Kubernetes. The goal is to create the engineering structure, documentation
standards, validation entrypoints, CI skeleton, testing layout, policy layout,
and evidence-reporting pattern before any cluster resources are deployed.

This goal must produce a clean, reviewable foundation that future goals can
build on without guessing the repo structure or platform standards.

The repository must make the following direction explicit:

- Kong is OSS, not Kong Enterprise and not Konnect.
- Kubernetes is the primary runtime.
- GitOps is the preferred operating model.
- The lab simulates a bank-grade platform product owned by an Integration /
  Infrastructure platform team.
- Enterprise-only Kong features must not be silently assumed.
- All future deployed functionality must be testable through automation.
- Day-2 operations, audit evidence, rollback, observability, and regression
  testing are first-class platform requirements.

## Non-goals

- Do not deploy anything to Kubernetes in this goal.
- Do not install Kong Gateway, Kong Ingress Controller, Gateway API CRDs, Argo
  CD, Keycloak, cert-manager, MetalLB, Prometheus, Grafana, Loki, Redis, or any
  synthetic API service.
- Do not create real secrets, private keys, certificates, API keys, tokens,
  passwords, kubeconfigs, or environment-specific credentials.
- Do not create working tenant APIs yet.
- Do not implement authentication, authorization, rate limiting, SSO,
  observability, GitOps sync, or incident automation yet.
- Do not add Kong Enterprise-only resources or configuration as if they are
  available in OSS.
- Do not use the Kong Admin API as a configuration source of truth.
- Do not create a large speculative implementation. This goal is the repo
  foundation only.

## Constraints

- The repo must be suitable for a small 3-node home Kubernetes cluster while
  modelling regulated-bank platform practices.
- All files created in this goal must be safe to commit.
- All validation commands required by this goal must run locally without
  requiring access to a Kubernetes cluster.
- The default path must be practical and OSS-compatible.
- The repository must distinguish clearly between Kong OSS, Kong Enterprise,
  Konnect, Kubernetes-native Kong usage, and external platform controls used to
  simulate enterprise governance.
- The repo must treat the following Kong capabilities as unavailable for the
  OSS baseline unless future proof shows otherwise:
  - Kong Enterprise RBAC.
  - Kong Enterprise Workspaces as a governance boundary.
  - Kong Enterprise OpenID Connect plugin.
  - Kong Enterprise Request Validator plugin.
  - Kong Enterprise MTLS Auth plugin.
  - Kong Enterprise Developer Portal.
  - Kong Enterprise audit-log assumptions.
- The replacement pattern for these must be documented as Kubernetes RBAC,
  Kubernetes namespaces, Git permissions, CODEOWNERS, GitOps approvals,
  policy-as-code, SSO around platform tools, automated tests, evidence reports,
  and runbooks.
- All future platform work must be designed around explicit validation gates.
- Every major future feature must eventually include manifests or code,
  automated positive tests, automated negative tests, documentation, rollback
  notes, an evidence report, and a runbook entry where relevant.
- No future phase should rely on manual checks as its primary proof.
- This goal must create reusable conventions for later goals.

## Required Repo Structure

Create the following structure.

```text
.
|-- README.md
|-- ROADMAP.md
|-- Makefile
|-- .gitignore
|-- .editorconfig
|-- .pre-commit-config.yaml
|-- CODEOWNERS
|-- .github/
|   `-- workflows/
|       `-- ci.yml
|-- docs/
|   |-- index.md
|   |-- architecture/
|   |   |-- README.md
|   |   |-- platform-principles.md
|   |   |-- oss-vs-enterprise.md
|   |   |-- operating-model.md
|   |   `-- testing-strategy.md
|   |-- adr/
|   |   |-- README.md
|   |   |-- adr-template.md
|   |   `-- 0001-platform-direction.md
|   |-- onboarding/
|   |   |-- README.md
|   |   `-- api-onboarding-template.md
|   |-- runbooks/
|   |   |-- README.md
|   |   `-- runbook-template.md
|   `-- decisions/
|       `-- README.md
|-- platform/
|   |-- README.md
|   |-- gitops/
|   |   `-- README.md
|   |-- kong/
|   |   `-- README.md
|   |-- identity/
|   |   `-- README.md
|   |-- observability/
|   |   `-- README.md
|   |-- security/
|   |   `-- README.md
|   `-- networking/
|       `-- README.md
|-- tenants/
|   |-- README.md
|   `-- tenant-template/
|       `-- README.md
|-- apis/
|   |-- README.md
|   `-- api-template/
|       |-- README.md
|       |-- openapi.yaml
|       |-- ownership.yaml
|       `-- tests/
|           `-- README.md
|-- policies/
|   |-- README.md
|   |-- conftest/
|   |   |-- README.md
|   |   `-- placeholder.rego
|   `-- examples/
|       |-- valid-api-metadata.yaml
|       `-- invalid-api-metadata.yaml
|-- tests/
|   |-- README.md
|   |-- unit/
|   |   |-- README.md
|   |   `-- test_repo_foundation.py
|   |-- policy/
|   |   |-- README.md
|   |   `-- test_policy_placeholders.py
|   |-- integration/
|   |   `-- README.md
|   `-- fixtures/
|       `-- README.md
|-- scripts/
|   |-- README.md
|   |-- validate_repo.py
|   `-- generate_evidence_report.py
|-- reports/
|   |-- README.md
|   `-- goal-000-summary.md
`-- mkdocs.yml
```

Small additions are allowed if they directly support this goal, but do not add
implementation folders for later goals unless they are placeholders with README
files.

## Deliverables

### Repository Documentation

`README.md` must explain:

- What this repo is.
- The Kong OSS bank-lab purpose.
- The platform-team ownership model.
- The "nothing deployed without tests" rule.
- The expected local validation commands.
- The fact that goal 000 does not deploy anything.

`ROADMAP.md` must define the complete programme at a high level, but only as a
roadmap. It must include the planned phases by name and describe their intent
without implementing them.

The roadmap must include these future phases:

- Platform prerequisites.
- Kong OSS baseline.
- Synthetic bank APIs.
- OSS authentication, authorization, and rate limiting.
- Tenancy, RBAC simulation, and change control.
- SSO-protected platform tools.
- Observability, logging, alerting, and dashboards.
- Secrets, certificates, and rotation workflows.
- Regression and failure-mode test suite.
- Day-2 operations and runbooks.

`docs/architecture/platform-principles.md` must define the operating principles
for the platform.

It must include:

- Git as source of truth.
- Kubernetes-first platform model.
- OSS-compatible design.
- Automated validation.
- Auditable change.
- Least privilege.
- Explicit ownership.
- Safe rollback.
- Synthetic but realistic banking scenarios.
- Day-2 operations from the beginning.

`docs/architecture/oss-vs-enterprise.md` must document Kong OSS versus Kong
Enterprise boundaries.

It must include a table with at least these rows:

| Capability | Kong OSS baseline position | Replacement pattern in this lab |
| --- | --- | --- |
| Kong RBAC | Not assumed available | Kubernetes RBAC, Git permissions, CODEOWNERS, policy-as-code |
| Kong Workspaces as governance boundary | Not used as OSS governance boundary | Namespaces, Argo CD projects, repo ownership |
| Kong OIDC plugin | Enterprise-only for this lab | Keycloak SSO for tools, JWT plugin for selected API traffic later |
| Request Validator plugin | Enterprise-only for this lab | OpenAPI linting, contract tests, backend validation |
| MTLS Auth plugin | Enterprise-only for this lab | TLS via cert-manager first; later outer-proxy or custom-plugin experiment if required |
| Developer Portal | Not Kong Enterprise portal | Static docs portal generated from Git |
| Audit logs | Not assumed as Kong Enterprise audit feature | Git PRs, CI logs, Argo CD history, Kubernetes events, evidence reports |

`docs/architecture/operating-model.md` must define the simulated bank personas:

- Platform admin.
- Platform operator.
- API team maintainer.
- Security reviewer.
- Read-only auditor.
- Synthetic external partner.
- Synthetic internal client owner.

It must describe what each persona owns and what they must not be allowed to do.

`docs/architecture/testing-strategy.md` must define the test layers:

- Static validation.
- Documentation validation.
- Policy-as-code tests.
- Unit tests.
- API contract tests.
- Integration tests.
- Negative tests.
- Failure-mode tests.
- Performance baseline tests.
- Evidence reports.

For goal 000, only static, documentation, unit, and placeholder policy tests
need to exist.

### ADRs

Create `docs/adr/adr-template.md` with sections:

- Status.
- Context.
- Decision.
- Consequences.
- Alternatives considered.
- Validation.
- Rollback / revisit criteria.

Create `docs/adr/0001-platform-direction.md`.

It must record these decisions:

- Use Kong OSS as the baseline.
- Use Kubernetes as the runtime.
- Prefer Gateway API and Kong Ingress Controller in later implementation.
- Use GitOps as the configuration model.
- Avoid exposing Kong Admin API as a human control plane.
- Simulate Enterprise governance using Kubernetes, Git, GitOps,
  policy-as-code, and SSO around platform tools.
- Require automated validation and evidence for each future phase.

### Templates

Create `docs/onboarding/api-onboarding-template.md`.

It must require future API onboarding requests to include:

- API name.
- Owning team.
- Business purpose.
- Exposure type: internal, external, partner, or admin.
- Lifecycle state.
- OpenAPI spec path.
- Upstream service.
- Required authentication profile.
- Required authorization profile.
- Expected consumers.
- Rate-limit requirement.
- Logging requirement.
- SLO target.
- Data classification.
- Rollback plan.
- Positive tests.
- Negative tests.
- Observability evidence.
- Support contact.

Create `docs/runbooks/runbook-template.md`.

It must include:

- Purpose.
- Symptoms.
- Severity.
- Affected components.
- Immediate checks.
- Diagnosis steps.
- Mitigation.
- Rollback.
- Validation.
- Communications.
- Evidence to collect.
- Follow-up actions.

Create `apis/api-template/openapi.yaml` as a minimal valid OpenAPI 3.x
placeholder for future API products.

Create `apis/api-template/ownership.yaml` as a placeholder ownership metadata
file.

It must include fields for:

- `api_name`
- `owning_team`
- `exposure`
- `lifecycle_state`
- `data_classification`
- `support_contact`
- `slo_target`
- `auth_profile`
- `rate_limit_profile`

### Validation Tooling

Create a `Makefile` with at least these targets:

- `help`
- `validate`
- `test`
- `policy-test`
- `docs`
- `evidence`
- `clean`

The targets must be local-safe.

`make validate` must run repository foundation checks.

`make test` must run the Python unit tests.

`make policy-test` must run placeholder policy tests or a local-safe fallback
that proves the policy directory and examples are present.

`make docs` must validate or build the MkDocs documentation site.

`make evidence` must generate or refresh `reports/goal-000-summary.md`.

`make clean` must remove generated local artifacts only.

The `Makefile` must not require cluster access.

Create `scripts/validate_repo.py`.

It must verify at minimum:

- Required directories exist.
- Required files exist.
- `README.md` exists.
- `ROADMAP.md` exists.
- `docs/adr/0001-platform-direction.md` exists.
- `docs/architecture/oss-vs-enterprise.md` exists.
- `reports/goal-000-summary.md` exists.
- No obvious plaintext secret files are present by filename pattern.
- No kubeconfig-like files are present by filename pattern.

Create `scripts/generate_evidence_report.py`.

It must update or generate `reports/goal-000-summary.md` with:

- Goal name.
- Date/time generated.
- Validation commands expected.
- Checklist of completed deliverables.
- Known limitations.
- Statement that no cluster deployment was performed.

### Tests

Create `tests/unit/test_repo_foundation.py`.

It must test that required files and directories exist.

Create `tests/policy/test_policy_placeholders.py`.

It must test that policy placeholder files and valid/invalid examples exist.

The tests must run with pytest.

They must not require Kubernetes, Docker, cloud credentials, internet access, or
local secrets.

### CI

Create `.github/workflows/ci.yml`.

It must run on pull requests and pushes.

It must run at least:

- `make validate`
- `make test`
- `make policy-test`
- `make docs`

CI must not require a Kubernetes cluster.

### Pre-commit

Create `.pre-commit-config.yaml`.

It should include safe baseline checks where practical, such as:

- Trailing whitespace.
- End-of-file fixer.
- YAML check.
- JSON check.
- Markdown-related checks if available.

Do not require tools that are not declared or documented.

### CODEOWNERS

Create `CODEOWNERS`.

It must model bank-like ownership.

Use placeholder teams if real GitHub teams are not known.

It must include ownership entries for:

- Platform files.
- Security/policy files.
- Docs.
- APIs.
- Tenants.
- Runbooks.
- CI.

Example placeholder owners are acceptable, such as:

- `@platform-team`
- `@security-team`
- `@api-governance-team`

### Evidence Report

Create `reports/goal-000-summary.md`.

It must include:

- Goal name.
- Objective summary.
- Files and directories created.
- Validation commands.
- Test status placeholders or actual status if commands were run.
- Known limitations.
- Explicit statement that no Kubernetes resources were deployed.
- Explicit statement that no secrets were created.
- Next recommended goal name only as a reference, without implementing it.

## Acceptance Criteria

- The repository contains the required structure.
- All required documentation files exist and contain meaningful content, not
  empty placeholders.
- The OSS versus Enterprise boundary is documented clearly.
- The platform operating model is documented clearly.
- The ADR template exists.
- ADR 0001 exists and records the platform direction.
- The API onboarding template exists.
- The runbook template exists.
- The `Makefile` exists and exposes the required targets.
- The validation script exists and is used by `make validate`.
- The evidence report script exists and is used by `make evidence`.
- The unit tests exist and are runnable with pytest.
- The policy placeholder tests exist and are runnable with pytest.
- The MkDocs configuration exists.
- The CI workflow exists and runs the required make targets.
- The repo does not contain real secrets.
- The repo does not contain kubeconfig files.
- The repo does not contain any manifest that deploys Kong or other platform
  components.
- The repo does not require a Kubernetes cluster for this goal.
- The repo does not assume Kong Enterprise features are available.
- The evidence report for goal 000 exists.
- All validation commands listed below pass locally.

## Validation Commands

Run these commands from the repository root.

```bash
make validate
```

Expected result: repository structure and safety checks pass.

```bash
make test
```

Expected result: unit tests pass.

```bash
make policy-test
```

Expected result: policy placeholder tests pass.

```bash
make docs
```

Expected result: documentation validates or builds successfully.

```bash
make evidence
```

Expected result: `reports/goal-000-summary.md` is generated or refreshed.

Run the full local gate:

```bash
make validate && make test && make policy-test && make docs && make evidence
```

Expected result: all commands complete successfully without Kubernetes access.

## Evidence Report

Update `reports/goal-000-summary.md` before stopping.

The report must contain:

```text
Goal: goal-000-repo-foundation
Status:
Generated at:
Validation commands run:
Results:
Created/updated files:
Known limitations:
Cluster changes performed: none
Secrets created: none
Enterprise Kong features used: none
Ready for next goal:
```

If any validation command could not be run, record:

- The command.
- Why it could not be run.
- What was done instead.
- What the user must run locally.

Do not claim validation succeeded unless the command was actually run
successfully.

## Stop Condition

Stop after the repository foundation is complete, the required validation
commands have been run where possible, and `reports/goal-000-summary.md` has
been created or updated.

Do not proceed to platform prerequisites.

Do not install anything in the cluster.

Do not add Kong manifests beyond placeholder documentation.

Do not implement later goals.

Do not continue past this foundation phase.

