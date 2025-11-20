# ArgoCD Applications

GitOps application definitions organized by functional domain.

## Domains

Applications are organized into functional domains:

### infrastructure/
Core cluster infrastructure components (certificates, storage, DNS, dashboards).

### database/
Database operators and instances.

### media/
Media stack applications.

### observability/
Monitoring, logging, and alerting tools.

### backups/
Backup and disaster recovery solutions.

## Application Structure

Each application directory contains:

- `*-application.yaml` - ArgoCD Application resource
- `kustomization.yaml` - Kustomize configuration (if used)
- `values.yaml` or `defaults.yaml` - Helm values (if using Helm)
- Kubernetes manifests - Deployment, Service, Ingress, etc.
- `README.md` - Application-specific documentation

## Target Revision Management

When working on feature branches, update the `targetRevision` field in `*-application.yaml`:

```yaml
spec:
  source:
    repoURL: "https://github.com/kpoxo6op/soyspray.git"
    targetRevision: "cinema"  # Match the working branch
    path: argocd/applications/media/radarr
```

Update `targetRevision` to match the working branch or tag when making changes.

