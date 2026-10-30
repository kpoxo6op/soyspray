// The built site: every reference is relative, revisioned by content and present, so a returning browser never
// mixes an old page with new models.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { existsSync, readFileSync, statSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { STL } from '../src/files.js';

const dist = resolve(dirname(fileURLToPath(import.meta.url)), '../dist');
const html = readFileSync(resolve(dist, 'index.html'), 'utf8');
const js = readFileSync(resolve(dist, 'app.js'), 'utf8');
const digest = (f) => createHash('sha256').update(readFileSync(resolve(dist, f))).digest('hex');

test('the page loads only its own revisioned files', () => {
  const refs = [...html.matchAll(/\b(?:src|href)="([^"]+)"/g)].map((m) => m[1]);
  assert.deepEqual(refs.map((r) => r.split('?')[0]).sort(), ['app.css', 'app.js', 'pearl.svg']);
  for (const r of refs) {
    const [file, query] = r.split('?v=');
    assert.ok(query && digest(file).startsWith(query), `${r} identifies its bytes`);
  }
  assert.doesNotMatch(html, /type="module"/);
});

test('models, decoder and print files ship with the page', () => {
  for (const m of ['pearl', 'prints', 'bench']) {
    const ref = js.match(new RegExp(`data/${m}\\.glb\\?v=([0-9a-f]{16})`));
    assert.ok(ref, `${m}.glb is referenced with a revision`);
    assert.ok(digest(`data/${m}.glb`).startsWith(ref[1]), `${m}.glb revision matches`);
  }
  for (const f of ['draco/draco_decoder.wasm', 'draco/draco_wasm_wrapper.js', ...STL.map((s) => `files/${s.file}`)]) {
    assert.ok(existsSync(resolve(dist, f)) && statSync(resolve(dist, f)).size > 1000, `${f} is in the build`);
  }
});
