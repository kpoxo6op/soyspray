# Goal005 Tenancy RBAC Apply

Status: pass

Supported states: not run, pass, fail, blocked, partial

Command: make goal005-tenancy-rbac-apply

Generated at: 2026-07-09T00:27:56+12:00

Kubernetes context: kubernetes-admin@cluster.local

## Output
namespace/tenant-accounts unchanged
namespace/tenant-cards unchanged
namespace/tenant-customer-profile unchanged
namespace/tenant-fraud unchanged
namespace/tenant-open-banking unchanged
namespace/tenant-payments unchanged
serviceaccount/retail-accounts-api-applier unchanged
serviceaccount/payments-api-applier unchanged
serviceaccount/risk-compliance-api-applier unchanged
serviceaccount/kong-platform-change-applier unchanged
role.rbac.authorization.k8s.io/goal005-tenant-api-applier unchanged
role.rbac.authorization.k8s.io/goal005-tenant-api-applier unchanged
role.rbac.authorization.k8s.io/goal005-tenant-api-applier unchanged
role.rbac.authorization.k8s.io/goal005-tenant-api-applier unchanged
role.rbac.authorization.k8s.io/goal005-tenant-api-applier unchanged
role.rbac.authorization.k8s.io/goal005-tenant-api-applier unchanged
role.rbac.authorization.k8s.io/goal005-platform-change-reader unchanged
rolebinding.rbac.authorization.k8s.io/goal005-tenant-api-applier unchanged
rolebinding.rbac.authorization.k8s.io/goal005-tenant-api-applier unchanged
rolebinding.rbac.authorization.k8s.io/goal005-tenant-api-applier unchanged
rolebinding.rbac.authorization.k8s.io/goal005-tenant-api-applier unchanged
rolebinding.rbac.authorization.k8s.io/goal005-tenant-api-applier unchanged
rolebinding.rbac.authorization.k8s.io/goal005-tenant-api-applier unchanged
rolebinding.rbac.authorization.k8s.io/goal005-platform-change-reader unchanged
configmap/goal005-tenant-catalog unchanged
httproute.gateway.networking.k8s.io/banklab-accounts configured
httproute.gateway.networking.k8s.io/banklab-payments configured
httproute.gateway.networking.k8s.io/banklab-cards configured
httproute.gateway.networking.k8s.io/banklab-customer-profile configured
httproute.gateway.networking.k8s.io/banklab-fraud-decisions configured
httproute.gateway.networking.k8s.io/banklab-open-banking configured
