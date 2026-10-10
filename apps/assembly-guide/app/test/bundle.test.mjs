import { test } from 'node:test';
import assert from 'node:assert/strict';
import { existsSync, readFileSync, statSync } from 'node:fs';
import { resolve } from 'node:path';
import { createHash } from 'node:crypto';
import { SITE } from './helpers.mjs';
import { CHAPTERS } from '../src/timeline.js';

const html = readFileSync(resolve(SITE, 'index.html'), 'utf8');
const js = readFileSync(resolve(SITE, 'app.js'), 'utf8');
const css = readFileSync(resolve(SITE, 'app.css'), 'utf8');

test('every runtime reference in index.html is relative and present', () => {
  const refs = [...html.matchAll(/\b(?:src|href)="([^"]+)"/g)].map((m) => m[1]).filter(r => !r.startsWith('data:'));
  assert.deepEqual(refs.map(r => r.split('?')[0]).sort(), ['app.css', 'app.js']);
  for (const r of refs) {
    assert.ok(!/^[a-z]+:|^\/\//i.test(r), `${r} is relative`);
    const f = resolve(SITE, r.split('?')[0]);
    assert.ok(existsSync(f) && statSync(f).size > 0, `${r} exists`);
  }
  // classic script (works from file://), no module loading
  assert.match(html, /<script src="app\.js(?:\?v=[a-f\d]+)?"><\/script>/);
  assert.doesNotMatch(html, /type="module"/);
});

// A stale revision can make a returning browser run an older player after promotion.
// The reference-presence check does not bind the requested version to its bytes.
test('asset revisions identify the delivered bytes for returning browsers', () => {
  const refs = [...html.matchAll(/\b(?:src|href)="([^"]+)"/g)].map(m => m[1]).filter(r => !r.startsWith('data:'));
  for (const ref of refs) {
    const url = new URL(ref, 'https://assembly.invalid/');
    const bytes = readFileSync(resolve(SITE, url.pathname.slice(1)));
    const digest = createHash('sha256').update(bytes).digest('hex');
    const revision = url.searchParams.get('v');
    assert.ok(revision && revision.length >= 12 && digest.startsWith(revision), `${ref} identifies its content`);
  }
});

test('the bundle carries its own meshes and makes no network requests', () => {
  for (const api of ['fetch(', 'XMLHttpRequest', 'importScripts', 'sendBeacon', 'WebSocket', 'EventSource', 'new Worker', 'import(']) {
    assert.ok(!js.includes(api), `app.js uses ${api}`);
  }
  for (const pat of ['@import', 'url(', 'http:', 'https:']) assert.ok(!css.includes(pat), `app.css contains ${pat}`);
  const urls = [...new Set(js.match(/https?:\/\/[^"'`\s)]+/g) || [])];
  const allowed = [/^http:\/\/www\.w3\.org\//, /^https:\/\/jcgt\.org\//]; // XML namespace and a shader comment
  for (const u of urls) assert.ok(allowed.some((re) => re.test(u)), `unexpected URL in bundle: ${u}`);
  assert.ok(js.length > 500_000, 'three.js and mesh data are bundled');
});

test('visible copy stays on the assembly task', () => {
  const visible = [
    ...CHAPTERS.flatMap((c) => [c.title, c.text]),
    ...[...html.matchAll(/(?:aria-label|title)="([^"]+)"/g)].map((m) => m[1]),
    html.replace(/<[^>]+>/g, ' '),
  ].join('\n');
  const banned = [
    /\bsources?\b/i, /\bagents?\b/i, /\bmodels?\b/i, /provenance/i, /warning/i, /caution/i, /\bheat\b/i, /thermal/i,
    /temperature/i, /verif/i, /\bprompt/i, /\bAI\b/, /claude/i, /gpt/i, /openscad/i, /\bscad\b/i, /\bCAD\b/,
    /photo/i, /inventory/i, /ikea/i, /clearance/i, /not tested/i, /\bTODO\b/,
  ];
  for (const re of banned) assert.doesNotMatch(visible, re, `visible copy matches ${re}`);
});
