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
