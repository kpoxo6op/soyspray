# GitHub Actions workflows

[`ci.yml`](ci.yml) runs for pushes and pull requests. It installs the pinned
development tools and runs `make check`.

The gate checks Python formatting and lint, Ansible lint, YAML and OpenAPI
validation, rendered Kustomize packages, tests, and the MkDocs build. It does
not deploy or modify the cluster.
