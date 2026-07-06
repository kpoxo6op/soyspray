# goal-002-kong-oss-baseline

Source: requested from ChatGPT Pro on 2026-07-06 after reporting the completed
`goal-001-platform-prereqs` implementation and asking for feedback plus the next
goal with corrections folded into goal 002.

## Goal 001 Feedback/Approval Status

Goal 001 is approved to proceed based on the reported evidence.

The reported local gate passed:

```bash
make validate && make validate-yaml && make validate-kustomize && make validate-prereqs && make test && make policy-test && make docs && make evidence-goal-001
```

Goal 001 correctly stayed before Kong installation:

```text
Cluster changes performed: none
Secrets created: none; only non-deployable examples/placeholders
Kong resources created: none
Enterprise Kong features used: none
```

Goal 001 created the required prerequisite structure for namespaces, GitOps
app-of-apps, Argo CD project templates, MetalLB examples, cert-manager examples,
SOPS/age examples, NetworkPolicy baseline, bootstrap scripts, validation
scripts, tests, CI targets, and evidence.

Goal 001 is accepted as the foundation for goal 002, subject to the
carry-forward corrections below.

## Corrections That Must Be Carried Into Goal 002

Before implementing the Kong baseline, verify and preserve the goal 001 state.

Required carry-forward checks and corrections:

- Re-run the goal 001 local gate before making Kong changes, or run the
  equivalent current full local validation gate if the Makefile has changed.
- Confirm that goal 001 evidence remains historically accurate at
  `reports/goal-001-summary.md`. Do not overwrite it. Create a new goal 002
  evidence report instead.
- Confirm that Booklore and Immich default/plain DB secret values remain
  explicit non-secret placeholders.
- Confirm that `CHANGE_ME_WITH_NON_REPO_SECRET` remains treated as a
  non-deployable placeholder, not as a valid deployable secret value.
- Confirm that repo-wide validation still rejects obvious plaintext/default
  secret markers, kubeconfig-like content, private keys, bearer tokens, API
  tokens, and deployable default credentials.
- Confirm that Kubespray submodule example exclusions remain narrow and
  intentional.
- Confirm that CI remains cluster-free. Do not add cluster-mutating checks to
  pull-request CI.
- Confirm that all goal 001 prerequisite manifests are still before-Kong-safe
  and that no Kong resources were accidentally added before goal 002.
- Confirm that Argo CD app-of-apps templates using placeholder repo URLs are
  still clearly non-production until replaced with a real repository URL.
- Confirm that MetalLB address-pool examples remain clearly example-only or
  environment-specific.
- Confirm that cert-manager examples do not contain committed private keys or
  real CA material.
- Confirm that SOPS/age examples do not contain a committed age private key.
- Confirm that NetworkPolicy baseline documentation states whether enforcement
  depends on the cluster CNI.
- If goal 001 optional cluster checks are still not run, record that in goal 002
  evidence. Goal 002 may still implement the Kong baseline locally, but cluster
  readiness must be explicitly reported as pending until the cluster smoke
  checks are run.
- If a Kubernetes context is available and the user explicitly permits cluster
  checks, run the cluster-aware prerequisite smoke checks before attempting a
  Kong install.

## Objective

Implement the baseline Kong OSS installation layer for the bank-lab platform.

This goal must add the first Kong runtime layer on top of the prerequisite
foundation from goal 001.

The baseline must use:

- Kong OSS.
- Kubernetes.
- Kong Ingress Controller.
- Gateway API as the preferred routing interface.
- DB-less Kong Gateway.
- Helm/GitOps-friendly installation manifests.
- Separate internal and external Gateway API entrypoints.
- Private/non-external Kong Admin API exposure.
- A minimal smoke backend for automated route validation.
- Automated positive and negative smoke tests.
- Local validation that does not require a cluster.
- Optional cluster validation that proves the deployment works when applied.

The intended implementation uses Kong Ingress Controller because KIC translates
Kubernetes Ingress and HTTPRoute resources into Kong Gateway configuration, and
Kong's Helm chart documentation describes `kong/ingress` as an opinionated
DB-less KIC-managed installation path.

The default Kong Gateway OSS image pin for this goal is:

```text
kong:3.9.3
```

The default Kong Ingress Controller line for this goal should be a pinned
supported 3.5.x release where compatible with the selected Helm chart.

The goal is complete only when the repository contains a testable Kong OSS
baseline and the evidence report records whether cluster deployment was
performed and whether smoke tests passed.

## Non-Goals

- Do not implement synthetic banking APIs yet.
- Do not implement accounts, payments, cards, customer profile, fraud, or
  open-banking APIs.
- Do not create real API consumers.
- Do not create API keys.
- Do not configure Key Auth, JWT auth, ACL, rate limiting, Redis, SSO, Keycloak,
  mTLS, production TLS certificates, Prometheus, Grafana, Loki, or Alertmanager.
- Do not use Kong Enterprise, Konnect, Enterprise RBAC, Enterprise Workspaces,
  Enterprise OpenID Connect, Enterprise Request Validator, Enterprise MTLS Auth,
  Enterprise Developer Portal, or Kong Manager as the platform control plane.
- Do not expose Kong Admin API externally.
- Do not make Kong Admin API a human configuration interface.
- Do not use Kong Admin API as the source of truth.
- Do not add custom Kong plugins.
- Do not build a custom Kong image.
- Do not add performance testing beyond a minimal smoke-level request check.
- Do not add day-2 incident drills yet.
- Do not make CI require a Kubernetes cluster.
- Do not run cluster-mutating commands unless the user explicitly permits
  cluster changes in the local environment.

## Constraints

- Kong must be OSS-compatible.
- Use the `kong` OSS image, not an Enterprise-only image.
- Do not use latest image tags.
- Do not use unpinned Helm chart versions.
- Do not use unpinned controller image tags.
- Do not use unpinned Gateway API CRD versions.
- Do not commit real secrets, kubeconfigs, TLS private keys, SOPS age private
  keys, generated service-account tokens, API keys, or passwords.
- The baseline must be DB-less.
- Do not introduce PostgreSQL for Kong in this goal.
- Kong Admin API must not be externally exposed.
- Kong proxy may be exposed through a Kubernetes LoadBalancer Service intended
  for MetalLB, but this must be documented and testable.
- The installation must be GitOps-friendly.
- All Kong configuration must be represented declaratively.
- All local validation must run without a Kubernetes cluster.
- Cluster validation commands must be explicit and opt-in.
- CI must remain cluster-free.
- The minimal smoke backend must be clearly labelled as a platform smoke
  service, not as a synthetic bank business API.
- The smoke backend must use a pinned image tag.
- The smoke route must be disposable and must not become part of the future API
  product model.
- The baseline must support separate internal and external Gateway API
  entrypoints even if both initially use the same Kong deployment.
- The internal and external entrypoints must use distinct hostnames.
- Use lab hostnames such as `kong-smoke.external.banklab.test`,
  `kong-smoke.internal.banklab.test`, `api.external.banklab.test`, and
  `api.internal.banklab.test`.
- Do not assume public DNS exists.
- Route smoke tests may use Host headers, `curl --resolve`, or port-forwarding.
- If MetalLB is not applied, the route smoke test must provide a port-forward
  fallback.
- If Gateway API CRDs are not installed, cluster smoke checks must report that
  clearly.
- If the cluster cannot be reached, local implementation may still pass, but the
  evidence report must state that cluster verification is pending.
- Do not claim Kong is installed unless cluster apply and cluster smoke tests
  actually ran successfully.

## Required Files

Create or update the following files.

