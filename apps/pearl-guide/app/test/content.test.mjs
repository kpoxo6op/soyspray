// The writing rules from STANDARDS.md that a machine can check, run over every caption, title and kit line.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { CHAPTERS, buildTimeline } from '../src/story.js';
import { GROUPS } from '../src/kit.js';
import { STL, SETTINGS, PLATE_NOTE } from '../src/files.js';

const BANNED = [
  'seamless', 'unlock', 'elevate', 'journey', 'delve', 'leverage', 'robust', 'effortless', 'supercharge', 'game-changer',
  'cutting-edge', 'revolutionary', 'empower', 'harness', 'streamline', 'tapestry', 'magic', 'simply', 'just', 'easy', 'easily',
  'obviously', 'dive into', "let's", 'welcome to', 'get started', 'it’s not', "it's not", 'not just', 'worth noting', 'imagine',
];
const PROPER = new Set(['Pearl', 'Pearl’s', "Pearl's", 'Jaycar', 'AliExpress', 'Spotlight', 'PB', 'Tech', 'Bambu', 'Studio', 'Lab', 'PLA', 'P1S', 'Claude', 'Kit', 'Files', 'Stage']);

const timeline = buildTimeline(CHAPTERS);
const visible = [
  ...timeline.chapters.flatMap((c) => [c.title, c.goal, c.work, ...c.beats.map((b) => b.text)]),
  ...GROUPS.flatMap((g) => [g.title, g.when, ...g.items.flatMap((i) => [i.name, i.why])]),
  ...STL.flatMap((f) => [f.name, f.note]),
  ...SETTINGS.flat(),
  PLATE_NOTE,
];

test('copy uses plain words: no stock phrases, exclamations, emoji or em dashes', () => {
  for (const text of visible) {
    const lower = text.toLowerCase();
    for (const w of BANNED) assert.ok(!new RegExp(`(^|[^a-z])${w.replace(/[-']/g, (c) => `\\${c}`)}([^a-z]|$)`).test(lower), `"${w}" in: ${text}`);
    assert.ok(!text.includes('!'), `exclamation in: ${text}`);
    assert.ok(!text.includes('—'), `em dash in: ${text}`);
    assert.ok(!/\s–\s/.test(text), `spaced en dash in: ${text}`);
    assert.ok(!/\p{Extended_Pictographic}/u.test(text), `emoji in: ${text}`);
    assert.ok(!/\?\s*$/.test(text), `question in: ${text}`);
  }
});

test('captions are one short instruction, on screen long enough to read', () => {
  for (const c of timeline.chapters) {
    for (const b of c.beats) {
      assert.ok(b.text.length <= 120, `${b.text.length} characters: ${b.text}`);
      assert.ok(b.d >= b.text.length / 14 + 1, `${b.d} s is too short to read: ${b.text}`);
    }
  }
});

test('titles are sentence case', () => {
  const titles = [...timeline.chapters.map((c) => c.title), ...GROUPS.map((g) => g.title)];
  for (const t of titles) {
    const [first, ...rest] = t.split(/\s+/);
    assert.match(first, /^[A-Z0-9]/, t);
    for (const w of rest) assert.ok(PROPER.has(w) || !/^[A-Z][a-z]/.test(w), `Title Case in: ${t}`);
  }
});

test('every chapter ends at a checkpoint you can see, count or weigh', () => {
  for (const c of timeline.chapters.slice(1)) {
    const last = c.beats[c.beats.length - 1];
    assert.ok(last.check, `${c.title} ends without a checkpoint`);
    assert.ok(c.beats.filter((b) => b.check).length === 1, `${c.title} has one checkpoint`);
  }
});

test('the timeline runs in order with no gaps', () => {
  let t = 0;
  for (const c of timeline.chapters) {
    assert.equal(c.start, t);
    for (const b of c.beats) {
      assert.equal(b.start, t);
      assert.ok(b.d > 0 && b.cam && b.cam.p.length === 3 && b.cam.t.length === 3);
      t = b.end;
    }
    assert.equal(c.end, t);
  }
  assert.equal(timeline.duration, t);
});
