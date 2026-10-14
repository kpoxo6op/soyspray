# Goal: the guide on the real Nood TV unit, with real cable retainers

Temporary brief for one long-running agent goal. Delete this file in the last
commit before merge; fold anything durable into `README.md`.

## Objective

Make `assembly.soyspray.vip` show the rack installed on the owner's Nood steel
3-door TV unit with **zero holes, screws, cuts or adhesive on the unit**, and make
every cable retainer a real, named, purchasable part whose installation the
player animates. Keep the YouTube-style 3D player's look and feel and make it at
least as good-looking as now. Ship it live through the repository's normal PR,
CI, image and digest-promotion path.

## Verified starting state (2026-10-14)

- Source: `apps/assembly-guide/app/src`. Console and room: `room.js`. Layout
  constants: `layout.js` (`SERVICE`, `HOUSE_FLOOR_Z`, `FLOOR_Z`). Leads and
  peripherals: `wiring.js` (`TV`, `WALL`, routes). Ties: `installation.js`.
  Chapters and copy: `timeline.js` (`CHAPTERS`, `WIRE_COPY`).
- The scene shows an invented 1800 mm wooden console: an 80 mm hole cut in its top
  (`SERVICE.hole`), a screwed cleat for the board, five screwed coil hangers under
  the top, rear-edge clips for the Zigbee lead, and a slatted door.
- The "magic retainers": `installation.js` builds rigid six-point black hoops at
  z 100/175/225/360 on both rear rails that reach 110–130 mm behind the rack
  (y 177 → 322/337), with the rear "cable lanes" hanging in mid-air inside them.
  A zip tie cannot hold that shape. They are unnamed, never installed on screen,
  and fade in during the `zip-ties` chapter. `room.js` also adds two unexplained
  metal L-brackets behind the USB tray (`[[63,224],[158,227.5]]`) under the USB
  coils.
- Copy still says zip ties, console cleat, compartment support, "secure the rack
  feet to the console top" and "console cable opening".
- Rack envelope: 253 × 209 mm footprint, 418 mm tall including feet.
- The matching upper frame is already being printed. Do not add new printed
  parts unless they are optional and clearly labelled.

## The unit (from the owner's photo; provisional until measured)

- Nood steel 3-door locker TV unit in a light sage-grey powder coat. It is an
  older Nood line (Ivy-style; Nood listed the Ivy 3-door as 120 cm wide). It is
  **not** the current Irvine 3-door (150 × 40 × 60 cm, keyed doors, one low louvre
  bank), so do not copy the Irvine's looks.
- Provisional envelope: W 1200 × D 400 × H 600 mm. A ~25 mm top slab with a slight
  overhang. The side panels continue down into four square corner legs with about
  100 mm floor clearance. No middle legs.
- Three equal recessed doors with no locks. Each has a vertical D-pull near its
  LEFT edge at mid-height, is hinged on its RIGHT edge, and has two pressed 5-slot
  louvre banks on its right half (upper and lower).
- Each compartment has one adjustable steel shelf on clips.
- Rear openings are unknown. Nood's current steel lockers have round factory cable
  openings low in the back panels of the end compartments. Use one in the left
  compartment provisionally.
- If the owner gives tape measurements or a back photo in chat, use those values
  and say which ones changed. Mark every remaining provisional dimension in the
  README and in the parts panel.

## Layout (no holes, no screws, no cuts, no adhesive on the unit)

- The rack stands on the top above the left compartment, rear feet at least 30 mm
  in from the back edge, on removable anti-slip or earthquake-putty pads. State
  the rack mass against the top's rating. If the rating is unknown, say so and
  assume 20 kg, the rating Nood gives its current 3-door locker.
- The left compartment is the service bay. The three bricks go on its floor with
  gaps between them. The six-outlet board goes on the shelf or the floor with its
  switch facing the door. Spare coils hang on magnetic hooks on the steel walls.
  The door closes fully, and no lead passes through a door gap. Animate the door
  swing (right-hinged).
- Leads leave through the factory rear opening, rise in the wall gap and pass
  over the top's back edge without a kink to the rear rails. WAN runs from the
  powerline adapter up the wall gap straight to the router.
- The powerline adapter stays in the wall socket behind the unit, so the wall gap
  must clear the adapter, its plug and its lead bend. Model this and test it.
- The spare board stays unplugged in the right compartment.
- The Zigbee dongle goes at the far end of the top, with its extension carried by
  magnetic hooks along the steel back. Keep it at least 1 m from the router
  antennas if the unit allows; otherwise use the maximum distance and say so.
- Fallback, only if the owner confirms the unit has no rear opening: hang the
  bricks and the board on the steel back panel with magnetic hooks in the wall
  gap, keep the doors shut, and still use zero holes.

## Retainer kit: real, explained, installed and sourced

