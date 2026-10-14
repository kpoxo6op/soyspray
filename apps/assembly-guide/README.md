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

The player keeps the frame/tray chapters and desktop/phone controls, and adds
Retainer kit cards, lead-by-lead retainer installation and a Parts sheet.
The older Nood three-door steel locker has right-hinged doors, left D-pulls and
two five-slot louvre banks per door. The rack rests on loose grip-mat pads;
magnetic hooks and ONE-WRAP ties carry the cables. No drilling, cuts, screws or
adhesive on the unit. The spare board stays unplugged. Confirm the factory rear
opening before following this layout; no lead goes through a door gap.

Kit: 8 rail ties + 13 coil keepers, 16 magnetic hooks, 2 loose 253 × 21 mm pads.
NZ links checked 2026-10-14: [ONE-WRAP 12 × 203 mm](https://www.mitre10.co.nz/shop/velcro-brand-one-wrap-brand-bundling-ties-12mm-x-203mm/p/246259)
(200 mm equivalent), [32 mm Magnet Source hooks](https://www.mitre10.co.nz/shop/magnet-source-magnectic-hook-32mm-pack-of-2-white/p/244346),
[Innova grip mat](https://www.bunnings.co.nz/innova-30-x-200cm-black-grip-mat_p8905397).
Walk-in alternative: [Bunnings ONE-WRAP 13 × 200 mm, 60-pack](https://www.bunnings.co.nz/velcro-brand-one-wrap-13mm-x-200mm-multicolour-ties-60-pack_p0388962).
The Parts sheet includes the printed-separately RackStack inventory and fasteners.

Provisional until measured: unit 1200 × 400 × 600 mm; top 25 mm with 5 mm
overhang; four 30 mm corner legs and 100 mm floor clearance; steel 2 mm;
door gaps 2.5 mm; shelf 310 mm above the floor, 350 mm deep with a 30 mm rear
gap; left factory opening Ø50 mm, centre 195 mm above the floor and 220 mm from
the left edge; wall gap 180 mm; socket centre 242 mm above the floor; adapter
60 × 42 × 110 mm and its port position; pad thickness 2 mm; hook projection
28 mm. Estimated loaded rack 7 kg versus an assumed 20 kg top rating: weigh it
and confirm the rating. Equipment envelopes, stock lead lengths and bends are
illustrative. The CAD feet reach 221 mm front-to-back (beyond the 209 mm frame);
the model keeps their rear edge 30 mm inside the top. Zigbee spacing is about
940 mm here, below 1 m. Test magnetic grip with the cable load and keep ventilation
clear. No new printed cable supports. Original CAD, photos and private notes are
outside the runtime package.
