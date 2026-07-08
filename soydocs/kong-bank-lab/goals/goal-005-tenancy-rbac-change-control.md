# Goal: goal-005-tenancy-rbac-change-control

## Approval Source

ChatGPT Pro approved `goal-004-auth-rate-limit-security` and issued this goal
body in the Kong project chat after reviewing goal004 runtime evidence.

## Objective

Implement a small but bank-like tenancy, RBAC, ownership, and change-control
model for the Kong platform.

Move from "secure APIs exist" to "a platform team can safely delegate API
ownership to simulated tenant teams while retaining governance."

Because the lab uses Kong OSS, do not use Kong Enterprise Workspaces or Kong
Enterprise RBAC unless explicitly enabled later. Simulate bank-style tenancy
using Kubernetes namespaces, Kubernetes RBAC, catalog metadata, Git-owned
ownership records, policy checks, and runtime impersonation tests.

## Completion Criteria

The goal is complete only when runtime cluster evidence proves:

- Tenant ownership exists for all six synthetic APIs.
- Each API has owning team, exposure classification, data classification,
  allowed plugin set, support/runbook metadata.
- Kubernetes RBAC service accounts exist for simulated tenant teams.
- Tenant service accounts can operate only within their allowed scope.
- Tenant service accounts cannot access other tenants, platform secrets,
  cluster-scoped Kong resources, network policies, Kong Admin exposure
  resources, or credential secrets.
- A normal governed API change can be applied, smoked, and rolled back.
- Goal004 security behavior remains intact after goal005.

## Default Platform Model

- Platform owner: `kong-platform`
- Simulated tenant teams:
  - `retail-accounts`
  - `payments`
  - `risk-compliance`
- Map the existing six synthetic APIs across those three tenants.
- Do not invent a seventh API.
- Do not remove or rename existing APIs.
- Use the exact API IDs from the current synthetic API manifests/catalog.
- Use "workspace" only as a logical platform concept in docs/catalog, not as a
  Kong Enterprise Workspace.

## Constraints

- Use Kong OSS-compatible patterns only.
- Do not require Kong Enterprise, Konnect, Kong Manager, Enterprise RBAC,
  Enterprise Workspaces, or Enterprise Dev Portal.
- Do not expose Kong Admin API.
- Do not print, commit, snapshot, or report credential values.
- Do not weaken or bypass goal004 controls: auth, ACL, JWT, route boundary
  protections, Redis rate limits, network policies, and admin exposure tests
  must continue to pass.
- Do not add a new validation-only gate. This goal must create runtime-applied
  manifests, runtime RBAC evidence, a real governed change, and rollback
  evidence.
- Use Git as the source of truth. Any runtime-applied resource must be backed by
  committed manifests or generated from committed scripts/templates.
- Keep the implementation small enough for the three-node M920q lab.
- Prefer simple Kubernetes RBAC and catalog checks over heavyweight policy
  infrastructure.
- Do not introduce cert-manager, Vault, Argo CD, Backstage, OPA Gatekeeper,
  Kyverno, or portal products unless already in the repo and already used by
  prior goals.
- All new tests and scripts must be deterministic and safe to repeat.

## Required Files

### Catalog

`platform/catalog/tenants.yaml`

Fields per tenant:

- `tenant_id`
- `display_name`
- `logical_workspace`
- `namespace`
- `owned_api_ids`
- `allowed_exposure`
- `allowed_plugins`
- `data_classifications_allowed`
- `support_contact`
- `reviewers`
- `break_glass_contact`
- `change_approval_group`

`platform/catalog/api-products/<api-id>.yaml`

One file per existing synthetic API, all six. Required fields:

- `api_id`
- `display_name`
- `tenant_id`
- `namespace`
- `logical_workspace`
- `exposure`
- `data_classification`
- `authn_model`
- `authz_model`
- `kong_service_name`
- `kong_route_names`
- `required_plugins`
- `optional_tenant_plugins`
- `credential_owner`
- `slo`
- `runbook`
- `docs_owner`
- `lifecycle_state`

