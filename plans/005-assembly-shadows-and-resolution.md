# Plan 005: The assembly guide redraws shadows only when something moved and adapts its resolution

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md` — unless a reviewer dispatched you and told you they
> maintain the index.
>
> **Drift check (run first)**: `git diff --stat 8f4005d..HEAD -- apps/assembly-guide/app/src apps/assembly-guide/app/test apps/assembly-guide/README.md`
> If any in-scope file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition.

## Status

- **Priority**: P2
- **Effort**: M
- **Risk**: MED
- **Depends on**: plans/004-assembly-name-tags-without-layout-reads.md (done)
- **Category**: perf
- **Planned at**: commit `8f4005d`, 2026-11-10

## Why this matters

Two things make the assembly guide's GPU work heavier than it needs to be.

First, `Viewer.setTime()` marks the shadow map dirty on every call, so every played frame draws the whole
scene twice: once into the 2048 px shadow map and once to the screen (up to 862 draw calls together). But the
parts stand still for most of the timeline while captions are read, the camera moves or something fades. Stepping
the timeline at 30 frames a second, the set of shadow casters and their positions is unchanged in 69% of
frames. `setTime()` also recomputes every world matrix and re-uploads every screw's instance matrix on those
frames.

Second, the guide renders at up to 2x the CSS resolution on every device and never backs off. The Pearl guide
(`apps/pearl-guide/app/src/stage.js`) starts phones at 1.5x and lowers the resolution a step when frames stay
slow; the assembly guide has neither.

After this plan the shadow map is redrawn only on frames where a shadow caster moved, appeared or left (the
picture is pixel-identical, verified by the reviewer), unchanged frames skip the matrix work, phones start at
1.5x, and sustained slow frames lower the resolution in steps of 0.25 down to a floor, recovering when frames
are quick again.

## Current state

Files (all under `apps/assembly-guide/app`):

- `src/scene.js` — the `Viewer` class. `setTime(t)` applies the timeline state; `render()` redraws the shadow
  map when `this.shadowDirty` is set (the renderer has `shadowMap.autoUpdate = false`).
- `src/soyrack/stage.js` — `SoyrackStage`: the cords (`Lead`) and straps, each a `Laid` that fades in. They cast
  a shadow whenever they are visible.
- `src/main.js` — the render loop step (inside `createLoop(...)`).
- `test/helpers.mjs` — `installDomStubs()` and `fakeRenderer()` build a `Viewer` in Node; `fakeRenderer` has a
  no-op `setPixelRatio()`.

`src/scene.js`, constructor (near line 127):

```js
    const renderer = injected || new WebGLRenderer({ antialias: true, alpha: true, powerPreference: 'high-performance' });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.setClearColor(0x000000, 0);
```

The constructor's signature already receives `phone` (true on narrow or touch devices):
`constructor({ container, timeline, meshes, Stage, floorZ, reducedMotion = false, phone = false, renderer: injected = null })`.

`src/scene.js`, the whole `setTime` method today:

```js
  /** Apply the timeline state at time t. */
  setTime(t) {
    evaluate(this.timeline, t, this.state);
    for (const [id, rec] of this.objects) {
      const s = this.state.get(id);
      rec.obj.position.set(s.p[0], s.p[1], s.p[2]);
      rec.obj.quaternion.set(s.q[0], s.q[1], s.q[2], s.q[3]);
      const kind = rec.node.kind;
      if (kind === 'group' || kind === 'screw') continue;
      const visible = s.alpha > 0.004;
      if (rec.obj.visible !== visible) rec.obj.visible = visible;
      if (!visible) continue;
      const transparent = s.alpha < 0.995;
      for (const m of rec.materials) {
        if (m.transparent !== transparent) {
          m.transparent = transparent;
          m.needsUpdate = true;
        }
        m.opacity = s.alpha;
        m.userData.glow.value = s.glow;
      }
      rec.obj.castShadow = s.alpha > 0.6;
    }
    this.root.updateMatrixWorld(true);
    if (this.stage) {
      this.stage.setTime(t);
      const frame = this.stage.camera();
      if (frame.key !== this.cameraKey) {
        this.cameraKey = frame.key;
        if (this.pristine) this.applyHomeView(!this.reducedMotion);
      }
    }
    const hidden = new Matrix4().makeScale(0, 0, 0);
    for (const { im, ids } of this.screwSets) {
      ids.forEach((id, i) => {
        const s = this.state.get(id);
        im.setMatrixAt(i, s.alpha > 0.5 ? this.objects.get(id).obj.matrixWorld : hidden);
      });
      im.instanceMatrix.needsUpdate = true;
    }
    this.dirty = true;
    this.shadowDirty = true;
  }
