# Threadfin

Threadfin provides an IPTV proxy for Plex Live TV. This app deploys Threadfin preconfigured with sample channels and default credentials so it can be added to Plex without manual setup.

## Application Details

- **Image**: `lscr.io/linuxserver/threadfin:1.0.0`
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

After configuring Threadfin with your IPTV sources, add the M3U URL `http://threadfin.media.svc.cluster.local:34400/m3u` as a tuner inside Plex Live TV & DVR setup.
