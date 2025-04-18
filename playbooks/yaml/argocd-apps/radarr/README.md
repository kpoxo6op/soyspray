# Radarr MVP

## Minimal Validation

- Web UI reachable at <http://radarr.media.svc.cluster.local:7878> or <192.168.1.130:7878>.
- Path **Settings → Download Clients**: add qBittorrent (host `qbittorrent.media.svc`, port 8080).
- Path **Settings → Indexers**: add Jackett (API key from Jackett UI).

Once those two tests pass, Radarr is production‑ready for further tuning.
