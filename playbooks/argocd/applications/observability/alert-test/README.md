# Alert Test Application

This ArgoCD application deploys four demo workloads that trigger specific Prometheus/Loki alerts for testing the alerting pipeline.

## Workloads

1. **crashloop-tester** - Triggers `KubePodCrashLooping`
2. **unschedulable-deployment** - Triggers `KubeDeploymentReplicasMismatch`
3. **always-fail** - Triggers `KubeJobFailed`
4. **error-burst** - Triggers `ApplicationErrorBurst` (Loki)
