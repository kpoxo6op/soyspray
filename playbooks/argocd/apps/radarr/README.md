# Radarr

Radarr is a movie collection manager for Usenet and BitTorrent users. It can monitor multiple RSS feeds for new movies and will interface with clients and indexers to grab, sort, and rename them.

## Application Details

- **Image**: `linuxserver/radarr:5.27.2-nightly`
- **Namespace**: `media`
- **Port**: `7878`
- **URL**: `https://radarr.soyspray.vip`

## Features

- Automatic movie downloading and management
- Integration with download clients (qBittorrent, etc.)
- Integration with indexers (Prowlarr)
- Automatic file organization and renaming
- Quality profiles and release preferences
- Calendar view of upcoming releases

## Storage

- **Config**: Persistent volume claim (`radarr-config`) using Longhorn storage
- **Movies**: Host path mounted to `/media/movies`
- **Downloads**: Host path mounted to `/media/downloads`

## Integration

Radarr integrates with other media stack applications:
- **Prowlarr**: For indexer management
- **qBittorrent**: For torrent downloading
- **Plex**: For media serving (future addition)

## Deployment

Deployed via ArgoCD as part of the GitOps workflow:

```bash
# Deploy via ArgoCD
argocd app sync radarr

# Check status
argocd app get radarr
kubectl get pods -n media -l app=radarr
```

## Configuration

Initial configuration can be done through the web interface at `https://radarr.soyspray.vip`

Key configuration items:
1. Connect to Prowlarr for indexers
2. Configure download client (qBittorrent)
3. Set up root folders for movies
4. Configure quality profiles
