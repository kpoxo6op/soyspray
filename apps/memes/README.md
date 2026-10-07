# Memes

Private phone feed at `https://memes.soyspray.vip`, reachable through LAN or
Tailscale and the internal nginx ingress. Open a personal invite, then rate one
meme at a time: **👍 Like**, **👎 Dislike**, or **Skip**. There is no undo.
The meme screen and feed API never disclose assignment arms or scores.

## Delivery state

This source package is **not registered** in the root Argo kustomization.
Deployment replicas are zero, preparation/import Jobs are suspended, and image
references await separate digest promotions. Source merges cannot start cluster
workloads. The image workflow tests and publishes web/import images independently
and reuses the repository promotion action unchanged. Distinct action directories
(`memes` and `memes/import`) give the two images separate promotion branches;
the importer entrypoint delegates to the same digest editor. Leave both draft promotions
open until goal 03; it must rebase them, retain both image entries, register Argo,
and deliberately enable workloads. No tokens, production assets, or private inputs
belong in this public repository or either image.

The dedicated namespace, Longhorn `memes-data` RWO 10Gi claim, and read-only
`memes-vk-archive` local PV/PVC are protected from pruning and deletion. The web
Deployment has one writer when enabled, `Recreate` strategy, and node-0 placement.
Importer and preparation also run on node-0 so they can share that destination.
Only preparation sets fsGroup; **never set fsGroup on the archive importer**.
The source claim and mount are read-only, and the importer verifies the mount's
read-only flag before reading. It never alters source files or permissions.
NetworkPolicy admits only nginx to port 8080 and denies pod egress. Models are
baked into the importer; view-time code has NumPy/SQLite and no ML dependencies.
The ingress has no public DNS annotation or tunnel and disables access logs;
application logs never include request paths, cookies, or invite tokens.

## Local development and checks

From the repository root, with Python 3.12.13 and Node 22:

```sh
python3 -m venv .build/memes-venv
.build/memes-venv/bin/pip install -r apps/memes/check-requirements.lock
cd apps/memes
npm ci
npx playwright install chromium
cd ../..
make check APP=memes PYTHON=.build/memes-venv/bin/python
make shared-check VENV=/path/to/repository-tooling-venv
```

`make check APP=memes` owns Ruff, Python HTTP/data/security tests, rendering both
Kustomizations, and authenticated phone/desktop browser tests. Tests generate
synthetic assets outside Git. `tests/e2e.py` drives real HTTP, compares results
against direct SQL, checks warm-up/allocation/template uniqueness, and logs a
refused repeat. This app does not require shared Makefile or CI inventory edits;
its new image workflow runs independently and also builds/tests both containers.

To run locally after import:

```sh
PYTHONPATH=apps/memes MEMES_DATA=/private/local/data \
  MEMES_HOST=127.0.0.1 MEMES_ORIGIN=http://127.0.0.1:8080 \
  MEMES_COOKIE_SECURE=false python -m memes.server
```

Use insecure cookies only on local loopback. Production cookies are Secure,
HttpOnly, SameSite=Lax, and last 365 days. All state mutations require the exact
configured Origin. Images and results require a hashed session cookie, and image
access is limited to impressions already assigned to that tester. `/healthz` is
the only anonymous status endpoint: `ok`, `catalog_count`, `catalog_version`,
`algo_version`. A missing/corrupt/frozen-version-mismatched catalog prevents startup.

## Frozen catalog import

