// The soldering page: the same writing rules as the Pearl guide (rules.mjs), plus what the page itself relies on.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { CHAPTERS, GUIDE, KIT, buildSolderTimeline } from '../src/soldering/index.js';
import { ACTORS } from '../src/soldering/scene.js';
import { checkCaptions, checkCheckpoints, checkCopy, checkIds, checkLinks, checkOrder, checkTitles, kitStrings } from './rules.mjs';

const timeline = buildSolderTimeline();

test('six chapters in the designed order, about six minutes a loop', () => {
  assert.deepEqual(timeline.chapters.map((c) => c.id), ['bench', 'first', 'fix', 'light', 'wires', 'small']);
  assert.equal(timeline.chapters.reduce((n, c) => n + c.beats.length, 0), 39);
  assert.ok(timeline.duration >= 330 && timeline.duration <= 420, `${timeline.duration} s`);
  assert.equal(CHAPTERS.length, timeline.chapters.length);
});

test('copy uses plain words: captions, titles, goals, the guide and the kit', () => {
  checkCopy([
    GUIDE.title, GUIDE.summary, GUIDE.section, GUIDE.lede,
    ...timeline.chapters.flatMap((c) => [c.title, c.goal, c.work, ...c.beats.map((b) => b.text)]),
    ...(KIT ? [KIT.title, KIT.lede, ...kitStrings(KIT.groups)] : []),
  ]);
});

test('captions are one short instruction, on screen long enough to read', () => {
  checkCaptions(timeline);
});

test('titles are sentence case', () => {
  checkTitles([GUIDE.title, ...timeline.chapters.map((c) => c.title), ...(KIT ? [KIT.title, ...KIT.groups.map((g) => g.title)] : [])]);
});

test('every chapter, the first included, ends at its one checkpoint', () => {
  checkCheckpoints(timeline.chapters);
});

test('the timeline runs in order with no gaps', () => {
  checkOrder(timeline);
});

test('chapter ids are link targets that do not clash with the panels', () => {
  checkIds(timeline.chapters);
});

test('links are relative and worded by the rules', () => {
  const links = checkLinks(timeline);
  assert.ok(links.some((l) => l.href === '../pearl/#solder'), 'the last beat leads back to Pearl');
});

test('the guide has what the catalog and the Chapters panel show', () => {
  assert.equal(GUIDE.slug, 'soldering');
  assert.equal(GUIDE.title, 'Soldering, first joints');
  for (const k of ['summary', 'section', 'lede']) assert.ok(GUIDE[k] && GUIDE[k].length <= 160, `GUIDE.${k}`);
});

test('the kit is the soldering subset of the Pearl kit, with a checked date', () => {
  if (!KIT) return;
  assert.match(KIT.checked, /^\d{1,2} [A-Z][a-z]{2} 20\d\d$/);
  const ids = KIT.groups.flatMap((g) => g.items.map((i) => i.id));
  assert.equal(new Set(ids).size, ids.length, 'an item appears once');
  for (const want of ['solder', 'flux', 'braid', 'multimeter', 'practice']) assert.ok(ids.includes(want), `kit lists ${want}`);
});

// ---------------------------------------------------------------- the story only asks for actors the scene has

// A stand-in for the scene context: every property and call returns itself, numbers read as 0, and the names the
// story asks for are recorded.
function recorder() {
  const asked = new Set();
  const labels = [];
  const target = function () {};
  const any = new Proxy(target, {
    get: (_, k) => (k === Symbol.toPrimitive ? () => 0 : k === Symbol.iterator ? [][Symbol.iterator] : k === 'then' ? undefined : any),
    apply: () => any,
    construct: () => any,
  });
  const S = new Proxy(
    {},
    {
      get(_, k) {
        if (k === 'a') return (n) => (asked.add(n), any);
        if (k === 'node') return (n) => (asked.add(n), any);
        if (['cutLeg', 'wet', 'brighten'].includes(k)) return (n) => (asked.add(n), any);
        if (k === 't') return 0;
        return any;
      },
    },
  );
  return { S, asked, labels };
}

test('every actor and anchor a beat uses is in the soldering cast', () => {
  const { S, asked } = recorder();
  for (const c of CHAPTERS) {
    for (const u of [0, 0.25, 0.5, 0.75, 1]) {
      c.setup?.(S, u * 10);
      for (const b of c.beats) {
        b.act?.(S, u, u * b.d);
        const list = b.labels ? b.labels(S, u) : [];
        assert.ok(list.length <= 5, `${c.id}: more than five labels at once`);
        assert.equal(new Set(list.map((l) => l.id)).size, list.length, `${c.id}: label ids repeat`);
        checkCopy(list.map((l) => l.text));
        for (const l of list) assert.ok(['t', 'b', 'l', 'r'].includes(l.side), `${c.id}: label ${l.id} side`);
      }
    }
  }
  const missing = [...asked].filter((n) => !ACTORS.includes(n));
  assert.deepEqual(missing, [], `not in the cast: ${missing.join(', ')}`);
  assert.equal(new Set(ACTORS).size, ACTORS.length, 'ACTORS lists each name once');
});
