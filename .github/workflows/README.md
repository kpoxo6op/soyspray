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

Changes to local composite actions also select all application checks, so an
action-only edit cannot bypass the real image-build and publication guards.

Image workflows that call `./.github/actions/docker-hub-cache` configure the
hosted runner's Docker daemon to check Google's public `mirror.gcr.io` cache before
Docker Hub. This reduces unauthenticated pull-rate failures while retaining the
Dockerfiles' exact digest pins and all packaged runtime and restore checks.
An uncached image falls back to Docker Hub; a failed pull still fails CI.
The cache action clears the hosted runner's shared Docker Hub login, preserves
other daemon settings and verifies the active mirror before starting test
containers. It uses no registry or cluster credentials.

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
can also run separately with `python3 apps/immich-offsite-backup/tests/test_backup.py`; they never
connect to Kubernetes or the production repository.

Each `*-image.yml` workflow builds and checks one app's image. The file list
in this folder is the index; read each workflow file for its triggers and
publication rules. They share one contract: pull requests and test-only changes
never publish; a runtime change merged to `main` publishes the tested image to
GHCR. Most workflows then open a draft digest promotion pull request; the three
voice workflows (`gi-stt`, `gi-voice`, `voice-health`) report the digest for a
separate reviewed promotion. No workflow holds cluster credentials, merges, or
deploys. The running digest changes only when a promotion is reviewed and merged
and Argo CD follows `main`.
