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

Before a print, the trusted preparer renders committed CAD into a new isolated
job directory and slices **those fresh bytes**, ignoring cached repository STLs.
It uses Bambu Studio 02.08.02.61 and the P1S 0.4 mm PETG profiles in `cad/print/`.
Every slicer warning rejects the job. An independent check intersects the placed
CAD at every deposition layer and compares the actual G-code paths against it:
one-ended cantilevers, floating starts, spans over 8 mm, excluded bed areas and
unknown geometry mappings are refused. Any failure removes the exported jobs.
The checker uses structural CAD sections, including designed infill regions;
it does not simulate individual infill beads, adhesion, cooling or strength.

The [print review](cad/print/REVIEW-2026-11-02.md) records the remaining holds,
physical checks and the MCP admission contract. The MCP integration requires
`prepare_print_job(part) → upload_file → print_file`: the server runs the configured
preparer and binds its own receipt to the exact uploaded and downloaded bytes.
Caller-supplied PASS reports and direct start commands are not accepted. A server
without a configured preparer refuses printing. Deployment is separately verified;
these source files alone do not change an installed MCP server.

For offline evidence, install `cad/` dependencies with `npm ci`, install `uv`, and
run `node preflight.mjs <new-job-dir> <part>...` from `cad/`. The Python dependencies
are pinned by `check-support.py.lock`. `python3 check-preflight.py <new-check-dir>`
exercises the actual renderer and slicer against old failed shelves, current shelves,
floating parts, excluded corners, warning-free long bridges, obsolete cached exports
and process failures. It verifies archive bytes and refuses output-directory reuse.
It never contacts the printer. GitHub CI runs the app checks; this manufacturing E2E
requires the qualified local Flatpak slicer and is also enforced for every prepared job.

`lower_posts_remaining` is a print-only preset for the three lower posts still
needed after the first `post_lower_a`: one A and two B, freshly rendered, in their
normal numbered-face-down orientation, moved only sideways into a fixed row with
10 mm between them and joined into one STL. Prepare it like a part
(`node preflight.mjs <new-job-dir> lower_posts_remaining`, or
`prepare_print_job(part="lower_posts_remaining")`); the slicer and the layer check
see one object, and the check covers all three posts on every layer. The preset is
not a guide part or browser mesh and is never written to `stl/`. With the current
profiles it sliced to about 384 min and 159 g, against 139 min and 54 g for one
post: one plate clearance instead of three, not a threefold speed-up. Prints
share the plate, so a post that lifts or a nozzle clog can spoil all three.
`check-preflight.py` verifies the job is exactly one current A and two current B
and that an overlapping layout is refused.

Tests check the chapters, where each test check leaves its hardware, the tags,
that every screw meets its own nut, cord lengths and overlaps, the buy list,
Zigbee spacing, the 260 × 240 × 450 mm envelope, and that the copy asks for no
drilling. Manufacturing fit belongs to the real slicer/layer E2E, not a nominal
256 mm bounding-box test. Original CAD, photos and private
notes stay outside the runtime package.
