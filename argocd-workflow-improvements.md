# ArgoCD Development Workflow Improvements

## Current Workflow Analysis

### Pain Points Identified
1. **Manual targetRevision management** - Having to update `targetRevision` in multiple ArgoCD applications
2. **Branch-based development** - Using branch names in `targetRevision` during development
3. **Manual tag management** - Forgetting to update tags in multiple places
4. **Repetitive actions** - Too many manual steps that are error-prone

### Current State Review
Your applications show inconsistent `targetRevision` patterns:
- `dingu`: Uses branch name `"dingu"`
- `readarr`, `prometheus`, `cert-manager`: Use tag `"v1.16.0"`

## Recommended Improved Workflow

### 1. Environment-Based Strategy

**Development Environment:**
```yaml
# Use HEAD/main branch for development
targetRevision: "HEAD"  # or "main"
```

**Production Environment:**
```yaml
# Use semantic versioning tags for production
targetRevision: "v1.16.0"
```

### 2. Automated Workflow with CI/CD

#### Option A: GitHub Actions/GitLab CI Pipeline
```yaml
# .github/workflows/argocd-deploy.yml
name: ArgoCD Deploy
on:
  push:
    branches: [main]
    tags: ['v*']
  pull_request:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Update targetRevision for development
        if: github.ref == 'refs/heads/main'
        run: |
          find playbooks/yaml/argocd-apps -name "*-application.yaml" -exec \
            sed -i 's/targetRevision: .*/targetRevision: "HEAD"/' {} \;
          
      - name: Update targetRevision for production
        if: startsWith(github.ref, 'refs/tags/v')
        run: |
          TAG=${GITHUB_REF#refs/tags/}
          find playbooks/yaml/argocd-apps -name "*-application.yaml" -exec \
            sed -i "s/targetRevision: .*/targetRevision: \"$TAG\"/" {} \;
```

#### Option B: Kustomize with Overlays (Recommended)
Restructure your applications to use Kustomize overlays:

```
argocd-apps/
├── base/
│   ├── dingu/
│   │   ├── deployment.yaml
│   │   ├── service.yaml
│   │   └── kustomization.yaml
│   └── readarr/
│       ├── deployment.yaml
│       ├── service.yaml
│       └── kustomization.yaml
├── overlays/
│   ├── dev/
│   │   ├── dingu-application.yaml
│   │   ├── readarr-application.yaml
│   │   └── kustomization.yaml
│   └── prod/
│       ├── dingu-application.yaml
│       ├── readarr-application.yaml
│       └── kustomization.yaml
```

### 3. ApplicationSet Pattern (Best Practice)

Replace individual Application manifests with ApplicationSet:

```yaml
# argocd-appset.yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: media-stack
  namespace: argocd
spec:
  generators:
  - git:
      repoURL: https://github.com/kpoxo6op/soyspray.git
      revision: HEAD
      directories:
      - path: playbooks/yaml/argocd-apps/*
  template:
    metadata:
      name: '{{path.basename}}'
      namespace: argocd
    spec:
      project: default
      source:
        repoURL: https://github.com/kpoxo6op/soyspray.git
        targetRevision: '{{.targetRevision | default "HEAD"}}'
        path: '{{path}}'
      destination:
        server: https://kubernetes.default.svc
        namespace: '{{.namespace | default "media"}}'
      syncPolicy:
        automated:
          prune: true
          selfHeal: true
        syncOptions:
          - CreateNamespace=true
```

### 4. Simplified Development Workflow

#### New Recommended Workflow:
1. **Create feature branch** - `git checkout -b feature/new-feature`
2. **Develop and test** - Make changes, test locally
3. **Commit changes** - `git commit -m "feat: add new feature"`
4. **Push branch** - `git push origin feature/new-feature`
5. **Create MR/PR** - Review process
6. **Merge to main** - Automatic deployment to dev environment
7. **Create release** - `git tag v1.17.0 && git push origin v1.17.0`
8. **Automatic production deployment** - Triggered by tag

#### Benefits:
- ✅ **Fewer manual steps** - No more manual targetRevision updates
- ✅ **Consistent versioning** - Automated tag management
- ✅ **Environment separation** - Clear dev/prod boundaries
- ✅ **Rollback safety** - Easy to revert to previous versions

### 5. Automation Scripts

Create helper scripts for common tasks:

```bash
#!/bin/bash
# scripts/release.sh
set -e

VERSION=$1
if [ -z "$VERSION" ]; then
    echo "Usage: $0 <version>"
    exit 1
fi

# Create and push tag
git tag "$VERSION"
git push origin "$VERSION"

# Update all applications to new version
find playbooks/yaml/argocd-apps -name "*-application.yaml" -exec \
    sed -i "s/targetRevision: .*/targetRevision: \"$VERSION\"/" {} \;

# Commit the updates
git add playbooks/yaml/argocd-apps/
git commit -m "chore: update applications to $VERSION"
git push origin main

echo "Released $VERSION successfully!"
```

### 6. Best Practices Implementation

#### Git Flow Strategy:
- **main** branch → Development environment (targetRevision: "HEAD")
- **tags** (v1.x.x) → Production environment (targetRevision: "v1.x.x")
- **feature branches** → Local development only

#### Semantic Versioning:
- **MAJOR**: Breaking changes
- **MINOR**: New features, backward compatible
- **PATCH**: Bug fixes, backward compatible

#### ArgoCD Configuration:
```yaml
# Recommended sync policy
syncPolicy:
  automated:
    prune: true
    selfHeal: true
  retry:
    limit: 5
    backoff:
      duration: "10s"
      factor: 2
      maxDuration: "5m"
  syncOptions:
    - CreateNamespace=true
    - PrunePropagationPolicy=foreground
    - PruneLast=true
```

## Implementation Plan

### Phase 1: Quick Wins (1-2 days)
1. Standardize all applications to use the same targetRevision pattern
2. Create release script for automated tagging
3. Update sync policies for better reliability

### Phase 2: Environment Separation (1 week)
1. Implement Kustomize overlays for dev/prod
2. Set up automated targetRevision updates
3. Create development environment applications

### Phase 3: Full Automation (2-3 weeks)
1. Implement ApplicationSet pattern
2. Set up CI/CD pipeline
3. Add monitoring and alerting for deployments

## Quick Start Implementation

To immediately improve your current workflow:

```bash
# 1. Standardize all applications to use HEAD for development
find playbooks/yaml/argocd-apps -name "*-application.yaml" -exec \
    sed -i 's/targetRevision: .*/targetRevision: "HEAD"/' {} \;

# 2. Create a release when ready for production
git tag v1.17.0
git push origin v1.17.0

# 3. Update production applications to use the new tag
find playbooks/yaml/argocd-apps -name "*-application.yaml" -exec \
    sed -i 's/targetRevision: .*/targetRevision: "v1.17.0"/' {} \;

# 4. Commit and push the updates
git add .
git commit -m "chore: update applications to v1.17.0"
git push origin main
```

This approach will immediately reduce your manual work and provide a foundation for further automation.