`exposure` must be `internal` or `external`. `data_classification` must be
`internal`, `confidential`, or `restricted`. `credential_owner` must be
`platform`, not tenant-owned.

### Change Control

`platform/change-control/change-classes.yaml`

Define classes:

- `standard`
- `normal`
- `emergency`
- `security`

Each class must define required approver type, minimum evidence, rollback
requirement, whether runtime smoke is mandatory, whether security review is
mandatory, and whether tenant self-service is allowed.

`platform/change-control/sample-changes/goal-005-normal-change.yaml`

The sample normal change request must be low-risk and tenant-owned. The default
sample change adds a temporary response header to one API route:

```text
X-Goal005-Change-Id: goal-005-normal-change
```

The change must be applied through a committed KongPlugin/Kubernetes manifest,
not a manual Admin API mutation. It must include change ID, tenant ID, API ID,
change class, reason, affected resources, expected runtime evidence, rollback
command, and approver placeholders.

### Runtime Overlays

`kubernetes/goal-005-tenancy-rbac/kustomization.yaml`

Runtime overlay for goal005 tenancy/RBAC resources.

`kubernetes/goal-005-tenancy-rbac/namespaces.yaml`

Create tenant namespaces only if not already present. If existing synthetic APIs
already use namespaces, do not move workloads unnecessarily. Catalog namespace
values must match runtime reality.

`kubernetes/goal-005-tenancy-rbac/serviceaccounts.yaml`

Create one service account per tenant:

- `retail-accounts-api-applier`
- `payments-api-applier`
- `risk-compliance-api-applier`

Create one platform service account:

- `kong-platform-change-applier`

`kubernetes/goal-005-tenancy-rbac/roles.yaml`

Tenant applier roles may manage namespaced tenant-owned API configuration
resources in the tenant's own namespace only. Minimal allowed namespaced
resources may include `services`, `ingresses` or `httproutes` depending on the
existing implementation, and `kongplugins.configuration.konghq.com` or
`kongconsumers.configuration.konghq.com` only if already tenant-scoped in the
existing design.

Do not grant tenant appliers access to credential Secrets, NetworkPolicies,
ClusterRoles, ClusterRoleBindings, KongClusterPlugins, CRDs, webhooks, gateway
controller resources, Kong Admin resources, or other tenant namespaces.

`kubernetes/goal-005-tenancy-rbac/rolebindings.yaml`

Bind tenant service accounts to their own tenant Roles only. Bind the platform
service account to the minimum platform role required for the goal005 apply
workflow.

`kubernetes/goal-005-tenancy-rbac/owner-labels-and-annotations.yaml`

Add or patch ownership labels/annotations onto Kong-facing resources where
practical.

Required labels or annotations:

- `platform.soyspray.io/tenant`
- `platform.soyspray.io/api-id`
- `platform.soyspray.io/logical-workspace`
- `platform.soyspray.io/exposure`
- `platform.soyspray.io/data-classification`
- `platform.soyspray.io/managed-by: gitops`
- `platform.soyspray.io/change-class`
- `platform.soyspray.io/runbook`

Use labels where Kubernetes-selector-safe. Use annotations for longer values.

`kubernetes/goal-005-change/normal-change/kustomization.yaml`

Overlay for the sample normal change. It must apply one temporary, observable
Kong configuration change to one tenant-owned API.

Default implementation: a Kong `response-transformer` plugin adding:

```text
X-Goal005-Change-Id: goal-005-normal-change
```

The plugin must be scoped to the chosen API, route, or service, not global.

`kubernetes/goal-005-change/rollback/kustomization.yaml`

Rollback overlay or delete manifest for the sample change. It must remove only
the goal005 sample change resources and leave stable goal005 tenancy/RBAC
resources in place.

## Required Scripts

`scripts/goal005_tenancy_config.py`

Shared goal005 tenancy, catalog, RBAC, and sample-change model.

`scripts/render_goal005_tenancy_rbac.py`