```

`src/scene.js` also has, later in the class, a method that begins with this comment (added by plan 003):

```js
  /**
   * Compile every shader the timeline will need before playback starts. Each part swaps between an opaque and
```

`src/soyrack/stage.js`, in `class Laid` (lines 50–73) and `class SoyrackStage` (lines 115–119):

```js
  update(t) {
    const c = this.chapter;
    const alpha = Math.max(0, Math.min(1, (t - (c.start - 0.3)) / FADE_IN));
    const active = t >= c.start && t < c.end;
    this.object.visible = alpha > 0.003;
    if (alpha !== this.alpha) {
      ...
    }
    if (active !== this.active) {
      this.active = active;
      for (const m of this.glowing) {
        m.emissive.setHex(active ? 0x73502c : 0x000000);
        m.emissiveIntensity = active ? 0.19 : 0;
      }
    }
  }
```

```js
  setTime(t) {
    this.time = t;
    for (const l of this.leads) l.update(t);
    for (const l of this.ties) l.update(t);
  }
```

`src/main.js`, the loop step:

```js
const loop = createLoop((now) => {
  const dt = last ? Math.min(0.1, (now - last) / 1000) : 0;
  last = now;
  if (player.tick(dt)) viewer.setTime(player.time);
  const cameraMoving = viewer.update(dt);
```

Conventions: two-space indent, single quotes, semicolons, comments that say why. Tests check behaviour, not
source text (AGENTS.md).

## Commands you will need

Run from `apps/assembly-guide/app` inside your worktree.

| Purpose | Command | Expected on success |
|---------|---------|---------------------|
| Install | `npm ci` | exit 0 |
| Build + test | `npm run build && npm test` | exit 0, `# fail 0` |
| Audit | `PLAYWRIGHT_PATH=/opt/node-tools/node_modules/playwright node tools/perf-audit.mjs --max-frame-requests 1 --max-new-programs 0 --max-layout-reads 1` | exit 0, `"pageErrors": []` |

The audit takes about a minute; give it a 10 minute timeout. Do not install Playwright.

## Scope

**In scope** (the only files you should modify or create):

- `apps/assembly-guide/app/src/scene.js` (constructor pixel-ratio lines, `setTime`, new `adapt` method)
- `apps/assembly-guide/app/src/soyrack/stage.js` (`Laid.update`, `SoyrackStage.setTime`)
- `apps/assembly-guide/app/src/main.js` (one line in the loop step)
- `apps/assembly-guide/app/test/shadows.test.mjs` (create)
- `apps/assembly-guide/README.md` (one paragraph)

**Out of scope** (do NOT touch):

- `Viewer.render()`, `Viewer.warmUp()`, the lights and shadow map size in `addLights`, `src/tags.js`,
  `src/loop.js`, `src/timeline.js`, `test/helpers.mjs`, `tools/perf-audit.mjs`.
- Merging meshes or materials to cut draw calls: deferred to a later plan.
- `apps/pearl-guide/**`, Docker, nginx, workflow and manifest files, `package.json`, `plans/`.

## Git workflow

- Work on the branch your worktree is already on. Do not create or switch branches.
- One commit, message:
  `perf(assembly-guide): redraw shadows only when a caster changed and adapt the resolution`
  with a short body giving the redraw share the new test printed (see Step 5).
- Do NOT push and do NOT open a pull request.

## Steps

### Step 1: Write the test first and watch it fail

Create `apps/assembly-guide/app/test/shadows.test.mjs` with exactly this content:

```js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { installDomStubs, fakeRenderer, meshes } from './helpers.mjs';

const makeElement = installDomStubs();
const { Viewer } = await import('../src/scene.js');
const { buildSoyrackTimeline, SoyrackStage, FLOOR_Z } = await import('../src/soyrack/index.js');

const timeline = buildSoyrackTimeline(meshes);
const makeViewer = (options = {}) => new Viewer({ container: makeElement(), timeline, meshes, Stage: SoyrackStage, floorZ: FLOOR_Z, renderer: fakeRenderer(makeElement), ...options });

/** Everything the shadow map depends on: which meshes cast a shadow right now, and where each one is. */
function casters(viewer) {
  viewer.scene.updateMatrixWorld(true);
  let hash = 0;
  let count = 0;
  const mix = (n) => {
    hash = (Math.imul(hash, 31) + Math.round(n * 1000)) | 0;
  };
  viewer.scene.traverse((o) => {
    if (!o.isMesh || !o.castShadow) return;
    for (let a = o; a; a = a.parent) if (!a.visible) return;
    count++;
    mix(o.id);
    o.matrixWorld.elements.forEach(mix);
    if (o.isInstancedMesh) o.instanceMatrix.array.forEach(mix);
  });
  return `${count}:${hash}`;
}

