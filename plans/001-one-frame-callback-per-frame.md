# Plan 001: Each guide runs one animation-frame callback per displayed frame

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md` — unless a reviewer dispatched you and told you they
> maintain the index.
>
> **Drift check (run first)**: `git diff --stat 8545766..HEAD -- apps/assembly-guide/app/src/main.js apps/pearl-guide/app/src/main.js`
> If either file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition.

## Status

- **Priority**: P1
- **Effort**: S
- **Risk**: LOW
- **Depends on**: none
- **Category**: perf (bug)
- **Planned at**: commit `8545766`, 2026-11-10

## Why this matters

Both 3D guides (`apps/assembly-guide`, `apps/pearl-guide`) share a render-loop bug. Every frame of playback
queues **two** follow-up animation frames instead of one, so the number of callbacks per displayed frame grows by
one on every frame until the reader pauses. Measured in headless Chromium on the current code: the assembly guide
makes 137, then 360, 585, 872, 1128 `requestAnimationFrame` calls in successive 250 ms windows (15 are correct);
the Pearl guide runs 143 full scene renders in the first 250 ms (15 are correct). This is the main reason both
sites feel slow, heat phones and stutter the longer they play. After this plan each guide runs exactly one
callback per frame, a unit test pins that behaviour, and each app has a headless audit script that reports it.

## Current state

Both apps are static three.js players bundled by esbuild into `dist/` and served by nginx. They are separate
npm projects with separate Docker build contexts, so they cannot import each other's files: the fix is applied
to each app separately, with the same small module copied into both.

Files:

- `apps/assembly-guide/app/src/main.js` — entry point of the assembly guide; holds the buggy loop (lines 57–79).
- `apps/assembly-guide/app/src/player.js` — `Player.tick(dt)` emits `'tick'` to listeners on every played frame.
- `apps/assembly-guide/app/test/*.test.mjs` — `node:test` suites, run by `npm test` (`node test/run-tests.mjs`
  runs every `test/*.test.mjs`).
- `apps/assembly-guide/app/tools/` — developer tools kept out of the image (`.dockerignore` lists `app/tools`).
- `apps/pearl-guide/app/src/main.js` — entry point of the Pearl guide; holds the same loop inside `async function start()` (lines 77–103).
- `apps/pearl-guide/app/test/*.test.mjs` — `node:test` suites, run by `npm test` (`node --test test/*.test.mjs`).

The bug, in `apps/assembly-guide/app/src/main.js:57-95`:

```js
// ---------------------------------------------------------------- render loop (on demand)
let raf = 0;
let last = 0;
function frame(now) {
  raf = 0;
  const dt = last ? Math.min(0.1, (now - last) / 1000) : 0;
  last = now;
  if (player.tick(dt)) viewer.setTime(player.time);
  const cameraMoving = viewer.update(dt);
  if (viewer.dirty) viewer.render();
  tags.update();
  if (player.playing || cameraMoving || viewer.tween) {
    raf = requestAnimationFrame(frame);
  } else {
    last = 0;
  }
}
function schedule() {
  if (!raf) raf = requestAnimationFrame(frame);
}
viewer.controls.addEventListener('change', schedule);
viewer.controls.addEventListener('start', schedule);
viewer.onRequestFrame = schedule;

let hashTimer = 0;
player.on((reason) => {
  if (reason !== 'tick') viewer.setTime(player.time);
  schedule();
  ...
```

`frame()` clears `raf` first. `player.tick(dt)` then emits `'tick'`, the `player.on` listener calls `schedule()`,
and because `raf` is 0 that queues a frame. The end of `frame()` then queues a second one and overwrites `raf`.
Next frame, two callbacks run and each does the same, and so on.

The same bug in `apps/pearl-guide/app/src/main.js:77-107` (two-space indented, inside `start()`):

```js
  let raf = 0;
  let last = 0;
  function frame(now) {
    raf = 0;
    const dt = last ? Math.min(0.1, (now - last) / 1000) : 0;
    last = now;
    player.tick(dt);
    if (player.playing && dt > 0) stage.adapt(dt * 1000);
    direct(player.time);
    stage.controls.update();
    stage.render();
    if (player.playing || stage.controls.enableDamping) {
      raf = requestAnimationFrame(frame);
      if (!player.playing && idleFrames++ > 90) {
        cancelAnimationFrame(raf);
        raf = 0;
        last = 0;
      }
    } else last = 0;
  }
  let idleFrames = 0;
  function schedule() {
    idleFrames = 0;
    if (!raf) raf = requestAnimationFrame(frame);
  }
  stage.controls.addEventListener('change', schedule);
  stage.controls.addEventListener('start', schedule);

  let hashTimer = 0;
  player.on((reason) => {
    schedule();
    ...
```

Conventions that apply:

- Plain ES modules, two-space indent, single quotes, semicolons, lines up to about 120 characters.
- Comments explain why, in plain words. Match the tone of the existing comments in each `main.js`.
- Tests use `node:test` and `node:assert/strict`. Repository rule (AGENTS.md): "Keep tests that protect
  observable behavior... Avoid assertions that only mirror source text or prose." Do not write tests that grep
  the source.
- The assembly guide's `test/bundle.test.mjs` asserts the built `app.js` makes no network requests (`fetch(`,
  `import(` and similar must not appear). Do not add any.
- The Pearl guide already exposes a debug handle: `window.__pearl = { player, timeline, stage, S, sheets };`
  (`apps/pearl-guide/app/src/main.js:132`). The assembly guide has none yet; this plan adds `window.__soyrack`.
- The repository is public. Commit nothing personal or secret.

## Commands you will need

Run from the repository root unless a `cd` is shown.

| Purpose | Command | Expected on success |
|---------|---------|---------------------|
| Install (assembly) | `cd apps/assembly-guide/app && npm ci` | exit 0 |
| Build + test (assembly) | `cd apps/assembly-guide/app && npm run build && npm test` | exit 0, `# fail 0` |
| Install (Pearl) | `cd apps/pearl-guide/app && npm ci` | exit 0 |
| Build + test (Pearl) | `cd apps/pearl-guide/app && npm run build && npm test` | exit 0, `# fail 0` |
| Audit (assembly) | `cd apps/assembly-guide/app && PLAYWRIGHT_PATH=/opt/node-tools/node_modules/playwright node tools/perf-audit.mjs --max-frame-requests 1` | exit 0, JSON with `"frameRequests": 1` |
| Audit (Pearl) | `cd apps/pearl-guide/app && PLAYWRIGHT_PATH=/opt/node-tools/node_modules/playwright node tools/perf-audit.mjs --max-frame-requests 1 --max-new-programs 0` | exit 0, JSON with `"frameRequests": 1` |

The audits start a headless Chromium with software WebGL. Each takes 30 to 90 seconds on the fixed code and
several minutes on the unfixed code (that slowness is the bug). Give them a 10 minute timeout. Playwright is
preinstalled at `/opt/node-tools/node_modules/playwright`; do not install it and do not add it to any
`package.json`.

## Scope

**In scope** (the only files you should modify or create):

- `apps/assembly-guide/app/src/loop.js` (create)
- `apps/assembly-guide/app/src/main.js`
- `apps/assembly-guide/app/test/loop.test.mjs` (create)
- `apps/assembly-guide/app/tools/perf-audit.mjs` (create)
- `apps/assembly-guide/README.md` (one new paragraph)
- `apps/pearl-guide/app/src/loop.js` (create)
- `apps/pearl-guide/app/src/main.js`
- `apps/pearl-guide/app/test/loop.test.mjs` (create)
- `apps/pearl-guide/app/tools/perf-audit.mjs` (create)
- `apps/pearl-guide/README.md` (the existing "Performance" section)

**Out of scope** (do NOT touch):

- `player.js` in either app — the `'tick'` event is correct and other listeners (the UI) rely on it.
- `scene.js`, `tags.js`, `stage.js`, any nginx, Docker, workflow or manifest file — other plans own those.
- `package.json` / `package-lock.json` in either app — no new dependencies.
- `plans/` — the reviewer maintains it.

## Git workflow

- Work on the branch your worktree is already on. Do not create or switch branches.
- One commit for the whole plan, message:
  `fix(guides): run one animation-frame callback per frame in both 3D guides`
  with a short body saying what was wrong and what was measured after.
- Do NOT push and do NOT open a pull request.

## Steps

### Step 1: Add the loop module to the assembly guide

Create `apps/assembly-guide/app/src/loop.js` with exactly this content:

```js
// The render loop: at most one animation-frame callback is ever pending. `step(now)` draws one frame and
// returns true while it needs another. `schedule()` asks for a frame from outside; called from inside a
// running step (the player announces every tick to its listeners) it only notes that one more is wanted,
// so a frame can never queue two follow-up frames.
export function createLoop(step, { request = (cb) => requestAnimationFrame(cb), cancel = (id) => cancelAnimationFrame(id) } = {}) {
  let id = 0;
  let running = false;
  let again = false;
  function run(now) {
    id = 0;
    running = true;
    again = false;
    let more = false;
    try {
      more = step(now);
    } finally {
      running = false;
    }
    if (more || again) id = request(run);
  }
  return {
    schedule() {
      if (running) again = true;
      else if (!id) id = request(run);
    },
    stop() {
      if (id) cancel(id);
      id = 0;
      again = false;
    },
    get pending() {
      return id !== 0;
    },
  };
}
```

**Verify**: `cd apps/assembly-guide/app && node -e "import('./src/loop.js').then((m) => console.log(typeof m.createLoop))"` → prints `function`

### Step 2: Add the loop test to the assembly guide

Create `apps/assembly-guide/app/test/loop.test.mjs` with exactly this content:

```js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createLoop } from '../src/loop.js';

/** A stand-in for the browser's frame queue: `flush()` runs the callbacks queued for the next frame. */
function fakeFrames() {
  let queue = [];
  let nextId = 1;
  const frames = {
    requests: 0,
    request(cb) {
      frames.requests++;
      queue.push({ id: nextId, cb });
      return nextId++;
    },
    cancel(id) {
      queue = queue.filter((q) => q.id !== id);
    },
    flush(now = 0) {
      const due = queue;
      queue = [];
      for (const q of due) q.cb(now);
      return due.length;
    },
  };
  return frames;
}

