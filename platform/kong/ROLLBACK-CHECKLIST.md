# Rollback Checklist

Rollback requires explicit cluster mutation permission.

- Rollback reason is recorded.
- Current Kubernetes context is recorded.
- Approved rollback command is recorded.
- `BANKLAB_ALLOW_CLUSTER_MUTATION=true` is set only for the rollback run.
- `BANKLAB_TARGET_CONTEXT` matches the intended cluster.
- `make kong-rollback` runs through the mutation guard.
- Remaining Kong resources are inspected with read-only commands.
- Resources outside the approved Kong baseline scope are not removed.
- Evidence records rollback result and follow-up action.
