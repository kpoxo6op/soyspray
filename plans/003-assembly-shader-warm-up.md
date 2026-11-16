# Plan 003: The assembly guide compiles every shader before playback starts

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md` — unless a reviewer dispatched you and told you they
> maintain the index.
>
> **Drift check (run first)**: `git diff --stat ec61531..HEAD -- apps/assembly-guide/app/src apps/assembly-guide/app/test apps/assembly-guide/README.md`
> If any in-scope file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition.

## Status

- **Priority**: P1
- **Effort**: S
- **Risk**: LOW
- **Depends on**: plans/001-one-frame-callback-per-frame.md (done)
- **Category**: perf
- **Planned at**: commit `ec61531`, 2026-11-10

## Why this matters

three.js compiles a shader program the first time a material is drawn in a new state, and that compile blocks
the page for the frame. In the assembly guide every part switches between an opaque and a see-through program
when it fades in or out, and cords and screws bring their own variants, so playback freezes the first time each
appears: the audit counts 8 programs when the page says it is ready and 13 after scrubbing through the
timeline, with the late compiles at 10.6 s, 64.0 s, 74.4 s and 75.1 s. The Pearl guide already avoids this by
compiling everything behind its loading screen. After this plan the assembly guide does the same: every program
is compiled, without blocking, before the page fades in, and none is compiled during playback.

## Current state

The assembly guide is a static three.js player in `apps/assembly-guide/app` (esbuild bundles `src/main.js` into
one `dist/app.js` in IIFE format for `es2020`, so **top-level `await` is not available** in `main.js`).

Files:

- `apps/assembly-guide/app/src/scene.js` — the `Viewer` class: renderer, scene, `setTime(t)`, `render()`.
- `apps/assembly-guide/app/src/main.js` — entry point; its last section starts the player.
- `apps/assembly-guide/app/src/index.html`, `src/style.css` — the page. `#app` starts at `opacity: 0` and fades
  in when it gets the class `ready`.
- `apps/assembly-guide/app/test/helpers.mjs` — `installDomStubs()` and `fakeRenderer()` let tests build a
  `Viewer` in Node without WebGL; see `test/scene.test.mjs` for how they are used.
- `apps/assembly-guide/app/tools/perf-audit.mjs` — headless audit; reports `programsAtReady`,
  `programsAfterScrub` and `newPrograms` (their difference).

The end of `apps/assembly-guide/app/src/main.js` today (lines 100–115):

```js
// ---------------------------------------------------------------- start
const startAt = readHashTime();
if (startAt !== null) player.seek(startAt, 'restore');
syncInset();
viewer.setTime(player.time);
ui.update();
schedule();
root.classList.add('ready');
// Debug handle for tools/perf-audit.mjs and the browser console; the page itself never reads it.
window.__soyrack = { player, timeline, viewer, tags };

if (startAt === null && !reducedMotion.matches) {
  setTimeout(() => {
    if (!player.playing && player.time === 0 && !player.scrubbing) player.play();
  }, 900);
}
```

`render()` at the end of the `Viewer` class in `apps/assembly-guide/app/src/scene.js` (line 544):

```js
  render() {
    if (this.shadowDirty) {
      this.renderer.shadowMap.needsUpdate = true;
      this.shadowDirty = false;
    }
    this.renderer.render(this.scene, this.camera);
    this.dirty = false;
  }
}
```

`apps/assembly-guide/app/src/style.css` (lines 34–44):

```css
#app {
  position: fixed;
  inset: 0;
  opacity: 0;
  transition: opacity 0.5s ease;
}

#app.ready,
#app.no-webgl {
  opacity: 1;
}
```

`apps/assembly-guide/app/src/index.html` ends with:

```html
</main>
<script src="app.js"></script>
</body>
</html>
```

Conventions and constraints:

- Two-space indent, single quotes, semicolons; comments say why, in plain words.
- `test/bundle.test.mjs` checks the page's visible words. These must not appear in any visible text you add:
  "model", "warning", "caution", "heat", "temperature", "verif...", "photo", "AI", "TODO". The loading line in
  this plan ("Loading the 3D view") is already checked against that list; use it exactly.
- The same test requires that the built `app.js` makes no network requests (no `fetch(`, no `import(`).
- Tests must check behaviour, not mirror source text (repository rule in AGENTS.md).