test('a step that asks for a frame while it runs still queues one callback per frame', () => {
  const frames = fakeFrames();
  let steps = 0;
  const loop = createLoop(() => {
    steps++;
    loop.schedule(); // what the player's tick listener does on every played frame
    loop.schedule();
    return true;
  }, frames);
  loop.schedule();
  for (let i = 0; i < 100; i++) assert.equal(frames.flush(i * 16), 1, `frame ${i} ran one callback`);
  assert.equal(steps, 100);
  assert.equal(frames.requests, 101);
});

test('schedule before a frame is idempotent and the loop rests when the step is done', () => {
  const frames = fakeFrames();
  let steps = 0;
  const loop = createLoop(() => {
    steps++;
    return false;
  }, frames);
  loop.schedule();
  loop.schedule();
  assert.equal(frames.requests, 1);
  assert.equal(loop.pending, true);
  assert.equal(frames.flush(), 1);
  assert.equal(steps, 1);
  assert.equal(loop.pending, false);
  assert.equal(frames.flush(), 0, 'nothing queued once the step returned false');
  loop.schedule();
  assert.equal(frames.flush(), 1, 'a later schedule starts it again');
  assert.equal(steps, 2);
});

test('a frame asked for during the last step is not lost', () => {
  const frames = fakeFrames();
  let steps = 0;
  const loop = createLoop(() => {
    if (steps++ === 0) loop.schedule(); // e.g. playback ended inside this step and a listener wants a redraw
    return false;
  }, frames);
  loop.schedule();
  frames.flush();
  assert.equal(loop.pending, true);
  assert.equal(frames.flush(), 1);
  assert.equal(steps, 2);
  assert.equal(frames.flush(), 0);
});