`models.json` pins [SigLIP 2 base](https://huggingface.co/google/siglip2-base-patch16-224)
and [multilingual E5 small](https://huggingface.co/intfloat/multilingual-e5-small),
upstream weight hashes, Tesseract 5.5.0, traineddata hashes, and feature settings.
The complete Python dependency pins are in `import-requirements.lock`.
`prepare-models.py` verifies upstream checkpoints, exports only SigLIP's vision
tower, and records hashes of the offline model files. Import verifies these files
again and records actual Python/library/OCR versions in the catalog.

Enumerate all regular image paths in sorted order; shuffle uniformly without
replacement using seed 20261007. Reject animated/undecodable images and short
sides below 300 pixels. Reject SHA-256 duplicates and any dHash within Hamming
6 of an accepted image; continue down the seeded permutation to refill the target.
The source is read-only. Serving JPEGs have long side at most 1080, quality 85.
OCR uses original pixels, `rus+eng --psm 11`, one thread each in four workers;
at least three words must each have confidence 60 and two Latin/Cyrillic letters.
E5 uses `query: `, masked mean pooling, L2 normalization, and at most 512 tokens.

Center image embeddings by their catalog mean, then L2-normalize. Center passing
text embeddings by the mean over passing items, then normalize; nonpassing items
get zeros. Append text ×0.5 to the image vector and L2-normalize again. Raw normalized
image cosine ≥0.92 and dHash pairs feed union-find template clustering, including
transitive links. Rejected duplicates and their mappings remain private. K-means
on item vectors uses 15 clusters, seed 20261007, 10 starts, 100 iterations.
`catalog_version` hashes sorted accepted source SHA-256s plus canonical model,
version and feature pins. Record rejection counts and timings alongside the catalog.

Staging checkpoints allow `--resume` only with identical inputs; source hashes
are checked again. Validate vectors, serving hashes, metadata and the feasibility
of 15 distinct warm-up template clusters, then atomically rename the ready catalog.
An existing frozen catalog is never overwritten. Do not reset production staging
or alter the archive to recover a failed import.

For a **local copied sample** (install importer pins from the CPU Torch wheel
index first and use pinned cached weights, or run inside the importer image):

```sh
PYTHONPATH=apps/memes python -m memes.importer \
  --source /private/local/sample --data /private/local/data \
  --target 0 --local-sample
PYTHONPATH=apps/memes:apps/memes/tests python apps/memes/tests/e2e.py \
  --data /private/local/data --reactions 180 --output /private/local/evidence.json
```

Target 0 means all eligible images; default is 10,000. Never use `--local-sample`
against `/srv/media/downloads/vk`. The declared import Job caps CPU at 4, memory
at 6Gi, deadline at six hours, and mounts only that source and the app destination.
There is no periodic import and no image content is copied into Git/GHCR.

## Selection and logging

Warm-up is one random member from each of 15 k-means clusters, ordered randomly,
with distinct templates. Bipartite matching handles templates spanning clusters;
infeasible catalogs fail before publication. Thereafter each selected slot draws
`random` with probability 0.25 and `rec` with probability 0.75. Probabilities,
selection-time score, rank when ranked, Git SHA/config hash, catalog version and
selection time are immutable impression fields. Random slots also get the current
recommendation score. No likes/reactions means uniform eligible selection;
skips never update taste.

The score is mean top-3 cosine to likes minus 0.5 × mean top-3 cosine to dislikes;
use fewer when fewer exist. Recommendation picks uniformly from the top five
eligible items. All arms exclude every previously committed meme and template
cluster for that tester; recommendation cannot make a fourth consecutive pick
from one k-means cluster. NumPy brute-force search handles 10,000 vectors.

**Queue contract:** keep the visible head plus exactly two committed upcoming
impressions, except when eligibility is exhausted. The client loads the head and
preloads both upcoming images. A reaction selects one new tail slot using every
reaction so far, including random-arm reactions. The two already committed slots
retain their arm and score. “Updates immediately” refers to the next slot selected
after a reaction. `served_at` records commitment to this queue, and `served_seq`
is the stable served order; `rendered_at` records the first actual display.

SQLite uses WAL, FULL synchronous writes, foreign keys and serialized immediate
transactions. Unique tester/meme and tester/template keys prevent repeats. Selection
fields cannot be updated; action/render fields fill once. A second action is 409
and creates a `refused-repeat` event. Render/action events append alongside filled
impression fields; the server refuses non-head actions. Reload/multiple tabs retain
the current head. Timings use server render/action timestamps, with client hidden
milliseconds clamped to elapsed time; `response_ms` excludes that hidden time.
`client_seq` is the page's action sequence. The only deliberate history erasure is
the documented privacy deletion command below.

## Results definitions

Evaluated impression = `rec` or `random` with action like or dislike. Warm-up,
skips and pending slots do not enter like rate or AUC; counts/skips/warm-up are
shown. Like rate = likes / (likes + dislikes), with a 95% Wilson interval.
Halves split all evaluated impressions in served order at floor(n/2); the second
half gets an odd extra impression. Each half then splits by arm.

AUC uses evaluated **random-arm** impressions only, comparing their recommendation
scores recorded at selection time; ties receive half credit. It is `n/a` without
at least one like and one dislike. The one-sentence verdict says “not enough data”
if either arm has fewer than 30 evaluated impressions, otherwise describes which
like rate is higher (or equal). Intervals are descriptive under adaptive eligibility;
this page does not establish causal significance or real-user success.

## Operator invites and privacy

After verified recovery in goal 03, run these inside the deployed web image:

```sh
python -m memes.admin invite --name tester-label
python -m memes.admin exclude --user-id 1
python -m memes.admin delete --user-id 1
```

`--data` before the subcommand overrides `/data`. Invite prints the full HTTPS
link **once** to stdout; capture it privately and never paste it into reports, Git
or PRs. Tokens contain 32 random bytes and only SHA-256 is stored. Opening an invite
creates a separate hashed cookie session for the same tester; repeat visits preserve
history. Exclusion flags the tester for later group analysis and keeps access/data.
Deletion revokes sessions and removes that tester's impressions/events, leaving the
shared catalog intact; secure-delete and WAL truncation clear active database pages.
Older backups can retain deleted data until retention expires.

To capture the first owner's link locally without displaying it, set a restrictive
umask, refuse an existing file, and redirect the admin command's stdout to the
orchestrator-provided private destination. Do not create a production invite in
this source goal. Browser/test invites are isolated local fixtures only.

## Goal 03 prerequisites and rollback

Backup/restore code and CronJob are deferred: current repository checks do not
require them for this unregistered PVC package. No Vault inputs, Secrets, S3
prefixes or backup schedule are created here. Goal 03 must establish app-owned
encrypted off-cluster backup, completed backup evidence, independently held unlock
material, and an isolated authenticated restore including WAL-aware SQLite,
catalog/vector/image hashes and existing invite/session identity **before the first
production invite**. Scheduling alone cannot satisfy this prerequisite.

Promotions change only image digests and cannot enable replicas, unsuspend Jobs or
register Argo. Goal 03 must also validate node-0 import duration/storage and phone
access. Restore both tested digests through GitHub to roll back source behavior;
retain frozen catalog, SQLite, PVC/PV and access identity. Never delete durable
resources or reset source storage as a rollback.