## Commands you will need

Run from `apps/assembly-guide/app` inside your worktree.

| Purpose | Command | Expected on success |
|---------|---------|---------------------|
| Install | `npm ci` | exit 0 |
| Build + test | `npm run build && npm test` | exit 0, `# fail 0` |
| Audit | `PLAYWRIGHT_PATH=/opt/node-tools/node_modules/playwright node tools/perf-audit.mjs --max-frame-requests 1 --max-new-programs 0` | exit 0, `"newPrograms": 0` |

The audit starts a headless Chromium with software WebGL and takes about a minute; give it a 10 minute timeout.
Playwright is preinstalled at that path; do not install it and do not add it to `package.json`.

## Scope

**In scope** (the only files you should modify or create):

- `apps/assembly-guide/app/src/scene.js`
- `apps/assembly-guide/app/src/main.js`
- `apps/assembly-guide/app/src/index.html`
- `apps/assembly-guide/app/src/style.css`
- `apps/assembly-guide/app/test/warmup.test.mjs` (create)
- `apps/assembly-guide/README.md` (one paragraph)

**Out of scope** (do NOT touch):

- `apps/pearl-guide/**` — Pearl already warms up.
- `src/loop.js`, `src/tags.js`, `src/player.js`, `src/soyrack/**`, `tools/perf-audit.mjs`, `test/helpers.mjs`.
- Any Docker, nginx, workflow or manifest file, `package.json`, `plans/`.

## Git workflow

- Work on the branch your worktree is already on. Do not create or switch branches.
- One commit, message: `perf(assembly-guide): compile every shader before playback starts`
  with a short body giving the audit's `programsAtReady`, `programsAfterScrub` and `newPrograms` after the change.
- Do NOT push and do NOT open a pull request.

## Steps

### Step 1: Record the starting point

Run `npm ci && npm run build`, then the audit **without** `--max-new-programs`:
`PLAYWRIGHT_PATH=/opt/node-tools/node_modules/playwright node tools/perf-audit.mjs --max-frame-requests 1`

**Verify**: exit 0; the JSON shows `"frameRequests": 1`, `"programsAtReady": 8`, `"newPrograms": 5` (small
differences in the program counts are fine; `newPrograms` must be above 0, which is what this plan fixes).

### Step 2: Add `warmUp()` to the Viewer

In `apps/assembly-guide/app/src/scene.js`, insert this method into the `Viewer` class directly **before** the
`render() {` method (keep one blank line between methods):

```js
  /**
   * Compile every shader the timeline will need before playback starts. Each part swaps between an opaque and
   * a see-through program as it fades, and a program compiled on first use freezes the page for that frame.
   */
  async warmUp() {
    const objects = [];
    const materials = new Set();
    this.scene.traverse((o) => {
      objects.push([o, o.visible]);
      if (!o.material) return;
      for (const m of Array.isArray(o.material) ? o.material : [o.material]) materials.add(m);
    });
    const was = [...materials].map((m) => [m, m.transparent]);
    for (const [o] of objects) o.visible = true;
    const pass = async () => {
      try {
        await this.renderer.compileAsync(this.scene, this.camera);
      } catch {
        /* older browsers: the render below compiles them instead */
      }
      this.renderer.shadowMap.needsUpdate = true;
      this.renderer.render(this.scene, this.camera);
    };
    for (const transparent of [false, true]) {
      for (const m of materials) {
        if (m.transparent !== transparent) {
          m.transparent = transparent;
          m.needsUpdate = true;
        }
      }
      await pass();
    }
    for (const [m, transparent] of was) {
      if (m.transparent !== transparent) {
        m.transparent = transparent;
        m.needsUpdate = true;
      }
    }
    for (const [o, visible] of objects) o.visible = visible;
    this.dirty = true;
    this.shadowDirty = true;
  }
```

**Verify**: `node -e "import('./test/helpers.mjs').then(async (h) => { h.installDomStubs(); const { Viewer } = await import('./src/scene.js'); console.log(typeof Viewer.prototype.warmUp); })"` → prints `function`

### Step 3: Test it

Create `apps/assembly-guide/app/test/warmup.test.mjs` with exactly this content:

```js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { installDomStubs, fakeRenderer, meshes } from './helpers.mjs';

const makeElement = installDomStubs();
const { Viewer } = await import('../src/scene.js');
const { buildSoyrackTimeline, SoyrackStage, FLOOR_Z } = await import('../src/soyrack/index.js');

const timeline = buildSoyrackTimeline(meshes);

function sceneState(viewer) {
  const rows = [];
  viewer.scene.traverse((o) => {
    const mats = o.material ? (Array.isArray(o.material) ? o.material : [o.material]) : [];
    rows.push([o.visible, ...mats.map((m) => m.transparent)]);
  });
  return JSON.stringify(rows);
}

test('warmUp shows the renderer every material opaque and see-through, then puts the scene back', async () => {
  const renderer = fakeRenderer(makeElement);
  const viewer = new Viewer({ container: makeElement(), timeline, meshes, Stage: SoyrackStage, floorZ: FLOOR_Z, renderer });
  viewer.setTime(timeline.duration * 0.4); // mid-assembly: some parts shown, some hidden, some fading
  const before = sceneState(viewer);
  const passes = [];
  const look = () => {
    const seen = { hidden: 0, opaque: 0, clear: 0 };
    viewer.scene.traverse((o) => {
      if (!o.visible) seen.hidden++;
      if (!o.material) return;
      for (const m of Array.isArray(o.material) ? o.material : [o.material]) seen[m.transparent ? 'clear' : 'opaque']++;
    });
    return seen;
  };
  renderer.compileAsync = async () => {
    passes.push(look());
  };
  const rendersBefore = renderer.calls.render;
  viewer.dirty = false;
  viewer.shadowDirty = false;

  await viewer.warmUp();

  assert.equal(passes.length, 2, 'two compile passes');
  assert.ok(passes[0].opaque > 100 && passes[0].clear === 0, 'first pass: every material opaque');
  assert.ok(passes[1].clear > 100 && passes[1].opaque === 0, 'second pass: every material see-through');
  assert.equal(passes[0].hidden + passes[1].hidden, 0, 'nothing is hidden from the compile passes');
  assert.equal(renderer.calls.render - rendersBefore, 2, 'each pass also draws once, shadows included');
  assert.equal(sceneState(viewer), before, 'visibility and transparency are restored');
  assert.ok(viewer.dirty && viewer.shadowDirty, 'the next frame redraws');
});

test('warmUp still restores the scene when the renderer cannot compile ahead of time', async () => {
  const renderer = fakeRenderer(makeElement); // no compileAsync at all, like an old browser
  const viewer = new Viewer({ container: makeElement(), timeline, meshes, Stage: SoyrackStage, floorZ: FLOOR_Z, renderer });
  viewer.setTime(12);
  const before = sceneState(viewer);
  const rendersBefore = renderer.calls.render;
  await viewer.warmUp();
  assert.equal(renderer.calls.render - rendersBefore, 2, 'the draws compile the shaders instead');
  assert.equal(sceneState(viewer), before);
});
```

**Verify**: `node --test test/warmup.test.mjs` → `# pass 2`, `# fail 0`

### Step 4: Start the player after the warm-up

In `apps/assembly-guide/app/src/main.js`, replace the whole last section (from the comment line
`// ---------------------------------------------------------------- start` to the end of the file, shown in
"Current state") with:

```js
// ---------------------------------------------------------------- start
// Shaders compile behind the hidden page; a failed warm-up only means they compile on first use instead.
viewer
  .warmUp()
  .catch((err) => console.error(err))
  .then(() => {
    const startAt = readHashTime();
    if (startAt !== null) player.seek(startAt, 'restore');
    syncInset();
    viewer.setTime(player.time);
    ui.update();
    schedule();
    root.classList.add('ready');
    // Debug handle for tools/perf-audit.mjs and the browser console; the page itself never reads it.
    window.__soyrack = { player, timeline, viewer, tags };

    if (startAt === null && !reducedMotion.matches) {
      setTimeout(() => {
        if (!player.playing && player.time === 0 && !player.scrubbing) player.play();
      }, 900);
    }
  });
```

Do not use `await` at the top level of this file (the bundle format does not allow it).

**Verify**: `npm run build` → exit 0, prints `built ...`

### Step 5: Show a quiet loading line if getting ready takes a while

1. In `apps/assembly-guide/app/src/index.html`, add this line directly after the line `</main>`:

```html
<div class="loading" role="status">Loading the 3D view</div>
```

