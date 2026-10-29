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

The player keeps the frame/tray chapters, Retainer kit cards, lead-by-lead
retainer installation and desktop/phone controls. Select the installation in
the transport bar: `?layout=v2` (default, **No holes**), `?layout=v1`
(**Drilled hole**) or `?layout=v3` (**Soyrack**). Switching reloads the complete
variant at the same playhead; seek, pause, rewind and free rotation work in all
three. Unknown values choose v2.

v3 is a new printed PETG rack around the three v2 node trays: a power base for
the bricks and a slim four-outlet board, M5 tie rods from the feet to the top
cap, drive, switch and router shelves, a four-slot keystone panel and a Zigbee
mast 1 m from the router. Its Parts sheet links the STLs in `cad/stl/`, four
small test prints first. `cad/soyrack.scad` is the source; `cd cad && npm ci &&
node render.mjs` renders the print STLs (lying on the bed origin), the v3
browser meshes and the print list in `app/data/v3/`. `cad/` stays out of the
image. Tests check the v3 chapters, leads, buy list, Zigbee spacing, the
260 × 240 × 450 mm envelope and that every STL fits a 256 mm bed.

The older Nood three-door steel locker has right-hinged doors, left D-pulls and
two five-slot louvre banks per door. Both variants use loose grip-mat pads,
magnetic hooks and ONE-WRAP ties. v2 has solid panels and shut doors throughout:
the board, bricks and plug-in adapters rest on the room floor under the rear
half, coils hang on outside-back hooks, and leads roll over the uncut rear edge.
The board switch faces the wall gap. The spare stays unplugged under the right
rear end, keeping its cord outside too. Nothing powered or connected is stored
in a cupboard. No screws, cuts, holes or adhesive on the unit in v2.

v1 preserves the cupboard scene and routes through one optional **drilled Ø50 mm
hole** in the left back panel. It is a modification to arrange before routing:
deburr and fit a matching cable grommet. The Parts sheet adds one
[Co-Mac 900 grommet](https://comac.nz/products/900), listed for a 50 mm panel hole
and 2.5 mm gauge; check its groove against the measured steel before drilling.
No chapter animates drilling. The top stays solid in both variants.

Kit in either variant: 8 rail ties + 13 coil keepers, 16 magnetic hooks,
2 loose 253 × 21 mm pads. NZ links checked 2026-10-14:
[ONE-WRAP 12 × 203 mm](https://www.mitre10.co.nz/shop/velcro-brand-one-wrap-brand-bundling-ties-12mm-x-203mm/p/246259)
(200 mm equivalent), [32 mm Magnet Source hooks](https://www.mitre10.co.nz/shop/magnet-source-magnectic-hook-32mm-pack-of-2-white/p/244346),
[Innova grip mat](https://www.bunnings.co.nz/innova-30-x-200cm-black-grip-mat_p8905397).
Walk-in alternative: [Bunnings ONE-WRAP 13 × 200 mm, 60-pack](https://www.bunnings.co.nz/velcro-brand-one-wrap-13mm-x-200mm-multicolour-ties-60-pack_p0388962).
The Parts sheet includes printed-separately RackStack parts and rack fasteners.

Provisional until measured: unit 1200 × 400 × 600 mm; top 25 mm, overhang 5 mm;
four 30 mm corner legs, floor clearance 100 mm; steel 2 mm; door gaps 2.5 mm;
shelf 310 mm above the floor, 350 mm deep, rear gap 30 mm; socket centre
242 mm above the floor; adapter 60 × 42 × 110 mm and port position;
pad thickness 2 mm; hook projection 28 mm. v1 hole centre is 195 mm above the
floor, 220 mm from the left edge, with a 180 mm wall gap. v2 uses 110 mm:
the wall plate and adapter project 62.5 mm, plus 40 mm for the lead corridor,
rounded up to the smallest 10 mm step. At 100 mm the corridor is only 37.5 mm.
The 250 mm floor board spans 100–350 mm in depth, leaving 5 mm to the wall.
Tests check all cable samples throughout payout/dressing, device envelopes,
solid panels, closed doors and both variants' Parts quantities. `make -C
apps/assembly-guide check` runs the full suite separately for both URLs.

Estimated loaded rack 7 kg versus assumed 20 kg top rating: weigh it and confirm
the rating. Equipment envelopes, stock lead lengths and bend radii remain
illustrative. CAD feet reach 221 mm front-to-back, with 30 mm rear margin.
Zigbee spacing is about 940 mm, below 1 m. Test magnetic grip with the cable
load and keep ventilation clear. No new printed cable supports. Original CAD,
photos and private notes stay outside the runtime package.
