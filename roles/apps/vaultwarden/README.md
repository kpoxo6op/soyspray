# Vaultwarden application role

This role manages the Vaultwarden Argo CD resources and the runtime bootstrap
Secret.

- [`defaults`](defaults/README.md) defines the public inputs.
- [`tasks`](tasks/README.md) contains the enabled and disabled paths.

Reconcile the application from the repository root:

```bash
make vaultwarden VAULTWARDEN_REVISION=HEAD
```

Remove the application without deleting its bootstrap Secret or retained data
volume:

```bash
make vaultwarden VAULTWARDEN_ENABLED=false
```
