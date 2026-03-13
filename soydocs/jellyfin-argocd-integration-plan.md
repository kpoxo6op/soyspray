# Jellyfin Argo CD Integration Plan

## Summary

Add `Jellyfin` as a new raw-manifest Argo CD app in the existing `media` stack,
alongside the current `qBittorrent` app and without changing or removing
`Plex` in the first rollout.

Jellyfin will mount the existing `qbittorrent-downloads` PVC read-only and
serve content from the existing category directories (`/downloads/tv`,
`/downloads/movies`, etc.) through an internal ingress such as
`jellyfin.soyspray.vip`.

Because the live `qbittorrent-downloads` PVC is currently only `20Gi`, increase
it to `200Gi` as part of the same change set so the shared storage can actually
hold the planned media volume.

## Target State

After Argo CD sync completes, Jellyfin should be effectively ready to use with
minimal manual work:

- Jellyfin is reachable at `https://jellyfin.soyspray.vip`.
- The server has already completed first-run bootstrap.
- The admin user already exists and can log in immediately.
- At least one non-admin playback user already exists for tablet use.
- The media libraries already exist and point to the qBittorrent downloads PVC.
- TV and movie content already starts scanning from the shared downloads paths.
- qBittorrent remains the only writer to the downloads PVC.
- No manual in-UI creation of libraries, users, or basic server settings is
  required for the initial rollout.

## Current Repo and Cluster State

- Argo CD media apps live under `playbooks/argocd/applications/media/`.
- `qBittorrent` already exists as a raw-manifest Argo app and uses a shared RWX
  PVC named `qbittorrent-downloads`.
- The current qBittorrent category layout is:
  - `/downloads/tv`
  - `/downloads/movies`
  - `/downloads/books`
  - `/downloads/audiobooks`
  - `/downloads/scenes`
  - `/downloads/incomplete`
- The live `qbittorrent-downloads` PVC is bound with `longhorn-rwx` and is
  currently sized at `20Gi`.
- `Plex` already exists in the repo and should remain deployed during the first
  Jellyfin rollout.

## Implementation Changes

- Add a new app directory at `playbooks/argocd/applications/media/jellyfin`
  following the same raw-manifest pattern used by `qBittorrent`, `Booklore`,
  and `Plex`.
- Create `jellyfin-application.yaml` with `targetRevision: "ellis-media"`
  during branch testing, then revert to `HEAD` before merge.
- Create `kustomization.yaml` with these resources:
  - `deployment.yaml`
  - `service.yaml`
  - `ingress.yaml`
  - `pvc-config.yaml`
  - `secret.yaml` or generated secret wiring for bootstrap credentials
  - `bootstrap-job.yaml`
  - `bootstrap-scripts-configmap.yaml`
  - optional `README.md`
- Add a new role at `roles/apps/jellyfin/tasks/main.yml` that applies the Argo
  CD `Application`, matching the existing `roles/apps/qbittorrent` pattern.
- Register the new role in `playbooks/deploy-argocd-apps.yml` under the Media
  section.
- Add secret handling for Jellyfin bootstrap credentials using the repo's
  existing secret-management pattern rather than hardcoding passwords in
  manifests.

## Runtime Design

- Use a single `Deployment` with `replicas: 1`.
- Use a dedicated config PVC, `jellyfin-config`, on `longhorn`,
  `ReadWriteOnce`, sized around `10Gi`.
- Mount the shared `qbittorrent-downloads` PVC read-only at `/media`.
- Expose a `ClusterIP` service on Jellyfin's HTTP port and terminate LAN access
  through nginx ingress at `jellyfin.soyspray.vip`.
- Do not use `hostNetwork`, UPnP, or router-facing ports; this stays LAN-only.
- Add an `emptyDir` mount for transcode/cache scratch space so temporary files
  do not pollute the media PVC.
- Start without hardware acceleration and size resources for mostly direct play
  on a tablet; treat transcoding as best-effort rather than a guaranteed
  capability in v1.
- Add readiness that waits for Jellyfin's HTTP API to be usable before any
  bootstrap automation runs.

## Unattended Bootstrap Design

- Add a PostSync-style bootstrap job, similar to the repo's qBittorrent and
  Prowlarr bootstrap patterns.
- The bootstrap job waits for the Jellyfin API to become available, then
  configures the server through Jellyfin's API rather than relying on manual
  UI setup.
