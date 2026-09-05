# GitHub Actions workflows

[`ci.yml`](ci.yml) runs for pushes and pull requests. It installs the pinned
development tools and runs `make check`.

The gate checks Python formatting and lint, Ansible lint, YAML
validation, rendered Kustomize packages, and application tests. It does
not deploy or modify the cluster.