```text
platform/kong/README.md
platform/kong/versions.yaml
platform/kong/namespace.yaml
platform/kong/kustomization.yaml
platform/kong/helm/README.md
platform/kong/helm/values-kong-oss-baseline.yaml
platform/kong/helm/values-kong-oss-baseline.schema.yaml
platform/kong/helm/render-kong-baseline.sh
platform/kong/gateway-api/README.md
platform/kong/gateway-api/kustomization.yaml
platform/kong/gateway-api/gateway-api-crds.README.md
platform/kong/gateway-api/gatewayclass-kong.yaml
platform/kong/gateway-api/gateway-external.yaml
platform/kong/gateway-api/gateway-internal.yaml
platform/kong/network-policies/README.md
platform/kong/network-policies/kustomization.yaml
platform/kong/network-policies/kong-default-deny.yaml
platform/kong/network-policies/kong-allow-dns.yaml
platform/kong/network-policies/kong-allow-kube-api-placeholder.yaml
platform/kong/network-policies/kong-allow-proxy-ingress.yaml
platform/kong/network-policies/kong-allow-smoke-upstream.yaml
platform/kong/smoke/README.md
platform/kong/smoke/kustomization.yaml
platform/kong/smoke/namespace.yaml
platform/kong/smoke/deployment.yaml
platform/kong/smoke/service.yaml
platform/kong/smoke/httproute-external.yaml
platform/kong/smoke/httproute-internal.yaml
platform/kong/argocd/README.md
platform/kong/argocd/kong-baseline-app.yaml
platform/kong/argocd/kong-gateway-api-app.yaml
platform/kong/argocd/kong-smoke-app.yaml
platform/kong/scripts/README.md
platform/kong/scripts/check-kong-baseline.sh
platform/kong/scripts/check-admin-not-exposed.sh
platform/kong/scripts/route-smoke.sh
platform/kong/scripts/render-and-lint-kong.sh
platform/gitops/app-of-apps/kong-baseline-app.yaml
docs/architecture/kong-oss-baseline.md
docs/architecture/gateway-api-baseline.md
docs/architecture/kong-admin-api-exposure.md
docs/architecture/kong-baseline-testing.md
docs/runbooks/kong-baseline-install.md
docs/runbooks/kong-baseline-rollback.md
docs/runbooks/kong-admin-api-exposure-check.md
tests/unit/test_goal_002_kong_structure.py
tests/unit/test_goal_002_kong_versions.py
tests/unit/test_goal_002_no_enterprise_features.py
tests/unit/test_goal_002_admin_api_private.py
tests/policy/test_goal_002_kong_policy.py
tests/policy/test_goal_002_no_forbidden_kong_resources.py
scripts/validate_kong_baseline.py
scripts/render_kong_baseline.py
scripts/check_kong_cluster.py
reports/goal-002-summary.md
```

Small path adjustments are allowed if the existing repository conventions from
goals 000 and 001 require them, but the resulting structure must remain clear
and documented.

Do not remove goal 000 or goal 001 files.

Do not overwrite goal 000 or goal 001 evidence.

## Deliverables

### Version Lock

Create `platform/kong/versions.yaml`.

It must record the exact versions used by the baseline and include at minimum:

```yaml
kong_gateway:
  image_repository: kong
  image_tag: "3.9.3"
  mode: dbless
  enterprise_enabled: false

kong_ingress_controller:
  image_repository: kong/kubernetes-ingress-controller
  image_tag: "REPLACE_WITH_PINNED_SUPPORTED_3_5_X_TAG"

helm:
  chart_name: kong/ingress
  chart_version: "REPLACE_WITH_PINNED_KONG_INGRESS_CHART_VERSION"
  repository: https://charts.konghq.com

gateway_api:
  channel: standard
  version: "v1.3.0"

deployment:
  namespace: platform-kong
  proxy_service_type: LoadBalancer
  admin_api_external_exposure: false
```

If Codex can determine a compatible pinned KIC tag, Helm chart version, and
Gateway API standard-channel version from existing repo context or available
tooling, replace the placeholders.

Correction from ChatGPT Pro review: for KIC `3.5.x`, use Gateway API `v1.3.0`
unless a newer Kong compatibility source is added and cited.

If Codex cannot verify compatibility, leave the placeholders in place, mark
cluster installation as blocked, and complete only the local repo
implementation. Do not invent unverified versions.

The validation script must fail cluster-install readiness if required version
placeholders remain. The validation script may allow local structure validation
to pass with placeholders only if the evidence report states that cluster
installation is blocked pending version pinning.

Do not use `latest`.

### Kong Namespace

Add a dedicated `platform-kong` namespace with standard bank-lab labels:

```yaml
banklab.konghq.com/managed-by: gitops
banklab.konghq.com/platform-layer: gateway
banklab.konghq.com/environment: lab
banklab.konghq.com/data-classification: synthetic
banklab.konghq.com/owner: platform-team
```

