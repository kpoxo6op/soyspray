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
Built asset URLs contain content revisions so returning phone browsers fetch
the promoted player instead of reusing an older cached script.

The app stores no state and requires no backup. To roll back, promote the
previous known-good image digest through a PR. Check the Argo Application is
Synced and Healthy, the ingress serves the page and two assets, and public DNS
has no record for `assembly.soyspray.vip`.

The player now includes the matching upper frame, every power/data lead,
supported stock-cable coils, straps and rail ties, and a proposed living-room
console. Pause, rewind, chapter seeking and free rotation work on desktop and
phone layouts. Stock lead lengths and equipment/console envelopes are examples,
not measured fabrication dimensions; spline joins illustrate routing rather
than enforcing a physical minimum bend radius. Original CAD, photos, house
files, private notes and the blog are outside this runtime package.
