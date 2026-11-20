// Tests for tools/import-hard.mjs (design.md, section 9.5).
//
// The synthetic tests always run. The tests against Hard's extracted text need the
// private file, which CI does not have: set READING_HARD_JSON to its path to run them.

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { importChapter, repairParagraph, skeleton } from '../tools/import-hard.mjs';

const here = dirname(fileURLToPath(import.meta.url));
const contentDir = join(here, '..', 'content', 'epictetus', 'handbook');
const hardPath = process.env.READING_HARD_JSON;
const hard = hardPath && existsSync(hardPath) ? JSON.parse(readFileSync(hardPath, 'utf8')) : null;
const needsHard = { skip: hard ? false : 'set READING_HARD_JSON to the private extraction to run' };

const shape = (r) => r.sections.map((s) => [s.n, s.para]);

// Synthetic input, invented sentences with the same damage as the extraction.

test('splits inline section labels and sets para from the paragraph', () => {
  const r = importChapter(7, ['7.1. First part here. 2. Second part. 3. ‘Third part.’', '4. Fourth part. 5. Fifth.']);
  assert.deepEqual(shape(r), [[1, 1], [2, 1], [3, 1], [4, 2], [5, 2]]);
  assert.equal(r.sections[2].original, '‘Third part.’');
});

test('splits only at the next expected number before a capital or opening quote', () => {
  const r = importChapter(9, ['9.1. He paid 3. obols, then 5. More words. 2. Next.']);
  assert.deepEqual(shape(r), [[1, 1], [2, 1]]);
  assert.equal(r.sections[0].original, 'He paid 3. obols, then 5. More words.');
});

test('a chapter with only its own number has one section', () => {
  const r = importChapter(12, ['12. One sentence only.']);
  assert.deepEqual(shape(r), [[1, 1]]);
  assert.equal(r.sections[0].original, 'One sentence only.');
});

test('an undivided chapter of several paragraphs gets one section per paragraph', () => {
  const r = importChapter(14, ['14. First paragraph.', 'Second paragraph.']);
  assert.deepEqual(shape(r), [[1, 1], [2, 2]]);
});

test('moves a drifted closing quote back and logs it', () => {
  const r = repairParagraph('He said, ‘Stop here. ‘Then he left, saying, ‘Go.’');
  assert.equal(r.text, 'He said, ‘Stop here.’ Then he left, saying, ‘Go.’');
  assert.equal(r.repairs.length, 1);
  assert.equal(r.repairs[0].kind, 'drifted closing quote');
  assert.deepEqual(r.warnings, []);
});

test('apostrophes do not close a quotation', () => {
  const r = repairParagraph('‘I’m fond of it, ‘and so on, ‘You’re right. ‘End.');
  assert.equal(r.text, '‘I’m fond of it,’ and so on, ‘You’re right.’ End.');
});

test('joins spaced hyphens and collapses doubled spaces, logging both', () => {
  const r = repairParagraph('An ill - educated  person.');
  assert.equal(r.text, 'An ill-educated person.');
  assert.deepEqual(r.repairs.map((x) => x.kind).sort(), ['doubled space', 'spaced hyphen']);
});

test('leaves an en dash between spaces alone', () => {
  assert.equal(repairParagraph('one – two').text, 'one – two');
});

test('a misread label is repaired and logged', () => {
  const r = importChapter(20, ['20.1. One.', '2. Two.', 'II. Not eleven, so not a label.', '3. Three.']);
  assert.equal(r.sections.length, 3);
  const r2 = importChapter(21, ['21.1. One.', ...Array.from({ length: 9 }, (_, i) => `${i + 2}. Text.`), 'II. Eleven.']);
  assert.equal(r2.sections.at(-1).n, 11);
  assert.equal(r2.sections.at(-1).original, 'Eleven.');
  assert.ok(r2.repairs.some((x) => x.kind === 'section label misread' && x.before === 'II.'));
});

