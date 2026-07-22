# In-cluster documentation site

This package publishes the repository's MkDocs guide inside the cluster at the
bank lab documentation address.

The pod has three responsibilities: `git-sync` fetches the selected revision,
the builder creates a strict MkDocs site, and unprivileged Nginx serves the last
successful build.

| Area | Files |
| --- | --- |
| Runtime configuration | [`config/`](config/) |
| Workload | [`deployment.yaml`](deployment.yaml) |
| Access | [`service.yaml`](service.yaml), [`ingress.yaml`](ingress.yaml) |
| Isolation | [`namespace.yaml`](namespace.yaml), [`networkpolicy.yaml`](networkpolicy.yaml) |
| Package entry point | [`kustomization.yaml`](kustomization.yaml) |
