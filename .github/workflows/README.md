# GitHub Actions workflows

[`ci.yml`](ci.yml) runs on pull requests and pushes to `main`. Topic-branch pushes
use their PR run, so the same head does not start a second copy of CI. A newer run
cancels the older run for the same PR or event/ref.

Shared checks always run: Python tests and formatting, Ansible lint, YAML
validation, configured Kustomize rendering, and native Prometheus rule tests.
The Boys and autism browser suites and Immich recovery checks run when their paths
change. Changes to shared deployment controls, the workflow, or its scope helper
select all three. Deleted paths count, and an unavailable base revision selects
all application checks. The final `check` job rejects failed, cancelled, or
unexpectedly skipped required checks. CI does not deploy or modify the cluster.

Run all configured repository checks explicitly:

```sh
make check
gh workflow run ci.yml --ref main
```

Manual CI dispatch always runs both browser suites, native Immich recovery tests,
and shared checks. It does not publish an Immich image. For a local
scope check, use `python -m scripts.ci_scope --base origin/main` after committing
the change. The helper selects tests; the app inventory still comes from Argo
Application metadata. Add a new browser suite to this workflow when an app needs
one. Keep `make check` as the complete local gate. The Docker-based Immich tests
can also run separately with `python3 apps/immich/tests/test_backup.py`; they never
connect to Kubernetes or the production repository.

`boys-image.yml` builds and checks the Boys image on source pull requests.
Test-only changes run the checks without publishing another digest. Runtime
source, Dockerfile, or build-context changes open a promotion after merge.
Use manual dispatch when a build-workflow change needs a new runtime image. A
successful runtime build publishes its GHCR digest and opens a draft promotion
PR. It has no cluster credentials and does not merge or deploy. Reruns use a
new image tag and promotion branch so they cannot overwrite a reviewed draft.
Close superseded promotion drafts during review.

The [autism image workflow](autism-image.yml) builds the static site with pinned
upstream images and checks the running image with phone and desktop browsers.
Source merges open a draft digest and configuration promotion. The running site
changes only when that promotion is deployed. See the [app guide](../../apps/autism-traits/README.md).

`immich-backup-image.yml` is called by the affected Immich CI job. It builds the
script bundle and runs the PostgreSQL/Restic recovery tests against the packaged
files. Only runtime changes merged to main publish an image and open a draft
Kustomize digest promotion. Manual checks do not publish unless `publish=true`
is requested on this image workflow. No cluster or backup credentials enter CI.
