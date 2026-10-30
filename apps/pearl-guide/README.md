# Pearl guide

Private build guide for Pearl, the indoor helium camera robot, served at
`https://pearl.soyspray.vip` the same way as the assembly guide: a static image
behind the private `soyspray.vip` ingress, reachable over Tailscale split DNS and
the LAN only. Do not add a public DNS record or a tunnel for this host.

Stage 0 is a 3D player in six chapters: meet Pearl, buy the kit, print the pod
on a Bambu Lab P1S, learn to solder, float the first orb (lift test) and spin a
fan (thrust test). Kit lists every part with its shop, link and price; Files
serves the printable STLs with the slicer settings. Ticks in Kit and Chapters
stay in the reader's browser. The app stores nothing and needs no backup.

## Source

- `app/src/story.js`: chapters, beats, captions, camera and animation.
- `app/src/kit.js`, `app/src/files.js`: shopping list and print files. Prices
  were read on the shops' NZ sites on the date in `kit.js`; recheck before buying.
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
