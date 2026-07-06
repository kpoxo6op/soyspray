# Goal: goal-003-synthetic-bank-apis
Objective
Create the synthetic banking API product layer for the Kong OSS bank-lab.

This goal adds realistic but lightweight mock API providers, API product metadata, OpenAPI specifications, tenant-owned Kubernetes manifests, Gateway API HTTPRoute resources, synthetic client profiles, local validation, documentation, runtime smoke-test tooling, and evidence reporting.

The goal must demonstrate how a regulated-bank platform team onboards API products through Git-managed, testable, reviewable configuration without introducing authentication, authorization, rate limiting, SSO, observability stack, or Enterprise-only Kong features yet.

The synthetic API domains are:

accounts
payments
cards
customer-profile
fraud-decisions
open-banking
The synthetic clients are:

mobile-banking-app
internet-banking-web
internal-crm
fraud-platform
payments-processor
external-fintech-partner
The required result is a repo-safe API product layer that can be locally validated and, with explicit permission, applied to the existing runtime-verified Kong OSS baseline.

Scope
Implement the following:

Synthetic bank API product definitions
OpenAPI specifications
Ownership metadata
Tenant Kubernetes manifests
Mock backend manifests
Gateway API HTTPRoutes
Tenant NetworkPolicies allowing Kong-to-upstream traffic
Synthetic client metadata
Generated API catalog documentation
Local static validation
OpenAPI validation
Route and ownership policy checks
Runtime-safe smoke-test scripts
Runtime-safe negative-test scripts
Evidence reporting
Guarded runtime apply and rollback targets
This goal must create API product assets for:

Accounts API
Payments API
Cards API
Customer Profile API
Fraud Decisions API
Open Banking Partner API
Each API must have:

OpenAPI spec
ownership metadata
tenant namespace mapping
mock backend manifests
service manifest
HTTPRoute manifest
NetworkPolicy allowing Kong proxy to reach the backend
local validation coverage
documentation page
positive smoke-test definition
negative smoke-test definition
rollback notes
This goal must create synthetic client profiles for:

mobile-banking-app
internet-banking-web
internal-crm
fraud-platform
payments-processor
external-fintech-partner
Each synthetic client profile must define:

client name
client type
owning team
intended APIs
intended exposure
future authentication profile
future authorization profile
future rate-limit profile
support contact
test persona purpose
This goal must use the existing Kong OSS runtime baseline from goal 002.

Do not revalidate or relitigate goal 002. Treat the existing approved runtime evidence as the baseline precondition.

Preconditions
The repository already contains:

Goal 000 foundation
Goal 001 platform prerequisites
Goal 002 Kong OSS baseline
gate-002-runtime-preflight
gate-002-cluster-apply-and-smoke
The Kong OSS runtime baseline has already been applied and runtime-verified.

Known baseline state:

Kong Gateway image: kong:3.9.3
KIC image: kong/kubernetes-ingress-controller:3.5.10
Gateway API version: v1.3.0
Helm chart: kong/ingress 0.24.0
Kong mode: DB-less
GatewayClass/kong: Accepted=True
Gateway/kong-external: Programmed=True
Gateway/kong-internal: Programmed=True
Gateway address: 192.168.20.22
External smoke route: banklab-kong-smoke-ok
Internal smoke route: banklab-kong-smoke-ok
Unknown host route: Kong 404
Admin API external exposure: negative
Goal 002 runtime fixes must be preserved:

Gateway API CRDs are installed.
KIC egress to Kubernetes API is allowed.
Private KIC-to-Kong Admin API 8444 network policy path is allowed.
Kong CRDs are installed cluster-wide for KIC cache sync.
KIC webhook TLS material may exist as runtime-created Kubernetes secrets.
Goal 003 must not remove, weaken, or overwrite these runtime fixes.

Goal 003 must preserve:

Kong OSS only
DB-less Kong
private Kong Admin API
Gateway API routing model
Git as source of truth
cluster mutation guardrails
secret hygiene
CI without cluster mutation
Non-goals
Do not implement authentication.

Do not create Kong Consumers.

Do not create API keys.

Do not configure Key Auth.

Do not configure JWT.

Do not configure ACL.

Do not configure rate limiting.

Do not configure Redis.

Do not configure SSO.

Do not install or configure Keycloak.

Do not install Prometheus, Grafana, Loki, or Alertmanager.

Do not implement tracing.

Do not implement production TLS.

Do not configure mTLS.

Do not create real certificates.

Do not create real secrets.

Do not commit kubeconfigs.

Do not commit private keys.

Do not create real bank data.

Do not create real customer data.

Do not create real payment data.

Do not create custom Kong plugins.

Do not create KongPlugin.

Do not create KongClusterPlugin.

Do not create KongConsumer.

Do not create KongIngress.

Do not use Kong Enterprise.

Do not use Konnect.

