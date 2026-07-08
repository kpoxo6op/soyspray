# Goal005 Tenancy, RBAC, And Change Control Decision

Status: accepted-for-implementation

## Context

Goal004 proved authentication, authorization, correlation IDs, Redis-backed
rate limits, and Admin API exposure safety for the six synthetic banking APIs.
Goal005 needs to prove that API ownership can be delegated without weakening
those controls.

## Decision

Use catalog metadata, Kubernetes namespaces, Kubernetes RBAC, namespaced Kong
resources, runtime impersonation checks, and Git-owned change-control records to
simulate a bank platform tenancy model on Kong OSS.

## Kong OSS Limitation

Kong OSS does not provide Enterprise Workspaces, Enterprise RBAC, Konnect, Kong
Manager, or an Enterprise Developer Portal. This lab therefore treats
`logical_workspace` as catalog metadata only.

## Kubernetes RBAC Simulation Approach

Tenant service accounts are created in tenant-owned namespaces and bound only to
Roles in namespaces that contain the tenant's API products. Roles allow safe
namespaced API configuration resources and do not include Secrets,
NetworkPolicies, cluster-scoped Kong resources, cluster RBAC, webhooks, or Kong
Admin resources.

## Consequences

The model is simple and auditable, but it is a simulation. It proves delegation
and isolation behavior through Kubernetes permissions rather than through Kong
Enterprise control planes.

## Risks

- Namespace-per-API ownership is more granular than a real enterprise workspace.
- Tenant service accounts can update selected namespaced API resources, so RBAC
  validation must remain strict.
- Runtime evidence depends on the Kubernetes API server's impersonation checks.

## Follow-Up Candidates

- Add policy-as-code once the OSS baseline has more goals behind it.
- Add richer audit evidence around pull requests and approvals.
- Add a portal or developer catalog only after the core runtime model is
  stable.