2. In `apps/assembly-guide/app/src/style.css`, directly after the rule

```css
#app.ready,
#app.no-webgl {
  opacity: 1;
}
```

   add (with a blank line before it):

```css
/* Shown only if getting ready takes longer than a moment (the shaders compile before the first frame). */
.loading {
  position: fixed;
  inset: 0;
  display: grid;
  place-items: center;
  color: var(--ink-dim);
  font-size: 14px;
  pointer-events: none;
  animation: loading-in 0.3s 0.5s both;
}

#app.ready ~ .loading,
#app.no-webgl ~ .loading {
  display: none;
}

@keyframes loading-in {
  from {
    opacity: 0;
  }
}
```

The line fades in only after half a second, so a quick start never flashes it, and it disappears as soon as
`#app` gets `ready` (or `no-webgl`).

**Verify**: `npm run build && npm test` → exit 0, `# fail 0` (46 tests: 44 existing plus the 2 new ones)

### Step 6: Run the audit with the new budget

**Verify**: `PLAYWRIGHT_PATH=/opt/node-tools/node_modules/playwright node tools/perf-audit.mjs --max-frame-requests 1 --max-new-programs 0` → exit 0; JSON shows `"newPrograms": 0`, `"lateCompiles": []`, `"pageErrors": []`, and `programsAtReady` equal to `programsAfterScrub` (about 16).

### Step 7: Document it

In `apps/assembly-guide/README.md`, replace the whole paragraph that begins `Performance is checked by count, not by feel.`
with exactly:

```md
Performance is checked by count, not by feel. `app/src/loop.js` runs the player: one animation-frame callback
per displayed frame, however often the player or the camera asks for one. Every shader compiles before the
page appears (`Viewer.warmUp` in `app/src/scene.js`), so playback never stops to compile one. After a build,
`PLAYWRIGHT_PATH=<playwright> node tools/perf-audit.mjs --max-frame-requests 1 --max-new-programs 0` (in `app/`)
plays the guide in a headless Chromium and reports frame requests per frame, shader programs compiled after the
page was ready, layout reads per frame and draw calls per chapter; each `--max-*` flag turns a number into a
pass or fail. It needs a Playwright with Chromium and is not part of `npm test`.
```

**Verify**: `grep -c "max-new-programs 0" ../README.md` → `1`

### Step 8: Commit

`git add` the six in-scope files and commit with the message from "Git workflow".

**Verify**: `git status --short` → empty; `git show --stat HEAD` lists exactly the six in-scope files.

## Test plan

- New `test/warmup.test.mjs` (content above), two cases: the renderer is shown every material once opaque and
  once see-through with nothing hidden, and the scene's visibility and transparency are exactly restored; and
  the same restore when the renderer has no `compileAsync` (older browsers).
- Existing suites stay green.
- Browser-level: the audit reports `newPrograms` 0.

## Done criteria

ALL must hold:

- [ ] `npm run build && npm test` exits 0 with `# fail 0`, including the 2 tests in `test/warmup.test.mjs`
- [ ] Audit with `--max-frame-requests 1 --max-new-programs 0` exits 0, `"newPrograms": 0`, `"pageErrors": []`
- [ ] `grep -n "await" src/main.js` shows no top-level `await`
- [ ] `git show --stat HEAD` lists only the six in-scope files

## STOP conditions

Stop and report back (do not improvise) if:

- `main.js`, `scene.js`, `style.css` or `index.html` do not match the excerpts in "Current state".
- After Step 6 the audit still reports `newPrograms` above 0, twice. Report the full JSON, including
  `lateCompiles`; do not add more warm-up passes on your own.
- The audit reports page errors or times out waiting for the page to become ready (that would mean the
  warm-up promise never settles).
- `test/bundle.test.mjs` fails on the loading line.
- An existing test fails and the cause is not an obvious typo of yours.

## Maintenance notes

- A new material state that changes the shader (a new light, fog, vertex colours, a clipping plane that is
  only sometimes on) needs a matching pass in `warmUp`. The audit's `--max-new-programs 0` catches a miss.
- The warm-up compiles a few programs that the timeline never uses (every material is tried in both states);
  that costs a little start-up time, not playback time.
- Reviewer: check that a rejected or missing `compileAsync` still starts the player, and that nothing visible
  changes: the page is hidden (`opacity: 0`) for the whole warm-up.
