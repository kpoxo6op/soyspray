# Reading

A reader for owned books at `https://reading.soyspray.vip`: original text
with glosses, a modern version, questions, exercises and writing prompts per
chapter. Boris made it public on 21 Nov 2026 to share with a friend. Every
response carries `X-Robots-Tag: noindex, nofollow`.

## Paths and content

`/` lists books, `/<book>/` opens a book, and
`/epictetus/handbook/1/` opens Handbook 1. Discourses use
`/epictetus/discourses/<book>/<chapter>/`; Fragments use
`/epictetus/fragments/<chapter>/`. Assets use content hashes in their query
strings; font filenames contain their hashes. HTML always revalidates.

## Adding a chapter

Follow the JSON schema in the reader design spec, section 9. The executable
validator is [validate.js](app/src/validate.js); [the fixture](app/test/fixtures/content/) is a complete
small example. Put real chapters in `app/content/<book>/<work>/` using the
numbered filenames in the schema. The build validates content before rendering;
errors fail the build, while gloss density and long plain versions produce
warnings. It never substitutes fixture content for missing real content.

The site is shared with friends, so every example in questions, exercises,
objections, prompts, glosses and the about page is general and timeless: no
job, tech, home-lab or family details from the owner's life. The validator
rejects tech vocabulary in English and Russian.

The Russian edition lives in `app/content/<book>/ru/` (`book.json`,
`glossary.json`, `about.json` and one overlay per chapter at the same path as
the English). Overlays carry only the words and must mirror the English shape;
the shape and writing rules are in the project notes (`ru-schema.md`). Every
page is built twice: `/…` in English and `/ru/…` in Russian. On a Russian
chapter the Russian text is the reading text with its own glosses, and Hard's
English appears only as the right column of the side-by-side view. The header
link (RU or EN) switches to the twin page; `theme.js` remembers the choice as
`reading.lang` and sends later visits to the same language. A book with a `ru`
folder must translate every chapter, or the build fails.

```sh
cd apps/reading/app
node build.mjs --content test/fixtures/content --out dist
node --test test/*.test.mjs
node build.mjs  # real content/ is required
```

The fixture defines the two containers left unspecified by the design:
`library.json` is `{ "schema": 1, "books": ["epictetus"] }`; `about.json` has
`schema`, `title`, and `sections` containing `title` and `paragraphs`.

Display, notes, Keep and progress use localStorage under `reading.`. Notes
provides JSON import and JSON/Markdown export plus an inline erasure confirmation.
Settings and read changes carry companion timestamps so imports can merge newer
changes, including removed read marks and kept passages. Day records include `t`.
With storage blocked, controls and writing remain available for the current visit.
Without JavaScript, the full chapter and gloss links remain readable.

This repository and its runtime images must contain no secrets or personal data.
Notes, kept passages and progress stay in each reader's browser; the server stores nothing.

## Access

The public route uses the dedicated Cloudflare Tunnel `reading-public`, whose
public hostname `reading.soyspray.vip` points at
`http://reading-origin.reading.svc.cluster.local:8080`, a headless Service, so the
connector reaches the pod directly. The private LAN and Tailscale route keeps the
existing Ingress through split DNS. The network policies allow the connector only
node-local DNS, the web pod and the Cloudflare tunnel endpoints; Calico also closes
node and Service addresses to it, and the web pod has no egress.

`bootstrap.yml` creates the missing `reading-cloudflared-token` Secret through the
shared `apps/bootstrap-secret-tasks.yml` procedure and never replaces an existing
one. Put `reading_cloudflared_token` in an Ansible Vault variables file outside the
checkout (the token is in the Cloudflare dashboard under the tunnel), then run from
the repository root:

```sh
source soyspray-venv/bin/activate
ansible-playbook -i inventory/soycluster/hosts.yml \
  --become --become-user=root --user ubuntu apps/reading/bootstrap.yml \
  --ask-vault-pass -e @/private/path/reading.vault.yml
```

Check the public route through public DNS (`dig @1.1.1.1 reading.soyspray.vip`),
not the split-DNS address, and `kubectl -n reading logs deployment/reading-cloudflared`.

## Checks

```sh
make -C apps/reading check   # Node 22 build, output test, both Kustomize packages
```

The build needs no packages. The tests check authoring errors, rendered structure, internal links, CSP-safe
markup, payload budgets and asset revisions. Tests build into an isolated
`dist-test/` directory and remove it without replacing production `dist/`. The image
workflow checks routes, slash redirects, gzip, caching and CSP from a read-only
container before publishing. `smoke` reports that a tailnet and a public check are still needed;
`restore-check` reports not-required because the app has no persistent state.

## Deploy and roll back

Merge the source PR first. Changes to `app/`, `Dockerfile`, `nginx.conf` or
`.dockerignore` build and test the image, publish it and open a draft digest
promotion PR for `manifests/deployment.yaml`. The initial all-zero digest is a
placeholder, not a runnable image. Keep the app unregistered until a real tested
digest has been promoted.

After the first promotion merges, a separate Argo registration PR adds
`../apps/reading/argocd` to `argocd/kustomization.yaml`. Argo then follows `main`.
Check the Application is Synced and Healthy, open `/`, `/epictetus/` and
`/epictetus/handbook/1/` from a tailnet device and from outside it. Later source merges leave the running image unchanged until promotion.
Roll back by reverting a digest promotion. No backup is required.
