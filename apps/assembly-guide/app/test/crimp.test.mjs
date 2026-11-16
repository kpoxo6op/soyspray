import { test } from 'node:test';
import assert from 'node:assert/strict';
import { meshes } from './helpers.mjs';
import { evaluate } from '../src/timeline.js';
import { buildSoyrackTimeline } from '../src/soyrack/index.js';
import { CRIMP_IDS, LEADS, WORK } from '../src/soyrack/crimp.js';
import {
  BOOT_ON, BOOT_PARKED, JACKET_END, LAMP_PATTERNS, PLUG, T568B, TRIM, TRIM_TIP, wirePaths,
} from '../src/soyrack/crimp-layout.js';
import { CONNECTORS } from '../src/ports.js';

const tl = buildSoyrackTimeline(meshes);
const chapter = (id) => tl.chapters.find((c) => c.id === id);
const at = (id, t) => evaluate(tl, t).get(id);
const onCable = (p) => p.map((v, k) => v - WORK[k]);
const near = (a, b, what, tol = 1e-6) => a.forEach((v, k) => assert.ok(Math.abs(v - b[k]) < tol, `${what}: ${a} vs ${b}`));

// Contract: the order the guide teaches is T568B, pin 1 to pin 8.
test('the wire order is T568B', () => {
  assert.deepEqual(T568B.map((w) => w.name), ['white-orange', 'orange', 'white-green', 'blue', 'white-blue', 'green', 'white-brown', 'brown']);
});

// Contract: with the contacts up and the clip down, looking along the cable to its cut end, pin 1 is
// on the left. The trimmed row lies flat in that order, 13 mm out of the jacket and level.
test('the trimmed row reads left to right in order, level, 13 mm out of the jacket', () => {
  const row = wirePaths('trimmed');
  const tips = row.map((w) => w.points.at(-1));
  for (let i = 1; i < tips.length; i++) assert.ok(tips[i][0] > tips[i - 1][0], `${row[i].wire.name} right of ${row[i - 1].wire.name}`);
  for (const t of tips) assert.ok(Math.abs(t[1] - TRIM_TIP) < 1e-9 && Math.abs(t[2]) < 1e-9, 'level and flat');
  assert.equal(TRIM_TIP - JACKET_END, TRIM);
  for (const w of row) assert.ok(Math.abs(w.points[0][1] - JACKET_END) <= 0.5 + 1e-9, `${w.wire.name} leaves the jacket`);
});

// Contract: the boot goes on before the plug and only reaches the plug after the crimp.
test('the boot is on the cable before the plug, and over the plug only after the crimp', () => {
  const boot = (t) => onCable(at('crimp.boot', t).p);
  near(boot(chapter('crimp-plug').start), [0, BOOT_PARKED, 0], 'boot parked before the plug goes on');
  assert.ok(BOOT_PARKED + 0 < PLUG.rear - 20, 'parked well clear of the plug');
  near(boot(chapter('crimp-press').end - 0.01), [0, BOOT_PARKED, 0], 'still parked through the crimp');
  near(boot(chapter('crimp-boot-on').end - 0.01), [0, BOOT_ON, 0], 'over the back of the plug at the end');
  assert.ok(BOOT_ON > PLUG.rear && BOOT_ON < PLUG.rear + 10, 'covers the back of the plug');
});

// Contract: the plug ends with all eight wire ends at its end wall and the jacket inside it, and the
// contacts go down only when the crimper closes.
test('the plug seats on the trimmed row and its contacts go down in the crimp', () => {
  near(onCable(at('crimp.plugG', chapter('crimp-plug').end - 0.01).p), [0, PLUG.front, 0], 'plug seated');
  assert.ok(PLUG.front - TRIM_TIP > 0 && PLUG.front - TRIM_TIP < 1.5, 'wire ends at the end wall');
  assert.ok(PLUG.rear < JACKET_END - 5, 'jacket well inside the plug');
  const pins = (t) => at('crimp.pins', t).p[2];
  assert.ok(Math.abs(pins(chapter('crimp-check').end - 0.01) - PLUG.pinLift) < 1e-6, 'contacts up before the crimp');
  assert.ok(Math.abs(pins(chapter('crimp-press').end - 0.01)) < 1e-6, 'contacts down after it');
});

// Contract: the lamps follow the kit leaflet: a good lead steps 1-8 on both units together with the
// remote's G dark on unshielded cable; an open line is dark on both; two swapped lines show the
// remote out of order; a short lights two remote lamps faintly.
test('the tester lamps follow the leaflet', () => {
  const remoteOrder = (p) => p.map((s) => s.remote);
  assert.deepEqual(remoteOrder(LAMP_PATTERNS.good), [[0], [1], [2], [3], [4], [5], [6], [7], []]);
  assert.deepEqual(LAMP_PATTERNS.good.map((s) => s.main), [0, 1, 2, 3, 4, 5, 6, 7, 8]);
  assert.deepEqual(LAMP_PATTERNS.open3[2], { main: null, remote: [], dim: false });
  assert.deepEqual(remoteOrder(LAMP_PATTERNS.swap24).slice(0, 4).map((r) => r[0] + 1), [1, 4, 3, 2]);
  const shorts = LAMP_PATTERNS.short45.filter((s) => s.dim);
  assert.deepEqual(shorts.map((s) => [s.main, s.remote]), [[3, [3, 4]], [4, [3, 4]]]);
});

// Contract: each lead is cut long enough for its route, both plugs and boots, and the trim at each end.
test('every cut length covers its route, its plugs and the trim', () => {
  for (const l of LEADS) {
    assert.ok(l.finished >= l.route + 2 * CONNECTORS.rj45.len, `${l.name} long enough when done`);
    assert.ok(l.finished >= 150, `${l.name} long enough to hold while crimping`);
    assert.ok(l.cut >= l.finished + 2 * (-JACKET_END - TRIM), `${l.name} allows for the trim`);
  }
  const text = chapter('crimp-plan').text;
  for (const l of LEADS) assert.match(text, new RegExp(`${l.cut / 10} cm`));
});

// Contract: the mat and the kit appear with the crimping section and are cleared before the leads go in.
test('the crimping section clears its mat before the leads go into the rack', () => {
  const crimp = [...tl.nodes.values()].filter((n) => n.kind !== 'group' && CRIMP_IDS.test(n.id));
  const before = evaluate(tl, chapter('crimp-plan').start - 0.7);
  const after = evaluate(tl, chapter('ethernet').start);
  for (const n of crimp) {
    assert.ok(before.get(n.id).alpha < 0.01, `${n.id} hidden before the section`);
    assert.ok(after.get(n.id).alpha < 0.01, `${n.id} cleared before the leads go in`);
  }
  const crimpChapters = tl.chapters.filter((c) => c.id.startsWith('crimp-'));
  assert.equal(crimpChapters.at(-1).index + 1, chapter('ethernet').index, 'the leads go in right after');
});
