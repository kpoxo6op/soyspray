// Content contracts: every stitch, chapter, fabric, project and problem is complete in both
// languages and every cross-reference points at something that exists.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { STITCHES, CATEGORIES, TASKS, FABRICS, byNo } from '../src/data/stitches.js';
import { PROCEDURES } from '../src/data/procedures.js';
import { PARTS, partById } from '../src/data/parts.js';
import { FABRIC_LIST } from '../src/data/fabrics.js';
import { PROJECTS } from '../src/data/projects.js';
import { PROBLEMS } from '../src/data/troubleshooting.js';
import { CAMERAS } from '../src/machine3d.js';

const bilingual = (rec, where) => {
  assert.ok(rec && typeof rec.en === 'string' && rec.en.trim(), `${where}: en`);
  assert.ok(typeof rec.ru === 'string' && rec.ru.trim(), `${where}: ru`);
};
const FEET = new Set(['0A', '1A', '2A', '3', '4', '5B', 'none']);

test('all 100 stitches are present once, numbered 00-99, bilingual and sewable', () => {
  assert.equal(STITCHES.length, 100);
  STITCHES.forEach((s, i) => {
    assert.equal(s.no, i);
    bilingual(s.name, `stitch ${i} name`);
    if (s.manual) bilingual(s.manual, `stitch ${i} manual`);
    assert.ok(CATEGORIES.some((c) => c.id === s.cat), `stitch ${i} category`);
    assert.ok(FEET.has(String(s.foot)), `stitch ${i} foot ${s.foot}`);
    assert.equal(typeof s.idt, 'boolean');
    assert.ok(s.uses.length >= 1, `stitch ${i} has a use`);
    for (const u of s.uses) {
      bilingual(u, `stitch ${i} use`);
      for (const f of u.fabrics) assert.ok(FABRICS.includes(f), `stitch ${i} fabric ${f}`);
    }
    for (const tip of s.tips) bilingual(tip, `stitch ${i} tip`);
    assert.ok(s.geom && ['line', 'satin', 'motif'].includes(s.geom.kind), `stitch ${i} geometry`);
    assert.ok(s.width.max <= 7 && s.width.def <= s.width.max && s.width.def >= s.width.min, `stitch ${i} width`);
    assert.ok(s.length.max <= 4.5 && s.length.def <= s.length.max && s.length.def >= s.length.min, `stitch ${i} length`);
  });
});

test('the manual names utility stitches 00-21 and marks IDT and feet as the manual does', () => {
  for (let i = 0; i <= 21; i++) assert.equal(STITCHES[i].official, true, `stitch ${i} official`);
  for (let i = 22; i <= 99; i++) assert.equal(STITCHES[i].official, false);
  assert.equal(byNo(0).name.en, 'Straight stitch');
  assert.equal(byNo(5).name.en, 'Three-step zigzag stitch');
  assert.equal(byNo(10).name.en, 'Blindhem stitch');
  assert.equal(byNo(10).foot, '3');
  for (const n of [16, 17, 18, 19]) assert.equal(byNo(n).foot, '5B');
  for (const n of [16, 17, 18, 19, 20, 21]) assert.equal(byNo(n).idt, false, `buttonhole ${n} without IDT`);
  for (const n of [59, 60, 61]) assert.equal(byNo(n).wing, true);
  for (let n = 67; n <= 79; n++) assert.equal(byNo(n).foot, '2A', `satin ${n} uses 2A`);
  for (const s of STITCHES) if (s.foot === '2A' || s.foot === '5B') assert.equal(s.idt, false, `${s.no}: IDT off with 2A/5B`);
});

test('tasks point at real stitches and cover the fabrics', () => {
  for (const tk of TASKS) {
    bilingual(tk.name, `task ${tk.id}`);
    for (const n of tk.nos) assert.ok(byNo(n), `task ${tk.id} stitch ${n}`);
  }
  for (const f of FABRICS) assert.ok(STITCHES.some((s) => s.uses.some((u) => u.fabrics.includes(f))), `fabric ${f} has stitches`);
});

