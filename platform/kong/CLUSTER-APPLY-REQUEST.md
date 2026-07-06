# Cluster Apply Request

Do not run cluster-mutating commands until approval is explicitly granted.

- Requested by:
- Date:
- Branch:
- Commit:
- Target cluster context:
- Commands requested:
- Expected resources to change:
- Expected resources not to change:
- Rollback command:
- Preflight evidence:
- Approval:

Required guarded command shape:

```bash
BANKLAB_ALLOW_CLUSTER_MUTATION=true BANKLAB_TARGET_CONTEXT=<expected-context> make kong-apply
```