test('the shadow map is redrawn on every frame that changes a shadow caster, and on well under half of all frames', () => {
  const viewer = makeViewer();
  viewer.setTime(0);
  let before = casters(viewer);
  let frames = 0;
  let redraws = 0;
  for (let t = 1 / 30; t < timeline.duration; t += 1 / 30) {
    viewer.shadowDirty = false; // as render() leaves it
    viewer.dirty = false;
    viewer.setTime(t);
    const now = casters(viewer);
    if (now !== before) assert.equal(viewer.shadowDirty, true, `casters changed at ${t.toFixed(2)} s without a shadow redraw`);
    assert.equal(viewer.dirty, true, 'every time step still redraws the picture');
    if (viewer.shadowDirty) redraws++;
    frames++;
    before = now;
  }
  assert.ok(redraws > 0, 'moving parts do redraw the shadows');
  assert.ok(redraws < frames * 0.5, `shadows redrawn on ${redraws} of ${frames} frames`);
});

test('seeking away and back redraws the shadows both times', () => {
  const viewer = makeViewer();
  viewer.setTime(timeline.duration);
  viewer.shadowDirty = false;
  viewer.setTime(0);
  assert.equal(viewer.shadowDirty, true);
  viewer.shadowDirty = false;
  viewer.setTime(0);
  assert.equal(viewer.shadowDirty, false, 'the same moment again changes nothing');
  viewer.setTime(timeline.duration);
  assert.equal(viewer.shadowDirty, true);
});

test('phones start at 1.5x and resolution steps down only after sustained slow frames', () => {
  const saved = globalThis.window.devicePixelRatio;
  globalThis.window.devicePixelRatio = 3;
  try {
    const phone = makeViewer({ phone: true });
    const ratios = [];
    phone.renderer.setPixelRatio = (r) => ratios.push(r);
    assert.equal(phone.ratio, 1.5);
    for (let i = 0; i < 30; i++) phone.adapt(40); // a brief stutter
    for (let i = 0; i < 200; i++) phone.adapt(16.7); // steady 60 Hz
    assert.equal(phone.ratio, 1.5, 'a brief stutter and steady frames change nothing');
    phone.dirty = false;
    for (let i = 0; i < 80; i++) phone.adapt(40);
    assert.equal(phone.ratio, 1.25, 'sustained slow frames lower it one step');
    assert.deepEqual(ratios, [1.25]);
    assert.equal(phone.dirty, true, 'and the picture is redrawn at the new size');
    for (let i = 0; i < 1000; i++) phone.adapt(40);
    assert.equal(phone.ratio, 0.85, 'it never goes below the floor');
    for (let i = 0; i < 2000; i++) phone.adapt(8);
    assert.equal(phone.ratio, 1.5, 'quick frames bring it back');

    const desktop = makeViewer();
    assert.equal(desktop.ratio, 2, 'desktops start at up to 2x');
  } finally {
    globalThis.window.devicePixelRatio = saved;
  }
});
```

**Verify**: `npm ci && node --test test/shadows.test.mjs` → `# fail 3` (all three fail on the current code; expected).

### Step 2: Let the stage say when a cord or strap appears or leaves

In `apps/assembly-guide/app/src/soyrack/stage.js`:

1. In `Laid.update(t)`, replace the line `this.object.visible = alpha > 0.003;` with:

```js
    const visible = alpha > 0.003;
    const changed = this.object.visible !== visible; // it casts a shadow whenever it shows
    this.object.visible = visible;
```

   and add `return changed;` as the last statement of `update(t)` (after the closing brace of the
   `if (active !== this.active) { ... }` block).

2. Replace `SoyrackStage.setTime` with:

```js
  /** Returns whether a cord or strap appeared or left, which is when the shadows need redrawing. */
  setTime(t) {
    this.time = t;
    let changed = false;
    for (const l of this.leads) if (l.update(t)) changed = true;
    for (const l of this.ties) if (l.update(t)) changed = true;
    return changed;
  }
```

**Verify**: `npm test` → `# fail 3`: the only failures are the 3 tests in `test/shadows.test.mjs` (the command exits 1 at this step; that is expected).

### Step 3: Make `setTime` notice whether anything that casts a shadow changed

In `apps/assembly-guide/app/src/scene.js`, replace the whole `setTime(t)` method (including its one-line
comment) with exactly:

```js
  /** Apply the timeline state at time t. */
  setTime(t) {
    evaluate(this.timeline, t, this.state);
    // `moved`: some node changed place, so world matrices and screw instances need updating. `shadows`: something
    // that casts a shadow changed place, appeared or left, so the shadow map needs redrawing. Parts hold still
    // for most of the timeline (captions, camera moves, fades), and those frames keep the last shadow map.
    let moved = !this.placed;
    let shadows = !this.placed;
    this.placed = true;
    const screwsCast = this.screwSets.some(({ im }) => im.castShadow); // they do not today; this keeps it true if they ever do
    for (const [id, rec] of this.objects) {
      const s = this.state.get(id);
      const { p, q } = s;
      const at = rec.obj.position;
      const turn = rec.obj.quaternion;
      const shifted = at.x !== p[0] || at.y !== p[1] || at.z !== p[2] || turn.x !== q[0] || turn.y !== q[1] || turn.z !== q[2] || turn.w !== q[3];
      if (shifted) {
        at.set(p[0], p[1], p[2]);
        turn.set(q[0], q[1], q[2], q[3]);
        moved = true;
      }
      const kind = rec.node.kind;
      if (kind === 'screw') {
        const drawn = s.alpha > 0.5;
        if (rec.drawn !== drawn) {
          rec.drawn = drawn;
          moved = true;
          if (screwsCast) shadows = true;
        } else if (shifted && drawn && screwsCast) shadows = true;
        continue;
      }
      if (kind === 'group') {
        if (shifted) shadows = true; // whatever it carries moved with it
        continue;
      }
      const visible = s.alpha > 0.004;
      if (rec.obj.visible !== visible) {
        rec.obj.visible = visible;
        shadows = true;
      } else if (shifted && visible) shadows = true; // a part still hidden casts nothing
      if (!visible) continue;
      const transparent = s.alpha < 0.995;
      for (const m of rec.materials) {
        if (m.transparent !== transparent) {
          m.transparent = transparent;
          m.needsUpdate = true;
        }
        m.opacity = s.alpha;
        m.userData.glow.value = s.glow;
      }
      const casts = s.alpha > 0.6;
      if (rec.obj.castShadow !== casts) {
        rec.obj.castShadow = casts;
        shadows = true;
      }
    }
    if (moved) this.root.updateMatrixWorld(true);
    if (this.stage) {
      // A stage that does not say whether it changed is taken to have changed.
      if (this.stage.setTime(t) !== false) shadows = true;
      const frame = this.stage.camera();
      if (frame.key !== this.cameraKey) {
        this.cameraKey = frame.key;
        if (this.pristine) this.applyHomeView(!this.reducedMotion);
      }
    }
    if (moved) {
      const hidden = new Matrix4().makeScale(0, 0, 0);
      for (const { im, ids } of this.screwSets) {
        ids.forEach((id, i) => {
          const s = this.state.get(id);
          im.setMatrixAt(i, s.alpha > 0.5 ? this.objects.get(id).obj.matrixWorld : hidden);
        });
        im.instanceMatrix.needsUpdate = true;
      }
    }
    if (shadows) this.shadowDirty = true;
    this.dirty = true;
  }
```

