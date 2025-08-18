# Plex

Plex Media Server organizes and streams your media collection.

## Summary

- **Image**: `linuxserver/plex:1.40.2`
- **URL**: `https://plex.soyspray.vip`

## Storage

- **Config**: Persistent volume claim (`plex-config`) using Longhorn storage
- **TV Shows**: Sonarr TV PVC (`sonarr-tv`) mounted read-only
- **Movies**: Radarr movies PVC (`radarr-movies`) mounted read-only

## Argo CD Application

```bash
argocd app sync plex
argocd app get plex
kubectl get pods -n media -l app=plex
```

## Configuration

Claim the server using the `PLEX_CLAIM` token from `.env` through the web interface at `https://plex.soyspray.vip`.
