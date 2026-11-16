import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { CHAPTERS, SHOTS, WORDS, buildTimeline } from '../network/story.js';
import { ACTOR_IDS } from '../network/scene.js';
import { DONE_KEY } from '../network/sheets.js';

const app = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const guides = JSON.parse(readFileSync(resolve(app, 'data/guides.json'), 'utf8'));
const known = new Set(ACTOR_IDS);
const isKnown = (id) => known.has(id) || (/^ruler(\d+)$/.test(id) && Number(id.slice(5)) <= 255);
const beats = CHAPTERS.flatMap((c) => c.beats.map((b) => ({ c, b })));

test('every beat points at things that exist in the scene and a shot that exists', () => {
  for (const { c, b } of beats) {
    const where = `${c.id}: ${b.text.slice(0, 40)}`;
    assert.ok(SHOTS[b.shot], `${where} uses shot ${b.shot}`);
    for (const id of b.focus) assert.ok(isKnown(id), `${where} focuses ${id}`);
    for (const [id] of b.labels) assert.ok(isKnown(id), `${where} labels ${id}`);
    for (const [path, kind] of b.flows) {
      assert.ok(['ok', 'no'].includes(kind), where);
      assert.ok(path.length >= 2, where);
      for (const id of path) assert.ok(isKnown(id), `${where} routes through ${id}`);
    }
  }
});

test('captions stay readable: one short sentence or two, at most five labels, time to read them', () => {
  const timeline = buildTimeline();
  for (const c of timeline.chapters) {
    for (const b of c.beats) {
      assert.ok(b.text.length <= 120, `${c.id}: ${b.text.length} characters`);
      assert.ok(b.labels.length <= 5, `${c.id}: ${b.labels.length} labels`);
      assert.ok(b.end - b.start >= b.text.length / 14 + 1, `${c.id}: too short on screen`);
      assert.doesNotMatch(b.text, /[!?—]|\b(simply|just|easy|seamless|leverage|robust)\b/i, `${c.id}: house style`);
    }
  }
});

test('the public address and the WAN prefix never appear in the guide', () => {
  const src = readFileSync(resolve(app, 'network/story.js'), 'utf8');
  for (const m of src.matchAll(/\b(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})\b/g)) {
    const [a, b] = [Number(m[1]), Number(m[2])];
    const allowed = (a === 192 && b === 168) || a === 10 || (a === 100 && b >= 64 && b <= 127) || (a === 169 && b === 254) || m[0] === '1.1.1.1' || m[0] === '8.8.8.8';
    assert.ok(allowed, `${m[0]} is not a private, Tailscale or well-known resolver address`);
  }
});

test('chapter ids are unique and the catalog lists them with the guide’s own Done key', () => {
  assert.equal(new Set(CHAPTERS.map((c) => c.id)).size, CHAPTERS.length);
  const entry = guides.find((g) => g.slug === 'network');
  assert.deepEqual(entry.chapters.map((c) => c.id), CHAPTERS.map((c) => c.id));
  assert.equal(entry.store, DONE_KEY);
});

test('the Words panel explains every term it lists, once', () => {
  assert.equal(new Set(WORDS.map(([t]) => t)).size, WORDS.length);
  for (const [t, d] of WORDS) assert.ok(d.length > 20 && d.length <= 140, t);
});

test('the built page loads only revisioned assets and links back to the catalog', () => {
  const html = readFileSync(resolve(app, 'dist/network/index.html'), 'utf8');
  const refs = [...html.matchAll(/(?:src|href)="([^"#]+)"/g)].map((m) => m[1]);
  assert.deepEqual(refs.filter((u) => u !== '../').sort(), refs.filter((u) => /\?v=[0-9a-f]{16}$/.test(u)).sort());
  assert.equal(refs.length, 4);
  assert.ok(refs.includes('../'));
});
