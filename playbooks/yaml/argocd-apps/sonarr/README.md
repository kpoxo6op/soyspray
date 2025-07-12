# Sonarr

Sonarr (formerly NZBdrone) is a PVR for Usenet and BitTorrent users. It can monitor multiple RSS feeds for new episodes of your favorite shows and will grab, sort, and rename them. It can also be configured to automatically upgrade the quality of files already downloaded when a better quality format becomes available.

## Application Details

- **Image**: `linuxserver/sonarr:4.0.15`
- **Namespace**: `media`
- **Port**: `8989`
- **URL**: `https://sonarr.soyspray.vip`

## Features

- Automatic TV series downloading and management
- Integration with download clients (qBittorrent, etc.)
- Integration with indexers (Prowlarr)
- Automatic file organization and renaming
- Quality profiles and release preferences
- Calendar view of upcoming episodes
- Season pack handling and episode tracking

## Storage

- **Config**: Persistent volume claim (`sonarr-config`) using Longhorn storage
- **TV Shows**: Host path mounted to `/media/tv`
- **Downloads**: Host path mounted to `/media/downloads`

## Integration

Sonarr integrates with other media stack applications:
- **Prowlarr**: For indexer management
- **qBittorrent**: For torrent downloading
- **Radarr**: For movie management (complementary)
- **Plex**: For media serving (future addition)

## TV vs Movies

- **Sonarr**: TV Series (Twin Peaks, Breaking Bad, Game of Thrones)
- **Radarr**: Movies (Avengers, Twin Peaks: Fire Walk with Me)

## Deployment

Deployed via ArgoCD as part of the GitOps workflow:

```bash
# Deploy via ArgoCD
argocd app sync sonarr

# Check status
argocd app get sonarr
kubectl get pods -n media -l app=sonarr
```

## Configuration

Initial configuration can be done through the web interface at `https://sonarr.soyspray.vip`

Key configuration items:
1. Connect to Prowlarr for indexers
2. Configure download client (qBittorrent)
3. Set up root folders for TV shows
4. Configure quality profiles and language preferences
5. Set up series monitoring preferences