Render the stable goal005 tenancy/RBAC resources.

`scripts/render_goal005_change.py`

Render the sample normal change resources.

`scripts/validate_goal005_tenancy_catalog.py`

Validate tenant and API product catalog consistency. It must fail if:

- an API product references an unknown tenant
- a tenant references an unknown API
- an API is missing from the catalog
- an API is owned by more than one tenant
- a tenant requests a plugin outside its allowlist
- an external API lacks explicit exposure classification
- a restricted/confidential API lacks a runbook
- credential ownership is anything other than `platform`

`scripts/validate_rendered_ownership.py`

Validate rendered Kubernetes/Kong manifests. It must fail if:

- Kong-facing resources lack ownership metadata
- a tenant resource references another tenant namespace
- a tenant resource references credential Secrets
- a tenant manifest creates or modifies KongClusterPlugin
- a tenant manifest creates or modifies NetworkPolicy
- a tenant manifest creates or modifies Admin API exposure
- a wildcard host or unsafe catch-all route is introduced without platform
  ownership

`scripts/goal005/rbac_smoke.sh`

Run runtime RBAC impersonation checks using `kubectl auth can-i`. It must check
both allowed and denied cases.

Required positive checks:

- Each tenant service account can read allowed API configuration resources in
  its own namespace.
- Each tenant service account can server-side dry-run apply an allowed
  tenant-owned namespaced KongPlugin or equivalent safe namespaced API config in
  its own namespace.
- The platform service account can read the tenant catalog ConfigMap or
  goal005-applied resources if such a resource is created.

Required negative checks:

- Each tenant service account cannot get/list Secrets in its namespace.
- Each tenant service account cannot get/list Secrets in any other tenant
  namespace.
- Each tenant service account cannot create or patch NetworkPolicy.
- Each tenant service account cannot create KongClusterPlugin.
- Each tenant service account cannot modify ClusterRole or ClusterRoleBinding.
- Each tenant service account cannot modify webhook configuration.
- Each tenant service account cannot access another tenant namespace's
  KongPlugin, Service, Ingress, HTTPRoute, or KongConsumer.
- Each tenant service account cannot access Kong Admin exposure resources.
- Any unexpected allow must fail the script.

`scripts/goal005/change_apply_smoke.sh`

Apply the sample normal change and prove the selected API returns:

- HTTP 200 for a valid request
- the original goal004 marker/header behavior
- the original correlation ID behavior
- the original rate-limit headers where applicable
- `X-Goal005-Change-Id: goal-005-normal-change`

`scripts/goal005/change_rollback_smoke.sh`

Roll back the sample normal change and prove:

- the selected API still returns HTTP 200 for a valid request
- the original goal004 marker/header behavior remains
- the `X-Goal005-Change-Id` header is absent
- goal004 authentication and authorization still behave correctly

`scripts/goal005/runtime_ready.sh`

Run the full runtime acceptance sequence for goal005.

## Required Tests

`tests/goal005/test_tenancy_catalog.py`

Minimum tests:

- all six APIs are present
- tenant IDs are unique
- each API has exactly one tenant
- each tenant owns at least one API
- required fields are present
- plugin allowlists are enforced
- credential ownership is platform-only
- exposure values are valid
- data classification values are valid
- runbook references are present

`tests/goal005/test_change_control.py`

Minimum tests:

- all required change classes exist
- normal changes require rollback
- security changes require security review
- emergency changes require retrospective evidence
- sample change references a known tenant
- sample change references a known API
- sample change has rollback command
- sample change evidence contract is complete

`tests/goal005/test_rendered_ownership.py`

Minimum tests:

- goal005 tenancy overlay renders
- goal005 normal-change overlay renders
- goal005 rollback overlay renders
- Kong-facing resources include ownership metadata
- tenant resources are namespaced
- tenant resources do not include credential Secret values
- tenant resources do not create KongClusterPlugin
- tenant resources do not expose Kong Admin
- tenant resources do not create NetworkPolicy
- sample change is route/service/API scoped, not global