test('stop cancels the pending frame, and a step that throws does not wedge the loop', () => {
  const frames = fakeFrames();
  let steps = 0;
  let fail = false;
  const loop = createLoop(() => {
    steps++;
    if (fail) throw new Error('boom');
    return true;
  }, frames);
  loop.schedule();
  loop.stop();
  assert.equal(frames.flush(), 0);
  assert.equal(steps, 0);
  loop.schedule();
  fail = true;
  assert.throws(() => frames.flush(), /boom/);
  fail = false;
  loop.schedule();
  assert.equal(frames.flush(), 1, 'schedule works again after the failed step');
  assert.equal(steps, 2);
});
```

**Verify**: `cd apps/assembly-guide/app && node --test test/loop.test.mjs` → `# pass 4`, `# fail 0`

### Step 3: Use the loop in the assembly guide's `main.js`

In `apps/assembly-guide/app/src/main.js`:

1. Add `import { createLoop } from './loop.js';` directly after the line `import { createTags } from './tags.js';`.
2. Replace the block from `let raf = 0;` through the closing brace of `function schedule() { ... }` (lines 58–76 in
   the excerpt above) with:

```js
let last = 0;
const loop = createLoop((now) => {
  const dt = last ? Math.min(0.1, (now - last) / 1000) : 0;
  last = now;
  if (player.tick(dt)) viewer.setTime(player.time);
  const cameraMoving = viewer.update(dt);
  if (viewer.dirty) viewer.render();
  tags.update();
  const more = player.playing || cameraMoving || Boolean(viewer.tween);
  if (!more) last = 0;
  return more;
});
function schedule() {
  loop.schedule();
}
```

   Keep `schedule` a function declaration: `createUI({ ..., onUserActivity: () => schedule() })` near line 39 and
   `syncInset()` near line 49 refer to it before this point in the file. Leave the three lines that follow
   (`viewer.controls.addEventListener('change', schedule);` and the next two) and the `player.on(...)` listener
   exactly as they are.
