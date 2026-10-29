import { test } from 'node:test';
import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { Group } from 'three';
import { SOURCE, placements, meshBytes } from './helpers.mjs';
import { decodeMeshes } from '../src/meshes.js';
import { evaluate } from '../src/timeline.js';
import { polyLength } from '../src/cablepath.js';
import { PORTS, CONNECTORS } from '../src/ports.js';
import { buildSoyrackTimeline, SoyrackStage } from '../src/soyrack/index.js';
import { VIEWS } from '../src/soyrack/stage.js';
import { CABLES, CABLE_BY_ID, MAST_RUN, TIES } from '../src/soyrack/cables.js';
import { DEVICES, DEVICE_BY_ID, FLOOR_Z } from '../src/soyrack/rack.js';
import { BUY, PRINTED, TEST_PRINTS } from '../src/soyrack/sheet.js';

const v3Meshes = decodeMeshes(new Uint8Array(readFileSync(resolve(SOURCE, 'data/v3/meshes.bin'))));
const meshes = { ...decodeMeshes(meshBytes), ...v3Meshes };
const tl = buildSoyrackTimeline(meshes, placements);
const shown = [...tl.nodes.values()].filter((n) => n.kind !== 'group');
const TEST_PIECE = /^coupon\./;
const STL_DIR = resolve(SOURCE, '../cad/stl');

// Contract: every chapter can be followed and frames its own view. A misspelt view name would
// silently fall back to the whole-rack framing.
test('v3 chapters tile the timeline and each frames its own view', () => {
  const stage = new SoyrackStage(tl, new Group());
  assert.equal(tl.chapters[0].start, 0);
  for (const c of tl.chapters) {
    if (c.index > 0) assert.equal(c.start, tl.chapters[c.index - 1].end);
    assert.ok(c.end - c.start >= 4.5, `${c.title} long enough to follow`);
    assert.ok(VIEWS[c.view], `${c.id} names a framed view`);
    stage.setTime((c.start + c.end) / 2);
    assert.equal(stage.camera().key, c.view);
  }
  assert.equal(tl.chapters.at(-1).end, tl.duration);
});

test('v3 builds deterministically and retraces arbitrary seeks', () => {
  const again = buildSoyrackTimeline(meshes, placements);
  assert.deepEqual(again.chapters.map((c) => [c.id, c.start, c.end]), tl.chapters.map((c) => [c.id, c.start, c.end]));
  const times = [0, 9.5, 33, 61.2, 97.4, 120, 141, tl.duration];
  const forward = times.map((t) => evaluate(tl, t));
  for (let i = times.length - 1; i >= 0; i--) assert.deepEqual(evaluate(again, times[i]), forward[i]);
});

// Contract: the test pieces are shown alone first and are gone before the base arrives; the
// finished rack shows every part, fastener and device at rest in its place.
test('v3 opens with the test prints alone and ends with everything else in place', () => {
  const start = evaluate(tl, 0);
  assert.deepEqual(shown.filter((n) => start.get(n.id).alpha > 0.01).map((n) => n.id).sort(),
    ['coupon.corner', 'coupon.keystone', 'coupon.nut', 'coupon.post']);
  const base = evaluate(tl, tl.chapters.find((c) => c.id === 'power-base').start);
  for (const n of shown.filter((n) => TEST_PIECE.test(n.id))) assert.ok(base.get(n.id).alpha < 0.01, `${n.id} cleared away`);
  const end = evaluate(tl, tl.duration);
  for (const n of shown.filter((n) => !TEST_PIECE.test(n.id))) {
    const s = end.get(n.id);
    assert.ok(s.alpha > 0.999, `${n.id} shown at the end`);
    assert.ok(s.glow < 1e-6, `${n.id} settled at the end`);
    for (let k = 0; k < 3; k++) assert.ok(Math.abs(s.p[k] - n.final.p[k]) < 1e-6, `${n.id} in place`);
  }
});

// Contract: each part of a cord, and each strap, appears with the chapter that lays it, never
// earlier, and stays.
test('cords and straps fade in with the chapter that lays them', () => {
  const stage = new SoyrackStage(tl, new Group());
  assert.equal(stage.leads.length, CABLES.reduce((n, c) => n + c.parts.length, 0));
  assert.equal(stage.ties.length, TIES.length);
  for (const [i, item] of [...stage.leads, ...stage.ties].entries()) {
    const what = item.cable ? item.cable.id : `strap ${i}`;
    stage.setTime(item.chapter.start - 0.5);
    assert.equal(item.object.visible, false, `${what} hidden before ${item.chapter.id}`);
    stage.setTime(item.chapter.end);
    assert.ok(item.object.visible && item.alpha === 1, `${what} shown once ${item.chapter.id} ends`);
  }
  stage.setTime(tl.duration);
  assert.ok([...stage.leads, ...stage.ties].every((l) => l.object.visible));
});

