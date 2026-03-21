# Jellyfin

Raw Kubernetes manifests for Jellyfin in the `media` namespace.

This deployment is intended for LAN-only playback and mounts the
`media-downloads` PVC read-only at `/media`. On this branch that claim is
backed by a static local PersistentVolume rooted at `/srv/media/downloads` on
`node-0`.

Fresh installs are bootstrapped to a single `Movies` library backed by
`/media/movies`. The library is created as `homevideos` so Jellyfin uses local
folder and file names instead of trying to match remote movie metadata.

## Bootstrap

An Argo CD PostSync job completes the initial Jellyfin setup by:

- finishing the first-run wizard
- creating the admin user
- creating a standard tablet user
- removing any libraries that are not part of the desired bootstrap state
- creating exactly one `Movies` library from `/media/movies`
- disabling internet providers for that library during bootstrap

Required secret keys in `media/jellyfin-secrets`:

- `JELLYFIN_ADMIN_USER`
- `JELLYFIN_ADMIN_PASSWORD`
- `JELLYFIN_TABLET_USER`
- `JELLYFIN_TABLET_PASSWORD`
