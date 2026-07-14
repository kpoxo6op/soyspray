# Verify

## Local gate

```sh
make check
```

This validates YAML and rendered manifests, runs the focused pytest suite, and
builds the documentation in strict mode.

## Runtime gate

```sh
make status
make smoke
```

Pass criteria:

- all three nodes are `Ready`
- every bank-lab Argo Application is `Synced` and `Healthy`
- two Kong gateway pods are available
- the customer app returns `200`
- valid API requests pass through Kong
- missing credentials are rejected
- the Admin API has no public exposure
- Grafana shows current request metrics

If Argo reports drift, inspect the diff before syncing. A shared object may still
be owned by an older Application during migration.
