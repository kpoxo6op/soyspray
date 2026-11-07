import { test } from 'node:test';
import assert from 'node:assert/strict';
import { Group } from 'three';
import { meshes, rackMeshes } from './helpers.mjs';
import { evaluate } from '../src/timeline.js';
import { polyLength } from '../src/cablepath.js';
import { PORTS, CONNECTORS } from '../src/ports.js';
import { buildSoyrackTimeline, SoyrackStage } from '../src/soyrack/index.js';
import { VIEWS } from '../src/soyrack/stage.js';
import { CABLES, CABLE_BY_ID, MAST_RUN, TIES } from '../src/soyrack/cables.js';
import { DEVICES, DEVICE_BY_ID, FLOOR_Z } from '../src/soyrack/rack.js';
import { BUY, PRINTED, TEST_PRINTS, soyrackSheetHTML } from '../src/soyrack/sheet.js';
import { PIECES, HOLES, JOINT, FOOT_TOP, BASE_NUT, NUT_Y, WINDOWS, onPiece } from '../src/soyrack/testprints.js';

const tl = buildSoyrackTimeline(meshes);
const shown = [...tl.nodes.values()].filter((n) => n.kind !== 'group');
const TEST_PIECE = /^coupon\./;

// Contract: every chapter can be followed and frames its own view. A misspelt view name would
// silently fall back to the whole-rack framing.
test('chapters tile the timeline and each frames its own view', () => {
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

test('the guide builds deterministically and retraces arbitrary seeks', () => {
  const again = buildSoyrackTimeline(meshes);
  assert.deepEqual(again.chapters.map((c) => [c.id, c.start, c.end]), tl.chapters.map((c) => [c.id, c.start, c.end]));
  const times = [0, 9.5, 33, 61.2, 97.4, 120, 141, tl.duration];
  const forward = times.map((t) => evaluate(tl, t));
  for (let i = times.length - 1; i >= 0; i--) assert.deepEqual(evaluate(again, times[i]), forward[i]);
});

// Contract: the test pieces are shown alone first and are gone before the base arrives; the
// finished rack shows every part, fastener and device at rest in its place.
test('the guide opens with the test prints alone and ends with everything else in place', () => {
  const start = evaluate(tl, 0);
  assert.deepEqual(shown.filter((n) => start.get(n.id).alpha > 0.01).map((n) => n.id).sort(),
    ['coupon.base', 'coupon.corner', 'coupon.keystone', 'coupon.post']);
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

// Contract: the checks are drawn on the printed test pieces, and each ends with its hardware
// where the fit is tested: the deck corner on the base corner and the post end in its pocket, the
// nut at the end of the base corner's slot with the corner screw down through all three into it,
// a nut behind each tray hole with a screw from the front through it, and a coupler in each window
// of the strip.
const near = (a, b, what) => a.forEach((v, k) => assert.ok(Math.abs(v - b[k]) < 1e-6, `${what}: ${a} vs ${b}`));
const poseAt = (id, chapter) => evaluate(tl, tl.chapters.find((c) => c.id === chapter).end - 0.01).get(id);
const offset = (a, b) => PIECES[a].centre.map((v, k) => v - PIECES[b].centre[k]);

test('each test-print check ends with its hardware where the fit is tested', () => {
  for (const { part, centre, size } of Object.values(PIECES)) {
    near(rackMeshes[part].centre, centre, `${part} centre`);
    near(rackMeshes[part].size, size, `${part} size`);
  }
  const pose = (piece, chapter) => poseAt(PIECES[piece].id, chapter);

  const base = pose('base', 'test-joint');
  const corner = pose('corner', 'test-joint');
  const post = pose('post', 'test-joint');
  near(corner.p, base.p.map((v, k) => v + offset('corner', 'base')[k]), 'deck corner on the base corner');
  near(post.p, corner.p.map((v, k) => v + offset('post', 'corner')[k]), 'post end in the pocket');
  const nut = onPiece('base', base, [...JOINT, BASE_NUT]);
  near(poseAt('coupon.nut', 'test-joint').p, nut, 'nut at the end of its slot');
  const bolt = poseAt('coupon.bolt', 'test-joint');
  near(bolt.p, onPiece('post', post, [...JOINT, FOOT_TOP]), 'screw head on the foot');
  assert.ok(bolt.p[2] - 25 < nut[2], 'screw down through the nut');

  const lastPost = pose('post', 'test-tray-nuts');
  HOLES.forEach(([x, y, z], i) => {
    const behind = onPiece('post', lastPost, [x, NUT_Y, z]);
    near(poseAt(`coupon.tnut${i + 1}`, 'test-tray-nuts').p, behind, `nut behind hole ${i + 1}`);
    const screw = poseAt(`coupon.m4${'ab'[i]}`, 'test-tray-nuts');
    near(screw.p, onPiece('post', lastPost, [x, y - 2, z]), `screw on hole ${i + 1}`);
    assert.ok(screw.p[1] + 12 > behind[1] + 3.2, `screw ${i + 1} through its nut`);
  });

  const strip = pose('keystone', 'test-keystone');
  WINDOWS.forEach((w, i) => near(poseAt(['coupon.key24', 'coupon.key20'][i], 'test-keystone').p, onPiece('keystone', strip, w), `coupler ${i + 1} seated`));
});

// Contract: a tag names something that is on screen while the tag shows, inside its chapter.
test('tags point at parts that are on screen while they show', () => {
  const tagged = tl.chapters.filter((c) => c.tags.length);
  assert.ok(tagged.length >= 5, 'the test-print chapters name their pieces and hardware');
  for (const c of tagged) {
    for (const tag of c.tags) {
      const from = c.start + (tag.from ?? 0.4);
      const until = tag.until == null ? c.end : c.start + tag.until;
      assert.ok(from < until && until <= c.end + 1e-9, `${tag.text} shows within ${c.id}`);
      assert.ok(tl.nodes.has(tag.node), `${tag.text} names ${tag.node}`);
      assert.ok(evaluate(tl, (from + until) / 2).get(tag.node).alpha > 0.5, `${tag.node} on screen for ${tag.text}`);
    }
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

// Contract: the rack goes together with M4 screws and nuts only, and every screw finds its own
// nut: each one has exactly one M4 nut on its axis within its length, and no nut is left over.
test('every rack screw meets its own nut', () => {
  const rack = shown.filter((n) => n.kind === 'screw' && !TEST_PIECE.test(n.id));
  assert.deepEqual([...new Set(rack.map((n) => n.mesh))].sort(), ['m4nut', 'm4x12', 'm4x25']);
  const nuts = rack.filter((n) => n.mesh === 'm4nut');
  const LENGTH = { m4x12: 12, m4x25: 25 };
  const used = new Set();
  for (const s of rack.filter((n) => n.mesh !== 'm4nut')) {
    const hits = nuts.filter((nut) => {
      const d = nut.final.p.map((v, k) => v - s.final.p[k]);
      const t = d[0] * s.dir[0] + d[1] * s.dir[1] + d[2] * s.dir[2];
      return Math.hypot(...d.map((v, k) => v - t * s.dir[k])) < 0.3 && t > 0 && t < LENGTH[s.mesh];
    });
    assert.equal(hits.length, 1, `${s.id} meets one nut`);
    used.add(hits[0].id);
  }
  assert.equal(used.size, nuts.length, 'every nut takes a screw');
});

// Contract: no soldering iron, pressed-in inserts or rods anywhere in the guide, and nothing is
// drilled: the rack stands on the TV unit on its pads.
test('the guide asks for screws and nuts only and drills nothing', () => {
  const copy = [...tl.chapters.flatMap((c) => [c.title, c.text, ...c.tags.map((t) => t.text)]), soyrackSheetHTML()].join('\n');
  for (const re of [/solder/i, /\biron\b/i, /\binserts?\b/i, /\brods?\b/i, /drill/i]) assert.doesNotMatch(copy, re);
  assert.match(copy, /no holes, screws or glue in the unit/);
});

// Contract: the mid deck is printed from its flat preset, not the on-edge STL that failed, and the
// guide never promises that a stuck plug can be cut or forced out.
test('the sheet sends the mid deck to its preset with a hand-only plug release', () => {
  const entry = soyrackSheetHTML().split('<li>').find((li) => li.includes('<strong>Mid deck</strong>'));
  assert.match(entry, /Print preset <strong>mid_deck_flat<\/strong>/);
  assert.match(entry, /mid_deck\.stl ↗<\/a> is only the assembled shape.*do not print it/);
  assert.match(entry, /untested/);
  const chapter = tl.chapters.find((c) => c.id === 'mid-deck').text;
  for (const copy of [entry, chapter]) {
    assert.match(copy, /M4 screw by hand/);
    assert.match(copy, /stop/);
    assert.doesNotMatch(copy, /pliers|flush cutter|breakaway|carve|snap/i);
  }
});

// Contract: the buy list covers every fastener the scene installs. The node trays carry over
// with their own screws, so only the new M4 × 12 are bought. The test checks take one corner
// screw, three nuts and two M4 × 12 from the same packs.
test('the buy list covers every fastener and lead the rack installs', () => {
  const count = (mesh, keep = () => true) => shown.filter((n) => n.mesh === mesh && !TEST_PIECE.test(n.id) && keep(n)).length;
  const forTests = (mesh) => shown.filter((n) => n.mesh === mesh && TEST_PIECE.test(n.id)).length;
  const bought = (key) => BUY.find((b) => b.key === key).quantity;
  assert.ok(count('m4nut') === 36 && bought('nut4') >= count('m4nut') + forTests('m4nut'));
  assert.ok(count('m4x25') === 12 && bought('bolt') >= count('m4x25') + forTests('m4x25'));
  assert.ok(bought('m4') >= count('m4x12', (n) => !n.id.startsWith('tray.')) + forTests('m4x12'));
  assert.ok(bought('pad') >= DEVICES.filter((d) => d.model === 'pad').length);
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
  for (const n of shown.filter((n) => n.kind === 'part' && rackMeshes[n.mesh] && !TEST_PIECE.test(n.id) && n.id !== 'zigbee_mast')) {
    const size = rackMeshes[n.mesh].size; // parts sit square or turned half a turn about z
    for (let k = 0; k < 3; k++) {
      lo[k] = Math.min(lo[k], n.final.p[k] - size[k] / 2);
      hi[k] = Math.max(hi[k], n.final.p[k] + size[k] / 2);
    }
  }
  assert.ok(hi[0] - lo[0] <= 260 && hi[1] - lo[1] <= 240, `footprint ${hi[0] - lo[0]} x ${hi[1] - lo[1]}`);
  assert.ok(lo[2] >= FLOOR_Z && hi[2] - FLOOR_Z <= 450, `height ${hi[2] - FLOOR_Z}`);
});
