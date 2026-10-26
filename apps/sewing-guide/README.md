# Sewing guide

Interactive guide to the PFAFF passport 3.0 sewing machine at
<https://sewing.soyspray.vip>: a 3D machine built from primitives with every manual
part as a hotspot and fourteen animated chapters (power, spool, bobbin winding,
bobbin, threading, threader, first seam, IDT, foot, needle, feed dogs, buttonhole,
cleaning, pack away); all 100 stitches drawn live from their needle paths at any
width and length, with foot, IDT, uses and fabrics; settings per fabric; four
first projects; troubleshooting by symptom. English and Russian, phone first.

Content comes from the owner's manual 471 01 87-26B and the machine's stitch
card. Stitch names 22 to 99 and all fabric-specific settings are the guide's own
recommendations and say so in the UI. The site stores only a language choice and
the first-hour checklist in the browser; the "ask" button shares the page link.

## Change and check

Source is in `app/` (esbuild, three.js, no framework). `npm ci && npm run build
&& npm test` builds `app/dist/` and checks content contracts (100 stitches,
bilingual text, chapter cameras and parts, cross-links), the stitch renderer at
extreme settings, and the built bundle. `node tools/serve.mjs` serves the build;
`node tools/screenshots.mjs` takes phone and desktop screenshots of every section
against it (needs playwright-core and a Chromium; set `CHROME_PATH`).

```sh
make check APP=sewing-guide
make diff APP=sewing-guide
make smoke APP=sewing-guide
```

The image workflow builds and tests the nginx image on pull requests, publishes
from `main` when runtime files changed, and opens a draft digest promotion.
`manifests/deployment.yaml` starts with an all-zero placeholder digest; the
first promotion replaces it. Argo follows `main`; the Application and project
keep `Prune=false,Delete=false`.

## Access and recovery

Private LAN and Tailscale route through the existing nginx ingress with a
cert-manager certificate (`sewing-guide-tls`); the ingress has no public DNS
annotation. The public route is a dedicated Cloudflare Tunnel whose connector
reaches only the web Service over TLS and the Cloudflare edge; the web container
has no egress. Create the tunnel `sewing-guide-public` in Cloudflare Zero Trust
with public hostname `sewing.soyspray.vip` pointing at
`https://sewing-guide.sewing-guide.svc.cluster.local:443` (origin server name
`sewing.soyspray.vip`), then store its token in an Ansible Vault file outside
the checkout and run:

```sh
source soyspray-venv/bin/activate
ansible-playbook -i inventory/soycluster/hosts.yml \
  --become --become-user=root --user ubuntu apps/sewing-guide/bootstrap.yml \
  --ask-vault-pass -e @/private/sewing-guide.vault.yml
```

The bootstrap preserves an existing token and stops on a different one. Without
the token the connector pods stay unready and the private route still works.
There is no data to back up; recovery is the pinned image plus the tunnel
identity. Roll back by promoting the previous digest.
