# Media Helper

Media Helper publishes the Git-managed channel catalog, M3U playlist, and XMLTV guide to Dispatcharr and Jellyfin. It has no browser interface and does not relay playback.

## Normal use

Edit `channels.json` to add, update, disable, or reorder a channel. Keep stable official pages, direct streams, or upstream catalog identifiers in Git. Do not add temporary signed media URLs.

Every enabled channel uses `delivery: dispatcharr`. Media Helper puts the catalog logo in XMLTV as the channel's static artwork.

The internal service provides:

- `GET /healthz`
- `GET /playlist.m3u`
- `GET /xmltv.xml`
- `GET /api/v1/channels`

Its ClusterIP service and network policy limit access to approved cluster workloads.

## Reliability and limits

Media Helper has no database. It downloads the stable IPTVX EPG_LITE address at most once every six hours and keeps only catalog-selected guide identifiers. A new result replaces the in-memory cache only when all required channels have programme data. A later failure keeps the last complete result. With no complete result, `/xmltv.xml` returns `503`.

Dispatcharr owns stream resolution, failover, and buffering. Jellyfin owns playback and the visible guide. Media Helper does not invent schedules, descriptions, recordings, or catch-up playback.

Telemiks and 25 Region use the live videos embedded by their official pages. A retry can recover a temporary failure, but it cannot repair an offline source.

## Checks

```bash
kubectl kustomize playbooks/argocd/applications/media/media-helper
source soyspray-venv/bin/activate
pytest -q tests/test_live_tv.py
kubectl -n media port-forward service/media-helper 8080:8080
```

In a second terminal:

```bash
curl --fail http://127.0.0.1:8080/healthz
curl --fail http://127.0.0.1:8080/playlist.m3u
curl --fail http://127.0.0.1:8080/xmltv.xml
curl --fail http://127.0.0.1:8080/api/v1/channels
```

Stop the port forward after the checks. An unknown path returns `404`. A required unavailable guide returns `503`.

## Deployment and rollback

The native root now owns this helper. See the [operator guide](../../../../../apps/media-helper/README.md).
The live-TV shutdown command applies only to Dispatcharr and Jellyfin. Roll back
with a reverted, pushed Git revision through the native Ansible operation.
