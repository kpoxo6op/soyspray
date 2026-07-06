# Kong Runtime Rollback Checklist

Rollback is a cluster-mutating action and requires the same explicit permission
guard as apply.

## When To Roll Back

- Kong or KIC pods cannot become ready.
- Gateway API resources are rejected.
- Smoke routes fail and no local configuration fix is safe.
- Kong Admin API becomes externally exposed.
- The apply touched resources outside the approved scope.

## Command Path

```bash
BANKLAB_ALLOW_CLUSTER_MUTATION=true BANKLAB_TARGET_CONTEXT=<expected-context> make kong-rollback
```

## Expected Reverts

- Kong baseline resources are removed or reverted.
- Smoke resources are removed or reverted.
- Gateway API smoke resources are removed or reverted.

## Resources That Must Not Be Removed

- Existing cluster prerequisites unless separately approved.
- Business API workloads.
- Real secrets.
- Argo CD itself.
- MetalLB, cert-manager, or unrelated platform namespaces.

## Post-Rollback Validation

Run read-only checks, record remaining resources, update evidence, and decide
whether to fix locally or request a new apply gate.