test('chapters: bilingual steps, known camera presets, known parts, animation keys are numbers', () => {
  const ids = new Set();
  for (const p of PROCEDURES) {
    assert.ok(!ids.has(p.id));
    ids.add(p.id);
    bilingual(p.title, p.id);
    bilingual(p.intro, p.id);
    assert.ok(p.steps.length >= 3, `${p.id} steps`);
    for (const s of p.steps) {
      bilingual(s.text, `${p.id} step`);
      if (s.check) bilingual(s.check, `${p.id} check`);
      assert.ok(CAMERAS[s.cam], `${p.id}: camera ${s.cam}`);
      for (const id of s.parts || []) assert.ok(partById(id), `${p.id}: part ${id}`);
      for (const [k, val] of Object.entries(s.anim || {})) assert.equal(typeof val, 'number', `${p.id}: anim ${k}`);
    }
  }
  for (const id of ['power', 'spool', 'wind', 'bobbin', 'thread', 'threader', 'first-seam', 'idt', 'foot', 'needle', 'feed-dogs', 'buttonhole', 'clean', 'pack']) assert.ok(ids.has(id), `chapter ${id}`);
});

test('parts: the manual numbers 1-34 are all present with a hotspot position', () => {
  const nos = PARTS.filter((p) => p.no != null).map((p) => p.no).sort((a, b) => a - b);
  assert.deepEqual(nos, Array.from({ length: 34 }, (_, i) => i + 1));
  for (const p of PARTS) {
    bilingual(p.name, p.id);
    bilingual(p.what, p.id);
    assert.equal(p.at.length, 3);
  }
});

test('fabrics, projects and problems are complete and cross-linked', () => {
  for (const f of FABRIC_LIST) {
    assert.ok(FABRICS.includes(f.id));
    bilingual(f.name, f.id);
    bilingual(f.needle, f.id);
    bilingual(f.pressure, f.id);
    for (const k of ['seam', 'edge', 'hem']) assert.ok(byNo(f[k].no), `${f.id} ${k}`);
    for (const k of ['seamAlt', 'edgeAlt', 'hemAlt']) for (const n of f[k] || []) assert.ok(byNo(n));
    assert.ok(f.notes.length);
    f.notes.forEach((n) => bilingual(n, f.id));
  }
  assert.equal(PROJECTS.length, 4);
  for (const p of PROJECTS) {
    bilingual(p.title, p.id);
    bilingual(p.teaches, p.id);
    assert.ok(FABRIC_LIST.some((f) => f.id === p.fabric), `${p.id} fabric`);
    p.need.forEach((n) => bilingual(n, p.id));
    p.steps.forEach((n) => bilingual(n, p.id));
    assert.ok(p.steps.length >= 4);
    for (const s of p.settings) {
      bilingual(s.label, p.id);
      if (s.no != null) assert.ok(byNo(s.no), `${p.id} setting ${s.no}`);
      else assert.ok(s.text);
    }
    for (const n of p.stitchLinks) assert.ok(byNo(n));
  }
  const sections = { stitches: (id) => byNo(Number(id)), machine: (id) => PROCEDURES.some((p) => p.id === id), fabrics: (id) => !id || FABRIC_LIST.some((f) => f.id === id) };
  assert.ok(PROBLEMS.length >= 10);
  for (const p of PROBLEMS) {
    bilingual(p.title, p.id);
    bilingual(p.looks, p.id);
    bilingual(p.why, p.id);
    assert.ok(p.fixes.length >= 2);
    for (const f of p.fixes) {
      bilingual(f, p.id);
      if (f.link) assert.ok(sections[f.link[0]] && sections[f.link[0]](f.link[1]), `${p.id}: link ${f.link.join('/')}`);
    }
  }
  assert.ok(PROBLEMS.some((p) => p.id === 'tunneling'), 'the silk zigzag problem is covered');
});
