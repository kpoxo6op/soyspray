// The stitch simulator must draw every stitch at any setting, and the built site must be
// self-contained with content-addressed asset names.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, existsSync, statSync, readdirSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createHash } from 'node:crypto';
import { STITCHES, byNo } from '../src/data/stitches.js';
import { renderStitchSVG, threadPaths } from '../src/stitch-render.js';

const SITE = resolve(dirname(fileURLToPath(import.meta.url)), '../dist');

test('every stitch renders to a non-empty SVG path at default, minimum and maximum settings', () => {
  for (const s of STITCHES) {
    for (const [width, length] of [
      [s.width.def, s.length.def],
      [s.width.min, s.length.min],
      [s.width.max, s.length.max],
    ]) {
      const paths = threadPaths(s, { width, length, heightMm: 30 });
      const points = paths.reduce((n, p) => n + p.length, 0);
      assert.ok(points >= 4, `stitch ${s.no} at ${width}/${length} has ${points} points`);
      for (const p of paths) for (const [x, y] of p) assert.ok(Number.isFinite(x) && Number.isFinite(y), `stitch ${s.no} finite`);
      const svg = renderStitchSVG(s, { width, length, heightMm: 30 });
      assert.match(svg, /^<svg /);
      assert.match(svg, /<path class="thread" d="M/);
    }
  }
});

test('geometry follows the needle: zigzag swings full width, straight stitch stays on the line', () => {
  const zz = threadPaths(byNo(2), { width: 6, length: 2, heightMm: 20 })[0];
  const xs = zz.map(([x]) => x);
  assert.equal(Math.max(...xs), 3);
  assert.equal(Math.min(...xs), -3);
  const straight = threadPaths(byNo(0), { width: 0, length: 2.5, heightMm: 10 })[0];
  assert.ok(straight.every(([x]) => x === 0));
  assert.ok(Math.abs(straight[1][1] - 2.5) < 1e-9, 'one stitch length per stitch');
  const three = threadPaths(byNo(5), { width: 6, length: 1, heightMm: 6 })[0];
  assert.ok(three.some(([x]) => Math.abs(x - 1) < 0.02), 'three-step zigzag lands between the swings');
});

test('the built site is self-contained and content-addressed', () => {
  const html = readFileSync(resolve(SITE, 'index.html'), 'utf8');
  const refs = [...html.matchAll(/\b(?:src|href)="([^"]+)"/g)].map((m) => m[1]).filter((r) => !r.startsWith('data:') && !r.startsWith('#'));
  assert.ok(refs.length >= 3);
  for (const r of refs) {
    assert.ok(!/^[a-z]+:|^\/\//i.test(r), `${r} is relative`);
    const f = resolve(SITE, r.split('?')[0]);
    assert.ok(existsSync(f) && statSync(f).size > 0, `${r} exists`);
  }
  for (const asset of ['app.js', 'app.css']) {
    const m = html.match(new RegExp(`"${asset}\\?v=([a-f0-9]+)"`));
    assert.ok(m, `${asset} has a revision`);
    const digest = createHash('sha256').update(readFileSync(resolve(SITE, asset))).digest('hex');
    assert.ok(digest.startsWith(m[1]), `${asset} revision identifies its bytes`);
  }
  assert.match(html, /<script type="module" src="app\.js\?v=[a-f\d]+"><\/script>/);
  const js = readFileSync(resolve(SITE, 'app.js'), 'utf8');
  assert.ok(js.length < 300000, `the shell stays small without three.js (${js.length} bytes)`);
  assert.ok(js.includes('Three-step zigzag'), 'content is bundled');
  assert.ok(js.includes('Трёхступенчатый'), 'russian content is bundled');
  const chunks = readdirSync(resolve(SITE, 'chunks'));
  const engine = chunks.find((f) => f.startsWith('machine3d-'));
  assert.ok(engine && statSync(resolve(SITE, 'chunks', engine)).size > 400000, 'three.js lives in the on-demand 3D chunk');
  assert.ok(js.includes(`./chunks/${engine}`), 'the shell imports the 3D chunk by its hashed name');
});

test('the service worker precaches exactly the files of this build', () => {
  const sw = readFileSync(resolve(SITE, 'sw.js'), 'utf8');
  const list = JSON.parse(sw.match(/const PRECACHE = (\[.*?\]);/s)[1]);
  const html = readFileSync(resolve(SITE, 'index.html'), 'utf8');
  for (const asset of ['app.js', 'app.css']) {
    const ref = html.match(new RegExp(`"(${asset}\\?v=[a-f0-9]+)"`))[1];
    assert.ok(list.includes(ref), `${ref} precached`);
  }
  assert.ok(list.includes('./'), 'the shell page is precached');
  const walk = (dir, prefix = '') => readdirSync(dir, { withFileTypes: true }).flatMap((d) => (d.isDirectory() ? walk(resolve(dir, d.name), `${prefix}${d.name}/`) : [`${prefix}${d.name}`]));
  const files = walk(SITE).filter((f) => f !== 'sw.js' && f !== 'index.html');
  for (const f of files) assert.ok(list.some((p) => p.split('?')[0] === f), `${f} precached`);
  assert.match(sw, /const VERSION = '[a-f0-9]{12}'/);
});
