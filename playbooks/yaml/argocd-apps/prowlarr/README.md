# Prowlarr

## Overview

Prowlarr is a torrent/nzb indexer aggregator. This directory deploys Prowlarr to
the `media` namespace with:

- A `Deployment` for linuxserver/prowlarr:1.34.1
- A PVC for `/config` data
- A LoadBalancer `Service` on `192.168.1.133:9696`

## Access

After ArgoCD sync:

- Visit <http://192.168.1.133:9696/> to configure Prowlarr
- Or use the internal DNS: `prowlarr.media.svc.cluster.local:9696`
