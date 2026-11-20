#!/usr/bin/env node
// One-off importer for Robin Hard's Handbook text (design.md, section 9.5).
//
// Input: a JSON object mapping chapter number to an array of paragraphs, with the
// edition's section numbers inline ("1.1. Some things … 2. The things …").
// Output: chapter skeletons in the content schema (section 9.2) with empty
// editorial fields, and a list of every repair for a human to check against the book.
//
// Usage:
//   node tools/import-hard.mjs <hard.json> [--chapters 1-5,33] [--out content/epictetus/handbook] [--force]
//
// Without --out it only prints the report. With --out it writes NNN.json files and
// never overwrites an existing chapter unless --force is given, because the files in
// content/ carry editorial work. Zero dependencies, Node 22.

import { readFileSync, writeFileSync, existsSync, mkdirSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { pathToFileURL } from 'node:url';

const OPEN = '‘';   // ‘
const CLOSE = '’';  // ’
const LETTER = /\p{L}/u;
const CLOSE_BEFORE = /[.,;:?!]/; // punctuation that may sit right before a closing quote

// OCR confusions seen in section labels ("II." for "11.").
const OCR_DIGITS = { I: '1', l: '1', '|': '1', O: '0', o: '0' };
const ocrToDigits = (s) => s.replace(/[Il|Oo]/g, (c) => OCR_DIGITS[c]);

function snippet(text, at, len = 28) {
  const a = Math.max(0, at - len);
  const b = Math.min(text.length, at + len);
  return (a > 0 ? '…' : '') + text.slice(a, b) + (b < text.length ? '…' : '');
}

// Repairs that need no knowledge of section structure. Returns the new text and a log.
export function repairParagraph(text) {
  const repairs = [];
  const warnings = [];

  // Apply one regex repair at a time so each log entry shows the text before and after.
  const each = (re, kind, fix) => {
    for (let m = re.exec(text); m; m = re.exec(text)) {
      const at = m.index;
      const before = snippet(text, at + 1);
      text = text.slice(0, at) + fix(m) + text.slice(at + m[0].length);
      repairs.push({ kind, before, after: snippet(text, at + 1), probe: text.slice(Math.max(0, at - 10), at + 12) });
      re.lastIndex = 0;
    }
  };

  // Doubled spaces, and leading or trailing space.
  each(/ {2,}/, 'doubled space', () => ' ');
  text = text.trim();

  // Spaced hyphens between letters: "ill - educated" -> "ill-educated".
  each(/(\p{L}) - (?=\p{L})/u, 'spaced hyphen', (m) => m[1] + '-');

  // Drifted closing quotes. Every closing quote that was followed by a space came out
  // as a space plus an opening quote before the next word: "be. ‘Then" for "be.’ Then".
  // Track whether a quotation is open; an opening quote met inside an open quotation,
  // preceded by a space, is the drifted close. One exception: right after a section
  // label ("so be it. 4. ‘Anytus") it is a real opening and the previous close was lost.
  const chars = [...text];
  let open = false;
  let openAt = -1;
  for (let i = 0; i < chars.length; i++) {
    const c = chars[i];
    if (c === OPEN) {
      if (!open) { open = true; openAt = i; continue; }
      const before = chars.slice(0, i).join('');
      if (/(?:^|\s)[\dIl|]{1,3}\. $/.test(before)) {
        warnings.push({
          kind: 'quotation still open at a section label; its closing quote is probably missing',
          at: snippet(text, i),
        });
        openAt = i;
        continue;
      }
      if (chars[i - 1] === ' ' && i >= 2 && chars[i - 2] !== ' ') {
        const ctxBefore = snippet(chars.join(''), i);
        chars[i - 1] = CLOSE;
        chars[i] = ' ';
        const now = chars.join('');
        repairs.push({ kind: 'drifted closing quote', before: ctxBefore, after: snippet(now, i), probe: now.slice(Math.max(0, i - 12), i) });
        open = false;
        continue;
      }
      warnings.push({ kind: 'opening quote inside an open quotation', at: snippet(text, i) });
    } else if (c === CLOSE && open) {
      const next = chars[i + 1];
      const prev = chars[i - 1];
      if (next === undefined || (!LETTER.test(next) && next !== ' ') || (next === ' ' && CLOSE_BEFORE.test(prev ?? ''))) {
        open = false;
      }
    }
  }
  text = chars.join('');
  if (open) {
    warnings.push({ kind: 'paragraph ends inside a quotation; a closing quote may be missing', at: snippet(text, openAt) });
  }

  return { text, repairs, warnings };
}

// Split one chapter into sections. `paragraphs` is the raw array from the extraction.
export function importChapter(chapter, paragraphs) {
  const ch = Number(chapter);
  const repairs = [];
  const warnings = [];
  const sections = [];
  let para = 0;
  let expected = 0; // last section number assigned
  let bareLabelOpen = false; // a paragraph that was only "2." (verse follows)
  let anyInlineLabel = false;

  const kept = [];
  paragraphs.forEach((raw, index) => {
    if (typeof raw !== 'string' || raw.trim() === '') {
      warnings.push({ kind: 'empty paragraph dropped', at: `paragraph ${index + 1}` });
      return;
    }
    const r = repairParagraph(raw);
    for (const x of r.repairs) repairs.push({ ...x, paragraph: index + 1 });
    for (const x of r.warnings) warnings.push({ ...x, paragraph: index + 1 });
    kept.push({ text: r.text, index });
  });

  // A chapter whose later paragraphs carry no section labels at all (and whose first
  // paragraph has no internal label) is split one section per paragraph.
  const labelRe = (n) => new RegExp(`(^|\\s)${n}\\. (?=[A-Z\u2018\u201C])`);
  const anyLabel = /(^|\s)\S{1,3}\. (?=[A-Z\u2018\u201C])|^\S{1,3}\.$/;
  if (kept.length) {
    const firstBody = kept[0].text.replace(/^\d+(\.\d+)?\. /, '');
    anyInlineLabel = labelRe(2).test(firstBody) || kept.slice(1).some((k) => anyLabel.test(k.text));
  }

  const startSection = (paraNo) => {
    expected += 1;
    sections.push({ n: expected, para: paraNo, original: '' });
  };

  // Append text to the current section, splitting at each next label " <n>. ".
  const splitInto = (text, paraNo) => {
    let rest = text;
    for (;;) {
      const m = rest.match(labelRe(expected + 1));
      if (!m) { sections.at(-1).original += rest; return; }
      sections.at(-1).original += rest.slice(0, m.index);
      rest = rest.slice(m.index + m[0].length);
      startSection(paraNo);
    }
  };

  kept.forEach((k, i) => {
    let text = k.text;
    if (i === 0) {
      const lead = text.match(new RegExp(`^${ch}(\\.1)?\\. `));
      if (!lead) throw new Error(`Handbook ${ch}: first paragraph does not start with "${ch}." or "${ch}.1."`);
      text = text.slice(lead[0].length);
      para = 1;
      startSection(para);
      splitInto(text, para);
      return;
    }

    // Bare label paragraph, e.g. "2." standing alone before verse lines.
    const bare = text.match(/^([\dIl|Oo]{1,3})\.$/);
    if (bare && ocrToDigits(bare[1]) === String(expected + 1)) {
      if (bare[1] !== String(expected + 1)) repairs.push({ kind: 'section label misread', before: bare[0], after: `${expected + 1}.`, section: expected + 1, paragraph: k.index + 1 });
      para += 1;
      startSection(para);
      bareLabelOpen = true;
      warnings.push({ kind: 'section label stands alone; the lines that follow are joined to it with line breaks (verse?)', at: `section ${expected}`, paragraph: k.index + 1 });
      return;
    }

    // Paragraph opening with the next section label (allowing OCR misreads like "II.").
    const head = text.match(/^([\dIl|Oo]{1,3})\. (?=[A-Z‘“])/);
    if (head && ocrToDigits(head[1]) === String(expected + 1)) {
      if (head[1] !== String(expected + 1)) {
        repairs.push({ kind: 'section label misread', before: `${head[1]}.`, after: `${expected + 1}.`, section: expected + 1, paragraph: k.index + 1 });
      }
      bareLabelOpen = false;
      para += 1;
      text = text.slice(head[0].length);
      startSection(para);
      splitInto(text, para);
      return;
    }

    if (bareLabelOpen) {
      const s = sections.at(-1);
      s.original += (s.original ? '\n' : '') + text;
      return;
    }

    if (!anyInlineLabel) {
      // The edition does not divide this chapter but it runs to several paragraphs:
      // each paragraph is a section (design.md 9.2, sections[].n).
      para += 1;
      startSection(para);
      splitInto(text, para);
      return;
    }

    warnings.push({ kind: 'paragraph has no section label; joined to the previous section as a new line', at: snippet(text, 0), paragraph: k.index + 1 });
    const s = sections.at(-1);
    s.original += '\n' + text;
  });

  for (const s of sections) {
    s.original = s.original.trim();
    const t = s.original;
    const where = `section ${s.n}`;
    if (t === '') warnings.push({ kind: 'empty section', at: where });
    if (/["']/.test(t)) warnings.push({ kind: 'straight quote left in text', at: `${where}: ${snippet(t, t.search(/["']/))}` });
    if (t.includes('--')) warnings.push({ kind: 'double hyphen', at: where });
    if (t.includes('...')) warnings.push({ kind: 'three full stops', at: where });
    if (/ [-–—] |— | —/.test(t)) warnings.push({ kind: 'spaced dash: check spacing against the book', at: `${where}: ${snippet(t, t.search(/ [-–—] |— | —/))}` });
    if (/ [,.;:?!]/.test(t)) warnings.push({ kind: 'space before punctuation', at: `${where}: ${snippet(t, t.search(/ [,.;:?!]/))}` });
    if (/:$/.test(t)) warnings.push({ kind: 'section ends with a colon: quoted text may be missing from the extraction', at: where });
    if (/^\[.*\]$/.test(t)) warnings.push({ kind: 'section is an editorial note, not text', at: where });
  }

  // Attach a section number to each repair by finding its repaired text.
  for (const r of repairs) {
    if (!r.section && r.probe) {
      const probes = [r.probe, r.probe.slice(0, 13), r.probe.slice(-12)].map((x) => x.trim()).filter(Boolean);
      const hit = probes.map((p) => sections.find((s) => s.original.includes(p))).find(Boolean);
      if (hit) r.section = hit.n;
    }
    delete r.probe;
  }

  return { chapter: ch, sections, repairs, warnings };
}

export function skeleton(imported) {
  return {
    schema: 1,
    book: 'epictetus',
    work: 'handbook',
    part: null,
    chapter: imported.chapter,
    title: '',
    titleBy: 'editor',
    setting: null,
    themes: [],
    sections: imported.sections.map((s) => ({ n: s.n, para: s.para, original: s.original, modern: '' })),
    glosses: {},
    takeaway: '',
    carry: '',
    questions: [],
    exercises: [],
    objection: null,
    prompts: [],
    seeAlso: [],
    compare: null,
  };
}

export function importAll(data, chapters) {
  const keys = chapters ?? Object.keys(data).map(Number).sort((a, b) => a - b);
  return keys.map((n) => {
    if (!(String(n) in data)) throw new Error(`chapter ${n} not in input`);
    return importChapter(n, data[String(n)]);
  });
}

export function report(results) {
  const out = [];
  let nRep = 0;
  let nWarn = 0;
  for (const r of results) {
    if (!r.repairs.length && !r.warnings.length) continue;
    out.push(`Handbook ${r.chapter}`);
    for (const x of r.repairs) {
      nRep += 1;
      const where = x.section ? `${r.chapter}.${x.section}` : `paragraph ${x.paragraph}`;
      out.push(`  repair  ${where}  ${x.kind}`);
      out.push(`          before: ${x.before}`);
      out.push(`          after:  ${x.after}`);
    }
    for (const w of r.warnings) {
      nWarn += 1;
      out.push(`  check   ${w.kind}${w.at ? `  (${w.at})` : ''}`);
    }
  }
  out.push(`${results.length} chapters, ${nRep} repairs, ${nWarn} things to check by hand.`);
  return out.join('\n');
}

function parseChapters(spec) {
  const set = new Set();
  for (const part of spec.split(',')) {
    const m = part.trim().match(/^(\d+)(?:-(\d+))?$/);
    if (!m) throw new Error(`bad --chapters value: ${part}`);
    const a = Number(m[1]);
    const b = m[2] ? Number(m[2]) : a;
    for (let n = a; n <= b; n++) set.add(n);
  }
  return [...set].sort((x, y) => x - y);
}

function main(argv) {
  const args = argv.slice(2);
  let input = process.env.READING_HARD_JSON;
  let out = null;
  let chapters = null;
  let force = false;
  for (let i = 0; i < args.length; i++) {
    const a = args[i];
    if (a === '--out') out = args[++i];
    else if (a === '--chapters') chapters = parseChapters(args[++i]);
    else if (a === '--force') force = true;
    else if (a === '-h' || a === '--help') {
      console.log('node tools/import-hard.mjs <hard.json> [--chapters 1-5] [--out dir] [--force]');
      return 0;
    } else input = a;
  }
  if (!input) {
    console.error('No input file. Pass the path or set READING_HARD_JSON.');
    return 2;
  }
  const data = JSON.parse(readFileSync(input, 'utf8'));
  const results = importAll(data, chapters);
  console.log(report(results));
  if (out) {
    mkdirSync(out, { recursive: true });
    for (const r of results) {
      const file = join(out, `${String(r.chapter).padStart(3, '0')}.json`);
      if (existsSync(file) && !force) {
        console.log(`exists, not overwritten: ${file}`);
        continue;
      }
      writeFileSync(file, JSON.stringify(skeleton(r), null, 2) + '\n');
      console.log(`wrote ${file}`);
    }
  }
  return 0;
}

if (import.meta.url === pathToFileURL(resolve(process.argv[1] ?? '')).href) {
  process.exitCode = main(process.argv);
}