3. Directly after the line `root.classList.add('ready');` add:

```js
// Debug handle for tools/perf-audit.mjs and the browser console; the page itself never reads it.
window.__soyrack = { player, timeline, viewer, tags };
```

**Verify**: `cd apps/assembly-guide/app && grep -c "requestAnimationFrame" src/main.js` → `0`
**Verify**: `cd apps/assembly-guide/app && npm ci && npm run build && npm test` → exit 0, `# fail 0`

### Step 4: Add the audit script to the assembly guide and run it

Create `apps/assembly-guide/app/tools/perf-audit.mjs` with exactly this content:

```js
// Headless performance audit of the built guide (dist/). Not part of `npm test`: it needs Playwright with a
// Chromium, which the app does not depend on. Run `npm run build` first, then:
//   PLAYWRIGHT_PATH=/path/to/node_modules/playwright node tools/perf-audit.mjs [--max-frame-requests N]
//     [--max-new-programs N] [--max-layout-reads N] [--max-draw-calls N]
// It prints one JSON report. With a --max-* flag it exits 1 when that budget is exceeded.
// The numbers are counts, not timings, so they are the same on any machine:
//   frameRequests    requestAnimationFrame calls per displayed frame during playback (1 is correct)
//   newPrograms      shader programs first compiled after the page said it was ready (each one is a freeze)
//   layoutReads      getBoundingClientRect calls per played frame in the chapters with name tags
//   maxDrawCalls     most draw calls in one frame (shadow pass included) at sampled moments of every chapter
import { createRequire } from 'node:module';
import http from 'node:http';
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const dist = resolve(here, '../dist');
const args = process.argv.slice(2);
const flag = (name) => {
  const i = args.indexOf(`--${name}`);
  return i < 0 ? null : Number(args[i + 1]);
};
const budgets = { frameRequests: flag('max-frame-requests'), newPrograms: flag('max-new-programs'), layoutReads: flag('max-layout-reads'), maxDrawCalls: flag('max-draw-calls') };

const require = createRequire(import.meta.url);
const { chromium } = require(process.env.PLAYWRIGHT_PATH || 'playwright');

const TYPES = { html: 'text/html', js: 'application/javascript', css: 'text/css' };
const server = http.createServer((req, res) => {
  const path = req.url.split('?')[0];
  const file = path === '/' ? 'index.html' : path.slice(1);
  try {
    const body = readFileSync(resolve(dist, file));
    res.writeHead(200, { 'content-type': TYPES[file.split('.').pop()] || 'application/octet-stream' });
    res.end(body);
  } catch {
    res.writeHead(404);
    res.end();
  }
});
await new Promise((ok) => server.listen(0, '127.0.0.1', ok));
const url = `http://127.0.0.1:${server.address().port}/#t=0`;

