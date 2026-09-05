# Autism traits assessment

Open <https://autism.soyspray.vip>, choose a length, and answer the questions.
Results describe traits and include their sources. Answers and scoring stay in
browser memory. Closing or refreshing the page removes the answers.

The site sends no answers, analytics or third-party script requests. Cloudflare
still processes connection metadata to deliver the public site. Nginx keeps
`connect-src 'none'`, accepts only GET and HEAD, and does not set cookies.

## Change and check the site

Source, images, scoring checks and browser checks are in `app/`. Nginx configuration
is in `config/`. Both upstream image versions are pinned in `Dockerfile`.

```sh
cd apps/autism-traits/app
npm ci
npm run check
npm run test:e2e
```

Run `make check` from the repository root for the full local gate. CI also builds
the image, checks its HTTP and TLS service, compares the served images with the
source files, and runs phone and desktop browsers against that image.

A source merge builds a GHCR image and opens a draft promotion PR. The promotion
contains its digest and the deployment configuration needed by the image. It does
not merge or deploy automatically. Review the promotion, run `make go`, and use
`make autism-traits AUTISM_TRAITS_REVISION=<pushed-branch>`. After merge, reconcile
`AUTISM_TRAITS_REVISION=HEAD` and verify the real site.

The current deployment is still in `kubernetes/autism-traits/` during adoption.
The native root now owns the existing Application and AppProject declared in
`argocd/`. Its Application cannot cascade deletion. The first immutable image
promotion passed live verification; old deployment files remain for the separate
cleanup step. New build output stays local and is not committed. Roll back the
digest and compatible configuration together; preserve existing access settings.

## Access and recovery

The public route uses the dedicated Cloudflare Tunnel `autism-traits-public`.
It connects to the existing Service over TLS with hostname verification. The
private LAN and Tailscale route uses the existing Ingress. Keep the certificate,
tunnel identity, connector token and network policies during image adoption.

The `platform` operator owns the site. The general legacy deployment no longer
submits its Application. `make autism-traits` uses the native root operation;
`AUTISM_TRAITS_ENABLED=false` cannot remove an adopted app. Retirement requires
an explicit operation after removing its root registration.

The existing [tunnel operating guide](../../kubernetes/autism-traits/README.md)
describes its DNS, CNI and public isolation checks. Use it until native Argo
adoption consolidates those deployment definitions here. Preserve the independent
external status-page integration.

There is no server-side answer database to restore. Rebuild the pinned source and
supply the backed-up tunnel token and certificate through the bootstrap procedure.
A successful HTTP response alone does not prove that the public tunnel or browser
privacy boundary works.
