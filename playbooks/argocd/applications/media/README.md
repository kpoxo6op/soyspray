# Media applications

This folder contains the private media stack. Jellyfin provides cartoons and Live TV. Dispatcharr manages live stream relays. Media Helper owns the Git-managed channel catalog, M3U playlist, and XMLTV guide.

- [Jellyfin](jellyfin/README.md)
- [Dispatcharr](dispatcharr/README.md)
- [Media Helper](media-helper/README.md)
- [qBittorrent](qbittorrent/README.md)
- [LazyLibrarian](lazylibrarian/README.md)
- [Booklore](booklore/README.md)
- [Immich](immich/README.md)

Members of `media-users` can use Jellyfin without cluster or Dispatcharr administration. Dispatcharr stays limited to `cluster-admins`. Access also requires LAN or private Tailscale connectivity.

## Normal use

Use stock Jellyfin Web at `https://tv.soyspray.vip` for administration, browser playback, SSO, and Quick Connect approval. The future television client is the official Jellyfin Android TV application described in [the Android TV plan](../../../../soydocs/android-tv/README.md).

## Checks

```bash
kubectl kustomize playbooks/argocd/applications/media/media-helper
kubectl kustomize playbooks/argocd/applications/media/dispatcharr
kubectl kustomize playbooks/argocd/applications/media/jellyfin
source soyspray-venv/bin/activate
pytest -q tests/test_live_tv.py
```

Confirm cartoons, the native Jellyfin Guide, and one selected Live TV channel. The stack has no custom Web Home screen or channel-snapshot service.

## Limits

Jellyfin plays one selected channel per client. Dispatcharr can smooth short upstream gaps, but it cannot repair an offline source or missing segment. Android TV appearance and device automation wait for real hardware.

## Start, shutdown, and rollback

```bash
LIVE_TV_ENABLED=true LIVE_TV_REVISION="$(git branch --show-current)" make live-tv
LIVE_TV_ENABLED=false LIVE_TV_REVISION=HEAD make live-tv
```

Shutdown keeps the Jellyfin and Dispatcharr configuration claims and shared media files. Roll back through a reverted, pushed Git revision.
