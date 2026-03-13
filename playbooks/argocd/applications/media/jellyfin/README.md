# Jellyfin

Raw Kubernetes manifests for Jellyfin in the `media` namespace.

This deployment is intended for LAN-only playback and mounts the existing
`qbittorrent-downloads` PVC read-only at `/media`.

## Bootstrap

An Argo CD PostSync job completes the initial Jellyfin setup by:

- finishing the first-run wizard
- creating the admin user
- creating a standard tablet user
- creating the TV and Movies libraries from qBittorrent download paths
- optionally creating a Scenes library when `/media/scenes` exists

Required secret keys in `media/jellyfin-secrets`:

- `JELLYFIN_ADMIN_USER`
- `JELLYFIN_ADMIN_PASSWORD`
- `JELLYFIN_TABLET_USER`
- `JELLYFIN_TABLET_PASSWORD`