// Software WebGL so the audit runs on machines without a GPU; a small canvas keeps it quick.
const browser = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
let report;
try {
  const page = await browser.newPage({ viewport: { width: 480, height: 320 } });
  const errors = [];
  page.on('pageerror', (e) => errors.push(e.message));
  // Count the page's own frame requests; the audit waits on the untouched original.
  await page.addInitScript(() => {
    const original = window.requestAnimationFrame.bind(window);
    window.__auditFrame = () => new Promise((ok) => original(ok));
    window.__auditRequests = 0;
    window.requestAnimationFrame = (cb) => {
      window.__auditRequests++;
      return original(cb);
    };
  });
  await page.goto(url);
  await page.waitForFunction(() => window.__soyrack && document.getElementById('app').classList.contains('ready'), null, { timeout: 120_000 });
  report = await page.evaluate(async () => {
    const { player, timeline, viewer } = window.__soyrack;
    const info = viewer.renderer.info;
    const frame = window.__auditFrame;
    const settle = async () => {
      await frame();
      await frame();
    };
    await settle();
    const programsAtReady = info.programs.length;

    // Frame requests per displayed frame, half a second into playback of a chapter without name tags.
    const quiet = timeline.chapters.find((c) => !c.tags.length) || timeline.chapters[0];
    player.seek(quiet.start + 1, 'restore');
    await settle();
    player.play();
    for (let i = 0; i < 30; i++) await frame();
    window.__auditRequests = 0;
    for (let i = 0; i < 10; i++) await frame();
    const frameRequests = Math.round(window.__auditRequests / 10);
    player.pause();
    await settle();

    let meshes = 0;
    const materials = new Set();
    viewer.scene.traverse((o) => {
      if (!o.isMesh) return;
      meshes++;
      for (const m of Array.isArray(o.material) ? o.material : [o.material]) materials.add(m);
    });

    // Layout reads per played frame, in the chapters that show name tags.
    let reads = 0;
    const original = Element.prototype.getBoundingClientRect;
    Element.prototype.getBoundingClientRect = function counted() {
      reads++;
      return original.call(this);
    };
    let layoutReads = 0;
    for (const c of timeline.chapters.filter((ch) => ch.tags.length)) {
      player.seek(c.start + (c.end - c.start) * 0.5, 'restore');
      await settle();
      player.play();
      await frame();
      reads = 0;
      const frames = 5;
      for (let i = 0; i < frames; i++) await frame();
      layoutReads = Math.max(layoutReads, Math.ceil(reads / frames));
      player.pause();
    }
    Element.prototype.getBoundingClientRect = original;

    // Draw calls and late shader compiles at five moments of every chapter, the first two inside its fade-in.
    const chapters = [];
    const lateCompiles = [];
    let known = info.programs.length;
    for (const c of timeline.chapters) {
      let calls = 0;
      let triangles = 0;
      for (const f of [0.02, 0.1, 0.35, 0.6, 0.9]) {
        const t = c.start + f * (c.end - c.start);
        player.seek(t, 'restore');
        await settle();
        calls = Math.max(calls, info.render.calls);
        triangles = Math.max(triangles, info.render.triangles);
        if (info.programs.length !== known) {
          lateCompiles.push({ chapter: c.id, time: Number(t.toFixed(1)), programs: info.programs.length });
          known = info.programs.length;
        }
      }
      chapters.push({ id: c.id, calls, triangles });
    }
    return {
      frameRequests,
      programsAtReady,
      programsAfterScrub: known,
      newPrograms: known - programsAtReady,
      lateCompiles,
      layoutReads,
      maxDrawCalls: Math.max(...chapters.map((c) => c.calls)),
      meshes,
      materials: materials.size,
      chapters,
    };
  });
  report.pageErrors = errors;
} finally {
  await browser.close();
  server.close();
}

