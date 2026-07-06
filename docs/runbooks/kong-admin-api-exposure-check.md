# Kong Admin API Exposure Check

Static check:

```bash
make kong-admin-exposure-test
```

After cluster apply, also inspect services and routes:

```bash
kubectl -n platform-kong get service
kubectl get gateway -A
kubectl get httproute -A
```

Expected result:

- No Admin API Service is `LoadBalancer` or `NodePort`.
- No Gateway or HTTPRoute points at Admin API.
- Proxy Service is the only external Service.
- Kong Manager and Portal are disabled.

If Admin API exposure is found, stop rollout and revert the goal-002 change.