Update namespace documentation to explain why Kong has a dedicated platform
namespace.

### Helm Values For Kong OSS Baseline

Create `platform/kong/helm/values-kong-oss-baseline.yaml`.

The values must configure a DB-less Kong OSS baseline and enforce or clearly
express:

```yaml
enterprise:
  enabled: false
image:
  repository: kong
  tag: "3.9.3"
```

The baseline must:

- Use DB-less mode.
- Not enable PostgreSQL.
- Not configure a database password.
- Not enable Enterprise-only features.
- Not enable Kong Manager as the platform control plane.
- Not enable Kong Portal.
- Not expose the Admin API externally.
- Expose the proxy through a LoadBalancer Service intended for MetalLB.
- Set resource requests and limits for Kong Gateway and KIC.
- Start with two Kong Gateway replicas unless the chart structure makes that
  impractical. If two replicas are not configured, document why.
- Include practical scheduling hardening such as labels, probes, rolling update
  strategy, pod disruption budget, anti-affinity, or topology spread where the
  chart supports them.
- Use stdout/stderr logging.
- Enable a status or metrics endpoint if supported by the OSS chart without
  installing Prometheus.

Do not configure business, authentication, or rate-limiting plugins in this
goal.

### Render Support

Create:

```text
platform/kong/helm/render-kong-baseline.sh
scripts/render_kong_baseline.py
```

These must render or validate the Kong Helm baseline without applying it.

The render command must not mutate the cluster. It may require Helm for full
rendering. If Helm is not installed, it must fail clearly with an actionable
message. It must not download charts during CI unless the repository already
has a safe and documented dependency workflow. If chart rendering requires
internet access, document that and keep CI local-safe.

### Gateway API Baseline

Create:

```text
platform/kong/gateway-api/gatewayclass-kong.yaml
platform/kong/gateway-api/gateway-external.yaml
platform/kong/gateway-api/gateway-internal.yaml
```

The GatewayClass must reference Kong as the controller.

The exact controller name must match the selected KIC version and chart
configuration.

The external Gateway must use hostnames such as:

```text
api.external.banklab.test
kong-smoke.external.banklab.test
```

The internal Gateway must use hostnames such as:

```text
api.internal.banklab.test
kong-smoke.internal.banklab.test
```

The Gateways must use HTTPRoute as the baseline route type.

TLS may be documented and prepared but must not depend on real certificates in
this goal. The default baseline may use HTTP listeners for smoke testing, with
documentation stating that TLS hardening is deferred to a later
certificate/rotation goal unless cert-manager is already installed and
configured.

The Gateway API README must explain GatewayClass ownership, internal versus
external Gateway intent, route attachment boundaries, why Gateway API is
preferred over raw Kong Admin API, how this maps to future tenant onboarding,
and what is deliberately deferred.

### Minimal Smoke Backend

Create a minimal smoke backend that is not a synthetic bank API.

Required files:

```text
platform/kong/smoke/namespace.yaml
platform/kong/smoke/deployment.yaml
platform/kong/smoke/service.yaml
platform/kong/smoke/httproute-external.yaml
platform/kong/smoke/httproute-internal.yaml
```

The smoke namespace may be `platform-kong-smoke` or another clearly
platform-owned smoke namespace. It must include standard labels.

The smoke Deployment must use a pinned image tag. Do not use `latest`.

The smoke service must expose a simple HTTP endpoint.

The smoke HTTPRoute resources must attach to the internal and external Gateway
resources.

The smoke hostnames must be:

```text
kong-smoke.external.banklab.test
kong-smoke.internal.banklab.test
```

or a consistent equivalent documented in the README.

The smoke route must be used only to prove the gateway baseline works. Do not
model it as a business API.

### Admin API Exposure Control

Create:

```text
docs/architecture/kong-admin-api-exposure.md
docs/runbooks/kong-admin-api-exposure-check.md
platform/kong/scripts/check-admin-not-exposed.sh
```

These must define and test the rule:

```text
Kong Admin API must not be externally reachable.
```

Static validation must check rendered or source manifests for:

- Admin service type must not be LoadBalancer.
- Admin service type must not be NodePort.
- Admin ports must not be exposed through the proxy service.
- Ingress/Gateway/HTTPRoute must not route to the Admin API.
- Admin API must not be documented as a human control plane.

If the chart creates an Admin API service, it must be ClusterIP only or
otherwise private to the cluster.

If the chart can disable the Admin API service while still allowing KIC to
operate safely, prefer disabling external service exposure and document the
internal control-plane path.

### NetworkPolicy For Kong Baseline

Create:

```text
platform/kong/network-policies/kong-default-deny.yaml
platform/kong/network-policies/kong-allow-dns.yaml
platform/kong/network-policies/kong-allow-kube-api-placeholder.yaml
platform/kong/network-policies/kong-allow-proxy-ingress.yaml
platform/kong/network-policies/kong-allow-smoke-upstream.yaml
```

The policies must be conservative and documented.

If the cluster CNI is not known to enforce NetworkPolicy, the README must state
that enforcement must be tested.

Do not create overly broad tenant access or business API allow rules yet.

The Kong NetworkPolicy README must explain how Kong receives ingress traffic,
how Kong reaches the smoke upstream, how KIC reaches the Kubernetes API server,
why API server egress may require environment-specific CIDRs, how to recover if
a policy blocks traffic, and which policies are safe examples versus required
baseline policies.

### Argo CD Integration

Create:

```text
platform/kong/argocd/kong-baseline-app.yaml
platform/kong/argocd/kong-gateway-api-app.yaml
platform/kong/argocd/kong-smoke-app.yaml
platform/gitops/app-of-apps/kong-baseline-app.yaml
```

These must fit the goal 001 app-of-apps structure.

If the repository URL is unknown, use `REPLACE_WITH_REPO_URL` and document that
Argo CD sync is blocked until replaced. Do not pretend unresolved placeholder
repo URLs are deployable.

The Argo CD documentation must explain how Kong baseline becomes part of
app-of-apps, which namespace owns the application, how sync order should work,
how rollback works through Git revert, how drift detection applies, and why
direct cluster edits are not the source of truth.

### Documentation

Create or update:

```text
docs/architecture/kong-oss-baseline.md
docs/architecture/gateway-api-baseline.md
docs/architecture/kong-admin-api-exposure.md
docs/architecture/kong-baseline-testing.md
docs/runbooks/kong-baseline-install.md
docs/runbooks/kong-baseline-rollback.md
docs/runbooks/kong-admin-api-exposure-check.md
platform/kong/README.md
README.md
ROADMAP.md
```

Documentation must cover selected Kong OSS version, selected KIC version,
selected Helm chart and version, DB-less mode, why PostgreSQL is not introduced
yet, why Kong Admin API is private, why Kong Manager is not the platform UI,
how Gateway API is used, internal versus external Gateway intent, how the smoke
route proves the baseline, local validation, cluster validation, GitOps or
controlled manual install, rollback, failed pod diagnosis, failed Gateway API
attachment diagnosis, failed smoke route diagnosis, Admin API exposure checks,
and what is deferred to later goals.

Do not convert later roadmap phases into implementation.

### Scripts

Create or update:

```text
scripts/validate_kong_baseline.py
scripts/render_kong_baseline.py
scripts/check_kong_cluster.py
platform/kong/scripts/check-kong-baseline.sh
platform/kong/scripts/check-admin-not-exposed.sh
platform/kong/scripts/route-smoke.sh
platform/kong/scripts/render-and-lint-kong.sh
```

The scripts must provide local static validation, Helm/Kustomize render
validation where tooling is available, version placeholder checks, forbidden
Enterprise feature checks, forbidden Admin API exposure checks, forbidden secret
checks, forbidden floating tag checks, optional cluster checks, and optional
route smoke tests.

Scripts must not require cluster access unless their name clearly indicates
cluster or smoke behavior.

Scripts that mutate the cluster must require explicit user action and must not
be run by default validation.

### Makefile Targets

Preserve all goal 000 and goal 001 targets.

Add or update these targets:

- `validate-kong-baseline`
- `render-kong-baseline`
- `kong-static-test`
- `kong-admin-exposure-test`
- `kong-cluster-smoke`
- `kong-route-smoke`
- `kong-install-dry-run`
- `kong-apply`
- `kong-rollback`
- `evidence-goal-002`

Target requirements:

- `make validate` must remain local-only.
- `make validate-kong-baseline` must run static validation for goal 002.
- `make render-kong-baseline` must render Kustomize and Helm output where
  tooling is available without applying anything.
- `make kong-static-test` must run local Kong baseline tests.
- `make kong-admin-exposure-test` must prove through static checks that Admin
  API is not externally exposed.
- `make kong-install-dry-run` must perform client-side or server-side dry-run
  where possible. If it requires a cluster, it must say so clearly.
- `make kong-cluster-smoke` must require a Kubernetes context and must not run
  in CI by default.
- `make kong-route-smoke` must require a running Kong baseline and must test the
  smoke route.
- `make kong-apply` must be explicit and must print a warning before applying
  resources.
- `make kong-rollback` must provide a controlled rollback path and must not
  delete unrelated resources.
- `make evidence-goal-002` must create or update
  `reports/goal-002-summary.md`.

Do not add cluster-mutating commands to the default target or CI.

### Tests

Add tests for goal 002.

Required test coverage:

- Kong baseline directory exists.
- Kong version lock exists.
- Kong Gateway image repository is `kong`.
- Kong Gateway image tag is pinned.
- No latest tags are used.
- Enterprise is disabled in values.
- DB-less mode is configured.
- PostgreSQL is not enabled for Kong.
- Kong Manager is not enabled as the platform control plane.
- Portal is not enabled.
- Admin API is not exposed as LoadBalancer.
- Admin API is not exposed as NodePort.
- Proxy service is intended to be LoadBalancer.
- GatewayClass manifest exists.
- Internal Gateway manifest exists.
- External Gateway manifest exists.
- Smoke backend manifests exist.
- Smoke image tag is pinned.
- HTTPRoute manifests exist.
- No business API manifests are introduced.
- No API consumers are introduced.
- No authentication plugins are introduced.
- No rate limiting plugins are introduced.
- No Enterprise-only plugins are introduced.
- No real secrets are introduced.
- No kubeconfigs are introduced.
- No private keys are introduced.

Required test files:

```text
tests/unit/test_goal_002_kong_structure.py
tests/unit/test_goal_002_kong_versions.py
tests/unit/test_goal_002_no_enterprise_features.py
tests/unit/test_goal_002_admin_api_private.py
tests/policy/test_goal_002_kong_policy.py
tests/policy/test_goal_002_no_forbidden_kong_resources.py
```

The tests must run with pytest and must not require Kubernetes, Docker, or
internet access.

### Policy Checks

Policy checks must reject:

- `kong/kong-gateway` Enterprise image unless explicitly justified in a future
  non-OSS branch.
- Latest image tags.
- Enterprise enabled in Helm values.
- Kong Manager enabled as a platform control plane.
- Portal enabled.
- PostgreSQL enabled for Kong.
- Admin API exposed by LoadBalancer.
- Admin API exposed by NodePort.
- Admin API routed by Gateway API.
- Enterprise-only plugins.
- Kong OIDC plugin.
- Kong Request Validator plugin.
- Kong MTLS Auth plugin.
- Plaintext real secrets.
- Kubeconfigs.
- Private keys.
- API tokens.
- Business API resources in this goal.
- Consumers in this goal.
- Rate limiting in this goal.
- Auth plugins in this goal.

Policy checks must allow:

- Gateway API GatewayClass.
- Gateway API Gateway.
- Gateway API HTTPRoute for smoke only.
- Kong OSS image.
- KIC image with pinned tag.
- DB-less mode.
- Private ClusterIP Admin API if required by the chart.
- LoadBalancer proxy service.

### CI

Update `.github/workflows/ci.yml`.

CI must remain local-only.

CI must run at least:

```bash
make validate
make validate-prereqs
make validate-kong-baseline
make kong-static-test
make kong-admin-exposure-test
make test
make policy-test
make docs
```

