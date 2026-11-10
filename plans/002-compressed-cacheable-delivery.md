# Plan 002: Both guides are served compressed and cached by content revision

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md` — unless a reviewer dispatched you and told you they
> maintain the index.
>
> **Drift check (run first)**: `git diff --stat 8545766..HEAD -- apps/assembly-guide/Dockerfile apps/pearl-guide/Dockerfile apps/pearl-guide/nginx.conf .github/workflows/assembly-guide-image.yml .github/workflows/pearl-guide-image.yml`
> If any of these changed since this plan was written, compare the
> "Current state" excerpts against the live files before proceeding; on a
> mismatch, treat it as a STOP condition.

## Status

- **Priority**: P1
- **Effort**: M
- **Risk**: LOW
- **Depends on**: none (can run in parallel with plan 001)
- **Category**: perf
- **Planned at**: commit `8545766`, 2026-11-10

## Why this matters

The assembly guide's image has no nginx configuration of its own, so its one script travels uncompressed
(1,032 KB; gzip makes it 336 KB) and no response says how long it may be cached. The Pearl guide compresses
scripts on the fly at nginx's weakest level and does not compress its models (760 KB of GLB), its WebAssembly
decoder (192 KB) or its print files, and it also sends no cache lifetime. Both builds already stamp asset URLs
with a content hash (`app.js?v=<16 hex>`), so those URLs can be cached for good. After this plan both images
carry a gzip copy of every compressible file, nginx serves that copy as is, revisioned URLs are cached for a
year as `immutable`, and the page itself is always revalidated. A first visit to the assembly guide drops from
about 1,040 KB to about 340 KB, a first visit to Pearl from about 1,260 KB to about 810 KB, and repeat visits
download only the small page.

## Current state

Each guide is a static site in an `nginxinc/nginx-unprivileged` image built by its `Dockerfile` (the Docker
build context is the app directory, for example `apps/assembly-guide`). A GitHub workflow builds the image,
starts it read-only and curls it. The cluster's ingress controller proxies to the pod over HTTP/1.1 and adds no
compression of its own.

`apps/assembly-guide/Dockerfile` (whole file):

```dockerfile
FROM node:22-bookworm-slim@sha256:83f487e0a63425e5b4d146fb5e5be574bcbe1b7b843d3ebafdd95eaf7767a7e5 AS build
WORKDIR /build
COPY app/package.json app/package-lock.json ./
RUN npm ci
COPY app/ ./
RUN npm run build && npm test

FROM nginxinc/nginx-unprivileged:1.30-alpine@sha256:ee7b7bc02a4af72c98d4365151f92d9b380c482c48d8c84bbbe44bd3192ba463
ARG SOURCE_REVISION=unknown
LABEL org.opencontainers.image.source="https://github.com/kpoxo6op/soyspray" \
      org.opencontainers.image.revision="${SOURCE_REVISION}"