Do not use Kong Enterprise RBAC.

Do not use Kong Enterprise Workspaces as a governance boundary.

Do not use Kong Enterprise OpenID Connect plugin.

Do not use Kong Enterprise Request Validator plugin.

Do not use Kong Enterprise MTLS Auth plugin.

Do not use Kong Enterprise Developer Portal.

Do not expose the Kong Admin API externally.

Do not make Kong Manager the platform UI.

Do not bypass the mutation guard.

Do not mutate the cluster unless explicit permission is granted.

Do not proceed to goal 004.

Security posture for this goal
The APIs created in this goal are synthetic and sandbox-only.

Because authentication and authorization are deferred to goal 004, all goal 003 API routes must be clearly labelled as:

sandbox
synthetic
temporary-no-auth
goal-003
External exposure must be tightly limited.

Default exposure model:

Internal gateway:
- accounts
- payments
- cards
- customer-profile
- fraud-decisions

External gateway:
- open-banking only
Do not expose accounts, payments, cards, customer-profile, or fraud-decisions on the external Gateway in this goal.

The Open Banking Partner API may be exposed on the external Gateway as a synthetic sandbox API only.

Every manifest and metadata file for an unauthenticated route must make the temporary goal-003 posture explicit.

Goal 004 must later replace this temporary posture with authentication, authorization, and rate limiting.

Required repo files
Create or update the following files.

soydocs/
└── kong-bank-lab/
    └── goals/
        └── goal-003-synthetic-bank-apis.md

apis/
├── README.md
└── synthetic-bank/
    ├── README.md
    ├── versions.yaml
    ├── kustomization.yaml
    ├── api-catalog.yaml
    ├── route-matrix.yaml
    ├── exposure-policy.yaml
    ├── _shared/
    │   ├── README.md
    │   ├── labels.yaml
    │   ├── mock-backend-standard.md
    │   └── network-policy-standard.md
    ├── accounts/
    │   ├── README.md
    │   ├── openapi.yaml
    │   ├── ownership.yaml
    │   ├── kustomization.yaml
    │   ├── configmap-mock-responses.yaml
    │   ├── deployment.yaml
    │   ├── service.yaml
    │   ├── httproute-internal.yaml
    │   ├── networkpolicy-allow-kong.yaml
    │   └── tests/
    │       ├── positive.yaml
    │       └── negative.yaml
    ├── payments/
    │   ├── README.md
    │   ├── openapi.yaml
    │   ├── ownership.yaml
    │   ├── kustomization.yaml
    │   ├── configmap-mock-responses.yaml
    │   ├── deployment.yaml
    │   ├── service.yaml
    │   ├── httproute-internal.yaml
    │   ├── networkpolicy-allow-kong.yaml
    │   └── tests/
    │       ├── positive.yaml
    │       └── negative.yaml
    ├── cards/
    │   ├── README.md
    │   ├── openapi.yaml
    │   ├── ownership.yaml
    │   ├── kustomization.yaml
    │   ├── configmap-mock-responses.yaml
    │   ├── deployment.yaml
    │   ├── service.yaml
    │   ├── httproute-internal.yaml
    │   ├── networkpolicy-allow-kong.yaml
    │   └── tests/
    │       ├── positive.yaml
    │       └── negative.yaml
    ├── customer-profile/
    │   ├── README.md
    │   ├── openapi.yaml
    │   ├── ownership.yaml
    │   ├── kustomization.yaml
    │   ├── configmap-mock-responses.yaml
    │   ├── deployment.yaml
    │   ├── service.yaml
    │   ├── httproute-internal.yaml
    │   ├── networkpolicy-allow-kong.yaml
    │   └── tests/
    │       ├── positive.yaml
    │       └── negative.yaml
    ├── fraud-decisions/
    │   ├── README.md
    │   ├── openapi.yaml
    │   ├── ownership.yaml
    │   ├── kustomization.yaml
    │   ├── configmap-mock-responses.yaml
    │   ├── deployment.yaml
    │   ├── service.yaml
    │   ├── httproute-internal.yaml
    │   ├── networkpolicy-allow-kong.yaml
    │   └── tests/
    │       ├── positive.yaml
    │       └── negative.yaml
    └── open-banking/
        ├── README.md
        ├── openapi.yaml
        ├── ownership.yaml
        ├── kustomization.yaml
        ├── configmap-mock-responses.yaml
        ├── deployment.yaml
        ├── service.yaml
        ├── httproute-external.yaml
        ├── networkpolicy-allow-kong.yaml
        └── tests/
            ├── positive.yaml
            └── negative.yaml

clients/
└── synthetic/
    ├── README.md
    ├── client-catalog.yaml
    ├── mobile-banking-app.yaml
    ├── internet-banking-web.yaml
    ├── internal-crm.yaml
    ├── fraud-platform.yaml
    ├── payments-processor.yaml
    └── external-fintech-partner.yaml