## Required Docs

`docs/platform/tenancy-model.md`

Describe the simulated bank platform ownership model, including platform team
responsibilities, tenant team responsibilities, logical workspace model, why
Kubernetes namespaces/RBAC are used instead of Kong Enterprise
Workspaces/RBAC, how API products map to tenants, how credentials remain
platform-owned, and what tenant teams are allowed and not allowed to change.

`docs/platform/change-control.md`

Describe the GitOps change-control workflow, including standard, normal,
emergency, and security change paths; required evidence per change class;
rollback expectations; approval expectations; audit trail expectations; and
how the sample goal005 change proves the model.

`docs/platform/api-product-onboarding.md`

Document how a new API product would be onboarded after goal005, including
catalog entry, owner assignment, exposure classification, data classification,
authn/authz choice, plugin request, review flow, runtime smoke, and rollback.

`docs/runbooks/goal-005-rbac-failure.md`

Runbook for an RBAC failure. It must include symptoms, likely causes, how to
identify the unexpected permission, how to roll back the offending
Role/RoleBinding, and how to prove tenant isolation is restored.

`docs/runbooks/goal-005-change-rollback.md`

Runbook for rolling back the sample change.

`docs/decisions/goal-005-tenancy-rbac-change-control.md`

Architecture decision record. It must include `Status:
accepted-for-implementation`, context, decision, consequences, Kong OSS
limitation, Kubernetes RBAC simulation approach, risks, and follow-up
candidates for later goals.

## Required Reports

- `reports/goal-005-summary.md`: generated evidence summary.
- `reports/goal-005-rbac-runtime.md`: generated RBAC runtime evidence.
- `reports/goal-005-change-rollout.md`: generated sample change rollout
  evidence.
- `reports/goal-005-change-rollback.md`: generated sample change rollback
  evidence.
- `docs/decisions/goal-005-runtime-approval.md`: generated or manually updated
  after evidence. Before approval, status should be `pending approval`; after
  review, it can be changed to approved.

## Required Makefile Targets

Add:

- `validate-goal005-tenancy`
- `render-goal005-tenancy-rbac`
- `render-goal005-change`
- `goal005-static-test`
- `goal005-contract-test`
- `goal005-tenancy-rbac-apply`
- `goal005-rbac-smoke`
- `goal005-change-apply-and-smoke`
- `goal005-change-rollback-and-smoke`
- `goal005-runtime-ready`
- `evidence-goal-005`

Update aggregate targets where appropriate:

- `validate`
- `test`
- `docs`

Do not remove or weaken existing goal003 or goal004 targets.

## Required Local Tests

From repo root:

```sh
make validate
make validate-yaml
make validate-kustomize
make validate-synthetic-apis
make validate-goal004-security
make validate-goal005-tenancy
make openapi-lint
make render-synthetic-apis
make render-goal004-security
make render-goal005-tenancy-rbac
make render-goal005-change
make goal004-static-test
make goal004-contract-test
make goal005-static-test
make goal005-contract-test
make test
make policy-test
make docs
make evidence-goal-005
```

Expected local evidence:

- All existing goal003 and goal004 validation remains green.
- Goal005 catalog tests pass.
- Goal005 rendered ownership tests pass.
- Goal005 change-control tests pass.
- Rendered manifests contain no Secret values.
- Rendered manifests do not expose Kong Admin.
- Rendered manifests do not create tenant-owned KongClusterPlugins.
- Rendered manifests do not grant tenant service accounts cross-tenant access.
- Rendered sample change is scoped to one selected API, route, or service.

## Required Runtime Commands

Run from repo root with current context:

```sh
kubectl config current-context
```

Expected:

```text
kubernetes-admin@cluster.local
```

Then run:

```sh
make synthetic-api-security-apply-and-smoke
make goal005-tenancy-rbac-apply
make goal005-rbac-smoke
make goal005-change-apply-and-smoke
make goal005-change-rollback-and-smoke
make goal005-runtime-ready
make evidence-goal-005
```

