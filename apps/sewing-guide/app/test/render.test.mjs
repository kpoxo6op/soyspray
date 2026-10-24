// The stitch simulator must draw every stitch at any setting, and the built site must be
// self-contained with content-addressed asset names.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, existsSync, statSync } from 'node:fs';
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
  assert.doesNotMatch(html, /type="module"/);
  const js = readFileSync(resolve(SITE, 'app.js'), 'utf8');
  assert.ok(js.length > 400000, 'three.js is bundled');
  assert.ok(js.includes('Three-step zigzag'), 'content is bundled');
  assert.ok(js.includes('Трёхступенчатый'), 'russian content is bundled');
});
