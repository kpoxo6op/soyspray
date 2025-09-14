# Threadfin

Threadfin provides an IPTV proxy for Plex Live TV. This app deploys Threadfin with a clean configuration ready for custom IPTV setup and Plex integration.

## Application Details

- **Image**: `fyb3roptik/threadfin:1.2.37`
- **Namespace**: `media`
- **Port**: `34400`
- **URL**: `https://threadfin.soyspray.vip`

## Features

- Configuration persisted on a Longhorn-backed PVC
- Clean installation ready for custom setup

## Deployment

Deployed via ArgoCD as part of the GitOps workflow:

```bash
argocd app sync threadfin
```

## Plex Integration

After configuring Threadfin with your IPTV sources, add the M3U URL `http://threadfin.media.svc.cluster.local:34400/m3u/threadfin.m3u` as a tuner inside Plex Live TV & DVR setup.
