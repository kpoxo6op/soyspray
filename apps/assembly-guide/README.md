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
URLs contain content revisions, so `nginx.conf` lets a browser keep a revisioned
file for a year while the page itself is checked on every visit: a promoted
player is picked up at once and nothing else is downloaded twice. The image also
carries a gzip copy of each file, which nginx serves as is; the 1 MB script
travels as about 340 KB.

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
links the STLs in `cad/stl/`, except that the mid deck is printed from its
`mid_deck_flat` preset. Its `mid_deck.stl` and browser mesh stay the assembled deck,
with no plugs. `cad/soyrack.scad` is the source;
`cd cad && npm ci && node render.mjs` renders the print STLs (lying on the bed
origin), the browser meshes and the print list in `app/data/v3/`. The node tray
mesh is `app/data/trays.bin`, which `app/tools/regenerate-data.sh` repacks from a
RackStack checkout. `cad/` and `app/tools/` stay out of the image.

The mast's standalone STL is not a qualified print job. The Parts sheet keeps
its reference link, but warns against printing it alone or using the old combined
preset with the superseded on-edge deck. An existing mast can be assembled;
a new mast needs a separately qualified job.

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
over air. The underside pockets have straight walls, as in the base deck, because their sloped
front walls would thin to nothing at the bed. The seat planes (z 203 below, z 205 on top), the
pocket outlines, the screw holes and everything above the seat are the mid deck's.

**The first version failed.** The deck printed on 2026-11-06 had a lattice of 2 mm ribs and a
solid boss in each pocket, 0.3 mm into the pocket walls and full contact with the seat. This
README called it breakaway and promised cleanup with pliers and a flush cutter. It was wrong: the
print finished, every layer check passed, and the lattice is solidly fused and cannot reasonably
be removed at home. That deck is rejected. Do not cut or machine it out.

**The second version was held.** Its separate plug had fins up to the seat plane, so 77.5 mm2 per
pocket was still welded to the ceiling, and no one can carve that out at home. It never printed.

Each pocket now holds a plug with nothing modelled between it and the deck: a 1.4 mm plate on the
bed, 0.4 mm clear of the walls, and 0.6 mm fins that stop at z 2.6, two empty 0.2 mm layers under the
seat plane. In the sliced job those two layers hold no solid over the plug, and the ceiling's first
layer bridges wall to wall with its beads at least 0.29 mm above the fins, taking a bead as round
and hanging from the nozzle. A bead that sags lands on a fin at most 6.6 mm from the last one, so
the fins limit the sag and are not welded on purpose. Each fin crosses the bridge direction. Removal
is by hand: lift the deck, then push an M4 screw down through the seat hole against the centre fin.

The layer check normally refuses a ceiling over air. `RELEASE_INTERFACES` in `check-support.py` names
this deck and its coupon. They alone are judged by geometry policy 2 and report it; every other part
stays on policy 1. For them the plug's top counts as support for the first ceiling layer, under the
same 8 mm span rule. An MCP server that admits only policy 1 refuses these jobs until a reviewed
change admits policy 2, and that server change is separate. In return the part must pass stricter checks than before. The
air gap must be exactly two empty layers, each plug must be 0.39 mm from the deck in the CAD and 0.2 mm
in the beads, and each ceiling bead must be 0.15 mm above the plug. The first layer must also be 1 mm
from the machine's load line. Bambu's cantilever warning
reads only the layer under a ceiling, so no real gap passes it with support off. These two parts
alone slice with support on, manual, with no enforcers (`PROCESS_OVERLAYS` in `preflight.mjs`). That
generates no support. Its deck differs from the shared profile's by at most 1.01 mm of path and 0.14 mm
of filament in any layer and feature, out of 1.33 km, and the E2E limits that. Slices are not
byte-repeatable: two on one profile differ by 0.014 mm and 0.06 mm of filament. Real
slicer support was tried and not used: its full-area interface sits about 0.07 mm below the beads, on
layers the check cannot compare. `check-preflight.py` shows the welded fins, one-layer and three-layer
gaps, a plug on or near its walls, sparse fins, the rejected lattice, a missing plug, an undeclared
part name, the shared profile and a moved load line are each refused.

The deck's first layer is 1.59 mm from the load line, its nearest stroke, measured between beads from
the start G-code and the actual first layer, and 5.6 mm from the excluded corner. No brim or skirt.

**Nothing here proves it comes out, fits or holds.** A deck of this version finished all 40 layers
on 2026-11-07; its plug release, fit and strength have not been tried. The first ceiling layer spans 20 mm, and its walls
cross each open side face in a 32 mm line. Sag or stringing may still tack beads to fins, and the
seat under a bridge can sit up to about 0.4 mm low, so a post may stop that much short of the seat
plane. Bed adhesion of the plates, warp of a 245 mm deck and strength are also unknown. If a plug
will not come out by hand and with that screw, this design has failed: do not cut, scrape or push
harder.

`mid_deck_pocket_coupon` is the deck's front left corner with one pocket and its plug, the same on
every layer as the deck: 47 x 29 x 8 mm, about 23 min and 7 g, for testing this before any further deck.

`base_tub` used to be refused because at 245 x 240 mm it crossed the P1S excluded corner. No
placement of the full footprint clears that corner, and the slicer places and validates a part by
its convex hull, so a notch does not help. It now prints turned a quarter in plan, 240 x 245 x
96 mm, its rear left corner cut straight from 6.8 mm in front of the rear face to 72 mm along it.
The rear lip stops 59 mm from that corner, where the cut would thin it below 1.2 mm. The trough
floor runs on to the cut. Nothing in front of the cut changed: the corner blocks, nut slots, screw
axes, comb, bricks' bays, vents and the rails under the board are the old tub's. The guide's mesh
keeps the square corner and shows only the moved strap slots below. The rear rail stands 0.4 mm shorter on its 4 mm stub left of the board, which
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

Performance is checked by count, not by feel. `app/src/loop.js` runs the player: one animation-frame callback
per displayed frame, however often the player or the camera asks for one. Every shader compiles before the
page appears (`Viewer.warmUp` in `app/src/scene.js`), so playback never stops to compile one. Name tags are
placed from boxes measured once and again after a resize, never per frame (`app/src/tags.js`). The shadow map
is redrawn only on frames where something that casts a shadow moved, appeared or left (`Viewer.setTime`),
about a third of them. Phones render at up to 1.5x, desktops at up to 2x, and `Viewer.adapt` lowers the
resolution a step when frames stay slow. After a build,
`PLAYWRIGHT_PATH=<playwright> node tools/perf-audit.mjs --max-frame-requests 1 --max-new-programs 0 --max-layout-reads 1`
(in `app/`) plays the guide in a headless Chromium and reports frame requests per frame, shader programs
compiled after the page was ready, layout reads per frame and draw calls per chapter; each `--max-*` flag turns
a number into a pass or fail. It needs a Playwright with Chromium and is not part of `npm test`.

Tests check the chapters, where each test check leaves its hardware, the tags,
that every screw meets its own nut, cord lengths and overlaps, the buy list,
Zigbee spacing, the 260 × 240 × 450 mm envelope, and that the copy asks for no
drilling. Manufacturing fit belongs to the real slicer/layer E2E, not a nominal
256 mm bounding-box test. Original CAD, photos and private
notes stay outside the runtime package.

Two web replicas run on separate nodes so a single node outage leaves the guide
available. The currently loaded player also runs entirely in the browser.