COPY --from=build /build/dist/ /usr/share/nginx/html/
USER 101:101
EXPOSE 8080
```

There is no `apps/assembly-guide/nginx.conf`. `apps/assembly-guide/app/dist/` after a build holds exactly
`index.html`, `app.js`, `app.css`; `index.html` refers to `app.js?v=<16 hex>` and `app.css?v=<16 hex>`.

`apps/pearl-guide/Dockerfile` is the same except that it already has the line
`COPY nginx.conf /etc/nginx/conf.d/default.conf` directly before `COPY --from=build ...`.

`apps/pearl-guide/nginx.conf` (whole file):

```nginx
server {
    listen 8080;
    server_name _;
    root /usr/share/nginx/html;

    gzip on;
    gzip_types text/css application/javascript text/javascript image/svg+xml;

    location = / {
        add_header Cache-Control "no-cache";
        try_files /index.html =404;
    }

    location = /index.html {
        add_header Cache-Control "no-cache";
    }

    location /files/ {
        add_header Content-Disposition "attachment";
    }

    location / {
        try_files $uri =404;
    }
}
```

Pearl's `dist/` holds `index.html`, `app.js`, `app.css`, `pearl.svg`, `data/*.glb` (requested by `app.js` as
`data/pearl.glb?v=<16 hex>`), `draco/draco_decoder.wasm`, `draco/draco_wasm_wrapper.js`, `draco/draco_decoder.js`
(requested without a revision) and `files/*.stl` (downloads, no revision).

`.github/workflows/assembly-guide-image.yml`, the two `paths:` lists (identical, under `push` and `pull_request`):

```yaml
    paths:
      - apps/assembly-guide/app/**
      - apps/assembly-guide/Dockerfile
      - apps/assembly-guide/.dockerignore
      - .github/workflows/assembly-guide-image.yml
```

and its HTTP check step:

```yaml
      - name: Check the real HTTP entrypoint
        run: |
          docker run --detach --name assembly-guide-image-check --read-only \
            --cap-drop ALL --security-opt no-new-privileges \
            --tmpfs /tmp:rw,size=16m,uid=101,gid=101 \
            -p 127.0.0.1:4173:8080 "$IMAGE:$IMAGE_TAG"
          trap 'docker logs assembly-guide-image-check' ERR
          curl --fail --retry 10 --retry-all-errors --retry-delay 1 \
            -o "$RUNNER_TEMP/assembly-index.html" http://127.0.0.1:4173/
          curl --fail -o "$RUNNER_TEMP/assembly-app.js" http://127.0.0.1:4173/app.js
          curl --fail -o "$RUNNER_TEMP/assembly-app.css" http://127.0.0.1:4173/app.css
          test -s "$RUNNER_TEMP/assembly-index.html"
          test "$(wc -c < "$RUNNER_TEMP/assembly-app.js")" -gt 500000
          test -s "$RUNNER_TEMP/assembly-app.css"
```

`.github/workflows/pearl-guide-image.yml`, its HTTP check step (its `paths:` already cover `apps/pearl-guide/**`):

```yaml
      - name: Check the real HTTP entrypoint
        run: |
          docker run --detach --name pearl-guide-check --read-only \
            --cap-drop ALL --security-opt no-new-privileges \
            --tmpfs /tmp:rw,size=16m,uid=101,gid=101 \
            -p 127.0.0.1:4173:8080 "$IMAGE:$IMAGE_TAG"
          trap 'docker logs pearl-guide-check' ERR
          curl --fail --retry 10 --retry-all-errors --retry-delay 1 \
            -o "$RUNNER_TEMP/pearl-index.html" http://127.0.0.1:4173/
          grep -q '<title>Pearl' "$RUNNER_TEMP/pearl-index.html"
          for path in app.js app.css pearl.svg data/pearl.glb data/prints.glb data/bench.glb \
            draco/draco_decoder.wasm draco/draco_wasm_wrapper.js files/pearl_v3_1_shell.stl; do
            curl --fail --silent --output /dev/null "http://127.0.0.1:4173/$path"
          done
          test "$(curl --silent --output /dev/null --write-out '%{http_code}' http://127.0.0.1:4173/missing)" = 404
```

Facts you need about nginx:

- `gzip_static on;` makes nginx send `file.gz` (with `Content-Encoding: gzip`) when it exists and the client
  accepts gzip, whatever the file type. Clients that do not accept gzip get the plain file.
- `add_header` in a `location` block replaces, not extends, the `add_header` lines of the enclosing `server`
  block. A location with its own `add_header` must repeat `Cache-Control`.
- `map` blocks belong at the top level of this file (the file is included inside nginx's `http` block).

Conventions:

- Repository rule (AGENTS.md): "Build custom runtime code into immutable GHCR images." Nothing here changes a
  Kubernetes manifest; the running sites change only through later, separate digest promotion PRs.
- Both READMEs say: do not create a public DNS record or tunnel for these hosts. Nothing here touches DNS or
  ingress.
- The repository is public. Commit nothing personal or secret.

## Commands you will need

Run from the repository root unless a `cd` is shown.

| Purpose | Command | Expected on success |
|---------|---------|---------------------|
| Build (assembly) | `cd apps/assembly-guide/app && npm ci && npm run build` | exit 0, `dist/` has 3 files |
| Build (Pearl) | `cd apps/pearl-guide/app && npm ci && npm run build` | exit 0 |
| Delivery check | `bash "$CHECK" apps/assembly-guide 4191` and `bash "$CHECK" apps/pearl-guide 4192` (script from Step 1) | last line `PASS delivery checks for <app>`, exit 0 |
| Workflow syntax | `python3 -c "import yaml,sys; [yaml.safe_load(open(f)) for f in sys.argv[1:]]; print('ok')" .github/workflows/assembly-guide-image.yml .github/workflows/pearl-guide-image.yml` | prints `ok` |

Docker is not available in this environment (no daemon); do not try to build the images. A local `nginx`
(`/usr/sbin/nginx`, with the gzip_static module) is installed and the delivery check uses it. The real image
build runs in GitHub CI after the reviewer pushes.

## Scope

**In scope** (the only files you should modify or create):

- `apps/assembly-guide/nginx.conf` (create)
- `apps/assembly-guide/Dockerfile`
- `apps/assembly-guide/README.md` (one sentence, see Step 6)
- `.github/workflows/assembly-guide-image.yml`
- `apps/pearl-guide/nginx.conf`
- `apps/pearl-guide/Dockerfile`
- `apps/pearl-guide/README.md` (one paragraph, see Step 6)
- `.github/workflows/pearl-guide-image.yml`

**Out of scope** (do NOT touch):

- Anything under `apps/*/app/` — no source, build script or test changes. In particular do not move compression
  into `build.mjs`: `dist/` must stay as the tests expect it.
- `apps/*/manifests/`, `apps/*/argocd/`, any ingress or cluster configuration.
- `.github/actions/publish-image-promotion` and the promotion step of the Pearl workflow.
- `plans/` — the reviewer maintains it.
- Do not commit the delivery check script; it lives in a temporary directory.

## Git workflow

- Work on the branch your worktree is already on. Do not create or switch branches.
- One commit for the whole plan, message:
  `perf(guides): serve both 3D guides gzip-compressed with revision-keyed caching`
  with a short body giving the before and after sizes the delivery check printed.
- Do NOT push and do NOT open a pull request.

## Steps

### Step 1: Save the delivery check script outside the repository

Run `CHECK="$(mktemp -d)/delivery-check.sh"` and write this content to `$CHECK` (remember the path; shell
variables do not survive between separate commands, so note the literal path it printed):

```bash
#!/usr/bin/env bash
# Serve an app's built dist/ through its real nginx.conf with a local nginx and check the delivery headers.
# usage: delivery-check.sh <app directory, e.g. apps/assembly-guide> <free port>
set -euo pipefail
app="$(cd "$1" && pwd)"
port="$2"
work="$(mktemp -d)"
trap 'nginx -c "$work/wrap.conf" -s stop >/dev/null 2>&1 || true; rm -rf "$work"' EXIT
cp -r "$app/app/dist" "$work/dist"
# Run the Dockerfile's own compression step, so the check covers the real command.
step="$(grep -E '^RUN find dist ' "$app/Dockerfile" | sed 's/^RUN //' || true)"
test -n "$step" || { echo "FAIL no 'RUN find dist' step in $app/Dockerfile"; exit 1; }
(cd "$work" && eval "$step")
sed -e "s#root /usr/share/nginx/html;#root $work/dist;#" -e "s#listen 8080;#listen 127.0.0.1:$port;#" "$app/nginx.conf" > "$work/site.conf"
cat > "$work/wrap.conf" <<CONF
user root;
pid $work/nginx.pid;
error_log $work/error.log;
events {}
http {
  include /etc/nginx/mime.types;
  default_type application/octet-stream;
  access_log off;
  client_body_temp_path $work/t1; proxy_temp_path $work/t2; fastcgi_temp_path $work/t3; uwsgi_temp_path $work/t4; scgi_temp_path $work/t5;
  include $work/site.conf;
}
CONF
nginx -t -c "$work/wrap.conf" >/dev/null 2>&1 || { nginx -t -c "$work/wrap.conf"; exit 1; }
nginx -c "$work/wrap.conf" >/dev/null 2>&1
base="http://127.0.0.1:$port"
fail=0
check() { # check <label> <path> <header regex that must match, or !regex that must not>...
  local label="$1" path="$2" headers; shift 2
  headers="$(curl -s -m 10 -o /dev/null -D - -H 'Accept-Encoding: gzip' "$base$path" | tr -d '\r')"
  for want in "$@"; do
    if [ "${want#!}" != "$want" ]; then
      if grep -qiE "${want#!}" <<<"$headers"; then echo "FAIL $label: unexpected ${want#!}"; fail=1; fi
    elif ! grep -qiE "$want" <<<"$headers"; then echo "FAIL $label: missing $want"; fail=1; fi
  done
}
script="$(grep -oE 'app\.js\?v=[0-9a-f]{16}' "$work/dist/index.html" | head -1)"
style="$(grep -oE 'app\.css\?v=[0-9a-f]{16}' "$work/dist/index.html" | head -1)"
check page / '^HTTP/1.1 200' '^Cache-Control: no-cache$' '^Content-Encoding: gzip$' '^Vary: Accept-Encoding$'
check page-with-revision "/?v=0123456789abcdef" '^Cache-Control: no-cache$'
check script "/$script" '^HTTP/1.1 200' '^Cache-Control: public, max-age=31536000, immutable$' '^Content-Encoding: gzip$' '^Vary: Accept-Encoding$'
check style "/$style" '^Cache-Control: public, max-age=31536000, immutable$' '^Content-Encoding: gzip$'
check script-without-revision /app.js '^Cache-Control: no-cache$' '!immutable'
check missing /missing '^HTTP/1.1 404'
# The compressed body must decode to the built file, and a client that does not ask for gzip gets it plain.
curl -s -m 20 -H 'Accept-Encoding: gzip' "$base/$script" | gzip -dc | cmp -s - "$work/dist/app.js" || { echo "FAIL script: gzip body differs from dist/app.js"; fail=1; }
curl -s -m 20 "$base/$script" | cmp -s - "$work/dist/app.js" || { echo "FAIL script: plain body differs from dist/app.js"; fail=1; }
plain="$(wc -c < "$work/dist/app.js")"
packed="$(curl -s -m 20 -H 'Accept-Encoding: gzip' -o /dev/null -w '%{size_download}' "$base/$script")"
echo "app.js: $plain bytes plain, $packed bytes on the wire"
[ "$packed" -lt $((plain / 2)) ] || { echo "FAIL script: not compressed"; fail=1; }
if [ -d "$work/dist/data" ]; then # Pearl guide extras: models, decoder and print files
  model="$(grep -oE 'pearl\.glb\?v=[0-9a-f]{16}' "$work/dist/app.js" | head -1)"
  check model "/data/$model" '^HTTP/1.1 200' '^Cache-Control: public, max-age=31536000, immutable$' '^Content-Encoding: gzip$'
  check decoder /draco/draco_decoder.wasm '^HTTP/1.1 200' '^Content-Type: application/wasm$' '^Content-Encoding: gzip$' '^Cache-Control: no-cache$'
  check print-file /files/pearl_v3_1_shell.stl '^HTTP/1.1 200' '^Content-Disposition: attachment$' '^Cache-Control: no-cache$'
  curl -s -m 20 --compressed "$base/files/pearl_v3_1_shell.stl" | cmp -s - "$work/dist/files/pearl_v3_1_shell.stl" || { echo "FAIL print-file: body differs"; fail=1; }
  curl -s -m 20 --compressed "$base/data/$model" | cmp -s - "$work/dist/data/pearl.glb" || { echo "FAIL model: body differs"; fail=1; }
