---
name: change-soyspray-app
description: Change or migrate a Soyspray application while preserving its data, access, and deployment identity. Use for app code, manifests, image promotion, native Argo ownership, and app-specific checks.
---

Read [AGENTS.md](../../../AGENTS.md), the app README, and its current Application.
Check live source revisions before deleting or moving a legacy path. Preserve
existing branch-delivered features when reconciling with main.

Keep each app's manifests, configuration, custom source, useful tests, and short
operating README under `apps/NAME/`. Use upstream Helm or Kustomize directly.
The native root lists explicit Applications and AppProjects. Scope each project
to actual repositories, destinations, and resource kinds. Remove submit-only
Ansible roles only after native adoption is deployed and verified.

For an ownership migration, record existing resource UIDs, names, claim bindings,
database identities, hostnames, access, and active source paths. Adopt first;
remove old definitions in a later reviewed step. Establish isolated recovery
before moving stateful ownership. Protect durable resources from prune and
Application deletion. Do not use a replacement PVC or a data copy as an implicit
migration, and do not change ingress controllers in an app ownership PR.

Package custom runtime code in immutable GHCR images. Source CI builds and tests
an image, then opens a promotion PR containing its digest and coupled configuration.
A source-only merge must not change the running app. Keep old images compatible
with additive data migrations until rollback has been verified.

For Boys, preserve the nine participant keys, personal PIN hashes, signing key,
sessions, old availability, event history, database path, PVC, and single writer.
Keep the crew claim flow and concurrent-claim protection. Calendar is the first
screen; links have their own simple screen. Preserve hidden compatibility data
without restoring the crowded trip dashboard. Keep private trip input encrypted
and out of public assets and unauthenticated responses.

Use checks that protect behavior, access, ownership, data, and deployment safety.
Tests need not precede implementation. Do not test prose, file counts, exact task
wording, or absence of retired files. For browser changes, check phone and desktop
layouts, keyboard use, failed saves, in-flight edits, conflicts, refresh, and
unsaved navigation. Compare real rendered workloads before deployment.

Use `make deploy APP=NAME` for affected-app and shared checks before deployment.
Run `make full-check` and `make go` for shared changes and final verification.
Keep deployment recipes in the app Makefile without calling back into the root.
Follow the
GitHub draft, commit, review, and exact-head verification rules in AGENTS.md.
Keep source and promotion PRs separate. Report local, CI, and deployed evidence
separately; mark unverified user journeys and restores unknown with a cause.