`make goal005-tenancy-rbac-apply` must apply the stable tenancy and RBAC
resources.

`make goal005-rbac-smoke` must produce explicit PASS/FAIL output for every
positive and negative impersonation check.

`make goal005-change-apply-and-smoke` must apply the sample normal change and
prove the selected API returns the temporary `X-Goal005-Change-Id` header.

`make goal005-change-rollback-and-smoke` must remove the sample change and prove
the selected API no longer returns the temporary header while still passing
normal goal004 positive smoke.

`make goal005-runtime-ready` must run the complete goal005 runtime acceptance
sequence, including the prior goal004 security smoke or an equivalent
dependency check.

## Runtime Evidence Contract

In `reports/goal-005-summary.md`, include:

- commit SHA
- branch name
- cluster context
- date/time
- list of six API products and owning tenants
- list of tenant namespaces
- list of tenant service accounts
- summary of local test results
- summary of runtime test results
- explicit statement that no credential values were printed or committed
- explicit statement that Kong Admin API exposure remained safe

In `reports/goal-005-rbac-runtime.md`, include a table of `kubectl auth can-i`
checks with:

- actor
- namespace
- verb
- resource
- expected result
- actual result
- PASS/FAIL

Include at minimum:

- own-namespace allowed checks
- cross-tenant denied checks
- Secret denied checks
- NetworkPolicy denied checks
- KongClusterPlugin denied checks
- ClusterRole/ClusterRoleBinding denied checks
- webhook denied checks
- Kong Admin exposure denied checks

In `reports/goal-005-change-rollout.md`, include:

- sample change ID
- tenant
- API
- route/service affected
- manifest applied
- HTTP smoke result
- observed temporary header
- goal004 marker/header preservation
- auth preservation
- rate-limit header preservation where applicable

In `reports/goal-005-change-rollback.md`, include:

- rollback command
- resources removed or reverted
- HTTP smoke result after rollback
- confirmation that temporary header is absent
- confirmation that goal004 security behavior still passes

In `docs/decisions/goal-005-runtime-approval.md`, include:

- `Status: pending approval`
- summary
- evidence links
- known issues
- rollback notes
- ready-for-approval statement

## Approval Gate

Goal005 can be approved only if all of the following are true:

- All required local tests pass.
- All required runtime commands pass.
- All six synthetic APIs are represented in the API product catalog.
- Every API product has exactly one tenant owner.
- Tenant RBAC is applied in the cluster.
- Runtime impersonation proves tenants are isolated from each other.
- Runtime impersonation proves tenants cannot read or modify credential
  Secrets.
- Runtime impersonation proves tenants cannot create or modify
  KongClusterPlugin, NetworkPolicy, ClusterRole, ClusterRoleBinding, webhook
  configuration, or Kong Admin exposure resources.
- The sample normal change is applied through committed manifests.
- The sample normal change is observable at runtime.
- The sample normal change is rolled back successfully.
- Goal004 positive smoke still passes after rollback.
- Goal004 negative auth behavior still passes after rollback.
- Goal004 Redis rate-limit behavior still passes after rollback.
- No credentials are printed, committed, or written into evidence reports.
- Kong Admin API remains unexposed.
- Evidence reports are committed.
- The branch is pushed.

## Stop Condition

Stop after goal005 evidence is complete, committed, and pushed.

Do not start goal006.

Do not introduce a separate validation-only gate.

If any tenant service account is unexpectedly allowed to access another tenant,
Secrets, cluster-scoped controls, NetworkPolicies, webhook configuration, or
Kong Admin exposure resources, stop, roll back the offending RBAC change, and
report goal005 as not ready.

If the sample change cannot be rolled back cleanly, stop and report goal005 as
not ready.

If any goal004 security behavior regresses, stop, roll back goal005 runtime
changes if needed, and report goal005 as not ready.

If credentials appear in logs, rendered manifests, reports, or commits, stop
and report goal005 as not ready.
