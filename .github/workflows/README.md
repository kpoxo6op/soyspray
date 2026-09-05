# GitHub Actions workflows

[`ci.yml`](ci.yml) runs for pushes and pull requests. It installs the pinned
development tools and runs `make check`.

The gate checks Python formatting and lint, Ansible lint, YAML
validation, rendered Kustomize packages, and application tests. It does
not deploy or modify the cluster.

`boys-image.yml` builds and checks the Boys image on source pull requests. A
successful main build publishes its GHCR digest and opens a draft promotion
PR. It has no cluster credentials and does not merge or deploy. Reruns use a
new image tag and promotion branch so they cannot overwrite a reviewed draft.
Close superseded promotion drafts during review.