fi
[ "$fail" = 0 ] && echo "PASS delivery checks for $(basename "$app")"
exit "$fail"
```

**Verify**: build both apps (commands table), then `bash "$CHECK" apps/pearl-guide 4192; echo "exit $?"` → `exit 1`
with a line `FAIL no 'RUN find dist' step in ...` (the check fails before your change; that is expected).

### Step 2: Give the assembly guide an nginx configuration

Create `apps/assembly-guide/nginx.conf` with exactly this content:

```nginx
# Assets carry a content revision (?v=<hash>, written by app/build.mjs), so a revisioned URL never changes
# and browsers may keep it for good. Everything else, the page above all, is revalidated on every visit.
map $arg_v $asset_cache {
    default "no-cache";
    "~^[0-9a-f]{16}$" "public, max-age=31536000, immutable";
}

server {
    listen 8080;
    server_name _;
    root /usr/share/nginx/html;

    # The Dockerfile stores a .gz beside every text asset; nginx sends that file instead of compressing per request.
    gzip_static on;
    gzip_proxied any;
    gzip_vary on;

    add_header Cache-Control $asset_cache;

    location = / {
        add_header Cache-Control "no-cache";
        try_files /index.html =404;
    }

    location = /index.html {
        add_header Cache-Control "no-cache";
    }

    location / {
        try_files $uri =404;
    }
}
```

**Verify**: `test -f apps/assembly-guide/nginx.conf && grep -c "gzip_static on" apps/assembly-guide/nginx.conf` → `1`

### Step 3: Compress in the assembly guide's image build and install the configuration

Edit `apps/assembly-guide/Dockerfile`:

1. Directly after the line `RUN npm run build && npm test` add these two lines:

```dockerfile
# A gzip copy beside every compressible file; nginx serves it as is (gzip_static in nginx.conf).
RUN find dist -type f \( -name '*.html' -o -name '*.js' -o -name '*.css' -o -name '*.svg' \) -exec gzip -9 -n -k {} +
```

2. Directly before the line `COPY --from=build /build/dist/ /usr/share/nginx/html/` add:

```dockerfile
COPY nginx.conf /etc/nginx/conf.d/default.conf
```

**Verify**: `bash "$CHECK" apps/assembly-guide 4191` → prints `app.js: 1032432 bytes plain, <about 336000> bytes on the wire` and `PASS delivery checks for assembly-guide`, exit 0. (The plain size differs if another plan already changed the app; what matters is PASS.)

### Step 4: Replace the Pearl guide's nginx configuration and compress in its image build

Replace the whole content of `apps/pearl-guide/nginx.conf` with:

```nginx
# Assets carry a content revision (?v=<hash>, written by app/build.mjs), so a revisioned URL never changes
# and browsers may keep it for good. Everything else, the page above all, is revalidated on every visit.
map $arg_v $asset_cache {
    default "no-cache";
    "~^[0-9a-f]{16}$" "public, max-age=31536000, immutable";
}

