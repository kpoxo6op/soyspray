# Readarr

## Overview

Readarr is a book/audiobook collection manager for Usenet and BitTorrent users. This directory deploys Readarr to the `media` namespace with:

- A `Deployment` for linuxserver/readarr
- A PVC for `/config` data
- A LoadBalancer `Service` on `192.168.1.131:8787`
- **Automated qBittorrent integration** via PostSync bootstrap

## Access

After ArgoCD sync:

- Visit <http://192.168.1.131:8787/> to access Readarr
- Or use the internal DNS: `readarr.media.svc.cluster.local:8787`

## Bootstrap Integration

The deployment includes a PostSync job that automatically configures:

- **qBittorrent download client** with hardcoded credentials (admin/123)
- Host: `qbittorrent.media.svc.cluster.local:8080`
- Category: `readarr`

The bootstrap script provides full debug output and handles idempotent configuration.

## Manual Verification

Check download clients via API:

```bash
curl -s -H "X-Api-Key: a85bb8f2ab19425f9c8c0bbc6f0aa29c" \
  http://192.168.1.131:8787/api/v1/downloadclient | jq '.[] | {id: .id, name: .name, enable: .enable}'
```

## Configuration

- Point to a download client (qBittorrent) and indexers (Jackett).