What changed, so you can check your edit: positions and rotations are written only when they differ. Two
flags come out of the loop. `moved` means some node changed place (or a screw crossed its draw threshold): only
then are the world matrices and the screw instance matrices updated. `shadows` means something that casts a
shadow changed place, appeared, left or crossed the shadow threshold, or the stage reported a change: only then
is `shadowDirty` set. A part that is still hidden casts nothing, and the instanced screws do not cast shadows
(their `InstancedMesh` leaves `castShadow` off), so neither triggers a shadow redraw. `this.dirty = true` stays
unconditional, because fades and glows change the picture without changing the shadows.

**Verify**: `node --test test/shadows.test.mjs` → the first two tests pass; the third (`phones start at 1.5x ...`) still fails.

### Step 4: Start phones at 1.5x and adapt the resolution to the frame rate

In `apps/assembly-guide/app/src/scene.js`:

1. In the constructor, replace the line `renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));` with:

```js
    // Phones have 2.5-3x screens and small GPUs: start at 1.5 and let adapt() trade resolution for frame rate.
    this.maxRatio = Math.min(window.devicePixelRatio || 1, phone ? 1.5 : 2);
    this.minRatio = Math.min(this.maxRatio, phone ? 0.85 : 1);
    this.ratio = this.maxRatio;
    this.frameMs = 16;
    this.slow = 0;
    this.quick = 0;
    renderer.setPixelRatio(this.ratio);
```

2. Insert this method directly **before** the comment block that begins
   `* Compile every shader the timeline will need before playback starts.` (that is, before the `/**` line of
   the `warmUp` method), with a blank line after it:

```js
  /** Feed the time between played frames. Sustained slow frames lower the resolution a step; quick ones restore it. */
  adapt(ms) {
    this.frameMs += (Math.min(ms, 100) - this.frameMs) * 0.1;
    this.slow = this.frameMs > 24 ? this.slow + 1 : 0;
    this.quick = this.frameMs < 13 ? this.quick + 1 : 0;
    let next = this.ratio;
    if (this.slow > 45 && this.ratio > this.minRatio) next = Math.max(this.minRatio, this.ratio - 0.25);
    if (this.quick > 120 && this.ratio < this.maxRatio) next = Math.min(this.maxRatio, this.ratio + 0.25);
    if (next !== this.ratio) {
      this.ratio = next;
      this.slow = this.quick = 0;
      this.renderer.setPixelRatio(next); // three resizes the drawing buffer to match
      this.dirty = true;
    }
  }
```

3. In `apps/assembly-guide/app/src/main.js`, in the loop step, directly after the line
   `if (player.tick(dt)) viewer.setTime(player.time);` add:

```js
  if (player.playing && dt > 0) viewer.adapt(dt * 1000);
```

**Verify**: `node --test test/shadows.test.mjs` → `# pass 3`, `# fail 0`
**Verify**: `npm run build && npm test` → exit 0, `# fail 0` (51 tests)

### Step 5: Measure the saving and run the audit

Run this from `apps/assembly-guide/app` and note the line it prints (use it in the commit body):

```sh
node --input-type=module -e "
const h = await import('./test/helpers.mjs');
const el = h.installDomStubs();
const { Viewer } = await import('./src/scene.js');
const { buildSoyrackTimeline, SoyrackStage, FLOOR_Z } = await import('./src/soyrack/index.js');
const timeline = buildSoyrackTimeline(h.meshes);
const v = new Viewer({ container: el(), timeline, meshes: h.meshes, Stage: SoyrackStage, floorZ: FLOOR_Z, renderer: h.fakeRenderer(el) });
let frames = 0, redraws = 0;
for (let t = 0; t < timeline.duration; t += 1 / 30) { v.shadowDirty = false; v.setTime(t); frames++; if (v.shadowDirty) redraws++; }
console.log('shadow redraws on ' + redraws + ' of ' + frames + ' frames (' + Math.round(100 * redraws / frames) + '%)');
"
```

**Verify**: prints a share between 20% and 45% (about 32% is expected; before this plan it was 100%).

**Verify**: `PLAYWRIGHT_PATH=/opt/node-tools/node_modules/playwright node tools/perf-audit.mjs --max-frame-requests 1 --max-new-programs 0 --max-layout-reads 1` → exit 0; `"frameRequests": 1`, `"newPrograms": 0`, `"pageErrors": []`.

### Step 6: Document it

