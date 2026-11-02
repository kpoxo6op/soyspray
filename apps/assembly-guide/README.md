# Soyspray assembly guide

The static 3D rack assembly player is served by a Kubernetes Deployment and
Service through the existing private `soyspray.vip` ingress. Tailscale split DNS
resolves `assembly.soyspray.vip` through OpenWrt to the cluster ingress. Do not
create a public DNS record or Cloudflare Tunnel for this host.

The source is in `app/`. `npm ci && npm run build && npm test` builds the three
static files in `app/dist/` and checks the player and 3D assembly contracts.
The Dockerfile packages that build into an immutable nginx image. The image
workflow tests the packaged HTTP server, publishes on `main`, and reports its
digest. A separate promotion PR pins that digest in the Deployment. Built asset
URLs contain content revisions so returning phone browsers fetch the promoted
player instead of reusing an older cached script.

The app stores no state and requires no backup. To roll back, promote the
previous known-good image digest through a PR. Check the Argo Application is
Synced and Healthy, the ingress serves the page and two assets, and public DNS
has no record for `assembly.soyspray.vip`.

The guide shows one rack, Soyrack: a printed PETG rack around the three
ventilated node trays from the old rack. It has a power base for the bricks, a
slim four-outlet board and the switch adapter, four posts screwed to the decks
at each corner, a drive tray, a switch shelf, a four-slot keystone panel (slot 1
goes out to the router on the wall) and a Zigbee mast 1 m from the USB 3 ports.
It goes together with M4 screws and nuts only: each post foot takes an M4 × 25
down into a nut held in a slot in the deck or base below, and tray screws go
into nuts dropped into slots behind the post holes. No soldering iron,
pressed-in inserts or rods. It stands on the TV unit on four silicone pads, with
no holes, screws or glue in the unit. Seek, pause, rewind and free rotation work
throughout.

Every stock cord is drawn at its real length, its spare wound into strapped
loops (`app/src/soyrack/cables.js`). The guide opens with four small test prints
and how to check each fit, with tags in the 3D view naming every piece and
fastener (`app/src/soyrack/testprints.js`, `app/src/tags.js`). The Parts sheet
links the STLs in `cad/stl/`. `cad/soyrack.scad` is the source;
`cd cad && npm ci && node render.mjs` renders the print STLs (lying on the bed
origin), the browser meshes and the print list in `app/data/v3/`. The node tray
mesh is `app/data/trays.bin`, which `app/tools/regenerate-data.sh` repacks from a
RackStack checkout. `cad/` and `app/tools/` stay out of the image.

Before a print, `cd cad && node preflight.mjs <job-dir> <part>...` re-renders
each part, requires the committed STL to match, and slices it with the
installed Bambu Studio Flatpak and the P1S PETG profiles in `cad/print/`. It
fails on a stale or uncommitted STL, on a slicing error (a part outside the
usable plate is one) and on any slicer warning, such as a floating cantilever:
change the part, do not accept the warning. Print only a `.gcode.3mf` from a
passing run, whose hash `preflight.json` records, and check the camera at the
layers it lists, where walls cross open air; a sound first layer says nothing
about them. Use a **new** job directory under the home directory on each run;
existing jobs are never overwritten. An interrupted check leaves `pass: false`.
CI does not currently run this check. The drive tray and switch shelf keep
solid floor under their device rims, so a vent slot never cuts the root of a rim.
The [print review](cad/print/REVIEW-2026-11-02.md) records the remaining blocked
parts and physical checks. The general printer upload API does not enforce this
report: the operator must verify a passing report and the job hash before upload.

Tests check the chapters, where each test check leaves its hardware, the tags,
that every screw meets its own nut, cord lengths and overlaps, the buy list,
Zigbee spacing, the 260 × 240 × 450 mm envelope, that every STL fits a 256 mm
bed, and that the copy asks for no drilling. Original CAD, photos and private
notes stay outside the runtime package.