// Contract: stock cords are drawn at their real length, plug bodies included. The spare is wound
// into loops, never cut short. The Zigbee extension carries on inside its mast to the socket.
const REAL_MM = { mains: 1000, dc: 1800, switchPower: 1500, usb: 460, zigbee: 1500 };
const stockKind = (id) => (/^usb[A-Z]/.test(id) ? 'usb' : id.replace(/\d+$/, ''));
const drawnLength = (cable) => cable.parts.reduce((s, p) => s + polyLength(p.points), 0);
const fullLength = (cable) => drawnLength(cable)
  + cable.parts.flatMap((p) => p.plugs).reduce((s, p) => s + CONNECTORS[p.type].len, 0)
  + (cable.id === 'zigbee' ? MAST_RUN + CONNECTORS.usbAf.len : 0);

test('every stock cord is drawn at its full length', () => {
  const stock = CABLES.filter((c) => REAL_MM[stockKind(c.id)]);
  assert.equal(stock.length, 10, 'three mains, three Lenovo, the switch, two drive leads and the extension');
  for (const cable of stock) {
    const full = fullLength(cable);
    assert.ok(Math.abs(full - REAL_MM[stockKind(cable.id)]) < 2, `${cable.id} is ${full.toFixed(1)} mm`);
  }
});

// Contract: no cord runs through another.
test('cords never pass through each other', () => {
  const CELL = 8;
  const grid = new Map();
  const samples = [];
  for (const cable of CABLES) {
    for (const { points } of cable.parts) {
      for (let i = 1; i < points.length; i++) {
        const [a, b] = [points[i - 1], points[i]];
        const n = Math.max(1, Math.ceil(Math.hypot(b[0] - a[0], b[1] - a[1], b[2] - a[2]) / 1.5));
        for (let k = 0; k < n; k++) samples.push({ cable, p: a.map((v, j) => v + ((b[j] - v) * k) / n) });
      }
    }
  }
  const cell = (p) => p.map((v) => Math.floor(v / CELL));
  for (const s of samples) {
    const key = cell(s.p).join();
    if (!grid.has(key)) grid.set(key, []);
    grid.get(key).push(s);
  }
  for (const s of samples) {
    const [i, j, k] = cell(s.p);
    for (let a = -1; a <= 1; a++) for (let b = -1; b <= 1; b++) for (let c = -1; c <= 1; c++) {
      for (const o of grid.get([i + a, j + b, k + c].join()) || []) {
        if (o.cable.id <= s.cable.id) continue;
        const gap = Math.hypot(o.p[0] - s.p[0], o.p[1] - s.p[1], o.p[2] - s.p[2]) - (o.cable.od + s.cable.od) / 2;
        assert.ok(gap > -0.05, `${s.cable.id} and ${o.cable.id} overlap at ${s.p.map((v) => v.toFixed(0))}`);
      }
    }
  }
});

// Contract: everything in the rack that needs power or data is plugged in, and no port takes
// two plugs.
test('every power inlet, drive and node network port takes exactly one lead', () => {
  const ends = CABLES.flatMap((c) => c.ends).filter(Boolean);
  assert.equal(new Set(ends).size, ends.length, 'no port takes two plugs');
  const needed = DEVICES.flatMap((d) => Object.entries(PORTS[d.model] || {})
    .filter(([id, p]) => id === 'power' || ['barrel', 'c5', 'microB3'].includes(p.type) || (d.model === 'm920q' && id === 'rj45'))
    .map(([id]) => `${d.id}.${id}`));
  assert.ok(needed.length >= 12);
  for (const port of needed) assert.ok(ends.includes(port), `${port} is connected`);
});

