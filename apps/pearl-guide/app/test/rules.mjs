// The writing rules from STANDARDS.md that a machine can check, as functions, so every page's content test runs the
// same rules and the pages cannot drift apart. Not a test file itself (it does not match *.test.mjs).
import assert from 'node:assert/strict';

export const BANNED = [
  'seamless', 'unlock', 'elevate', 'journey', 'delve', 'leverage', 'robust', 'effortless', 'supercharge', 'game-changer',
  'cutting-edge', 'revolutionary', 'empower', 'harness', 'streamline', 'tapestry', 'magic', 'simply', 'just', 'easy', 'easily',
  'obviously', 'dive into', "let's", 'welcome to', 'get started', 'it’s not', "it's not", 'not just', 'worth noting', 'imagine',
];

/** Words allowed to start with a capital inside a sentence-case title. */
export const PROPER = new Set([
  'Pearl', 'Pearl’s', "Pearl's", 'Jaycar', 'AliExpress', 'Spotlight', 'PB', 'Tech', 'Bambu', 'Studio', 'Lab', 'PLA', 'P1S', 'Claude',
  'Kit', 'Files', 'Stage', 'LED', 'LEDs', 'AWG', 'CXG', 'JST-PH', 'DRV8833', 'ANENG', 'LiPo',
]);

/** Plain words: no stock phrases, exclamation marks, emoji, em dashes, spaced en dashes or questions. */
export function checkCopy(strings) {
  for (const text of strings) {
    assert.equal(typeof text, 'string', `not text: ${text}`);
    const lower = text.toLowerCase();
    for (const w of BANNED) assert.ok(!new RegExp(`(^|[^a-z])${w.replace(/[-']/g, (c) => `\\${c}`)}([^a-z]|$)`).test(lower), `"${w}" in: ${text}`);
    assert.ok(!text.includes('!'), `exclamation in: ${text}`);
    assert.ok(!text.includes('—'), `em dash in: ${text}`);
    assert.ok(!/\s–\s/.test(text), `spaced en dash in: ${text}`);
    assert.ok(!/\p{Extended_Pictographic}/u.test(text), `emoji in: ${text}`);
    assert.ok(!/\?\s*$/.test(text), `question in: ${text}`);
  }
}

/** One short instruction per caption, on screen long enough to read: at most 120 characters, d >= chars / 14 + 1. */
export function checkCaptions(timeline) {
  for (const c of timeline.chapters) {
    for (const b of c.beats) {
      assert.ok(b.text.length <= 120, `${b.text.length} characters: ${b.text}`);
      assert.ok(b.d >= b.text.length / 14 + 1, `${b.d} s is too short to read: ${b.text}`);
    }
  }
}

/** Sentence case: a capital or digit first, then no Title Case words except names. */
export function checkTitles(titles, proper = PROPER) {
  for (const t of titles) {
    const [first, ...rest] = t.split(/\s+/);
    assert.match(first, /^[A-Z0-9]/, t);
    for (const w of rest) assert.ok(proper.has(w) || !/^[A-Z][a-z]/.test(w), `Title Case in: ${t}`);
  }
}

/** Every chapter ends at one checkpoint, on its last beat. */
export function checkCheckpoints(chapters) {
  for (const c of chapters) {
    const last = c.beats[c.beats.length - 1];
    assert.ok(last.check, `${c.title} ends without a checkpoint`);
    assert.equal(c.beats.filter((b) => b.check).length, 1, `${c.title} has one checkpoint`);
  }
}

/** The timeline runs in order with no gaps, and every beat has a camera. */
export function checkOrder(timeline) {
  let t = 0;
  for (const c of timeline.chapters) {
    assert.equal(c.start, t);
    for (const b of c.beats) {
      assert.equal(b.start, t);
      assert.ok(b.d > 0 && b.cam && b.cam.p.length === 3 && b.cam.t.length === 3, `${c.id}: beat ${b.index + 1} needs a camera`);
      t = b.end;
    }
    assert.equal(c.end, t);
  }
  assert.equal(timeline.duration, t);
}

/** Chapter ids are link targets (#id): a slug, unique, and never a panel's name. */
export const RESERVED_IDS = ['chapters', 'kit', 'files'];
export function checkIds(chapters) {
  const seen = new Set();
  for (const c of chapters) {
    assert.match(c.id, /^[a-z][a-z0-9-]*$/, c.id);
    assert.ok(!RESERVED_IDS.includes(c.id), `${c.id} is a panel's address`);
    assert.ok(!seen.has(c.id), `duplicate chapter id ${c.id}`);
    seen.add(c.id);
  }
}

/** A beat's link: text that follows the copy rules, and a relative href, since both pages ship in one image. */
export function checkLinks(timeline) {
  const links = timeline.chapters.flatMap((c) => c.beats.filter((b) => b.link).map((b) => b.link));
  for (const l of links) {
    assert.ok(l.text && l.href, 'a link needs text and an href');
    assert.ok(!/^([a-z]+:|\/)/i.test(l.href), `link is not relative: ${l.href}`);
  }
  checkCopy(links.map((l) => l.text));
  return links;
}

/** Every visible line of a kit: group titles and notes, item names and reasons. */
export function kitStrings(groups) {
  return groups.flatMap((g) => [g.title, g.when, ...g.items.flatMap((i) => [i.name, i.why])]);
}
