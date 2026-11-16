import { test } from 'node:test';
import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { chapterHref } from '../src/page.js';

const app = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const guides = JSON.parse(readFileSync(resolve(app, 'data/guides.json'), 'utf8'));
const html = readFileSync(resolve(app, 'dist/index.html'), 'utf8');

test('every chapter of every guide is listed with a link that opens its guide there', () => {
  assert.deepEqual(guides.map((g) => g.path), ['/assembly/', '/crimping/', '/pearl/', '/network/']);
  for (const g of guides) {
    assert.ok(g.chapters.length > 0);
    assert.equal(new Set(g.chapters.map((c) => c.id)).size, g.chapters.length, `${g.slug} chapter ids are unique`);
    for (const c of g.chapters) {
      const href = chapterHref(g, c);
      assert.match(href, g.link === 'id' ? /^\/(assembly|crimping|network)\/#[a-z0-9-]+$/ : /^\/pearl\/#t=\d+(\.\d)?$/);
      assert.ok(html.includes(`<soy-chapter href="${href}"`), `${href} is on the page`);
    }
  }
  const rows = html.match(/<soy-chapter /g) || [];
  assert.equal(rows.length, guides.reduce((t, g) => t + g.chapters.length, 0));
});

test('Pearl ticks are shared with the Pearl guide on the same site', () => {
  const pearl = guides.find((g) => g.slug === 'pearl');
  const sheets = resolve(app, '../../pearl-guide/app/src/sheets.js');
  if (!existsSync(sheets)) return; // the image build has only this app
  assert.ok(readFileSync(sheets, 'utf8').includes(`done: '${pearl.store}'`));
});

test('the page loads only revisioned assets, so the year-long cache is safe', () => {
  const refs = [...html.matchAll(/(?:src|href)="([^"#]+)"/g)].map((m) => m[1]).filter((u) => !u.startsWith('/') && !u.startsWith('data:'));
  assert.deepEqual(refs.sort(), refs.filter((u) => /\?v=[0-9a-f]{16}$/.test(u)).sort());
  assert.equal(refs.length, 2);
});

test('guides.json matches the guides\' current chapters', async (t) => {
  const deps = ['../../pearl-guide/app/node_modules/three', '../../assembly-guide/app/node_modules/three'];
  if (!deps.every((d) => existsSync(resolve(app, d)))) return t.skip('run npm ci in both guide apps to compare');
  const { extractGuides } = await import('../tools/extract-guides.mjs');
  assert.deepEqual(await extractGuides(), guides, 'run node tools/extract-guides.mjs and commit data/guides.json');
});
