# Plex (bare‑metal–like, Direct remote)

This app deploys Plex as a single Deployment on the node network. It includes:
- Auto‑claim using `PLEX_ACCOUNT_TOKEN`
- Library mount at `/data` (PVC `sonarr-tv`)
- Service and Ingress for easier web access
- SSL certificate via cert-manager

## Prerequisites

1. Ensure UPnP/NAT‑PMP is enabled on the router.
2. Create the Plex account token secret:
   ```bash
   kubectl -n media create secret generic plex-account-token \
     --from-literal=token='<YOUR_X_PLEX_TOKEN>'
   ```

## Deploy

```bash
argocd app sync plex
```

## Verify

1. Check claim status:

   ```bash
   kubectl -n media exec deploy/plex -- curl -s http://127.0.0.1:32400/identity | grep claimed
   ```

   Expected: `claimed="1"`.

2. Access Plex via:

   **HTTPS (Recommended):**
   ```
   https://plex.soyspray.vip/web
   ```

   **Direct LAN access:**
   ```
   http://<NODE-IP>:32400/web
   ```

   Add a library that points to `/data`.

3. From the internet (app.plex.tv), start playback. The dashboard shows the client as **Remote (\<public‑IP>)** and the connection type **Direct**.

## Notes

* The pod uses `hostNetwork: true` so Plex binds to the node's port **32400**. The router opens the port automatically via UPnP for Direct remote access.
* Service and Ingress provide convenient HTTPS access while maintaining direct LAN connectivity.
* The configuration is ephemeral. Re‑claiming runs on every start. Libraries are defined in Plex UI; media files are mounted read‑only from PVC `sonarr-tv` at `/data`.
