# Plan 004: The assembly guide places name tags without reading layout every frame

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md` — unless a reviewer dispatched you and told you they
> maintain the index.
>
> **Drift check (run first)**: `git diff --stat fae06c2..HEAD -- apps/assembly-guide/app/src apps/assembly-guide/app/test apps/assembly-guide/README.md`
> If any in-scope file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition.

## Status

- **Priority**: P2
- **Effort**: S
- **Risk**: LOW
- **Depends on**: plans/003-assembly-shader-warm-up.md (done)
- **Category**: perf
- **Planned at**: commit `fae06c2`, 2026-11-10

## Why this matters

The first five chapters of the assembly guide pin name tags to parts in the 3D view. On every frame
`tags.update()` asks the browser for the size of the tag layer and of the canvas, and then
`viewer.projectRackPoint()` asks for the canvas size again for each visible tag and also recomputes the world
matrix of all 459 meshes for each tag. Each size question comes right after the previous tag's position was
written, so the browser has to lay the page out again in the middle of the frame, several times per frame (the
audit counts 6 `getBoundingClientRect` calls per played frame). After this plan the two boxes are measured once
and again only after a resize, the projection measures nothing, and tags land on exactly the same pixels.

## Current state

Files (all under `apps/assembly-guide/app`):

- `src/tags.js` — `createTags({ root, before, player, timeline, viewer })` builds the tag elements and returns
  `{ update }`; `update()` runs once per frame from the render loop in `src/main.js`.
- `src/scene.js` — the `Viewer` class; `projectRackPoint(p)` is used only by `src/tags.js`.
- `test/helpers.mjs` — `installDomStubs()` and `fakeRenderer()` build a `Viewer` in Node without WebGL.
- `tools/perf-audit.mjs` — headless audit; `layoutReads` is the number of `getBoundingClientRect` calls per
  played frame (rounded up) in the chapters with name tags.

`src/tags.js`, the setup just before `function show` (lines 39–42) and the start of `update()` (lines 52–62):

```js
  const q = new Quaternion();
  const p = new Vector3();
  const offset = new Vector3();
  let width = 0;