console.log(JSON.stringify(report, null, 2));
const failures = [];
if (report.pageErrors.length) failures.push(`page errors: ${report.pageErrors.join('; ')}`);
if (budgets.frameRequests !== null && report.frameRequests > budgets.frameRequests) failures.push(`${report.frameRequests} frame requests per displayed frame (budget ${budgets.frameRequests})`);
if (budgets.newPrograms !== null && report.newPrograms > budgets.newPrograms) failures.push(`${report.newPrograms} shader programs compiled after ready (budget ${budgets.newPrograms})`);
if (budgets.layoutReads !== null && report.layoutReads > budgets.layoutReads) failures.push(`${report.layoutReads} layout reads per frame (budget ${budgets.layoutReads})`);
if (budgets.maxDrawCalls !== null && report.maxDrawCalls > budgets.maxDrawCalls) failures.push(`${report.maxDrawCalls} draw calls in one frame (budget ${budgets.maxDrawCalls})`);
for (const f of failures) console.error(`FAIL ${f}`);
process.exit(failures.length ? 1 : 0);
```

**Verify**: `cd apps/assembly-guide/app && PLAYWRIGHT_PATH=/opt/node-tools/node_modules/playwright node tools/perf-audit.mjs --max-frame-requests 1` → exit 0; the JSON has `"frameRequests": 1` and `"pageErrors": []`.
For reference, the same script on the code before this plan reports a `frameRequests` in the tens. The other
numbers in the report (`newPrograms` about 5, `layoutReads` about 6, `maxDrawCalls` about 862) are expected at
this point; later plans improve them. Do not try to change them here.

### Step 5: The same loop module and test in the Pearl guide

Create `apps/pearl-guide/app/src/loop.js` with the identical content as Step 1, and
`apps/pearl-guide/app/test/loop.test.mjs` with the identical content as Step 2.

**Verify**: `cd apps/pearl-guide/app && cmp src/loop.js ../../assembly-guide/app/src/loop.js && cmp test/loop.test.mjs ../../assembly-guide/app/test/loop.test.mjs && node --test test/loop.test.mjs` → no `cmp` output, `# pass 4`, `# fail 0`

### Step 6: Use the loop in the Pearl guide's `main.js`

In `apps/pearl-guide/app/src/main.js`:

1. Add `import { createLoop } from './loop.js';` directly after the line `import { createSheets } from './sheets.js';`.
2. Inside `start()`, replace the block from `  let raf = 0;` through the closing brace of `function schedule() { ... }`
   (lines 77–101 in the excerpt above, including `let idleFrames = 0;`) with:

```js
  let last = 0;
  let idleFrames = 0;
  const loop = createLoop((now) => {
    const dt = last ? Math.min(0.1, (now - last) / 1000) : 0;
    last = now;
    player.tick(dt);
    if (player.playing && dt > 0) stage.adapt(dt * 1000);
    direct(player.time);
    stage.controls.update();
    stage.render();
    // Damping keeps the camera gliding after a drag: allow it 90 quiet frames, then rest.
    const more = player.playing || (stage.controls.enableDamping && idleFrames++ <= 90);
    if (!more) last = 0;
    return more;
  });
  function schedule() {
    idleFrames = 0;
    loop.schedule();
  }
```

   Leave the lines that follow (`stage.controls.addEventListener('change', schedule);` and on) as they are.

**Verify**: `cd apps/pearl-guide/app && grep -c "requestAnimationFrame" src/main.js` → `0`
**Verify**: `cd apps/pearl-guide/app && npm ci && npm run build && npm test` → exit 0, `# fail 0`

### Step 7: Add the audit script to the Pearl guide and run it

Create `apps/pearl-guide/app/tools/perf-audit.mjs` with exactly this content:

```js
// Headless performance audit of the built guide (dist/). Not part of `npm test`: it needs Playwright with a
// Chromium, which the app does not depend on. Run `npm run build` first, then:
//   PLAYWRIGHT_PATH=/path/to/node_modules/playwright node tools/perf-audit.mjs [--max-frame-requests N]
//     [--max-new-programs N] [--max-draw-calls N]
// It prints one JSON report. With a --max-* flag it exits 1 when that budget is exceeded.
// The numbers are counts, not timings, so they are the same on any machine:
//   frameRequests    requestAnimationFrame calls per displayed frame during playback (1 is correct)
//   newPrograms      shader programs first compiled after the loading screen went away (each one is a freeze)
//   maxDrawCalls     most draw calls in one frame (shadow pass included) at sampled moments of every chapter
import { createRequire } from 'node:module';
import http from 'node:http';
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const dist = resolve(here, '../dist');
const args = process.argv.slice(2);
const flag = (name) => {
  const i = args.indexOf(`--${name}`);
  return i < 0 ? null : Number(args[i + 1]);
};
const budgets = { frameRequests: flag('max-frame-requests'), newPrograms: flag('max-new-programs'), maxDrawCalls: flag('max-draw-calls') };

const require = createRequire(import.meta.url);
const { chromium } = require(process.env.PLAYWRIGHT_PATH || 'playwright');

const TYPES = { html: 'text/html', js: 'application/javascript', css: 'text/css', svg: 'image/svg+xml', wasm: 'application/wasm' };
const server = http.createServer((req, res) => {
  const path = req.url.split('?')[0];
  const file = path === '/' ? 'index.html' : path.slice(1);
  try {
    const body = readFileSync(resolve(dist, file));
    res.writeHead(200, { 'content-type': TYPES[file.split('.').pop()] || 'application/octet-stream' });
    res.end(body);
  } catch {
    res.writeHead(404);
    res.end();
  }
});
await new Promise((ok) => server.listen(0, '127.0.0.1', ok));
const url = `http://127.0.0.1:${server.address().port}/#t=0`;

