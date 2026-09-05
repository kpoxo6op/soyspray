# GitHub Actions workflows

[`ci.yml`](ci.yml) runs for pushes and pull requests. It installs the pinned
development tools and runs `make check`.

The gate checks Python formatting and lint, Ansible lint, YAML
validation, rendered Kustomize packages, and application tests. It does
not deploy or modify the cluster.

`boys-image.yml` builds and checks the Boys image on source pull requests.
Test-only changes run the checks without publishing another digest. Runtime
source, Dockerfile, or build-context changes open a promotion after merge.
Use manual dispatch when a build-workflow change needs a new runtime image. A
successful runtime build publishes its GHCR digest and opens a draft promotion
PR. It has no cluster credentials and does not merge or deploy. Reruns use a
new image tag and promotion branch so they cannot overwrite a reviewed draft.
Close superseded promotion drafts during review.