server {
    listen 8080;
    server_name _;
    root /usr/share/nginx/html;

    # The Dockerfile stores a .gz beside every compressible file; nginx sends that file instead of compressing per request.
    gzip_static on;
    gzip_proxied any;
    gzip_vary on;

    add_header Cache-Control $asset_cache;

    location = / {
        add_header Cache-Control "no-cache";
        try_files /index.html =404;
    }

    location = /index.html {
        add_header Cache-Control "no-cache";
    }

    location /files/ {
        add_header Cache-Control $asset_cache;
        add_header Content-Disposition "attachment";
    }

    location / {
        try_files $uri =404;
    }
}
```

Edit `apps/pearl-guide/Dockerfile`: directly after the line `RUN npm run build && npm test` add:

```dockerfile
# A gzip copy beside every compressible file; nginx serves it as is (gzip_static in nginx.conf).
RUN find dist -type f \( -name '*.html' -o -name '*.js' -o -name '*.css' -o -name '*.svg' -o -name '*.glb' -o -name '*.wasm' -o -name '*.stl' \) -exec gzip -9 -n -k {} +
```

**Verify**: `bash "$CHECK" apps/pearl-guide 4192` → prints `app.js: <about 760000> bytes plain, <about 203000> bytes on the wire` and `PASS delivery checks for pearl-guide`, exit 0.

### Step 5: Make CI check the same things on the real images

In `.github/workflows/assembly-guide-image.yml`:

1. In **both** `paths:` lists add the line `      - apps/assembly-guide/nginx.conf` directly after
   `      - apps/assembly-guide/Dockerfile`.
2. At the end of the `run: |` block of the step `Check the real HTTP entrypoint` (after the line
   `test -s "$RUNNER_TEMP/assembly-app.css"`), append these lines with the same ten-space indentation:

```yaml
          script="$(grep -oE 'app\.js\?v=[0-9a-f]{16}' "$RUNNER_TEMP/assembly-index.html" | head -1)"
          curl --fail --silent --header 'Accept-Encoding: gzip' \
            --dump-header "$RUNNER_TEMP/assembly-app.headers" \
            -o "$RUNNER_TEMP/assembly-app.js.gz" "http://127.0.0.1:4173/$script"
          grep -qi '^content-encoding: gzip' "$RUNNER_TEMP/assembly-app.headers"
          grep -qi '^cache-control: public, max-age=31536000, immutable' "$RUNNER_TEMP/assembly-app.headers"
          gzip -dc "$RUNNER_TEMP/assembly-app.js.gz" | cmp - "$RUNNER_TEMP/assembly-app.js"
          test "$(wc -c < "$RUNNER_TEMP/assembly-app.js.gz")" -lt 450000
          curl --fail --silent --dump-header "$RUNNER_TEMP/assembly-index.headers" \
            -o /dev/null http://127.0.0.1:4173/
          grep -qi '^cache-control: no-cache' "$RUNNER_TEMP/assembly-index.headers"
