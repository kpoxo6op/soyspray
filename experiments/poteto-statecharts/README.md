# Poteto statechart experiments

Three small experiments found one reproducible recovery gap and demonstrated two
existing safeguards. This is an unmerged research package, not a production fix
or a claim that Soyspray is formally verified. No cluster operations were run.

Start with the [visual report](results/visuals/index.html), the three PNGs
([intake](results/visuals/01-intake.png), [stale operation](results/visuals/02-stale-operation.png),
[promotion](results/visuals/03-promotion.png)), or the [research](research.md).
Each run retains its Mermaid source, Pele SVG, report and raw TLC output.

## Results

| Experiment | Current behavior | Negative case | Evidence |
| --- | --- | --- | --- |
| Evidence intake | Uninterrupted publication passes, 4 states | One interruption reaches 14 states; retry fails at two publication boundaries | Both reproduced against `evidence.install` using real disposable files |
| Stale-operation recovery | Version guard passes, 7 states | Removing the version permits termination of a newer operation, 7 states | Real patch builder and temporary source mutant; API conflict behavior emulated |
| Separate image promotion | Source/build/publish/promotion flow passes, 6 states | Hypothetical source auto-deployment violates approval boundary, 7 states | Model-only negative control; 7 existing promotion-helper tests pass |

All six runs produced their expected results in about 13 seconds on this laptop,
excluding setup, modeling, code replay and rendering. These are tiny models, not
a performance benchmark. `results/summary.json` records run durations.

### Confirmed recovery gap

`RetryRecovers` means retrying the same valid archive after one process stop does
not reject a matching version solely because publication stopped between steps.
The shortest counterexample has three actions from verified staging:

1. Write and flush `COMPLETE`.
2. Stop the receiver process.
3. Retry the identical archive; verification rejects the writable root.

A second path renames staging into `versions/` before stopping, with the same
retry error: `Published pack directory is not read-only`. The model identifies
both rejected states; TLC reports the shortest path to the invariant violation.

`replay.py` runs the real packer and receiver, exits a child with `os._exit(77)`
immediately after the real marker chmod or rename, then retries in the parent.
It changes no application code. Both replays retain a verified previous version,
and startup rejects the interrupted version. This is a recovery/availability
gap, not evidence of corrupt data being served or a live incident. Local modes
were `0775` rather than required `0555`; the writable mode depends on umask.

The existing eight evidence tests pass. Their interruption test kills the
receiver during extraction, before `COMPLETE`, so it does not own these later
boundaries. The added replay covers the observable contract at those boundaries,
using actual files and a real process exit rather than source-text assertions.
It remains an experiment that expects the current failure, not a regression test
to adopt unchanged after a fix.

A future fix needs deliberate recovery semantics for a fully hashed version
whose root was not sealed. Simply skipping read-only verification would weaken
startup protection. No recovery fix or production change is included here.

### Source mapping and assumptions

Coverage was checked at `358c97f8` (full commit and file hashes in
`provenance.json`). The rerun refuses changed covered files until the model is
reviewed and the coverage record is updated.

| Model actions | Code or policy boundary | Bounds and exclusions |
| --- | --- | --- |
| `WriteMarker`, `Publish`, `Seal`, `Retry` | `apps/agents/evidence.py`: `install`, `verify`; marker write, staging rename, root chmod and existing-version retry | One valid new pack, one writer, one process stop; begins after extraction/hash verification. No power loss, partial marker write, fsync failure, disk corruption, simultaneous writers or NFS claim |
| `Reread`, `Replace`, `Patch` | `apps/agents/operations/retire_stale_sync.py`: final re-read and `termination_patch` resourceVersion | One reviewed operation and at most one replacement. Server equality check and patch application assumed atomic. Existing identity guards assumed passed; no real API exercised |
| `MergeSource`, `BuildAndTest`, `PublishImage`, `MergePromotion`, `Reconcile` | `.github/actions/publish-image-promotion/action.yml`; `apps/domain-health/promote-image.py`; pinned deployment digest and Argo Application source on `main` | One old/new digest, successful build, publication and reconcile. No registry trust, CI permissions, branch protection, rollback, failed build or competing promotion |

The promotion model's `approved` variable means the separate promotion merged;
it does not prove who reviewed it. Its shortcut is explicitly hypothetical and
is not replayed as a real workflow bug. The stale-operation replay uses the real
request builder and a temporary source mutation, with a small local API emulator.
It checks client behavior under the documented server contract, not the server.
Three existing stale-operation tests and seven promotion tests also pass.

The charts suppress terminal self-loops and merge states that differ only in
the one-crash budget. Reports disclose collapsed steps: intake normal 1,
intake crash 5, stale-operation variants 3 each, promotion variants 1 each.
No violation labels are merged away. These are safety checks; eventual recovery
under repeated failures or fairness assumptions is not proven.

## Reproduce

Use Python with PyYAML (the repository venv), Node 22.18+ on the 22.x line or
23.6+, Java 11+, and the pinned upstream tools. The recorded run used Node
22.23.4 and Temurin 25.0.5+8. Obtain tools outside the repository:

```sh
git clone https://github.com/cursor/plugins.git /tmp/pstack-research
git -C /tmp/pstack-research checkout 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
mkdir -p /tmp/statechart-tools
curl -fL https://github.com/tlaplus/tlaplus/releases/download/v1.7.4/tla2tools.jar \
  -o /tmp/statechart-tools/tla2tools.jar
npm install --prefix /tmp/statechart-tools --ignore-scripts --save-exact pele@1.9.0
```

The runner verifies the recorded TLC SHA256 and upstream commit, copies models
to a disposable directory, and requires a new output directory:

```sh
python experiments/poteto-statecharts/run.py \
  --upstream /tmp/pstack-research --java /absolute/path/to/java \
  --tlc /tmp/statechart-tools/tla2tools.jar --out /tmp/statechart-rerun
node experiments/poteto-statecharts/render.mjs \
  /tmp/statechart-rerun /tmp/statechart-tools
python -m http.server 4179 --bind 127.0.0.1 --directory /tmp/statechart-rerun
```

Open `http://127.0.0.1:4179/visuals/`. The saved PNGs were full-page captures in
visible Chrome at 1440 CSS pixels, DPR 1. SVG and HTML render locally without a
remote diagram service. The renderer preserves the generated Mermaid graph;
it only adds CSS and explanatory panels.

The runner succeeds when the expected pass/fail pattern and code replays hold.
**Success is not six passing models:** intake-crash and both negative controls
must fail their stated invariant. Each state's rule verdict remains in the raw
report. To inspect a single case, use upstream `/statechart` with that model,
its matching config/view and a new output directory.

Existing checks used:

```sh
python -m unittest discover -s apps/agents/tests -p test_evidence.py -v
PYTHONPATH=apps/agents python -m unittest discover -s apps/agents/tests -p test_stale_sync.py -v
python -m pytest -q apps/domain-health/tests/test_domain_health_promotion.py
```

No global skill installation, orchestration policy, release workflow, manifest,
runtime source or deployment was changed. Remove this experiment directory to
roll back the research artifacts.
