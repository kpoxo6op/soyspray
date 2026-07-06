# Kong Baseline Install

Do not run this by default. Cluster changes require explicit user permission.

Before apply:

```bash
kubectl apply -f https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.3.0/standard-install.yaml
make validate && make validate-yaml && make validate-kustomize && make validate-prereqs
make validate-kong-baseline && make render-kong-baseline
make kong-static-test && make kong-admin-exposure-test
make cluster-smoke && make cluster-prereq-smoke
make kong-install-dry-run
```

Apply only after permission:

```bash
make kong-apply
```

Then verify:

```bash
make kong-cluster-smoke
make kong-route-smoke
make kong-admin-exposure-test
```

Do not claim Kong is installed unless apply and smoke checks pass.