// Software WebGL so the audit runs on machines without a GPU; a small canvas keeps it quick.
const browser = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
let report;
try {
  const page = await browser.newPage({ viewport: { width: 480, height: 320 } });
  const errors = [];
  page.on('pageerror', (e) => errors.push(e.message));
  // Count the page's own frame requests; the audit waits on the untouched original.
  await page.addInitScript(() => {
    const original = window.requestAnimationFrame.bind(window);
    window.__auditFrame = () => new Promise((ok) => original(ok));
    window.__auditRequests = 0;
    window.requestAnimationFrame = (cb) => {
      window.__auditRequests++;
      return original(cb);
    };
  });
  await page.goto(url);
  await page.waitForFunction(() => window.__pearl, null, { timeout: 180_000 });
  report = await page.evaluate(async () => {
    const { player, timeline, stage } = window.__pearl;
    const info = stage.renderer.info;
    const frame = window.__auditFrame;
    const settle = async () => {
      await frame();
      await frame();
    };
    await settle();
    const programsAtReady = info.programs.length;

    // Frame requests per displayed frame, half a second into playback.
    player.seek(timeline.chapters[0].start + 1, 'restore');
    await settle();
    player.play();
    for (let i = 0; i < 30; i++) await frame();
    window.__auditRequests = 0;
    for (let i = 0; i < 10; i++) await frame();
    const frameRequests = Math.round(window.__auditRequests / 10);
    player.pause();
    await settle();

    // Draw calls and late shader compiles at four moments of every chapter.
    const chapters = [];
    const lateCompiles = [];
    let known = info.programs.length;
    for (const c of timeline.chapters) {
      let calls = 0;
      let triangles = 0;
      for (const f of [0.05, 0.3, 0.6, 0.9]) {
        const t = c.start + f * (c.end - c.start);
        player.seek(t, 'restore');
        await settle();
        calls = Math.max(calls, info.render.calls);
        triangles = Math.max(triangles, info.render.triangles);
        if (info.programs.length !== known) {
          lateCompiles.push({ chapter: c.id, time: Number(t.toFixed(1)), programs: info.programs.length });
          known = info.programs.length;
        }
      }
      chapters.push({ id: c.id, calls, triangles });
    }
    return {
      frameRequests,
      programsAtReady,
      programsAfterScrub: known,
      newPrograms: known - programsAtReady,
      lateCompiles,
      maxDrawCalls: Math.max(...chapters.map((c) => c.calls)),
      chapters,
    };
  });
  report.pageErrors = errors;
} finally {
  await browser.close();
  server.close();
}