// Contract: the buy list covers every fastener the scene installs. The node trays carry over
// with their own screws, so only the new M4 screws are bought.
test('the buy list covers every fastener and lead the rack installs', () => {
  const count = (mesh, keep = () => true) => shown.filter((n) => n.mesh === mesh && keep(n)).length;
  const bought = (key) => BUY.find((b) => b.key === key).quantity;
  assert.ok(bought('rod') >= count('m5rod') && count('m5rod') === 4);
  assert.ok(bought('coupler') >= count('m5coupler'));
  assert.ok(bought('capscrew') >= count('m5x50') && count('m5x50') === 4);
  assert.ok(bought('nut') >= Math.max(count('m5nut'), count('m5washer')));
  assert.ok(bought('insert') >= count('m4x12'), 'one insert per M4 hole');
  assert.ok(bought('m4') >= count('m4x12', (n) => !n.id.startsWith('tray.')));
  assert.ok(bought('pad') >= count('foot'));
  assert.ok(bought('keystone') >= DEVICES.filter((d) => d.model === 'keystone').length);
  assert.ok(bought('strap') >= TIES.length);
});

// Contract: the reason for the mast. The dongle stays at least 1 m from every node USB 3 port,
// on the 1.5 m USB 2 extension the buy list names.
test('the Zigbee dongle stands 1 m from the USB 3 ports on its extension', () => {
  const dongle = DEVICE_BY_ID.dongle;
  const gap = (p) => Math.hypot(p[0] - dongle.centre[0], p[1] - dongle.centre[1], p[2] - dongle.centre[2]);
  for (const d of DEVICES.filter((d) => d.model === 'm920q')) {
    for (const [id, p] of Object.entries(PORTS.m920q).filter(([, p]) => p.type === 'usbA')) {
      assert.ok(gap(p.pos.map((v, k) => v + d.centre[k])) >= 1000, `${d.id}.${id}`);
    }
  }
  assert.ok(Math.abs(fullLength(CABLE_BY_ID.zigbee) - BUY.find((b) => b.key === 'extension').length) < 2);
});

// Contract: the rack keeps to the space agreed for the TV unit top: 260 x 240 mm, 450 mm tall.
test('the assembled rack stays inside its 260 x 240 x 450 mm space', () => {
  const lo = [Infinity, Infinity, Infinity];
  const hi = [-Infinity, -Infinity, -Infinity];
  for (const n of shown.filter((n) => n.kind === 'part' && v3Meshes[n.mesh] && !TEST_PIECE.test(n.id) && n.id !== 'zigbee_mast')) {
    const size = v3Meshes[n.mesh].size; // parts sit square or turned half a turn about z
    for (let k = 0; k < 3; k++) {
      lo[k] = Math.min(lo[k], n.final.p[k] - size[k] / 2);
      hi[k] = Math.max(hi[k], n.final.p[k] + size[k] / 2);
    }
  }
  assert.ok(hi[0] - lo[0] <= 260 && hi[1] - lo[1] <= 240, `footprint ${hi[0] - lo[0]} x ${hi[1] - lo[1]}`);
  assert.ok(lo[2] >= FLOOR_Z && hi[2] - FLOOR_Z <= 450, `height ${hi[2] - FLOOR_Z}`);
});

function stlBounds(bytes) {
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  const triangles = view.getUint32(80, true);
  assert.equal(bytes.byteLength, 84 + 50 * triangles, 'binary STL');
  const lo = [Infinity, Infinity, Infinity];
  const hi = [-Infinity, -Infinity, -Infinity];
  for (let t = 0; t < triangles; t++) {
    for (let v = 0; v < 3; v++) {
      for (let k = 0; k < 3; k++) {
        const x = view.getFloat32(84 + t * 50 + 12 + v * 12 + k * 4, true);
        lo[k] = Math.min(lo[k], x);
        hi[k] = Math.max(hi[k], x);
      }
    }
  }
  return { lo, hi };
}

// Contract: every file the parts sheet links exists, fits a 256 mm bed and lies on it as
// printed. The image build copies only app/, so this runs from the repository checkout.
test('every printed part has an STL that fits the bed and lies on it', { skip: !existsSync(STL_DIR) && 'outside the repository checkout' }, () => {
  for (const { part } of [...PRINTED, ...TEST_PRINTS]) {
    const file = resolve(STL_DIR, `${part}.stl`);
    assert.ok(existsSync(file), `${part}.stl exists`);
    const { lo, hi } = stlBounds(new Uint8Array(readFileSync(file)));
    for (let k = 0; k < 3; k++) assert.ok(hi[k] - lo[k] <= 256, `${part} fits the bed on axis ${k}`);
    assert.ok(Math.abs(lo[2]) < 0.01, `${part} lies on the bed`);
  }
});