```

In `.github/workflows/pearl-guide-image.yml`, at the end of the `run: |` block of the step
`Check the real HTTP entrypoint` (after the line that tests `/missing` for `404`), append with the same
indentation:

```yaml
          script="$(grep -oE 'app\.js\?v=[0-9a-f]{16}' "$RUNNER_TEMP/pearl-index.html" | head -1)"
          curl --fail --silent --header 'Accept-Encoding: gzip' \
            --dump-header "$RUNNER_TEMP/pearl-app.headers" \
            --output /dev/null "http://127.0.0.1:4173/$script"
          grep -qi '^content-encoding: gzip' "$RUNNER_TEMP/pearl-app.headers"
          grep -qi '^cache-control: public, max-age=31536000, immutable' "$RUNNER_TEMP/pearl-app.headers"
          for path in data/pearl.glb draco/draco_decoder.wasm files/pearl_v3_1_shell.stl; do
            curl --fail --silent --header 'Accept-Encoding: gzip' \
              --dump-header "$RUNNER_TEMP/pearl-asset.headers" \
              --output /dev/null "http://127.0.0.1:4173/$path"
            grep -qi '^content-encoding: gzip' "$RUNNER_TEMP/pearl-asset.headers"
          done
          grep -qi '^content-disposition: attachment' "$RUNNER_TEMP/pearl-asset.headers"
          curl --fail --silent --dump-header "$RUNNER_TEMP/pearl-index.headers" \
            --output /dev/null http://127.0.0.1:4173/
          grep -qi '^cache-control: no-cache' "$RUNNER_TEMP/pearl-index.headers"
