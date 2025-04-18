# qBittorrent (Raw K8s Manifests)

This folder contains a minimal raw Kubernetes definition of qBittorrent,
including:

1. Namespace `media`
2. PVCs for config and downloads
3. A Deployment with environment variables and resource limits
4. A Service of type LoadBalancer with IP 192.168.1.127

## Validation Steps

1. Wait for the Service to assign the LoadBalancer IP **192.168.1.127**.
2. Visit <http://192.168.1.127:8080> in your browser.
3. Log into qBittorrent (default user/pass is usually admin/adminadmin or per image doc).
4. Add a test torrent (e.g. a Linux ISO). Confirm it downloads.