test('skeleton has the chapter schema with empty editorial fields', () => {
  const s = skeleton(importChapter(3, ['3. Text.']));
  assert.equal(s.schema, 1);
  assert.equal(s.work, 'handbook');
  assert.deepEqual(s.sections, [{ n: 1, para: 1, original: 'Text.', modern: '' }]);
  assert.deepEqual(s.questions, []);
});

// Hard's text.

test('Handbook 1: five sections in two paragraphs, drifted quote repaired', needsHard, () => {
  const r = importChapter(1, hard['1']);
  assert.deepEqual(shape(r), [[1, 1], [2, 1], [3, 1], [4, 2], [5, 2]]);
  assert.match(r.sections[0].original, /^Some things are within our power/);
  assert.match(r.sections[4].original, /appear to be\.’ Then examine it/);
  assert.match(r.sections[4].original, /‘That’s nothing to me\.’$/);
  assert.deepEqual(r.repairs.map((x) => [x.kind, x.section]), [['drifted closing quote', 5]]);
  assert.deepEqual(r.warnings, []);
});

test('Handbook 2: two sections, nothing to repair', needsHard, () => {
  const r = importChapter(2, hard['2']);
  assert.deepEqual(shape(r), [[1, 1], [2, 1]]);
  assert.match(r.sections[1].original, /^Remove your aversion/);
  assert.deepEqual(r.repairs, []);
});

test('Handbook 3: one section, quote after a comma repaired', needsHard, () => {
  const r = importChapter(3, hard['3']);
  assert.deepEqual(shape(r), [[1, 1]]);
  assert.match(r.sections[0].original, /‘This is a jug that I’m fond of,’ and then/);
  assert.equal(r.repairs.length, 1);
});

test('Handbook 33: sixteen sections, misread label 11 and spaced hyphens repaired', needsHard, () => {
  const r = importChapter(33, hard['33']);
  assert.deepEqual(r.sections.map((s) => s.n), Array.from({ length: 16 }, (_, i) => i + 1));
  assert.deepEqual(r.sections.map((s) => s.para), [1, 2, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 11, 12, 13, 13]);
  assert.match(r.sections[10].original, /^Don’t go casually/);
  assert.match(r.sections[1].original, /horse-races/);
  assert.match(r.sections[7].original, /over-critical/);
  assert.match(r.sections[11].original, /situation\?’ And then/);
  const kinds = r.repairs.map((x) => x.kind);
  assert.equal(kinds.filter((k) => k === 'section label misread').length, 1);
  assert.equal(kinds.filter((k) => k === 'spaced hyphen').length, 2);
});

test('Handbook 53: verse joined, empty paragraph dropped, damage flagged for a human', needsHard, () => {
  const r = importChapter(53, hard['53']);
  assert.deepEqual(shape(r), [[1, 1], [2, 2], [3, 3], [4, 3]]);
  assert.equal(r.sections[1].original.split('\n').length, 2);
  assert.match(r.sections[3].original, /^‘Anytus and Meletus/);
  const kinds = r.warnings.map((w) => w.kind).join('\n');
  assert.match(kinds, /empty paragraph dropped/);
  assert.match(kinds, /ends with a colon/);
  assert.match(kinds, /closing quote is probably missing/);
});

test('chapter files differ from the import only by gloss markup', needsHard, () => {
  const strip = (s) => s.replace(/\[\[([^\]|]+)\|[a-z0-9-]+\]\]/g, '$1');
  let checked = 0;
  for (const n of Object.keys(hard).map(Number)) {
    const file = join(contentDir, `${String(n).padStart(3, '0')}.json`);
    if (!existsSync(file)) continue;
    const doc = JSON.parse(readFileSync(file, 'utf8'));
    const r = importChapter(n, hard[String(n)]);
    assert.deepEqual(
      doc.sections.map((s) => [s.n, s.para, strip(s.original)]),
      r.sections.map((s) => [s.n, s.para, s.original]),
      `Handbook ${n}`,
    );
    checked += 1;
  }
  assert.ok(checked > 0, 'no chapter files found');
});
