# Prowlarr

## Overview

Prowlarr is a torrent/nzb indexer aggregator. This directory deploys Prowlarr to
the `media` namespace with:

- A `Deployment` for linuxserver/prowlarr:1.34.1
- A PVC for `/config` data
- A LoadBalancer `Service` on `192.168.50.213:9696`

## Access

After ArgoCD sync:

- Visit <http://192.168.50.213:9696/> to configure Prowlarr
- Or use the internal DNS: `prowlarr.media.svc.cluster.local:9696`

## API Key

The default API key is stored in `initial-config-configmap.yaml`.

## Manual Indexer Management

### Add Indexer (RuTracker Example)

Edit credentials in `rutracker_payload.json`

Add indexer via API

```bash
curl -X POST \
    -H "Content-Type: application/json" \
    -H "X-Api-Key: 7057f5abbbbb4499a54941f51992a68c" \
    -d @rutracker_payload.json \
    http://192.168.50.213:9696/api/v1/indexer
```

### Verify Indexers

```bash
curl -s -H "X-Api-Key: 7057f5abbbbb4499a54941f51992a68c" \
  http://192.168.50.213:9696/api/v1/indexer | jq '.[] | {id: .id, name: .name, enabled: .enable}'
```