1. **Rail ties**: VELCRO® ONE-WRAP® hook-and-loop ties, 12 × 200 mm, or an
   equivalent. Each tie wraps the rear rail post *and* the bundle lying flat
   against it: thread the tail through the slot, pull snug, press closed. No
   tools, and reusable. Delete the floating hoops and re-route the rear lanes so
   bundles sit within about 20 mm of the rail's rear face.
2. **Coil keepers**: the same tie, one per spare stock-lead coil.
3. **Magnetic hooks**: on the steel compartment walls and along the back. They
   replace the screwed hangers, the cleat and the rear-edge clips.
4. Delete the USB L-brackets. Strap the USB spare coils to the rear-left rail
   with ties.
5. Use no zip ties anywhere, so no cutter is needed.

NZ sources checked 2026-10-14. Re-open each one before citing it, show a
"checked <date>" stamp, and cite only links you actually opened:

- Bunnings NZ, everhang 35 mm silver magnetic hook, 10-pack, NZ$16.80:
  https://www.bunnings.co.nz/everhang-35mm-silver-magnetic-hook-10-pack_p0519731
- Mitre 10 NZ, Magnet Source magnetic hook 32 mm, 2-pack, NZ$14.57:
  https://www.mitre10.co.nz/shop/magnet-source-magnectic-hook-32mm-pack-of-2-white/p/244346
- VELCRO ONE-WRAP 12 × 200 mm: element14 NZ VEL-EC60466 (15-pack)
  https://nz.element14.com/velcro/vel-ec60466/cable-tie-12mm-x-0-2m-pk15/dp/2420178 ;
  RS NZ 459-3663 (5-pack) https://nz.rs-online.com/web/p/hook-loop-tapes/4593663 .
  Also find a walk-in NZ option (Bunnings, Jaycar, Warehouse Stationery or PB Tech).
- Anti-slip or earthquake putty for the rack feet: find an NZ source.

## Player changes (tweak and enhance; do not rebuild)

- Keep every frame and tray chapter, the pacing, the dark stage, the transport bar,
  captions, seek, pause, rewind, free rotation and the phone layout.
- Add a "Retainer kit" chapter before the first wire chapter. Use a macro camera,
  and show each retainer as a product card (name, size, quantity, where to buy)
  with a leader line to its 3D model. Animate one tie wrapping a rail and bundle
  and closing, and one magnetic hook snapping onto steel.
- In each wire chapter, close the tie or hook that lead uses as the lead passes it
  (short glow), instead of showing every retainer at the end.
- Rename `zip-ties` to "Snug the ties", covering final tension and the coil
  keepers. In `living-placement`, set the rack down onto its pads with no screws.
- Add a transport-bar button that opens a compact "Parts and where to buy" sheet:
  printed parts (matching frame printed separately), fasteners from the RackStack
  BOM, and the retainer kit with quantities, NZ links and the checked date. It
  must work at 390 px width.
- Visuals: matte powder-coat steel, pressed louvres with real depth, bevelled
  edges, tubular D-pulls, door gaps and contact shadows. Copy stays short and
  plain, and every retainer mention names the part.

## Tests (observable behaviour, not prose)

- No cable centreline sample passes through the unit's panels or top except at
  the modelled rear opening, and the top has no hole.
- Every rail tie encloses its rail and stays within 25 mm of it. Every magnetic
  hook sits on a steel face. Every stock coil has exactly one keeper.
- The rack footprint lies on the top with margin. The powerline adapter clears
  the unit's back.
- Parts-sheet quantities equal the retainer counts in the scene.
- The existing tests still pass. Change an expectation only where the physical
  design changed, and say why.

## Delivery (follow `AGENTS.md`)

1. Work on branch `ccr-9f2b8563-qbeqnc` in a separate git worktree, and leave the
   primary checkout on `main`. Commit after each milestone: unit model, layout and
   re-routing, retainer kit and chapter, parts sheet, polish.
2. Before every push, run `make -C apps/assembly-guide check`. Capture Playwright
   screenshots at 1280×760 and 390×844 for the retainer chapter, the service bay,
   the rear wiring, Connected and Living room, and compare them with the current
   live site. Fix anything uglier, clipped or unreadable.
3. Mark the PR ready and wait for CI to pass, then squash-merge it. Take the
   tested image digest from the `Assembly guide image` run on `main`, and open a
   separate promotion PR that pins it in `manifests/deployment.yaml`. Merge that
   PR after CI passes.
4. Verify the Argo Application is Synced and Healthy, the page and both assets are
   served from the tailnet, the new chapters render, and public DNS still has no
   record for `assembly.soyspray.vip`.
5. Keep this repository public-safe: no names, addresses, order details, home
   photos or credentials.

## Done when

All of the following are true: the unit is modelled; no retainer floats; every
retainer is named, sourced and shown being installed; all tests are green; both
PRs are merged; the live site serves the new image. Finish with a 10-line report
covering what changed, screenshots, provisional dimensions still to measure,
shopping list with quantities, and rollback (promote the previous digest
`sha256:7166d40f…`).
