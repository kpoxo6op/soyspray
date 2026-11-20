// The writing rules from STANDARDS.md that a machine can check (rules.mjs), run over every caption, title, link and
// kit line of the Pearl guide.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { CHAPTERS, GUIDE, buildTimeline } from '../src/story.js';
import { GROUPS, KIT } from '../src/kit.js';
import { STL, SETTINGS, PLATE_NOTE } from '../src/files.js';
import { checkCaptions, checkCopy, checkIds, checkLinks, checkOrder, checkTitles, kitStrings } from './rules.mjs';

const timeline = buildTimeline(CHAPTERS);

test('copy uses plain words: no stock phrases, exclamations, emoji or em dashes', () => {
  checkCopy([
    GUIDE.title, GUIDE.lede, KIT.title, KIT.lede,
    ...timeline.chapters.flatMap((c) => [c.title, c.goal, c.work, ...c.beats.map((b) => b.text)]),
    ...kitStrings(GROUPS),
    ...STL.flatMap((f) => [f.name, f.note]),
    ...SETTINGS.flat(),
    PLATE_NOTE,
  ]);
});

test('captions are one short instruction, on screen long enough to read', () => {
  checkCaptions(timeline);
});

test('titles are sentence case', () => {
  checkTitles([...timeline.chapters.map((c) => c.title), ...GROUPS.map((g) => g.title)]);
});

test('every chapter ends at a checkpoint you can see, count or weigh', () => {
  // the opening chapter shows Pearl and asks nothing of you yet
  for (const c of timeline.chapters.slice(1)) {
    const last = c.beats[c.beats.length - 1];
    assert.ok(last.check, `${c.title} ends without a checkpoint`);
    assert.equal(c.beats.filter((b) => b.check).length, 1, `${c.title} has one checkpoint`);
  }
});

test('the timeline runs in order with no gaps', () => {
  checkOrder(timeline);
});

test('chapter ids are link targets that do not clash with the panels', () => {
  checkIds(timeline.chapters);
});

test('the soldering chapter keeps its id and leads to the soldering page', () => {
  const c = timeline.chapters.find((ch) => ch.id === 'solder');
  assert.ok(c, 'chapter id solder is kept, so its Done tick and #solder links still work');
  assert.equal(c.title, 'Solder the switched lead');
  assert.equal(c.beats.length, 4);
  assert.deepEqual(c.beats[0].link, { href: '../soldering/', text: 'Open the soldering page' });
  const links = checkLinks(timeline);
  assert.equal(links.length, 1);
});

test('the guide names only the kit Boris has: no Jaycar trip, no stale total', () => {
  const said = timeline.chapters.flatMap((c) => [c.goal, c.work, ...c.beats.map((b) => b.text)]).join('\n');
  assert.ok(!/Jaycar/.test(said), 'no chapter sends him to Jaycar');
  assert.ok(!/\$\d/.test(said), 'no chapter quotes a total; the Kit panel adds it up');
  assert.ok(!/station/i.test(said), 'he has a pen iron, not a station');
});
