# Goal005 Tenancy Model

Goal005 simulates a bank platform operating model on Kong OSS. It does not use
Kong Enterprise Workspaces or Enterprise RBAC. The logical workspace is catalog
metadata only; Kubernetes namespaces and Kubernetes RBAC provide the runtime
isolation proof.

## Platform Team Responsibilities

The `kong-platform` owner controls the shared gateway, Kong controller,
credential lifecycle, Admin API exposure posture, baseline security plugins,
runtime evidence, and rollback runbooks. Runtime credential Secrets remain
platform-owned and are generated from local operator environment variables only.

## Tenant Team Responsibilities

Tenant teams own API product metadata and low-risk namespaced API configuration
inside their approved scope. Tenant applier service accounts can read and
server-side dry-run apply safe namespaced Kong/API resources only in namespaces
assigned to their tenant.

Tenant teams cannot read Secrets, manage NetworkPolicies, create
KongClusterPlugins, modify cluster RBAC, modify webhook configuration, access
other tenants, or expose Kong Admin resources.

## Logical Workspaces

Logical workspaces are recorded in `platform/catalog/tenants.yaml` and
`platform/catalog/api-products/*.yaml`.

| Logical Workspace | Tenant | APIs |
| --- | --- | --- |
| `retail-banking` | `retail-accounts` | `accounts`, `cards`, `customer-profile` |
| `payments-banking` | `payments` | `payments`, `open-banking` |
| `risk-compliance` | `risk-compliance` | `fraud-decisions` |

## Why Kubernetes RBAC

Kong OSS does not include Enterprise Workspaces or Enterprise RBAC. Kubernetes
RBAC gives this lab a small, auditable approximation: tenant service accounts
are bound only to Roles in tenant-owned API namespaces, while platform service
accounts keep control of shared platform resources.

## API Product Ownership

Every API product has exactly one tenant owner, explicit exposure and data
classification, required security plugins, optional tenant plugins, runbook
metadata, and platform-owned credential ownership. The catalog is the source of
truth and the goal005 renderers use it to stamp ownership labels and annotations
onto Kong-facing resources.