CI must not run cluster or mutating targets such as `make kong-apply`,
`make kong-rollback`, `make kong-cluster-smoke`, `make kong-route-smoke`,
`make cluster-smoke`, or `make cluster-prereq-smoke` unless they are explicitly
skipped by default and require manual workflow dispatch with a real cluster.

## Optional Cluster Installation Path

If the user explicitly permits cluster changes and a valid kube context exists,
goal 002 may apply the baseline.

Before applying, run:

```bash
make cluster-smoke
make cluster-prereq-smoke
make kong-install-dry-run
```

If these pass and the user has permitted apply, run:

```bash
make kong-apply
```

Then run:

```bash
make kong-cluster-smoke
make kong-route-smoke
make kong-admin-exposure-test
```

The cluster smoke must verify at minimum:

- `platform-kong` namespace exists.
- Kong Gateway pods are ready.
- KIC pods are ready.
- Proxy service exists and has expected type.
- Admin API is not externally exposed.
- GatewayClass exists.
- Internal Gateway exists.
- External Gateway exists.
- Smoke backend is ready.
- External and internal smoke HTTPRoute resources are accepted or condition
  status is reported.
- Smoke route returns expected response.
- Unknown route returns expected failure.
- Admin API is not reachable through the proxy.

If Gateway API CRDs are missing, the cluster smoke must report the missing CRDs
clearly.

If MetalLB is not installed or no LoadBalancer IP is assigned, the route smoke
must use port-forward fallback or report the exact blocker.

If NetworkPolicy blocks traffic, record the failed path and update docs/runbooks
if needed.

Do not silently bypass failing smoke tests.

Do not claim cluster success unless the tests actually pass.

## Acceptance Criteria

- Goal 001 carry-forward checks have been completed.
- Goal 000 and goal 001 local validation remain passing.
- Kong OSS baseline files exist.
- Kong version lock exists.
- Kong Gateway image is pinned to an OSS image.
- No floating image tags are used.
- No unpinned Helm chart version is used for cluster-ready install.
- No unpinned KIC version is used for cluster-ready install.
- No unpinned Gateway API CRD version is used for cluster-ready install.
- DB-less mode is configured.
- PostgreSQL is not introduced.
- Enterprise is disabled.
- Kong Manager is not enabled as the platform control plane.
- Kong Portal is not enabled.
- Kong Admin API is not externally exposed.
- Kong proxy exposure is documented and intended for MetalLB.
- Dedicated Kong namespace exists.
- Gateway API baseline exists.
- Internal Gateway exists.
- External Gateway exists.
- Smoke backend exists.
- Smoke HTTPRoutes exist.
- Smoke backend is clearly not a business API.
- Kong-specific NetworkPolicy baseline exists.
- Argo CD application templates exist for the Kong baseline.
- Documentation explains installation, rollback, testing, Admin API exposure
  control, and known limitations.
- Makefile includes goal 002 validation targets.
- Local validation remains cluster-free.
- CI remains cluster-free.
- Static tests verify no Enterprise features are used.
- Static tests verify no Admin API external exposure is configured.
- Static tests verify no real secrets are committed.
- Policy tests pass.
- Evidence report exists at `reports/goal-002-summary.md`.

If cluster apply was not performed, evidence clearly states:

```text
Cluster changes performed: none
Cluster verification: not run
Ready for next goal: no; run cluster apply and smoke tests first
```

If cluster apply was performed and all smoke tests passed, evidence clearly
states:

```text
Cluster changes performed: Kong OSS baseline applied
Cluster verification: pass
Ready for next goal: goal-003-synthetic-bank-apis
```

## Validation Commands

Run from the repository root.

Required local validation:

```bash
make validate
make validate-yaml
make validate-kustomize
make validate-prereqs
make validate-kong-baseline
make render-kong-baseline
make kong-static-test
make kong-admin-exposure-test
make test
make policy-test
make docs
make evidence-goal-002
```

Required full local gate:

```bash
make validate && make validate-yaml && make validate-kustomize && make validate-prereqs && make validate-kong-baseline && make render-kong-baseline && make kong-static-test && make kong-admin-exposure-test && make test && make policy-test && make docs && make evidence-goal-002
```