```

**Verify**: the workflow syntax command from the table → prints `ok`.
**Verify**: `grep -c "apps/assembly-guide/nginx.conf" .github/workflows/assembly-guide-image.yml` → `2`

### Step 6: Document it

1. In `apps/assembly-guide/README.md`, first paragraph block, replace the sentence
   `Built asset URLs contain content revisions so returning phone browsers fetch the promoted player instead of reusing an older cached script.`
   (it is wrapped over three lines) with this text, wrapped at about 80 columns like the lines around it:

   `Built asset URLs contain content revisions, so nginx.conf lets a browser keep a revisioned file for a year while the page itself is checked on every visit: a promoted player is picked up at once and nothing else is downloaded twice. The image also carries a gzip copy of each file, which nginx serves as is; the 1 MB script travels as about 340 KB.`

   Write `nginx.conf` in backticks.

2. In `apps/pearl-guide/README.md`, add this paragraph at the very end of the file (after the paragraph of the
   `## Deploy and roll back` section), separated by a blank line:

```md
`nginx.conf` serves the gzip copy the image build stores beside every script, model, decoder and print file,
caches URLs that carry a content revision (`?v=`) for a year and has the page itself checked on every visit.
The image workflow checks those headers on the built image.
```

**Verify**: `grep -c "gzip" apps/assembly-guide/README.md apps/pearl-guide/README.md` → each at least `1`

