# Explain catalog

One private site for the 3D guides: `https://explain.soyspray.vip` lists every guide
and chapter, `/assembly/` is the Soyrack assembly guide and `/pearl/` is the Pearl
guide. It is served like the guides: a static image behind the private
`soyspray.vip` ingress, reachable over Tailscale split DNS and the LAN only. Do not
add a public DNS record or a tunnel for this host.

## How the paths work

This app serves only the catalog page at `/`. The guides keep their own images and
Deployments. Each guide has a second Ingress, `ingress-explain.yaml`, for
`explain.soyspray.vip` with the path `/assembly` or `/pearl`. ingress-nginx merges
the three Ingresses into one server, with the certificate from this app's Ingress.
Each guide's `nginx.conf` strips its prefix, so `/pearl/app.js?v=…` is the same file
as `pearl.soyspray.vip/app.js?v=…`, and `/pearl` redirects to `/pearl/` so the page's
relative asset URLs resolve. `assembly.soyspray.vip` and `pearl.soyspray.vip` keep
working unchanged.

Because the guides now share an origin with the catalog, the catalog shows the
Pearl guide's own Done ticks (`pearl.stage0.done` in local storage). Ticks a reader
made on `pearl.soyspray.vip` stay with that host.

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
`npm test` fails when it no longer matches them.

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
`argocd/kustomization.yaml`. The guides' prefix routes need their own promoted images
(the `nginx.conf` change) before `/pearl/` and `/assembly/` serve. Roll back by
reverting a promotion; the old guide hosts do not depend on any of this.

Check the Application is Synced and Healthy, that `/`, `/assembly/#crimp-plan` and
`/pearl/#t=191` load from a tailnet device, and that public DNS has no record for
`explain.soyspray.vip`. The app stores nothing and needs no backup.