docs/
├── api-catalog/
│   ├── README.md
│   ├── index.md
│   ├── accounts.md
│   ├── payments.md
│   ├── cards.md
│   ├── customer-profile.md
│   ├── fraud-decisions.md
│   └── open-banking.md
├── architecture/
│   ├── synthetic-bank-apis.md
│   ├── api-product-model.md
│   ├── synthetic-client-model.md
│   └── goal-003-runtime-boundary.md
└── runbooks/
    ├── synthetic-api-onboarding.md
    ├── synthetic-api-runtime-smoke.md
    └── synthetic-api-rollback.md

platform/
└── kong/
    └── synthetic-apis/
        ├── README.md
        ├── kustomization.yaml
        ├── argocd/
        │   ├── README.md
        │   └── synthetic-bank-apis-app.yaml
        └── scripts/
            ├── README.md
            ├── synthetic-api-apply.sh
            ├── synthetic-api-rollback.sh
            ├── synthetic-api-smoke.sh
            ├── synthetic-api-negative-test.sh
            └── collect-synthetic-api-evidence.sh

scripts/
├── validate_synthetic_bank_apis.py
├── validate_openapi_specs.py
├── render_synthetic_apis.py
├── generate_api_catalog.py
├── generate_synthetic_api_smoke_plan.py
└── generate_evidence_report.py

tests/
├── unit/
│   ├── test_goal_003_synthetic_api_structure.py
│   ├── test_goal_003_openapi_specs.py
│   ├── test_goal_003_api_ownership_metadata.py
│   ├── test_goal_003_route_matrix.py
│   ├── test_goal_003_synthetic_clients.py
│   └── test_goal_003_runtime_boundary.py
├── policy/
│   ├── test_goal_003_no_forbidden_kong_resources.py
│   ├── test_goal_003_exposure_policy.py
│   ├── test_goal_003_no_auth_until_goal004.py
│   ├── test_goal_003_no_secrets.py
│   └── test_goal_003_network_policy.py
└── integration/
    └── synthetic_apis/
        ├── README.md
        ├── smoke_cases.yaml
        └── negative_cases.yaml

reports/
├── goal-003-summary.md
├── synthetic-api-smoke-plan.md
├── synthetic-api-runtime-evidence.md
├── synthetic-api-route-smoke-results.md
└── synthetic-api-negative-test-results.md
Small path adjustments are allowed only when they preserve the same intent and remain consistent with the existing repository structure.

Do not remove files from previous goals.

Do not overwrite historical evidence from goals 000, 001, or 002.

API product requirements
Each API must include an ownership.yaml file with at least:

api_name:
api_domain:
owning_team:
tenant_namespace:
exposure:
lifecycle_state:
data_classification:
support_contact:
slo_target:
openapi_path:
upstream_service:
route_host:
route_paths:
auth_profile: none-temporary-goal003-sandbox
authorization_profile: none-temporary-goal003-sandbox
rate_limit_profile: deferred-goal004
logging_profile: standard
future_auth_goal: goal-004-auth-rate-limit-security
rollback_owner:
Allowed exposure values:

internal
external
Allowed lifecycle_state value for this goal:

sandbox
Allowed data_classification value for this goal:

synthetic
Allowed auth_profile value for this goal:

none-temporary-goal003-sandbox
Allowed authorization_profile value for this goal:

none-temporary-goal003-sandbox
Allowed rate_limit_profile value for this goal:

deferred-goal004
Each API must include labels on all Kubernetes resources:

banklab.konghq.com/managed-by: gitops
banklab.konghq.com/platform-layer: synthetic-api
banklab.konghq.com/environment: lab
banklab.konghq.com/data-classification: synthetic
banklab.konghq.com/lifecycle: sandbox
banklab.konghq.com/auth-profile: none-temporary-goal003-sandbox
banklab.konghq.com/goal: goal-003
Each API must map to the expected namespace:

accounts -> tenant-accounts
payments -> tenant-payments
cards -> tenant-cards
customer-profile -> tenant-customer-profile
fraud-decisions -> tenant-fraud
open-banking -> tenant-open-banking
API domain requirements
Accounts API
Purpose:

Synthetic account-list and account-detail API for internal banking channels.
Required route:

host: api.internal.banklab.test
path prefix: /accounts/v1
gateway: platform-kong/kong-internal
namespace: tenant-accounts
Minimum OpenAPI paths:

GET /accounts/v1/health
GET /accounts/v1/accounts
GET /accounts/v1/accounts/{accountId}
Required smoke marker:

banklab-accounts-ok
Payments API
Purpose:

Synthetic payment initiation and payment-status API for internal payment flows.
Required route:

host: api.internal.banklab.test
path prefix: /payments/v1
gateway: platform-kong/kong-internal
namespace: tenant-payments
Minimum OpenAPI paths:

GET /payments/v1/health
GET /payments/v1/payment-requests
GET /payments/v1/payment-requests/{paymentRequestId}
POST /payments/v1/payment-requests
Required smoke marker:

banklab-payments-ok
The POST operation is synthetic only. Do not implement real payment movement.

Cards API
Purpose:

Synthetic card-list and card-status API for internal digital channels.
Required route:

host: api.internal.banklab.test
path prefix: /cards/v1
gateway: platform-kong/kong-internal
namespace: tenant-cards
Minimum OpenAPI paths:

GET /cards/v1/health
GET /cards/v1/cards
GET /cards/v1/cards/{cardId}
Required smoke marker:

banklab-cards-ok
Do not include real PANs, real card numbers, or real cardholder data.

Customer Profile API
Purpose:

Synthetic customer profile API for internal CRM and servicing scenarios.
Required route:

host: api.internal.banklab.test
path prefix: /customers/v1
gateway: platform-kong/kong-internal
namespace: tenant-customer-profile
Minimum OpenAPI paths:

GET /customers/v1/health
GET /customers/v1/customers
GET /customers/v1/customers/{customerId}
Required smoke marker:

banklab-customer-profile-ok
Do not include real names, real addresses, real phone numbers, real emails, or real personal information.

Fraud Decisions API
Purpose:

Synthetic fraud decision API for internal risk scoring and transaction decision demos.
Required route:

host: api.internal.banklab.test
path prefix: /fraud/v1
gateway: platform-kong/kong-internal
namespace: tenant-fraud
Minimum OpenAPI paths:

GET /fraud/v1/health
GET /fraud/v1/decisions
GET /fraud/v1/decisions/{decisionId}
POST /fraud/v1/decisions
Required smoke marker:

banklab-fraud-decisions-ok
The POST operation is synthetic only. Do not implement real fraud scoring.

Open Banking Partner API
Purpose:

Synthetic external partner API for open-banking style onboarding and exposure demos.
Required route:

host: api.external.banklab.test
path prefix: /open-banking/v1
gateway: platform-kong/kong-external
namespace: tenant-open-banking
Minimum OpenAPI paths:

GET /open-banking/v1/health
GET /open-banking/v1/accounts
GET /open-banking/v1/payments
Required smoke marker:

banklab-open-banking-ok
This is the only externally exposed synthetic API in goal 003.

Route requirements
Use the existing Gateway API baseline.

Expected Gateway parents:

platform-kong/kong-internal
platform-kong/kong-external
Required route model:

accounts:
  host: api.internal.banklab.test
  path_prefix: /accounts/v1
  parent: platform-kong/kong-internal

payments:
  host: api.internal.banklab.test
  path_prefix: /payments/v1
  parent: platform-kong/kong-internal

cards:
  host: api.internal.banklab.test
  path_prefix: /cards/v1
  parent: platform-kong/kong-internal

customer-profile:
  host: api.internal.banklab.test
  path_prefix: /customers/v1
  parent: platform-kong/kong-internal

fraud-decisions:
  host: api.internal.banklab.test
  path_prefix: /fraud/v1
  parent: platform-kong/kong-internal

open-banking:
  host: api.external.banklab.test
  path_prefix: /open-banking/v1
  parent: platform-kong/kong-external
Do not expose the following APIs on the external Gateway in this goal:

accounts
payments
cards
customer-profile
fraud-decisions
Do not create wildcard hostnames.

Do not create catch-all routes.

Do not create Admin API routes.

Do not attach routes to the wrong Gateway.

Do not create cross-namespace backend references unless a matching ReferenceGrant is created and justified. The preferred model is that each HTTPRoute and its backend Service live in the same tenant namespace.

If the existing Gateway manifests do not allow route attachment from the tenant namespaces, update the repo declaratively to permit only the intended tenant namespaces by label selector.

Do not use unrestricted from: All unless a clear reason is documented and policy tests still constrain the actual routes.

Mock backend requirements
Mock backends must be lightweight and deterministic.

Use one mock backend per API domain.

Each mock backend must:

run in the API tenant namespace
use a pinned container image tag
avoid latest tags
serve deterministic JSON
serve a health endpoint
return an API-specific marker
use synthetic-only data
have resource requests and limits
run as non-root where practical
expose a Kubernetes Service
be reachable only through intended NetworkPolicy paths
Preferred implementation pattern:

nginx-unprivileged or equivalent pinned lightweight HTTP image
ConfigMap-mounted static JSON responses
read-only root filesystem where practical
non-root security context
resource requests and limits
Record the chosen backend image in:

apis/synthetic-bank/versions.yaml
Do not use latest.

If a chosen mock image cannot be runtime-verified later, stop and record the blocker instead of silently changing the image.

Preferred endpoints for smoke testing:

