# Alert Test Application

This ArgoCD application deploys four demo workloads that trigger specific Prometheus/Loki alerts for testing the alerting pipeline.

## Workloads

1. **crashloop-tester** - Triggers `KubePodCrashLooping`
2. **unschedulable-deployment** - Triggers `KubeDeploymentReplicasMismatch`
3. **always-fail** - Triggers `KubeJobFailed`
4. **error-burst** - Triggers `ApplicationErrorBurst` (Loki)

## Deploy Test Workloads

```bash
kubectl apply -f playbooks/yaml/argocd-apps/alert-test/alert-test-application.yaml

kubectl -n argocd get applications.argoproj.io alert-test -w
```

## Re-run Tests

Re-apply the Application manifest from the Deploy section. For a fresh failing job run without re-deploying:

```bash
kubectl -n alert-test delete job always-fail
```