```

```js
  function update() {
    const t = player.time;
    const box = layer.getBoundingClientRect();
    const canvas = viewer.canvas.getBoundingClientRect();
    const floor = box.height - viewer.bottomInset; // keep clear of the caption and transport bar
    if (box.width !== width) {
      width = box.width;
      svg.setAttribute('viewBox', `0 0 ${box.width} ${box.height}`);
      for (const it of items) it.size = null; // the type size may have changed with the layout
    }
```

and inside its loop over the tags (line 73):

```js
      const a = viewer.projectRackPoint(p);
      const ax = a.x + canvas.left - box.left;
      const ay = a.y + canvas.top - box.top;
```

`src/scene.js`, in the `Viewer` class:

```js
  projectRackPoint(p) {
    this.root.updateMatrixWorld(true);
    const v=p.clone().applyMatrix4(this.root.matrixWorld).project(this.camera);
    const rect=this.canvas.getBoundingClientRect();
    return {x:(v.x+1)*rect.width/2,y:(1-v.y)*rect.height/2,visible:Math.abs(v.x)<1&&Math.abs(v.y)<1&&v.z<1};
  }
```

and in its constructor:

```js
    this.raycaster = new Raycaster();
    this.canvas.addEventListener('dblclick', (e) => this.focusAt(e.clientX, e.clientY));
```

Why dropping `updateMatrixWorld(true)` is safe: `this.root` is a fixed group (a constant rotation from the
rack's z-up frame to three's y-up world) and `setTime()` already updates the world matrices whenever parts
move. The camera's matrices are refreshed by every draw, and the render loop draws before it updates the tags.

Conventions: two-space indent, single quotes, semicolons, comments that say why. `Vector3` is already imported
in `scene.js`. Tests check behaviour, not source text (AGENTS.md).

## Commands you will need

Run from `apps/assembly-guide/app` inside your worktree.

| Purpose | Command | Expected on success |
|---------|---------|---------------------|
| Install | `npm ci` | exit 0 |
| Build + test | `npm run build && npm test` | exit 0, `# fail 0` |
| Audit | `PLAYWRIGHT_PATH=/opt/node-tools/node_modules/playwright node tools/perf-audit.mjs --max-frame-requests 1 --max-new-programs 0 --max-layout-reads 1` | exit 0, `"layoutReads"` 0 or 1 |

The audit takes about a minute; give it a 10 minute timeout. Do not install Playwright.

## Scope

**In scope** (the only files you should modify or create):

- `apps/assembly-guide/app/src/tags.js`
- `apps/assembly-guide/app/src/scene.js` (`projectRackPoint` and one line in the constructor)
- `apps/assembly-guide/app/test/tags.test.mjs` (create)
- `apps/assembly-guide/README.md` (one paragraph)

**Out of scope** (do NOT touch):

- The placement logic in `tags.js` below the projection call (sides, overlap avoidance, leader lines): tags
  must land exactly where they do today.
- `src/main.js`, `src/loop.js`, `src/ui.js`, `src/soyrack/**`, `tools/perf-audit.mjs`, `test/helpers.mjs`.
- `apps/pearl-guide/**`, Docker, nginx, workflow and manifest files, `package.json`, `plans/`.

## Git workflow

- Work on the branch your worktree is already on. Do not create or switch branches.
- One commit, message: `perf(assembly-guide): place name tags without measuring the page every frame`
  with a short body giving `layoutReads` before and after.
- Do NOT push and do NOT open a pull request.

## Steps

### Step 1: Write the test first and watch it fail

Create `apps/assembly-guide/app/test/tags.test.mjs` with exactly this content:

```js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { Vector3 } from 'three';
import { installDomStubs, fakeRenderer, meshes } from './helpers.mjs';

const makeElement = installDomStubs();
const { Viewer } = await import('../src/scene.js');
const { createTags } = await import('../src/tags.js');
const { buildSoyrackTimeline, SoyrackStage, FLOOR_Z } = await import('../src/soyrack/index.js');

const timeline = buildSoyrackTimeline(meshes);

function makeViewer() {
  const renderer = fakeRenderer(makeElement);
  let measured = 0;
  renderer.domElement.getBoundingClientRect = () => {
    measured++;
    return { left: 0, top: 0, width: 1280, height: 800 };
  };
  const viewer = new Viewer({ container: makeElement(), timeline, meshes, Stage: SoyrackStage, floorZ: FLOOR_Z, renderer });
  viewer.camera.updateMatrixWorld(); // the real renderer does this on every draw
  return { viewer, measured: () => measured };
}

test('projectRackPoint maps the point the camera looks at to the middle of the canvas, measuring nothing', () => {
  const { viewer, measured } = makeViewer();
  const before = measured();
  const centre = viewer.root.worldToLocal(viewer.controls.target.clone());
  const a = viewer.projectRackPoint(centre, 1280, 800);
  assert.ok(Math.abs(a.x - 640) < 0.5 && Math.abs(a.y - 400) < 0.5, `centre lands at ${a.x}, ${a.y}`);
  assert.equal(a.visible, true);
  const half = viewer.projectRackPoint(centre, 640, 400);
  assert.ok(Math.abs(half.x - 320) < 0.5 && Math.abs(half.y - 200) < 0.5, 'the result scales with the size it is given');
  const behind = viewer.root.worldToLocal(viewer.camera.position.clone().multiplyScalar(2).sub(viewer.controls.target));
  assert.equal(viewer.projectRackPoint(behind, 1280, 800).visible, false, 'a point behind the camera is not visible');
  const far = viewer.root.worldToLocal(viewer.controls.target.clone().add(new Vector3(1e5, 0, 0)));
  assert.equal(viewer.projectRackPoint(far, 1280, 800).visible, false, 'a point off to the side is not visible');
  assert.equal(measured(), before, 'no layout was read');
});

/** Just enough DOM for createTags: elements that count how often their box is measured. */
function fakeDom() {
  const counts = { measured: 0 };
  const observers = [];
  const element = () => ({
    style: {},
    className: '',
    textContent: '',
    offsetWidth: 80,
    offsetHeight: 20,
    classList: { add() {}, toggle() {} },
    setAttribute() {},
    appendChild() {},
    append() {},
    insertBefore() {},
    getBoundingClientRect() {
      counts.measured++;
      return { left: 0, top: 0, width: 1280, height: 800 };
    },
  });
  globalThis.document = { createElement: element, createElementNS: element };
  globalThis.ResizeObserver = class {
    constructor(cb) {
      this.cb = cb;
      observers.push(this);
    }
    observe() {}
  };
  return { counts, element, resize: () => observers.forEach((o) => o.cb([])) };
}

test('name tags measure the page once, not on every frame, and again after a resize', () => {
  const { viewer, measured } = makeViewer();
  const saved = { document: globalThis.document, ResizeObserver: globalThis.ResizeObserver };
  const dom = fakeDom();
  try {
    const chapter = timeline.chapters.find((c) => c.tags.length);
    const player = { time: chapter.start + (chapter.end - chapter.start) * 0.5 };
    viewer.setTime(player.time);
    const tags = createTags({ root: dom.element(), before: dom.element(), player, timeline, viewer });
    const total = () => dom.counts.measured + measured();

    tags.update();
    const first = total();
    assert.ok(first >= 1 && first <= 2, `the first frame measures the layer and the canvas (${first})`);
    for (let i = 0; i < 50; i++) {
      player.time += 1 / 60;
      viewer.setTime(player.time);
      tags.update();
    }
    assert.equal(total(), first, '50 more frames measure nothing');

    dom.resize();
    tags.update();
    tags.update();
    assert.equal(total(), first * 2, 'a resize costs one more measurement');
  } finally {
    globalThis.document = saved.document;
    globalThis.ResizeObserver = saved.ResizeObserver;
  }
});
```

**Verify**: `npm ci && node --test test/tags.test.mjs` → `# fail 2` (both tests fail on the current code; that is expected).

### Step 2: Make `projectRackPoint` measure nothing

In `apps/assembly-guide/app/src/scene.js`:

1. In the constructor, directly after the line `this.raycaster = new Raycaster();` add:

```js
    this.projected = new Vector3();
```

2. Replace the whole `projectRackPoint(p) { ... }` method with:

```js
  /**
   * Where a point in the rack's frame lands on the canvas, in CSS pixels of a canvas `width` x `height`.
   * It reads the matrices that setTime and the last render left behind and measures nothing, so the
   * name tags can call it for every tag on every frame.
   */
  projectRackPoint(p, width, height) {
    const v = this.projected.copy(p).applyMatrix4(this.root.matrixWorld).project(this.camera);
    return { x: ((v.x + 1) * width) / 2, y: ((1 - v.y) * height) / 2, visible: Math.abs(v.x) < 1 && Math.abs(v.y) < 1 && v.z < 1 };
  }
```

**Verify**: `node --test test/tags.test.mjs` → the first test (`projectRackPoint maps the point ...`) passes; the second still fails.

### Step 3: Measure the two boxes once in `tags.js`

In `apps/assembly-guide/app/src/tags.js`:

1. Directly after the line `let width = 0;` add (with a blank line before it):

```js
  // The boxes of the tag layer and the canvas, measured once and again after either changes size. Measuring
  // on every frame would force the browser to lay the page out in the middle of each frame.
  let boxes = null;
  const remeasure = new ResizeObserver(() => {
    boxes = null;
  });
  remeasure.observe(layer);
  remeasure.observe(viewer.canvas);
```

2. In `update()`, replace the two lines

```js
    const box = layer.getBoundingClientRect();
    const canvas = viewer.canvas.getBoundingClientRect();
```

   with

```js
    if (!boxes) boxes = { box: layer.getBoundingClientRect(), canvas: viewer.canvas.getBoundingClientRect() };
    const { box, canvas } = boxes;
```

3. Replace `const a = viewer.projectRackPoint(p);` with
   `const a = viewer.projectRackPoint(p, canvas.width, canvas.height);`

Change nothing else in the file.

**Verify**: `node --test test/tags.test.mjs` → `# pass 2`, `# fail 0`
**Verify**: `npm run build && npm test` → exit 0, `# fail 0` (48 tests)

### Step 4: Run the audit

**Verify**: `PLAYWRIGHT_PATH=/opt/node-tools/node_modules/playwright node tools/perf-audit.mjs --max-frame-requests 1 --max-new-programs 0 --max-layout-reads 1` → exit 0; `"layoutReads"` is 0 or 1 (it was 6), `"newPrograms": 0`, `"pageErrors": []`.
(One read can remain: when a chapter's caption changes height, `main.js` re-measures the caption once. That is
not per frame.)

### Step 5: Document it

In `apps/assembly-guide/README.md`, replace the whole paragraph that begins `Performance is checked by count, not by feel.`
with exactly:

```md
Performance is checked by count, not by feel. `app/src/loop.js` runs the player: one animation-frame callback
per displayed frame, however often the player or the camera asks for one. Every shader compiles before the
page appears (`Viewer.warmUp` in `app/src/scene.js`), so playback never stops to compile one. Name tags are
placed from boxes measured once and again after a resize, never per frame (`app/src/tags.js`). After a build,
`PLAYWRIGHT_PATH=<playwright> node tools/perf-audit.mjs --max-frame-requests 1 --max-new-programs 0 --max-layout-reads 1`
(in `app/`) plays the guide in a headless Chromium and reports frame requests per frame, shader programs
compiled after the page was ready, layout reads per frame and draw calls per chapter; each `--max-*` flag turns
a number into a pass or fail. It needs a Playwright with Chromium and is not part of `npm test`.
```

**Verify**: `grep -c "max-layout-reads 1" ../README.md` → `1`

### Step 6: Commit

`git add` the four in-scope files and commit with the message from "Git workflow".

**Verify**: `git status --short` → empty; `git show --stat HEAD` lists exactly the four in-scope files.

## Test plan

- New `test/tags.test.mjs` (content above): the projection maps the point the camera looks at to the middle of
  the canvas, scales with the size it is given, reports points behind or beside the view as not visible, and
  reads no layout; and `createTags().update()` measures at most twice on the first frame, not at all on the
  next 50 frames, and once more after a resize.
- Existing suites stay green.
- Browser-level: audit `layoutReads` at most 1.

## Done criteria

ALL must hold:

- [ ] `npm run build && npm test` exits 0 with `# fail 0`, including the 2 tests in `test/tags.test.mjs`
- [ ] Audit with `--max-frame-requests 1 --max-new-programs 0 --max-layout-reads 1` exits 0
- [ ] `grep -c "getBoundingClientRect" src/tags.js` → `1` (one line, inside the `if (!boxes)`)
- [ ] `git show --stat HEAD` lists only the four in-scope files

## STOP conditions

Stop and report back (do not improvise) if:

- `tags.js` or `projectRackPoint` do not match the excerpts in "Current state".
- `projectRackPoint` is called from anywhere other than `src/tags.js` (`grep -rn projectRackPoint src test`).
- The audit still reports `layoutReads` above 1 after your change, twice. Report the full JSON.
- An existing test fails and the cause is not an obvious typo of yours.

## Maintenance notes

- If the tag layer or canvas can ever move without changing size (today both fill the page), the cached boxes
  would go stale; invalidate `boxes` at that point too.
- `projectRackPoint` now depends on the camera matrices of the last draw. Callers outside the render loop must
  draw first (or call `camera.updateMatrixWorld()`).
- Reviewer: tags must land on the same pixels as before. The reviewer compares tag positions between the
  builds before and after this change at two window sizes.
