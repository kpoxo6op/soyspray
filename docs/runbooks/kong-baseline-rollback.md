# Kong Baseline Rollback

Preferred rollback is Git revert followed by Argo CD sync to the previous known
good commit.

The local helper target exists as an explicit, guarded path:

```bash
CONFIRM_KONG_ROLLBACK=1 make kong-rollback
```

Rollback must remove or revert only goal-002 Kong resources:

- `platform-kong`
- `platform-kong-smoke`
- Kong Gateway API resources
- Kong smoke routes and backend

Do not delete prerequisite namespaces, MetalLB, cert-manager, SOPS examples, or
other tenant/platform resources.
