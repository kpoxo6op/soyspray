# GitOps Bootstrap

The goal 001 GitOps structure models an Argo CD app-of-apps pattern.

The app manifests use `REPLACE_WITH_REPO_URL` until the actual repo URL is
selected. This prevents placeholder YAML from looking production-ready.

## App Boundaries

- Root app points at the app-of-apps directory.
- Namespace app points at `platform/namespaces`.
- Networking app points at `platform/networking`.
- Security app points at `platform/security`.
- cert-manager and MetalLB apps point at their prerequisite paths.

## Project Boundaries

The AppProject examples separate platform prerequisites, security prerequisites,
and tenant applications. Later goals can tighten those boundaries once live Argo
CD state is part of the workflow.

## Rollback

Rollback should use Git revert, then an explicit Argo CD sync. Argo CD must not
be used to bypass pull-request review.

