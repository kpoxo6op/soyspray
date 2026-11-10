# Pearl guide

Private build guide for Pearl, the indoor helium camera robot, served at
`https://pearl.soyspray.vip` the same way as the assembly guide: a static image
behind the private `soyspray.vip` ingress, reachable over Tailscale split DNS and
the LAN only. Do not add a public DNS record or a tunnel for this host.

Stage 0 is a 3D player in seven chapters: meet Pearl, buy the kit, load the
printer (about 2 m of leftover PETG through Boris's Bambu Lab P1S, and a first
side duct), print the pod, learn to solder (ending with a battery lead that has
Pearl's power switch and its 2 × 10 kΩ battery divider, checked on the meter),
float the first orb (lift test, with the pod's margin) and spin a fan (thrust
test). It follows the Pearl repository's v3.1 design as of its 9 Nov 2026 design
check: switch cradle on the hatch, 10 kΩ divider on D10, slicer print weight in
the sums. Its staged path follows `docs/SIMULATION_AND_BUILD_PATH.md` there. Kit lists every part with its shop, link and price;
Files serves the printable STLs with the slicer settings. `#files`, `#kit` or
`#chapters` in the address opens that panel. Ticks in Kit and Chapters stay in
the reader's browser. The app stores nothing and needs no backup.

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

Shaders compile behind the loading screen (`warmUp` in `app/src/main.js`); actors change material state only when
their opacity changes (`Actor.commit`); the pod's insides draw only while the hatch is open. Phones render at up
to 1.5x and `Stage.adapt` lowers the resolution when frames run slow; desktops start at up to 2x.

## Checks

```sh
make -C apps/pearl-guide check   # npm ci, build, content/kit/build tests, kustomize
```

`npm test` enforces the machine-checkable writing rules (plain words, caption
length against reading time, checkpoints) and that the build ships every model,
decoder and print file with content revisions. Review each new beat by eye at
1440×900 and 390×844 before merging; the tests cannot judge framing.

## Deploy and roll back

Merging a change under `app/`, `Dockerfile`, `nginx.conf` or `.dockerignore`
builds and tests the image, publishes it to GHCR and opens a draft promotion PR
that pins the digest in `manifests/deployment.yaml`. The running site changes
only when that promotion merges and Argo CD syncs. Roll back by reverting the
promotion. Check the Application is Synced and Healthy, the page and models load
from a tailnet device, and public DNS has no record for `pearl.soyspray.vip`.

`nginx.conf` serves the gzip copy the image build stores beside every script, model, decoder and print file,
caches URLs that carry a content revision (`?v=`) for a year and has the page itself checked on every visit.
The image workflow checks those headers on the built image.
