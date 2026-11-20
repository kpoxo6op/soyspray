# Pearl guide

Private build guide for Pearl, the indoor helium camera robot, served at
`https://explain.soyspray.vip/pearl/` beside the other guides (`apps/explain`): a
static image behind the private `soyspray.vip` ingress, reachable over Tailscale
split DNS and the LAN only. Do not add a public DNS record or a tunnel for it.

`pearl.soyspray.vip` moved there for good on 15 Nov 2026. Its page now answers
with `public/moved.html`, which reads the reader's ticks on the old host (they are
stored per site), sends them to `/pearl/?carry=…` with the chapter in the hash,
and the guide merges them (`adoptCarried` in `app/src/sheets.js`); every other
old path is a 301 to the same path under `/pearl/`, except `/soldering/`,
which redirects to `https://explain.soyspray.vip/soldering/`. Keep `manifests/ingress.yaml`
and its certificate so old links keep landing on the redirect.

Stage 0 is a 3D player in seven chapters: meet Pearl, buy the kit, load the
printer (about 2 m of leftover PETG through Boris's Bambu Lab P1S, and a first
side duct), print the pod, solder the switched lead (it points to the soldering
page first, then solders Pearl's power switch and its 2 × 10 kΩ battery divider
into a battery lead, checked on the meter, once those parts arrive),
float the first orb (lift test, with the pod's margin) and spin a fan (thrust
test). It follows the Pearl repository's v3.1 design as of its 9 Nov 2026 design
check: switch cradle on the hatch, 10 kΩ divider on D10, slicer print weight in
the sums. Its staged path follows `docs/SIMULATION_AND_BUILD_PATH.md` there. Kit lists every part with its shop, link and price;
Files serves the printable STLs with the slicer settings. `#files`, `#kit` or
`#chapters` in the address opens that panel. Ticks in Kit and Chapters stay in
the reader's browser. The app stores nothing and needs no backup.

## Soldering and shared controls

`https://explain.soyspray.vip/soldering/` teaches first joints in the same image.
It builds from `app/src/soldering-main.js` and the content in `app/src/soldering/`.
Its folder ships only `data/bench.glb`, its own Draco decoder and revisioned JS/CSS;
there is no Files panel. A null kit omits the Kit button and dialog.

It is six chapters and 39 beats, about 6 minutes a loop, written for a first-time
solderer with the kit Boris bought: set up the bench, your first joint, fix a bad
joint, build the traffic light, join two wires and Pearl-size pads. Each chapter ends
at a checkpoint, and `#bench`, `#first`, `#fix`, `#light`, `#wires` or `#small` opens
one. The page loops by default (`?loop=0` turns that off) so it can run on the TV at
the bench. Its Kit panel shows the soldering part of Pearl's list.

Both pages accept `#<chapter-id>`, `#t=<seconds>`, `#chapters`, `#kit` and
`#t=<seconds>&kit` on load and when the hash changes. Pearl also accepts `#files`.
Playback writes `#t=` so a reload resumes there. Beat links appear below the caption.
Soldering Done ticks use `explain.soldering.done`; Pearl keeps `pearl.stage0.done`.
Both Kit panels use `pearl.stage0.kit`. Only Pearl adopts carried old-host ticks.

A canvas click or tap toggles playback; a drag of 6 px or more, a pinch, or the
second click of a double click does not. Space/K toggles play, arrows seek or step
chapters, R rewinds, V resets the view and F toggles full screen. Media keys support
PlayPause, Play, Pause, Stop (pause and return to the start), TrackNext,
TrackPrevious, FastForward (+10 seconds) and Rewind (−10 seconds).

Soldering loops by default; Pearl does not. `?loop` forces looping on and `?loop=0`
turns it off. A completed forward playthrough restarts after 2.5 seconds; any other
player event cancels the pending restart. Reduced motion disables looping.

## Source

- `app/src/story.js`: chapters, beats, captions, camera and animation.
- `app/src/kit.js`, `app/src/files.js`: shopping list and print files. Prices
  were read on the shops' NZ sites on the date in `kit.js`; recheck before buying.
- `app/src/p1s.js`: the P1S drawn in code at its real size, with what the
  loading chapter moves (door, toolhead, bed, screen, PTFE tube, the PETG coil).
  The layout follows Bambu's P1S photos; the steps follow Bambu's P1 wiki;
  temperatures are Bambu Studio presets; lengths come from slicing the real STL
  in Bambu Studio 2.8.2.
- `app/data/*.glb`, `app/files/*.stl`: exported from the Pearl repository with
  `pearl-v3/scripts/export_web_v3.py`. Re-export there and copy here when the
  design changes; never edit the models here.
- `STANDARDS.md`: the visual, writing and teaching rules for every stage.

## Performance

Shaders compile behind the loading screen (`warmUp` in `app/src/boot.js`); actors change material state only when
their opacity changes (`Actor.commit`); the pod's insides draw only while the hatch is open. Phones render at up
to 1.5x and `Stage.adapt` lowers the resolution when frames run slow; desktops start at up to 2x.

`app/src/loop.js` runs the player: one animation-frame callback per displayed frame, however often the player
or the camera asks for one. After a build, run these in `app/`:

```sh
PLAYWRIGHT_PATH=<playwright> node tools/perf-audit.mjs --page soldering --max-frame-requests 1 --max-new-programs 0 --max-draw-calls 240 --max-programs 21 --max-triangles 150000
PLAYWRIGHT_PATH=<playwright> node tools/perf-audit.mjs --max-frame-requests 1 --max-new-programs 0 --max-draw-calls 280 --max-programs 23 --max-triangles 160000
```

The audit serves each page independently in headless Chromium and reports per-chapter
triangles and draw calls, programs at ready, late compiles and frame requests. It
requires Playwright with Chromium and a local port; it is not part of `npm test`.

## Checks

```sh
make -C apps/pearl-guide check   # npm ci, build, content/kit/build tests, kustomize
```

`npm test` enforces the machine-checkable writing rules (plain words, caption
length against reading time, checkpoints) and that the build ships every model,
decoder and print file with content revisions. Review each new beat by eye at
1440×900, 390×844 and 960×540 before merging; the tests cannot judge framing.

## Deploy and roll back

Merging a change under `app/`, `Dockerfile`, `nginx.conf` or `.dockerignore`
builds and tests the image, publishes it to GHCR and opens a draft promotion PR
that pins the digest in `manifests/deployment.yaml`. The running site changes
only when that promotion merges and Argo CD syncs. Roll back by reverting the
promotion. Check the Application is Synced and Healthy, the page and models load
from a tailnet device at `explain.soyspray.vip/pearl/` and `/soldering/`, `pearl.soyspray.vip`
forwards there with its ticks, and public DNS has no record for either host.

`nginx.conf` serves the gzip copy the image build stores beside every script, model, decoder and print file,
caches URLs that carry a content revision (`?v=`) for a year and has the page itself checked on every visit.
The image workflow checks those headers on the built image.

For the soldering rollout, promote this image before the catalog image so chapter
links have a destination. Regenerate the catalog's `data/guides.json` only after
the content builder's last chapter change. Roll back the catalog promotion first,
then this image; the `/soldering` ingress may remain and return 404.