- The bootstrap data should come from Kubernetes secrets and configmaps so the
  bootstrap is repeatable and GitOps-friendly.
- The bootstrap must be idempotent: re-running it should update missing pieces
  without duplicating users or libraries.
- The bootstrap should configure:
  - first-run completion
  - server name and basic LAN-only settings
  - admin user
  - one standard playback user for tablet use
  - TV library at `/media/tv`
  - Movies library at `/media/movies`
  - optional Scenes library at `/media/scenes`
- The bootstrap should leave `/media/incomplete`, `/media/books`, and
  `/media/audiobooks` out of Jellyfin unless explicitly added in a later change.
- The bootstrap should fail loudly if the expected directories do not exist on
  the mounted PVC, so Argo sync reveals storage/path problems early.

## Secrets and Initial Credentials

- Store bootstrap credentials in Kubernetes secrets created by Ansible role
  wiring, consistent with how other apps inject sensitive values.
- Define at least these secret-backed inputs:
  - Jellyfin admin username
  - Jellyfin admin password
  - Jellyfin tablet user username
  - Jellyfin tablet user password
- Treat the tablet user as a normal playback account, not an administrator.
- Keep these values environment-driven so they can be rotated without changing
  the raw manifests structure.

## Library Mapping

- Keep qBittorrent as the writer and Jellyfin as a read-only consumer of the
  same PVC.
- Reuse the existing qBittorrent category layout from its config:
  - `/media/tv`
  - `/media/movies`
  - optionally `/media/scenes`
- Do not expose `/media/incomplete` in Jellyfin and do not point libraries at
  the PVC root.
- Do not add automated library-import or file-moving jobs in v1.
- Create the Jellyfin libraries automatically during bootstrap so the initial
  login lands on a ready-to-scan server.

## qBittorrent Storage Change

- Update the qBittorrent downloads PVC manifest so `qbittorrent-downloads`
  requests `200Gi` instead of `20Gi`.
- Keep the storage class as `longhorn-rwx` and keep qBittorrent's mount path
  and category paths unchanged.
- Do not create a second media PVC in this version; the integration is
  intentionally based on the existing shared downloads volume.

## Networking and Access

- Keep qBittorrent at `torrent.soyspray.vip`.
- Add Jellyfin ingress at `jellyfin.soyspray.vip` in the `media` namespace,
  using the same cert-manager and nginx ingress conventions already used by
  other media apps.
- Scope the plan to LAN/tablet access only; no remote publishing, no Plex-style
  direct remote access, and no SSO or OAuth integration in v1.
- Optimize for browser and Jellyfin-app access from a tablet on the local
  network.

## Test Plan

### Static checks

- `kustomize build` succeeds for the new Jellyfin app directory.
- The Argo `Application` manifest points to the correct repo path and branch
  during branch testing.
- The deploy playbook includes the new `apps/jellyfin` role.
- The bootstrap configmap and job render with the expected paths and secret
  references.

### Kubernetes and Argo acceptance

- Argo sync creates the Jellyfin pod, service, ingress, and config PVC
  successfully.
- The Jellyfin pod mounts `qbittorrent-downloads` read-only and
  `jellyfin-config` read-write.
- The resized `qbittorrent-downloads` PVC reports the new requested capacity.
- The bootstrap job completes successfully after the Jellyfin API becomes ready.
- Re-running sync does not create duplicate users or duplicate libraries.

### Functional validation

- `https://jellyfin.soyspray.vip` loads on the tablet over LAN.
- Initial Jellyfin setup is already complete when the login page appears.
- The admin user can log in immediately with the configured credentials.
- The tablet user can log in immediately with the configured credentials.
- A TV library pointed at `/media/tv` and a Movies library pointed at
  `/media/movies` both scan successfully.
- The configured libraries are already present without manual UI creation.
- Playback works from the tablet for at least one direct-play file from the
  shared PVC.
- qBittorrent continues writing to `/downloads/...` without any path changes or
  regression.

## Assumptions and Defaults

- Keep `Plex` deployed and untouched during the initial Jellyfin rollout.
- Use raw Kubernetes manifests, not Helm, to match the repo's existing media
  app style.
- Use the existing `qbittorrent-downloads` PVC as the source of truth rather
  than introducing a curated-library pipeline.
- Default shared PVC size is `200Gi`.
- v1 includes automated Jellyfin bootstrap for users and libraries, but still
  excludes remote access, SSO or OAuth, and file post-processing.