In `apps/assembly-guide/README.md`, replace the whole paragraph that begins `Performance is checked by count, not by feel.`
with exactly:

```md
Performance is checked by count, not by feel. `app/src/loop.js` runs the player: one animation-frame callback
per displayed frame, however often the player or the camera asks for one. Every shader compiles before the
page appears (`Viewer.warmUp` in `app/src/scene.js`), so playback never stops to compile one. Name tags are
placed from boxes measured once and again after a resize, never per frame (`app/src/tags.js`). The shadow map
is redrawn only on frames where something that casts a shadow moved, appeared or left (`Viewer.setTime`),
about a third of them. Phones render at up to 1.5x, desktops at up to 2x, and `Viewer.adapt` lowers the
resolution a step when frames stay slow. After a build,
`PLAYWRIGHT_PATH=<playwright> node tools/perf-audit.mjs --max-frame-requests 1 --max-new-programs 0 --max-layout-reads 1`
(in `app/`) plays the guide in a headless Chromium and reports frame requests per frame, shader programs
compiled after the page was ready, layout reads per frame and draw calls per chapter; each `--max-*` flag turns
a number into a pass or fail. It needs a Playwright with Chromium and is not part of `npm test`.
```

**Verify**: `grep -c "Viewer.adapt" ../README.md` → `1`

### Step 7: Commit

`git add` the five in-scope files and commit with the message from "Git workflow".

**Verify**: `git status --short` → empty; `git show --stat HEAD` lists exactly the five in-scope files.

## Test plan

- New `test/shadows.test.mjs` (content above), three cases:
  1. Stepping the whole timeline at 30 frames a second, every step that changes the set or placement of shadow
     casters (judged independently of the code under test, from the scene's world matrices) leaves
     `shadowDirty` set; every step still sets `dirty`; and shadows are redrawn on fewer than half the steps.
  2. Seeking to the end and back redraws the shadows both times; applying the same moment twice does not.
  3. A phone with a 3x screen starts at 1.5x; a brief stutter changes nothing; sustained slow frames step down
     by 0.25 and redraw; it never goes below 0.85; quick frames restore 1.5; a desktop starts at up to 2x.
- Existing suites stay green (in particular `test/scene.test.mjs`, which steps the timeline and checks
  transforms, screws against nuts and hidden future parts).
- Browser-level: the audit stays within its budgets with no page errors.

## Done criteria

ALL must hold:

- [ ] `npm run build && npm test` exits 0 with `# fail 0`, including the 3 tests in `test/shadows.test.mjs`
- [ ] The Step 5 one-liner prints a redraw share between 20% and 45%
- [ ] Audit with `--max-frame-requests 1 --max-new-programs 0 --max-layout-reads 1` exits 0, `"pageErrors": []`
- [ ] `git show --stat HEAD` lists only the five in-scope files

## STOP conditions

Stop and report back (do not improvise) if:

- `setTime`, the constructor lines, `Laid.update`, `SoyrackStage.setTime` or the loop step do not match the
  excerpts in "Current state".
- The first shadows test reports "casters changed at ... without a shadow redraw" after Step 3. That means
  something moves a shadow caster outside the cases this plan covers; report the time it printed. Do not
  loosen the test and do not fall back to setting `shadowDirty` unconditionally.
- Any test in `test/scene.test.mjs` or `test/soyrack.test.mjs` fails after Step 3.
- The redraw share in Step 5 is outside 20% to 45%.

## Maintenance notes

- Anything new that moves, shows or hides a shadow caster outside `Viewer.setTime` (a new kind of stage object,
  an animation driven elsewhere) must set `viewer.shadowDirty = true` itself, or its shadow will lag. A stage
  whose `setTime` returns nothing is treated as always changed, which is safe but gives up the saving.
- `adapt` only runs while playing. Thresholds match the Pearl guide's `Stage.adapt` (slow above 24 ms for 45
  frames, quick below 13 ms for 120 frames); on a 60 Hz phone a lowered resolution therefore stays lowered.
- Reviewer: the picture must be identical to always-redraw. The reviewer renders the same time steps with both
  builds and compares the canvas pixels.
- Deferred: drawing the shadow map on every second moving frame on phones (Pearl does) and merging the device
  sub-meshes to cut draw calls. Measure on a phone first.
