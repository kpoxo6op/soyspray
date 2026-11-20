# Explain catalog

One private site for the 3D guides: `https://explain.soyspray.vip` lists every guide
and chapter, `/assembly/` is the Soyrack assembly guide, `/crimping/` teaches crimping its
Ethernet leads (served by the assembly guide's image), `/pearl/` is the Pearl
guide, `/soldering/` teaches first joints (served by the Pearl image), and `/network/` explains the home network from zero (built into this image,
`app/network/`). It is served like the guides: a static image behind the private
`soyspray.vip` ingress, reachable over Tailscale split DNS and the LAN only. Do not
add a public DNS record or a tunnel for this host.

## How the paths work

This app serves the catalog page at `/` and the network explainer at `/network/`.
The Soyrack and Pearl guides keep their own images and Deployments. Each guide has a second Ingress, `ingress-explain.yaml`, for
`explain.soyspray.vip` with the path `/assembly` or `/pearl` (the assembly guide's also routes `/crimping`; Pearl's also routes `/soldering`). ingress-nginx merges
the three Ingresses into one server, with the certificate from this app's Ingress.
Each guide's `nginx.conf` strips its prefix, so `/pearl/app.js?v=…` is the same file
as `pearl.soyspray.vip/app.js?v=…`, and `/pearl` redirects to `/pearl/` so the page's
relative asset URLs resolve. `/soldering/` is a real folder in the Pearl image;
its prefix is retained and `/soldering` redirects to `/soldering/`.

The old hosts moved here for good: `assembly.soyspray.vip` answers with a 301 to
`/assembly/`, and `pearl.soyspray.vip` answers with a page that carries the reader's
ticks across before forwarding (see each guide's README). Because the guides share
an origin with the catalog, the catalog shows each guide's own Done ticks
(`pearl.stage0.done`, `explain.soldering.done`, `explain.network.done` in local storage).
Soldering chapter links use ids, such as `/soldering/#bench`; its Kit panel shares
`pearl.stage0.kit` with Pearl.

## Network explainer

`app/network/` is a 3D player in 16 chapters for someone who has never set up a
network: addresses and the router's jobs, the WAN line and NAT, the LAN cable and
Wi-Fi, the cluster's addresses, the pod network, how a name reaches a site,
Tailscale and today's firewalls (chapters 1 to 11, from the router's and cluster's
real settings, read on 15 Nov 2026), then proposals: subnets, rules between them,
how to get there, monitoring and other ideas (12 to 16). Captions follow the Pearl
guide's standards; every term is in the Words panel. `story.js` holds the chapters
as data, `scene.js` draws the network as plain blocks, and the player controls are
Pearl's. Nothing in it names the public address or the provider's prefix; a test
checks that every address in the story is private, Tailscale or a public resolver.

Performance follows the other guides: one animation frame at a time and none while
paused, every shader compiled behind the loading screen, lambert materials and no
shadows, packets and ruler ticks instanced, phones at 1.5× resolution stepping down
under load. `node tools/perf-audit.mjs` (with Playwright) measures it.

## UI SDK

The page is built with [UI SDK](https://ui-sdk.dev) (`@ui-sdk/web` and
`@ui-sdk/core`, pinned to `0.1.0-beta.2`, a beta whose APIs may change): its web
components for the search field, guide picker, Hide done switch, progress meters
and buttons, plus one custom primitive, `soy-chapter` (`app/src/chapter.js`), for a
chapter row with its link and Done toggle. The page creates the agent bridge at
`window.agent`. An agent in a browser can call `agent.snapshot()` to get every
component with its label, state and actions as JSON, and `agent.act({ steps })` to
change them, for example
`{ ref: "Strip 3 cm of jacket", action: "setDone", args: [true] }`, without
screenshots or clicks. Nothing on the page needs a person's confirmation, so the
bridge has no `allow` callback. Rows the filter hides carry `data-agent-hidden`, so
the bridge leaves them out as a screen reader does.

The chapter list is rendered into the HTML at build time from `app/data/guides.json`,
so it shows before the script runs. `node tools/extract-guides.mjs` (in `app/`, after
`npm ci` in both guide apps) regenerates that file from the guides' sources, and
`npm test` fails when it no longer matches them. Soldering is extracted from
`apps/pearl-guide/app/src/soldering/story.js`. Regenerate `guides.json` last, after
the content builder's final chapter changes; never hand-edit it.

## Checks

```sh
make -C apps/explain check   # npm ci in both guides, build, tests, kustomize
```

The image workflow also runs those tests against both guides' sources, so a guide
change that renames or adds a chapter fails here until `guides.json` is regenerated.
The guides' image workflows check the prefixed paths on their built images.

The script is 126 KB, 45 KB gzipped, almost all of it UI SDK; the same page with
native controls is 7 KB. The page is text, so this costs a few milliseconds of parse
on a phone and nothing on the guides themselves, which load their own scripts.

`tools/agent-bench/` holds the agent comparison: `node build.mjs --plain` writes the
native-control twin to `dist-plain/` (never shipped), `server.mjs` opens either page
in Chromium for one agent run and logs every call. See the report in
`docs/ui-sdk-report.md`.

## Deploy and roll back

The first merge does not register this app with Argo. Merging a change under `app/`,
`Dockerfile`, `nginx.conf` or `.dockerignore` builds and tests the image, publishes it
and opens a draft promotion PR that pins the digest in `manifests/deployment.yaml`.
After the first promotion merges, a separate PR adds `../apps/explain/argocd` to
`argocd/kustomization.yaml`. Merge the guides' promotions only after
`explain.soyspray.vip/` and `/network/` load: those images both serve the prefixed
paths and turn the old hosts into redirects to this site. Until then the old hosts
keep serving the guides as before. Roll back by reverting a promotion.

Check the Application is Synced and Healthy, that `/`, `/network/`,
`/assembly/#ethernet`, `/crimping/#crimp-plan`, `/soldering/#bench` and `/pearl/#print` load from a tailnet device, that
`assembly.soyspray.vip/#ethernet` and `pearl.soyspray.vip/#print` land on those, and that public DNS has no record for
`explain.soyspray.vip`. The app stores nothing and needs no backup.

For the soldering release, promote the Pearl image first and verify `/soldering/`
loads before promoting this catalog image. Check a Soldering Done tick appears in
the catalog. Roll back in the reverse order: catalog first, Pearl second.