### Step 7: Re-run both delivery checks and commit

**Verify**: `bash "$CHECK" apps/assembly-guide 4191 && bash "$CHECK" apps/pearl-guide 4192` → two `PASS` lines, exit 0.

`git add` the eight in-scope files and commit with the message from "Git workflow".

**Verify**: `git status --short` → empty; `git show --stat HEAD` lists exactly the eight in-scope files.

## Test plan

- No unit tests: this is server configuration. The gate is the delivery check (local nginx, real `nginx.conf`,
  real compression command from the Dockerfile) and, after push, the two image workflows, which now assert the
  same headers on the real images.
- Cases the delivery check covers: page is `no-cache` and stays `no-cache` even with a `?v=` on it; revisioned
  script and stylesheet are `immutable` and gzip-encoded; an unrevisioned script URL is `no-cache`; gzip body
  decodes to the built file; a client without gzip gets the plain file; 404 still works; for Pearl also the
  model, the WebAssembly decoder (with `application/wasm`) and a print file with `Content-Disposition: attachment`.

## Done criteria

ALL must hold:

- [ ] `bash "$CHECK" apps/assembly-guide 4191` ends with `PASS delivery checks for assembly-guide`
- [ ] `bash "$CHECK" apps/pearl-guide 4192` ends with `PASS delivery checks for pearl-guide`
- [ ] The workflow syntax command prints `ok`
- [ ] `grep -c "apps/assembly-guide/nginx.conf" .github/workflows/assembly-guide-image.yml` → `2`
- [ ] `git show --stat HEAD` lists only the eight in-scope files; nothing under `apps/*/app/` changed

## STOP conditions

Stop and report back (do not improvise) if:

- A Dockerfile, the Pearl `nginx.conf` or a workflow does not match the excerpts in "Current state".
- `nginx -t` rejects a configuration (the check prints nginx's error) and the cause is not a typo of yours.
- The delivery check fails twice after a reasonable fix attempt. Report its full output.
- `nginx` is not installed or cannot start. Do not install packages; report it.
- You think a file under `apps/*/app/` or a manifest needs to change.

## Maintenance notes

- A new asset type must be added to the `find` list in the Dockerfile, or it is served uncompressed.
- A new `location` block with its own `add_header` must repeat the `Cache-Control` line.
- The `immutable` rule trusts that a 16-hex `?v=` is a content hash. Both `build.mjs` files write it that way;
  a future build that stops revisioning an asset still works, the asset is then revalidated on each visit.
- Pearl's Draco decoder files are requested without a revision, so they are revalidated (a small 304) on each
  visit. Revisioning them in `build.mjs` would remove that request; deferred as a small follow-up.
- Reviewer: the real proof is the two image workflows on the pull request; read their "Check the real HTTP
  entrypoint" step output.
