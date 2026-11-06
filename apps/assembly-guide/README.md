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

`upper_posts_remaining` is the same kind of preset for all four upper posts: two A
and two B, 10 mm apart. It sliced to 191 min and 78 g, against 61 min and 20 g for
one upper post. The layer check used to reject every upper post because its
cap-nut slot floor lies exactly on the slicer's mid-layer sampling plane; a path may
now fit just below that plane, while support is still judged only from the section
above it. The E2E shows the pinned checker's false failure on the same job.

`top_cap` prints upside down, so each 8 mm socket-head seat used to end in a ring
ceiling, and the slicer laid closed wall loops over air there. Each seat now closes
onto its 4.5 mm screw hole in two 0.2 mm steps: first a slot as wide as the hole
across the seat, then a square. Every new path bridges at most 5.7 mm between solid
edges. The seat stays 8 mm across and 4.4 mm deep, so the heads still sit flush. The
hole only gets larger, by the slot and square, and the browser mesh is unchanged. The
cap sliced to 331 min and 156 g. The E2E checks that the old seats are still refused and
that the new cap differs from the old one only inside the four seats. Brush any stray
strand out of a seat before fitting the screw.

`mid_deck_and_mast` prints the last two parts that fit the bed in one job: the
Zigbee mast, and the mid deck standing on its rear edge 10 mm behind it, 245 mm wide,
8 mm deep and 209 mm tall. Lying flat, the deck closed each underside post pocket in
a 20.5 mm ceiling over air; on edge, every face that looks down slopes at 45 degrees
or closes in a short bridge. Each post pocket keeps its seat plane (z 203 below,
z 205 on top) and its exact outline there; only its front wall slopes 3 mm forwards
over the 3 mm depth, so the posts and their screws fit as before. The front rim and
the rear faces of the front pads stand on 4 mm fillets inside the recess, each lead
slot keeps its 60 mm rear end and closes in a pointed roof towards the front, each
vent slot ends in a point, and the two rear corners meet the bed in a small chamfer.
The mast foot is 13 mm instead of 9 mm: each ballast pocket is still 21 mm across and
6 mm deep for three M10 washers pushed up from below, then closes in a 45 degree cone
to an 8 mm vent through the foot. Its cable exit is now an open groove through the
foot. Alone, the slicer still turns the mast on the bed, which the layer check
refuses; with the mast at the deck's left end the batch keeps its place. It sliced to
567 min and 218 g, with no bridge longer than 1.2 mm. The deck has no brim and stands
on an 8 mm edge, so a knock or a lifting corner can topple it; digital checks do not
prove that it stays put or how strong it is on edge.

`mid_deck_flat` is a print-only preset for the mid deck alone, lying flat on its underside
and turned a quarter in plan: 209 x 245 x 8 mm on the bed, clear of the excluded corner. It
is for reprinting the deck after the edge-standing print of `mid_deck_and_mast` failed; the
mast is not in it. Lying flat, each underside post pocket would close in a 20.5 mm ceiling
over air, so a breakaway lattice stands in each pocket from the bed to the seat plane: 2 mm
ribs running front to back, a solid boss round the screw hole and a rib along the side face,
where the pocket opens. The ceiling bridges at most about 7 mm across the rib tops. The
underside pockets have straight walls, as in the base deck, because their sloped front walls
would thin to nothing at the bed. The seat planes (z 203 below, z 205 on top), the pocket
outlines, the screw holes and everything above the seat are the mid deck's. It sliced to
282 min and 129 g. Prepare it like a part (`node preflight.mjs <new-job-dir> mid_deck_flat`
or `prepare_print_job(part="mid_deck_flat")`); it is never written to `stl/` or the guide.

After printing, break the lattice out of the four underside pockets with pliers and a flush
cutter. The ribs are fused to the seat plane and the pocket walls, so scrape or file the seat
flat and the walls clean until each lower post goes fully into its pocket and sits on the seat
without rocking. Check the M4 hole through each seat is clear. `check-preflight.py` compares
the flat deck with the canonical deck section by section (`check-flat-deck.py`), checks the
lattice is printed in every pocket up to the seat plane, and checks that the same deck without
its lattice is refused at the pocket ceilings. A digital pass says nothing about bed adhesion of
a 245 mm PETG plate, how cleanly the lattice breaks out, or strength.

`base_tub` used to be refused because at 245 x 240 mm it crossed the P1S excluded corner. No
placement of the full footprint clears that corner, and the slicer places and validates a part by
its convex hull, so a notch does not help. It now prints turned a quarter in plan, 240 x 245 x
96 mm, its rear left corner cut straight from 6.8 mm in front of the rear face to 72 mm along it.
The rear lip stops 59 mm from that corner, where the cut would thin it below 1.2 mm. The trough
floor runs on to the cut. Nothing in front of the cut changed: the corner blocks, nut slots, screw
axes, comb, bricks' bays, vents and the rails under the board are the old tub's, and the guide's
mesh is unchanged. The rear rail stands 0.4 mm shorter on its 4 mm stub left of the board, which
sits wholly on solid rail. A board deeper than the rail may hang over the cut at that end.

The layer check then found two defects no one had reached. Two brick strap slots ran under the
outer comb fins, so each fin crossed its slot in a 22 mm span: the slots moved 1.5 and 0.5 mm
sideways, beside the fins. Each nut slot ceiling closed as a ring round its screw hole, as the cap
seats did, so it now steps to the hole in two 0.2 mm layers. The seat plane and hole axis stay, but
the nut first bears on 11.1 mm2 there instead of 26.6 mm2, then 22.2 mm2 at 0.2 mm and the full
26.6 mm2 at 0.4 mm above it. A digital pass does not measure how the seat takes the load, so stop
tightening once the screw has pulled the stack tight.

It sliced to 864 min and 395 g with 2 mm between its hull and the excluded corner. It covers
53,000 mm2 of bed with no brim and runs to within 1 mm of the plate's edge, so a corner lifting
late in a 14 hour job is the main risk. Its left wall also prints across 3.6 mm of the machine's
load line leg at x 240; watch that first layer. The bed levelling box overlaps the excluded corner;
how the printer probes there has not been observed. `check-preflight.py` compares it with the old tub section by section
(`check-base-tub.py`) and refuses each of the three defects when put back.

Tests check the chapters, where each test check leaves its hardware, the tags,
that every screw meets its own nut, cord lengths and overlaps, the buy list,
Zigbee spacing, the 260 × 240 × 450 mm envelope, and that the copy asks for no
drilling. Manufacturing fit belongs to the real slicer/layer E2E, not a nominal
256 mm bounding-box test. Original CAD, photos and private
notes stay outside the runtime package.
