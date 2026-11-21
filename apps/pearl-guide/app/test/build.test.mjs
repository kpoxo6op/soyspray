// The built site: every reference is relative, revisioned by content and present, so a returning browser never
// mixes an old page with new models.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { existsSync, readFileSync, readdirSync, statSync } from 'node:fs';
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

// The second page must ship independently; the Pearl build tests cannot catch leaked models or story code.
test('soldering ships only its revisioned runtime, bench, table photo and decoder', () => {
  const solder = readFileSync(resolve(dist, 'soldering/index.html'), 'utf8');
  const bundle = readFileSync(resolve(dist, 'soldering/app.js'), 'utf8');
  const refs = [...solder.matchAll(/\b(?:src|href)="([^"]+)"/g)].map((m) => m[1]).filter((r) => !r.startsWith('data:'));
  assert.deepEqual(refs.map((r) => r.split('?')[0]).sort(), ['app.css', 'app.js']);
  for (const r of refs) {
    const [file, revision] = r.split('?v=');
    assert.match(revision || '', /^[0-9a-f]{16}$/);
    assert.ok(digest(`soldering/${file}`).startsWith(revision), `${r} identifies its bytes`);
  }
  assert.deepEqual(readdirSync(resolve(dist, 'soldering/data')).sort(), ['bench.glb', 'sort.jpg', 'table.jpg']);
  for (const file of ['bench.glb', 'sort.jpg', 'table.jpg']) {
    const revision = bundle.match(new RegExp(`data/${file.replace('.', '\\.')}\\?v=([0-9a-f]{16})`));
    assert.ok(revision, `bundle names ${file} with a revision`);
    assert.ok(digest(`soldering/data/${file}`).startsWith(revision[1]));
  }
  assert.equal(/data\/(?:pearl|prints)\.glb/.test(bundle), false, 'soldering has no Pearl model URLs');
  for (const file of ['draco_decoder.wasm', 'draco_wasm_wrapper.js']) {
    assert.ok(statSync(resolve(dist, 'soldering/draco', file)).size > 1000);
    assert.equal(digest(`soldering/draco/${file}`), digest(`draco/${file}`));
  }
  for (const pearlOnly of ['Stage 0 gets you ready', 'purge chute']) {
    assert.ok(readFileSync(resolve(dist, 'app.js'), 'utf8').includes(pearlOnly), `Pearl bundle has "${pearlOnly}"`);
    assert.equal(bundle.includes(pearlOnly), false, `Pearl story and printer stay out of soldering ("${pearlOnly}")`);
  }
  assert.doesNotMatch(solder, /btnFiles|filesSheet/);
});

test('soldering exposes a Kit button and dialog only when it has kit content', async () => {
  const { KIT } = await import('../src/soldering/kit.js');
  const solder = readFileSync(resolve(dist, 'soldering/index.html'), 'utf8');
  assert.equal(solder.includes('id="btnKit"'), !!KIT);
  assert.equal(solder.includes('id="kitSheet"'), !!KIT);
});