GET /accounts/v1/health
GET /payments/v1/health
GET /cards/v1/health
GET /customers/v1/health
GET /fraud/v1/health
GET /open-banking/v1/health
Each health endpoint must return a unique marker:

banklab-accounts-ok
banklab-payments-ok
banklab-cards-ok
banklab-customer-profile-ok
banklab-fraud-decisions-ok
banklab-open-banking-ok
OpenAPI requirements
Each API must have a valid OpenAPI 3.x spec.

Each openapi.yaml must include:

openapi version
info.title
info.version
info.description
servers
tags
paths
operationId for every operation
responses for every operation
synthetic example responses
x-banklab-api-domain
x-banklab-owning-team
x-banklab-lifecycle
x-banklab-data-classification
x-banklab-auth-profile
Each OpenAPI spec must include at least:

GET health endpoint
GET example resource endpoint
one error response example
Payments and fraud-decisions may include synthetic POST operations, but runtime smoke must use only health and read-only mock endpoints in this goal.

No OpenAPI spec may include:

real customer identifiers
real account numbers
real PANs
real card numbers
real addresses
real phone numbers
real email addresses
real bank data
real personal information
All examples must be synthetic.

Synthetic client requirements
Create synthetic client profiles under:

clients/synthetic/
Required clients:

mobile-banking-app
internet-banking-web
internal-crm
fraud-platform
payments-processor
external-fintech-partner
Each client profile must include:

client_name:
client_type:
owning_team:
intended_exposure:
intended_apis:
future_auth_profile:
future_authorization_profile:
future_rate_limit_profile:
support_contact:
test_persona:
data_classification: synthetic
credentials_created: false
Do not create credentials.

Do not create API keys.

Do not create Kong Consumers.

Do not create Kubernetes Secrets.

Client profiles are metadata only in this goal.

NetworkPolicy requirements
Each tenant API namespace must include a NetworkPolicy allowing Kong proxy traffic to the mock backend.

The policy must:

allow ingress from platform-kong namespace or Kong proxy pods
allow only the mock backend service port
preserve default-deny posture
not allow broad tenant-to-tenant traffic
not allow unrestricted ingress from all namespaces
not allow unrestricted egress unless explicitly justified
Add static tests to verify that every synthetic API has a corresponding:

networkpolicy-allow-kong.yaml
Preserve all goal 002 runtime network policy fixes.

Do not remove or weaken:

KIC egress to Kubernetes API
private KIC-to-Kong Admin API 8444 path
Kong Admin API ClusterIP-only posture
Documentation requirements
Create API catalog documentation under:

docs/api-catalog/
The catalog index must show:

API name
domain
owning team
tenant namespace
exposure
host
path prefix
lifecycle state
data classification
temporary auth posture
future auth goal
OpenAPI spec path
support contact
Each API page must show:

purpose
owner
exposure
sample route
sample response marker
OpenAPI link
synthetic data statement
temporary no-auth warning
future security controls
rollback notes
Create architecture docs:

docs/architecture/synthetic-bank-apis.md
docs/architecture/api-product-model.md
docs/architecture/synthetic-client-model.md
docs/architecture/goal-003-runtime-boundary.md
Create runbooks:

docs/runbooks/synthetic-api-onboarding.md
docs/runbooks/synthetic-api-runtime-smoke.md
docs/runbooks/synthetic-api-rollback.md
The runtime-boundary doc must state:

Local validation is required.
Cluster mutation is optional and guarded.
Goal 003 can be locally complete without cluster mutation.
Goal 003 is not runtime-verified until apply and smoke tests pass.
Goal 004 must not start until synthetic APIs are runtime-verified, unless the user explicitly accepts a local-only handoff.
Argo CD requirements
Create an Argo CD application template:

platform/kong/synthetic-apis/argocd/synthetic-bank-apis-app.yaml
It must fit the existing app-of-apps model.

If the repo URL is unknown, keep using:

REPLACE_WITH_REPO_URL
Do not pretend unresolved placeholder repo URLs are deployable.

Argo CD templates must not sync automatically from CI.

Do not run argocd app sync in this goal unless explicit cluster mutation permission is granted and the command is guarded.

Scripts and Makefile targets
Add or update scripts:

scripts/validate_synthetic_bank_apis.py
scripts/validate_openapi_specs.py
scripts/render_synthetic_apis.py
scripts/generate_api_catalog.py
scripts/generate_synthetic_api_smoke_plan.py
Add or update runtime scripts:

platform/kong/synthetic-apis/scripts/synthetic-api-apply.sh
platform/kong/synthetic-apis/scripts/synthetic-api-rollback.sh
platform/kong/synthetic-apis/scripts/synthetic-api-smoke.sh
platform/kong/synthetic-apis/scripts/synthetic-api-negative-test.sh
platform/kong/synthetic-apis/scripts/collect-synthetic-api-evidence.sh
Any cluster-mutating runtime script must call:

platform/kong/scripts/require-cluster-mutation-permission.sh
before mutation.

Add Makefile targets:

validate-synthetic-apis
openapi-lint
render-synthetic-apis
synthetic-api-static-test
synthetic-api-contract-test
synthetic-api-smoke-plan
synthetic-api-install-dry-run
synthetic-api-apply
synthetic-api-smoke
synthetic-api-negative-test
synthetic-api-rollback
synthetic-api-runtime-ready
evidence-goal-003
Target behavior:

validate-synthetic-apis:
  local-only
  validates required files, metadata, labels, route matrix, exposure policy

openapi-lint:
  local-only
  validates OpenAPI specs without requiring internet access

render-synthetic-apis:
  local-only
  renders Kustomize manifests without applying them

synthetic-api-static-test:
  local-only
  runs static goal 003 tests

synthetic-api-contract-test:
  local-only
  validates OpenAPI, metadata, route matrix, and smoke cases are consistent

synthetic-api-smoke-plan:
  local-only
  generates reports/synthetic-api-smoke-plan.md

synthetic-api-install-dry-run:
  cluster-aware
  must not mutate unless server-side dry-run requires API interaction
  must be clearly documented

synthetic-api-apply:
  cluster-mutating
  must be guarded
  must fail closed without BANKLAB_ALLOW_CLUSTER_MUTATION=true and BANKLAB_TARGET_CONTEXT

synthetic-api-smoke:
  cluster-read-only
  must not mutate
  requires applied APIs

synthetic-api-negative-test:
  cluster-read-only
  must not mutate
  requires applied APIs

synthetic-api-rollback:
  cluster-mutating
  must be guarded

synthetic-api-runtime-ready:
  local/read-only evidence check
  must fail until runtime evidence proves apply and smoke passed

evidence-goal-003:
  local-only
  generates or updates reports/goal-003-summary.md
Do not add cluster-mutating targets to CI.

Tests
Add or update unit tests:

tests/unit/test_goal_003_synthetic_api_structure.py
tests/unit/test_goal_003_openapi_specs.py
tests/unit/test_goal_003_api_ownership_metadata.py
tests/unit/test_goal_003_route_matrix.py
tests/unit/test_goal_003_synthetic_clients.py
tests/unit/test_goal_003_runtime_boundary.py
Add or update policy tests:

tests/policy/test_goal_003_no_forbidden_kong_resources.py
tests/policy/test_goal_003_exposure_policy.py
tests/policy/test_goal_003_no_auth_until_goal004.py
tests/policy/test_goal_003_no_secrets.py
tests/policy/test_goal_003_network_policy.py
Test requirements:

all six APIs exist
all six APIs have OpenAPI specs
all six APIs have ownership metadata
all six APIs have tenant manifests
all six APIs have mock backend manifests
all six APIs have services
all six APIs have HTTPRoutes
all six APIs have NetworkPolicies
all six APIs have positive and negative test definitions
all six synthetic clients exist
API catalog exists
route matrix exists
exposure policy exists
OpenAPI specs parse
OpenAPI specs contain required metadata
ownership metadata matches route matrix
route hosts are correct
route path prefixes are correct
external exposure is limited to open-banking only
internal APIs are not externally exposed
no wildcard hostnames exist
no catch-all routes exist
no Admin API routes exist
no KongPlugin resources exist
no KongClusterPlugin resources exist
no KongConsumer resources exist
no API keys exist
no Kubernetes Secrets are committed
no kubeconfigs are committed
no private keys are committed
no latest image tags are used
mock backend image is pinned
temporary no-auth posture is labelled
future goal 004 security posture is documented
NetworkPolicies exist for every API
cluster-mutating targets are guarded
CI remains cluster-free
goal 002 runtime fixes are not removed
Tests must run locally.

Tests must not require Kubernetes.

Tests must not require Docker.

Tests must not require internet access.

CI requirements
Update CI to include local-only goal 003 checks.

CI must run:

make validate-synthetic-apis
make openapi-lint
make render-synthetic-apis
make synthetic-api-static-test
make synthetic-api-contract-test
make synthetic-api-smoke-plan
CI must not run:

make synthetic-api-install-dry-run
make synthetic-api-apply
make synthetic-api-smoke
make synthetic-api-negative-test
make synthetic-api-rollback
make synthetic-api-runtime-ready
CI must remain cluster-free.

Local validation commands
Run from the repository root.

Required local gate:

make validate
make validate-yaml
make validate-kustomize
make validate-synthetic-apis
make openapi-lint
make render-synthetic-apis
make synthetic-api-static-test
make synthetic-api-contract-test
make synthetic-api-smoke-plan
make test
make policy-test
make docs
make evidence-goal-003
Full local gate:

make validate && make validate-yaml && make validate-kustomize && make validate-synthetic-apis && make openapi-lint && make render-synthetic-apis && make synthetic-api-static-test && make synthetic-api-contract-test && make synthetic-api-smoke-plan && make test && make policy-test && make docs && make evidence-goal-003
Expected result:

all local checks pass
no cluster mutation occurs
no secrets are created
no Kong Enterprise features are used
no Kong auth/rate-limit resources are created
goal 003 evidence is generated
Do not include goal 002 revalidation in the required local gate.

Runtime boundary
Goal 003 is repo-safe by default.

Cluster mutation is not permitted unless explicit user permission is granted.

Permission must include:

Branch:
Commit:
Target Kubernetes context:
Commands approved:
Expected resources to change:
Expected resources not to change:
Rollback command:
Approval:
Required environment variables before mutation:

export BANKLAB_ALLOW_CLUSTER_MUTATION=true
export BANKLAB_TARGET_CONTEXT=<expected-kubernetes-context>
Before mutation, verify:

kubectl config current-context
The output must exactly match:

$BANKLAB_TARGET_CONTEXT
Cluster-mutating commands for this goal:

make synthetic-api-apply
make synthetic-api-rollback
These must fail closed without the mutation guard.

Cluster-read-only runtime validation commands:

make synthetic-api-smoke
make synthetic-api-negative-test
platform/kong/synthetic-apis/scripts/collect-synthetic-api-evidence.sh
make synthetic-api-runtime-ready
These must not mutate the cluster.

Optional runtime apply sequence
Run only after explicit permission is granted.

Pre-apply local checks:

make validate-synthetic-apis
make openapi-lint
make render-synthetic-apis
make synthetic-api-static-test
make synthetic-api-contract-test
make synthetic-api-smoke-plan
Dry-run:

make synthetic-api-install-dry-run
Apply:

make synthetic-api-apply
Runtime smoke:

make synthetic-api-smoke
Runtime negative tests:

make synthetic-api-negative-test
Admin API safety check:

make kong-admin-exposure-test
Evidence collection:

platform/kong/synthetic-apis/scripts/collect-synthetic-api-evidence.sh
make evidence-goal-003
make synthetic-api-runtime-ready
Expected runtime success:

all six mock backends ready
all intended HTTPRoutes accepted
internal routes return expected markers
external open-banking route returns expected marker
unknown host returns expected Kong 404
invalid path returns expected failure
internal APIs are not externally exposed
Admin API remains externally unreachable
synthetic-api-runtime-ready passes
Runtime smoke requirements
Runtime smoke must test:

GET http://api.internal.banklab.test/accounts/v1/health
GET http://api.internal.banklab.test/payments/v1/health
GET http://api.internal.banklab.test/cards/v1/health
GET http://api.internal.banklab.test/customers/v1/health
GET http://api.internal.banklab.test/fraud/v1/health
GET http://api.external.banklab.test/open-banking/v1/health
Expected markers:

banklab-accounts-ok
banklab-payments-ok
banklab-cards-ok
banklab-customer-profile-ok
banklab-fraud-decisions-ok
banklab-open-banking-ok
Runtime smoke may use:

Host headers
curl --resolve
LoadBalancer IP
port-forward fallback
If LoadBalancer or DNS is unavailable, record the blocker and use the documented fallback. Do not claim full external route validation unless the external route is actually tested.

Negative runtime tests must verify:

unknown host returns Kong 404
unknown route returns expected failure
accounts is not reachable through api.external.banklab.test
payments is not reachable through api.external.banklab.test
cards is not reachable through api.external.banklab.test
customer-profile is not reachable through api.external.banklab.test
fraud-decisions is not reachable through api.external.banklab.test
Admin API is not reachable through proxy
Admin API service is not LoadBalancer
Admin API service is not NodePort
Evidence requirements
Create or update:

reports/goal-003-summary.md
The report must include:

Goal: goal-003-synthetic-bank-apis
Status:
Branch:
Commit:
Generated at:

Objective summary:

Baseline assumed:
- Kong OSS runtime verified:
- GatewayClass:
- Internal Gateway:
- External Gateway:
- Admin API external exposure:
- Goal 002 runtime fixes preserved:

Created APIs:
- accounts:
- payments:
- cards:
- customer-profile:
- fraud-decisions:
- open-banking:

Synthetic clients:
- mobile-banking-app:
- internet-banking-web:
- internal-crm:
- fraud-platform:
- payments-processor:
- external-fintech-partner:

Local validation commands run:
- make validate:
- make validate-yaml:
- make validate-kustomize:
- make validate-synthetic-apis:
- make openapi-lint:
- make render-synthetic-apis:
- make synthetic-api-static-test:
- make synthetic-api-contract-test:
- make synthetic-api-smoke-plan:
- make test:
- make policy-test:
- make docs:
- make evidence-goal-003:

Runtime commands run:
- make synthetic-api-install-dry-run:
- make synthetic-api-apply:
- make synthetic-api-smoke:
- make synthetic-api-negative-test:
- make kong-admin-exposure-test:
- collect-synthetic-api-evidence:
- make synthetic-api-runtime-ready:

Route matrix:
-

Exposure policy:
-

OpenAPI validation:
-

NetworkPolicy validation:
-

Cluster changes performed:

Secrets created:

Kong Enterprise features used:

KongPlugin resources created:

KongConsumer resources created:

Authentication configured:

Rate limiting configured:

Runtime verification:

Known limitations:

Ready for next goal:
Required local-only values when runtime apply is not run:

Status: pass; local-only
Cluster changes performed: none
Secrets created: none
Kong Enterprise features used: none
KongPlugin resources created: none
KongConsumer resources created: none
Authentication configured: no; deferred to goal-004
Rate limiting configured: no; deferred to goal-004
Runtime verification: not run
Ready for next goal: no; run guarded synthetic API apply and smoke before goal-004, unless explicitly accepted as local-only
Required values when runtime apply and smoke pass:

Status: pass; runtime-verified
Cluster changes performed: synthetic bank APIs applied
Secrets created: none
Kong Enterprise features used: none
KongPlugin resources created: none
KongConsumer resources created: none
Authentication configured: no; deferred to goal-004
Rate limiting configured: no; deferred to goal-004
Runtime verification: pass
Ready for next goal: goal-004-auth-rate-limit-security
If runtime apply is attempted but fails:

Status: failed or blocked
Cluster changes performed: recorded
Runtime verification: failed or partial
Ready for next goal: no
Do not claim runtime success unless runtime commands actually pass.

Additional evidence files
Generate:

reports/synthetic-api-smoke-plan.md
It must include:

host
path
expected status
expected marker
gateway
tenant namespace
service
client persona
negative cases
If runtime is run, update:

reports/synthetic-api-runtime-evidence.md
reports/synthetic-api-route-smoke-results.md
reports/synthetic-api-negative-test-results.md
Each runtime evidence file must support:

not run
pass
fail
blocked
Acceptance criteria
The goal body is saved at:

soydocs/kong-bank-lab/goals/goal-003-synthetic-bank-apis.md
All six synthetic APIs exist.

All six APIs have valid OpenAPI specs.

All six APIs have ownership metadata.

All six APIs have tenant manifests.

All six APIs have mock backend manifests.

All six APIs have service manifests.

All six APIs have HTTPRoute manifests.

All six APIs have NetworkPolicy manifests.

All six APIs have positive and negative test definitions.

All six synthetic client profiles exist.

The API catalog exists.

The route matrix exists.

The exposure policy exists.

The API catalog documentation builds.

The internal APIs attach only to the internal Gateway.

The Open Banking API attaches only to the external Gateway.

No wildcard routes exist.

No catch-all routes exist.

No Admin API route exists.

No Kong Enterprise features are used.

No KongPlugin resources are created.

No KongClusterPlugin resources are created.

No KongConsumer resources are created.

No authentication is configured.

No rate limiting is configured.

No Redis dependency is introduced.

No real secrets are committed.

No kubeconfigs are committed.

No private keys are committed.

Mock backend images are pinned.

No image uses latest.

Every unauthenticated route is labelled as temporary, synthetic, sandbox-only, and deferred to goal 004 for security controls.

Every tenant API has a NetworkPolicy allowing only the intended Kong-to-upstream path.

Goal 002 runtime fixes are preserved.

Local validation passes.

CI remains cluster-free.

Cluster mutation remains guarded.

Evidence report exists.

Stop/gate condition
Local-only completion
Stop after the repo-safe synthetic API layer is implemented, all required local validation commands pass, and reports/goal-003-summary.md is updated.

Required final local-only state:

Status: pass; local-only
Cluster changes performed: none
Runtime verification: not run
Ready for next goal: no; runtime apply and smoke required before goal-004 unless explicitly accepted as local-only
Do not proceed to goal 004 after local-only completion.

Do not mutate the cluster without explicit permission.

Runtime-verified completion
If explicit cluster mutation permission is granted, stop after applying the synthetic APIs, running smoke tests, running negative tests, confirming Admin API exposure remains negative, collecting evidence, and updating reports/goal-003-summary.md.

Required final runtime-verified state:

Status: pass; runtime-verified
Cluster changes performed: synthetic bank APIs applied
Runtime verification: pass
Ready for next goal: goal-004-auth-rate-limit-security
Failed or blocked runtime completion
If runtime apply or smoke tests fail, stop after recording evidence and either leaving the cluster for investigation or running guarded rollback if explicitly approved.

Required final failed or blocked state:

Status: failed or blocked
Runtime verification: failed or partial
Ready for next goal: no
Do not hide failed runtime checks.

Do not bypass failed runtime checks.

Do not continue to goal 004 until runtime status is pass or the user explicitly records an accepted exception.
