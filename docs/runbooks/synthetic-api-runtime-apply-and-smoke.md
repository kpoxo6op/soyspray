# Synthetic API Runtime Apply And Smoke

Purpose: move goal 003 from local-only to runtime-verified only after explicit
approval, guarded apply, route smoke, negative tests, Admin API safety checks,
and evidence collection.

Required approval before mutation:

```text
I approve running gate-003-synthetic-api-runtime-apply-and-smoke cluster-mutating commands.

Branch: kong-goals-foundation
Commit: <current-HEAD-short-sha>
Target Kubernetes context: kubernetes-admin@cluster.local
Commands approved:
- make synthetic-api-tenant-namespaces-dry-run
- make synthetic-api-tenant-namespaces-apply
- make synthetic-api-install-dry-run
- make synthetic-api-apply
- make synthetic-api-smoke
- make synthetic-api-negative-test
- make kong-admin-exposure-test
- platform/kong/synthetic-apis/scripts/collect-synthetic-api-evidence.sh
- platform/kong/synthetic-apis/scripts/collect-synthetic-api-runtime-state.sh
- make evidence-goal-003
- make evidence-gate-003-synthetic-api-runtime
- make goal003-runtime-ready

Expected resources to change:
- tenant-accounts Namespace if absent
- tenant-payments Namespace if absent
- tenant-cards Namespace if absent
- tenant-customer-profile Namespace if absent
- tenant-fraud Namespace if absent
- tenant-open-banking Namespace if absent
- tenant-accounts synthetic API resources
- tenant-payments synthetic API resources
- tenant-cards synthetic API resources
- tenant-customer-profile synthetic API resources
- tenant-fraud synthetic API resources
- tenant-open-banking synthetic API resources
- synthetic API Deployments
- synthetic API Services
- synthetic API ConfigMaps
- synthetic API HTTPRoutes
- synthetic API NetworkPolicies

Expected resources not to change:
- Kong Gateway deployment
- Kong Ingress Controller deployment
- Kong GatewayClass except status reconciliation
- Kong internal and external Gateways except status reconciliation
- Kong Admin API service
- Kong CRDs
- Gateway API CRDs
- platform prereq namespaces other than the six listed tenant namespaces
- unrelated namespaces
- unrelated secrets
- unrelated workloads

Rollback command:
- make synthetic-api-rollback

Rollback note:
- Rollback removes synthetic API resources.
- Rollback intentionally leaves tenant Namespace prereqs in place.

Approval:
- approved
```

Before mutation:

```bash
make validate
make validate-yaml
make validate-kustomize
make validate-synthetic-apis
make openapi-lint
make render-synthetic-api-tenant-namespaces
make render-synthetic-apis
make synthetic-api-static-test
make synthetic-api-contract-test
make synthetic-api-smoke-plan
make test
make policy-test
make docs
make validate-synthetic-api-runtime-gate
```

After explicit approval:

```bash
export BANKLAB_ALLOW_CLUSTER_MUTATION=true
export BANKLAB_TARGET_CONTEXT=<expected-kubernetes-context>
kubectl config current-context
make synthetic-api-tenant-namespaces-dry-run
make synthetic-api-tenant-namespaces-apply
make synthetic-api-install-dry-run
make synthetic-api-apply
make synthetic-api-smoke
make synthetic-api-negative-test
make kong-admin-exposure-test
platform/kong/synthetic-apis/scripts/collect-synthetic-api-evidence.sh
platform/kong/synthetic-apis/scripts/collect-synthetic-api-runtime-state.sh
make evidence-goal-003
make evidence-gate-003-synthetic-api-runtime
make goal003-runtime-ready
```

Namespace bootstrap:
- Tenant namespaces are sourced from `platform/namespaces`.
- The goal003 runtime gate applies only the six tenant namespaces required by
  the synthetic APIs.
- Namespace bootstrap is guarded and explicitly approved.
- The synthetic API rollback removes synthetic API resources but intentionally
  leaves tenant namespace prereqs in place.
- Do not delete tenant namespaces as part of normal synthetic API rollback.

Rollback path:

```bash
export BANKLAB_ALLOW_CLUSTER_MUTATION=true
export BANKLAB_TARGET_CONTEXT=<expected-kubernetes-context>
make synthetic-api-rollback
```

Do not start goal 004 until `make goal003-runtime-ready` passes.
