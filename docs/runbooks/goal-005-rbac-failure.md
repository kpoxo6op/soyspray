# Goal005 RBAC Failure Runbook

## Symptoms

- `make goal005-rbac-smoke` reports an unexpected `yes` for a denied action.
- A tenant service account can read Secrets, access another tenant namespace,
  create a NetworkPolicy, create a KongClusterPlugin, or modify cluster-scoped
  RBAC/webhook resources.

## Likely Causes

- A Role contains a forbidden resource such as `secrets` or `networkpolicies`.
- A RoleBinding points to the wrong service account namespace.
- A tenant service account was bound in another tenant namespace.
- A ClusterRoleBinding accidentally grants broad permissions.

## Identify The Permission

Run the exact failing `kubectl auth can-i` line from
`reports/goal-005-rbac-runtime.md`, then inspect the Role and RoleBinding in
the reported namespace.

```sh
kubectl -n <namespace> get role goal005-tenant-api-applier -o yaml
kubectl -n <namespace> get rolebinding goal005-tenant-api-applier -o yaml
```

## Roll Back

Revert the offending Role or RoleBinding change in Git, push the branch, then
reapply the stable goal005 RBAC resources.

```sh
make goal005-tenancy-rbac-apply
make goal005-rbac-smoke
```

Tenant isolation is restored only when every denied check in
`reports/goal-005-rbac-runtime.md` reports `PASS`.
