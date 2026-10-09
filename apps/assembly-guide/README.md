# Soyspray assembly guide

The static 3D rack assembly player is served by a Kubernetes Deployment and
Service through the existing private `soyspray.vip` ingress. Tailscale split DNS
resolves `assembly.soyspray.vip` through OpenWrt to the cluster ingress. Do not
create a public DNS record or Cloudflare Tunnel for this host.

The source is in `app/`. `npm ci && npm run build && npm test` builds the three
static files in `app/dist/` and checks the chapter/player and 3D assembly
contracts. The Dockerfile packages that build into an immutable nginx image.
The image workflow tests the packaged HTTP server, publishes on `main`, and
reports its digest. A separate promotion PR pins that digest in the Deployment.

The app stores no state and requires no backup. To roll back, promote the
previous known-good image digest through a PR. Check the Argo Application is
Synced and Healthy, the ingress serves the page and two assets, and public DNS
has no record for `assembly.soyspray.vip`.