console.log(JSON.stringify(report, null, 2));
const failures = [];
if (report.pageErrors.length) failures.push(`page errors: ${report.pageErrors.join('; ')}`);
if (budgets.frameRequests !== null && report.frameRequests > budgets.frameRequests) failures.push(`${report.frameRequests} frame requests per displayed frame (budget ${budgets.frameRequests})`);
if (budgets.newPrograms !== null && report.newPrograms > budgets.newPrograms) failures.push(`${report.newPrograms} shader programs compiled after ready (budget ${budgets.newPrograms})`);
if (budgets.maxDrawCalls !== null && report.maxDrawCalls > budgets.maxDrawCalls) failures.push(`${report.maxDrawCalls} draw calls in one frame (budget ${budgets.maxDrawCalls})`);
for (const f of failures) console.error(`FAIL ${f}`);
process.exit(failures.length ? 1 : 0);
```

**Verify**: `cd apps/pearl-guide/app && PLAYWRIGHT_PATH=/opt/node-tools/node_modules/playwright node tools/perf-audit.mjs --max-frame-requests 1 --max-new-programs 0` → exit 0; the JSON has `"frameRequests": 1`, `"newPrograms": 0` and `"pageErrors": []`.

### Step 8: Document it

1. In `apps/assembly-guide/README.md`, insert this paragraph (followed by a blank line) directly **before** the
   last paragraph of the file, the one that begins `Tests check the chapters, where each test check leaves its hardware`:

```md
Performance is checked by count, not by feel. `app/src/loop.js` runs the player: one animation-frame callback
per displayed frame, however often the player or the camera asks for one. After a build,
`PLAYWRIGHT_PATH=<playwright> node tools/perf-audit.mjs --max-frame-requests 1` (in `app/`) plays the guide in
a headless Chromium and reports frame requests per frame, shader programs compiled after the page was ready,
layout reads per frame and draw calls per chapter; each `--max-*` flag turns a number into a pass or fail.
It needs a Playwright with Chromium and is not part of `npm test`.
```

2. In `apps/pearl-guide/README.md`, in the `## Performance` section, add this as a second paragraph of that
   section (blank line before and after):

```md
`app/src/loop.js` runs the player: one animation-frame callback per displayed frame, however often the player
or the camera asks for one. After a build,
`PLAYWRIGHT_PATH=<playwright> node tools/perf-audit.mjs --max-frame-requests 1 --max-new-programs 0` (in `app/`)
plays the guide in a headless Chromium and fails if a frame queues more than one callback or a shader compiles
after the loading screen. It needs a Playwright with Chromium and is not part of `npm test`.
```

**Verify**: `grep -c "perf-audit.mjs" apps/assembly-guide/README.md apps/pearl-guide/README.md` → each file reports at least `1`

### Step 9: Commit

`git add` the ten in-scope files and commit with the message from "Git workflow".

**Verify**: `git status --short` → empty (ignored `dist/` and `node_modules/` do not show); `git show --stat HEAD` lists exactly the ten in-scope files.

## Test plan

- New: `test/loop.test.mjs` in each app (4 tests each, content given above): one callback per frame when the step
  asks for a frame itself; idempotent `schedule()` and resting; a frame asked for during the last step is not
  lost; `stop()` and recovery after a throwing step.
- Existing suites must stay green in both apps.
- Browser-level check: both audit scripts report `frameRequests` of 1.

## Done criteria

ALL must hold:

- [ ] `cd apps/assembly-guide/app && npm run build && npm test` exits 0 with `# fail 0`
- [ ] `cd apps/pearl-guide/app && npm run build && npm test` exits 0 with `# fail 0`
- [ ] `grep -c "requestAnimationFrame" apps/assembly-guide/app/src/main.js apps/pearl-guide/app/src/main.js` reports `0` for both
- [ ] Assembly audit with `--max-frame-requests 1` exits 0 and reports `"frameRequests": 1`
- [ ] Pearl audit with `--max-frame-requests 1 --max-new-programs 0` exits 0 and reports `"frameRequests": 1`
- [ ] `git show --stat HEAD` lists only the ten in-scope files

## STOP conditions

Stop and report back (do not improvise) if:

- Either `main.js` does not match the excerpts in "Current state" (the code drifted).
- An audit reports `frameRequests` above 1 after your change, twice. Report the full JSON.
- An audit cannot start Chromium or times out after 10 minutes. Report the error text; do not install browsers.
- A previously passing test in either app fails after your change and the cause is not an obvious typo of yours.
- The fix seems to need a change to `player.js` or any other out-of-scope file.

## Maintenance notes

- Anything that wants a redraw must call `schedule()`; nothing else may call `requestAnimationFrame` for the
  player. The grep in the done criteria is the quick check.
- The two `loop.js` files and their tests are deliberate copies; the apps have separate Docker contexts. If a
  shared explainer kit is ever created, this module is the first candidate to move there.
- Reviewer: check that `last` is reset when the loop rests (otherwise the first frame after a pause would jump),
  and that Pearl's 90-frame damping allowance behaves as before.
- Deferred: the audit numbers other than `frameRequests` for the assembly guide are addressed by plans 003–005.
