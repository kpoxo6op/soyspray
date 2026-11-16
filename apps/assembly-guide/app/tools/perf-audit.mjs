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