Expected result: all local checks pass without requiring a Kubernetes cluster,
except where `render-kong-baseline` explicitly depends on Helm/chart access. If
render cannot complete because external chart access is unavailable, record the
blocker and do not claim render success.

Optional cluster validation before apply, only with a valid kube context and
explicit user permission:

```bash
make cluster-smoke
make cluster-prereq-smoke
make kong-install-dry-run
```

Optional cluster apply, only with explicit user permission:

```bash
make kong-apply
```

Optional cluster validation after apply:

```bash
make kong-cluster-smoke
make kong-route-smoke
make kong-admin-exposure-test
```

Optional rollback validation:

```bash
make kong-rollback
```

Do not run rollback unless intentionally testing rollback.

## Evidence Report Requirements

Create or update `reports/goal-002-summary.md`.

The report must contain this structure:

```text
Goal: goal-002-kong-oss-baseline
Status:
Branch:
Generated at:
Objective summary:

Goal 001 approval status:
- 

Goal 001 corrections reviewed:
- 

Corrections applied:
- 

Selected versions:
- Kong Gateway image:
- Kong Gateway tag:
- Kong Ingress Controller image:
- Kong Ingress Controller tag:
- Kong Helm chart:
- Kong Helm chart version:
- Gateway API channel:
- Gateway API version:

Validation commands run:
- make validate:
- make validate-yaml:
- make validate-kustomize:
- make validate-prereqs:
- make validate-kong-baseline:
- make render-kong-baseline:
- make kong-static-test:
- make kong-admin-exposure-test:
- make test:
- make policy-test:
- make docs:
- make evidence-goal-002:

Optional cluster commands run:
- make cluster-smoke:
- make cluster-prereq-smoke:
- make kong-install-dry-run:
- make kong-apply:
- make kong-cluster-smoke:
- make kong-route-smoke:
- make kong-rollback:

Created files:
- 

Updated files:
- 

Kong namespace:
- 

Kong Helm baseline:
- 

Gateway API baseline:
- 

Smoke backend:
- 

Admin API exposure control:
- 

NetworkPolicy baseline:
- 

Argo CD integration:
- 

Local validation result:

Cluster changes performed:

Cluster verification:

Secrets created:

Kong resources created:

Enterprise Kong features used:

Admin API externally exposed:

Known limitations:

Ready for next goal:
```

Required values if no cluster apply was performed:

```text
Cluster changes performed: none
Cluster verification: not run
Secrets created: none; only non-deployable examples/placeholders were added if applicable
Kong resources created: none applied; manifests/templates only
Enterprise Kong features used: none
Admin API externally exposed: no, based on static validation
Ready for next goal: no; run cluster apply and smoke tests before goal-003
```

Required values if cluster apply and smoke tests passed:

```text
Cluster changes performed: Kong OSS baseline applied
Cluster verification: pass
Secrets created: none; only non-deployable examples/placeholders were added if applicable
Kong resources created: Kong OSS baseline, Gateway API baseline, smoke backend
Enterprise Kong features used: none
Admin API externally exposed: no
Ready for next goal: goal-003-synthetic-bank-apis
```

If any command could not be run, the evidence report must state which command
was not run, why it was not run, whether this blocks completion, and what must
be done before goal 003.

Do not claim validation passed unless the command actually passed.

Do not claim Kong is installed unless cluster apply and cluster smoke tests
actually passed.

## Stop Condition

Stop after the Kong OSS baseline repository implementation is complete,
carry-forward corrections from goal 001 are handled, local validation has been
run, and `reports/goal-002-summary.md` has been created or updated.

If cluster apply was not explicitly permitted, stop after local validation and
evidence generation. Record that cluster verification is pending and that the
platform is not ready for goal 003 until Kong apply and smoke tests pass.

If cluster apply was explicitly permitted, stop after applying the Kong OSS
baseline, running cluster smoke tests, running route smoke tests, proving Admin
API is not externally exposed, and updating `reports/goal-002-summary.md`.

Do not implement synthetic banking APIs.

Do not implement auth plugins.

Do not implement rate limiting.

Do not implement Redis.

Do not implement SSO.

Do not implement observability stack.

Do not implement secrets rotation.

Do not implement incident drills.

Do not proceed to goal 003.
