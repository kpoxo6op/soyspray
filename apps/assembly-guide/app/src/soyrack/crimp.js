// Crimping the rack's Ethernet leads: a work mat beside the rack, Boris's bswjdz kit on it, and one
// lead made step by step, then tested on the 468 tester. The steps follow the kit leaflet: strip,
// untwist, line up T568B, trim, slide into the plug, crimp, test and read the lamps.
//
// Every node id starts with `crimp.`; the section clears the mat away before the leads go in.

import { add3, qaxis, qmul } from '../math.js';
import { polyLength } from '../cablepath.js';
import { CONNECTORS } from '../ports.js';
import { HOLD_IN } from '../timeline.js';
import { CABLE_BY_ID } from './cables.js';
import { FLOOR_Z } from './rack.js';
import {
  BOOT, BOOT_ON, BOOT_PARKED, JACKET_END, LAMP_PATTERNS, LED_X, MAIN, MAT, PIN_PITCH, PLUG, REMOTE, STRIP, TESTER_TOP, TRIM, TRIM_TIP,
} from './crimp-layout.js';
import {
  CRIMPER, buildBoot, buildCrimperLower, buildCrimperUpper, buildJacket, buildLamp, buildLead, buildMain, buildMat, buildPiece,
  buildPins, buildPlug, buildRemote, buildShieldedPlug, buildStripper, buildSwitch, buildWires,
} from './crimp-models.js';

const ID_Q = [0, 0, 0, 1];
/** The mat's centre on the floor, to the right of the rack, clear of its cords. */
export const BENCH = [760, -60, FLOOR_Z];
const K = (p) => add3(BENCH, p);
/** The cut end of the cable being made, held 18 mm over the mat: the cable frame of crimp-layout.js. */
export const WORK = K([0, 0, 18]);
const W = (p) => add3(WORK, p);

const FLAT = qaxis([1, 0, 0], Math.PI / 2); // a tool drawn in its xz plane, laid on the mat
const turnZ = (a, q = ID_Q) => qmul(qaxis([0, 0, 1], a), q);

// ---------------------------------------------------------------- the five leads

const ROUTES = [
  { id: 'eth0', name: 'node-0', boot: 'blue' },
  { id: 'eth1', name: 'node-1', boot: 'blue' },
  { id: 'eth2', name: 'node-2', boot: 'blue' },
  { id: 'uplink', name: 'Keystone 1', boot: 'yellow' },
  { id: 'spareLan', name: 'Keystone 2', boot: 'green' },
];
const TRIM_LOSS = STRIP - TRIM; // stripped, then trimmed back: lost from each end
const MIN_LEAD = 150; // shorter than this is hard to hold while crimping
/**
 * Each lead finished: its route between the plugs, a plug and boot at each end and 3 cm to spare,
 * rounded up to the centimetre and never under 15 cm. It is cut longer by what the trim takes off.
 */
export const LEADS = ROUTES.map((r) => {
  const route = CABLE_BY_ID[r.id].parts.reduce((s, p) => s + polyLength(p.points), 0);
  const finished = Math.max(MIN_LEAD, Math.ceil((route + 2 * CONNECTORS.rj45.len + 30) / 10) * 10);
  return { ...r, route, finished, cut: Math.ceil((finished + 2 * TRIM_LOSS) / 10) * 10 };
});
const cm = (mm) => `${mm / 10} cm`;
/** "44 cm for node-0, …" with the two keystone leads said once when they match. */
function cutList() {
  const nodes = LEADS.slice(0, 3).map((l) => `${cm(l.cut)} for ${l.name}`);
  const [k1, k2] = LEADS.slice(3);
  const keys = k1.cut === k2.cut ? [`${cm(k1.cut)} for each keystone lead`] : [`${cm(k1.cut)} for keystone 1`, `${cm(k2.cut)} for keystone 2`];
  const all = [...nodes, ...keys];
  return `${all.slice(0, -1).join(', ')} and ${all.at(-1)}`;
}
const ZERO = 20; // ruler zero, from the mat's left edge

// ---------------------------------------------------------------- nodes

const CRIMPER_KIT = { p: K([-170, 112, 8.5]), q: FLAT };
const STRIPPER_KIT = { p: K([40, 122, MAT.size[2] + 4.5]), q: FLAT };
const PLUG_KIT = { p: K([52, 12, 7]), q: turnZ(0.45) };
const SHIELD_KIT = { p: K([88, 12, 7]), q: turnZ(0.45) };
const BOOT_KIT = { p: K([128, 16, 8.9]), q: turnZ(0.45) };
const PIECE_Y = [-6, -40, -74, -108, -142]; // in front, by the ruler

const LAMPS_M = LED_X.map((_, k) => `crimp.lampM${k}`);
// The remote's G lamp never lights here: unshielded cable has no G line.
const LAMPS_R = LED_X.slice(0, 8).map((_, k) => `crimp.lampR${k}`);

export function crimpPlacements() {
  const groups = {
    'crimp.crimper': { parent: 'world', pivot: [0, 0, 0], p: CRIMPER_KIT.p, q: CRIMPER_KIT.q },
    'crimp.jaw': { parent: 'crimp.crimper', pivot: CRIMPER.pivot, p: CRIMPER.pivot, q: ID_Q },
    'crimp.plugG': { parent: 'world', pivot: [0, 0, 0], p: PLUG_KIT.p, q: PLUG_KIT.q },
  };
  return { groups, instances: [], screws: [] };
}

const dev = (id, build, centre, extra = {}) => ({ id, model: id, size: [0, 0, 0], centre, build, ...extra });

export const CRIMP_DEVICES = [
  dev('crimp.mat', buildMat, K([0, 0, MAT.size[2] / 2]), { size: MAT.size, zero: ZERO }),
  ...LEADS.map((l, i) => dev(`crimp.cut${i}`, buildPiece, K([-MAT.size[0] / 2 + ZERO + l.cut / 2, PIECE_Y[i], MAT.size[2] + 2.75]), { length: l.cut })),
  dev('crimp.crimperLow', buildCrimperLower, [0, 0, 0], { group: 'crimp.crimper' }),
  dev('crimp.crimperUp', buildCrimperUpper, [0, 0, 0], { group: 'crimp.jaw' }),
  dev('crimp.stripper', buildStripper, STRIPPER_KIT.p, { q: STRIPPER_KIT.q }),
  dev('crimp.main', buildMain, K(MAIN.centre)),
  dev('crimp.remote', buildRemote, K(REMOTE.centre)),
  dev('crimp.switch', buildSwitch, K([MAIN.switch.x.OFF, MAIN.switch.y, TESTER_TOP + 0.8])),
  ...LED_X.map((x, k) => dev(LAMPS_M[k], buildLamp, K([x, MAIN.ledY, TESTER_TOP + 0.35]))),
  ...LAMPS_R.map((id, k) => dev(id, buildLamp, K([LED_X[k], REMOTE.ledY, TESTER_TOP + 0.35]))),
  dev('crimp.plug', buildPlug, [0, 0, 0], { group: 'crimp.plugG' }),
  // The contacts stand proud of the plug until the crimp presses them down.
  dev('crimp.pins', buildPins, [0, 0, PLUG.pinLift], { group: 'crimp.plugG' }),
  dev('crimp.shield', buildShieldedPlug, SHIELD_KIT.p, { q: SHIELD_KIT.q }),
  dev('crimp.boot', buildBoot, BOOT_KIT.p, { q: BOOT_KIT.q, colour: BOOT.colour }),
  dev('crimp.jacket', buildJacket, WORK, {
    // Straight past where the boot waits, then down onto the mat and away along its front edge.
    points: [[0, JACKET_END, 0], [0, -80, 0], [0, -128, 0], [2, -142, -5], [10, -153, -12], [26, -160, -15.25], [60, -162, -15.25], [160, -162, -15.25], [420, -162, -15.25]],
  }),
  dev('crimp.slug', buildJacket, WORK, { points: [[0, JACKET_END, 0], [0, -15, 0], [0, 0, 0]], step: 1 }),
  ...['pairs', 'fan', 'flat', 'trimmed', 'offcut'].map((state) => dev(`crimp.${state}`, buildWires, WORK, { state })),
  dev('crimp.lead', buildLead, BENCH),
];

// ---------------------------------------------------------------- script helpers

/** Opacity of `ids` from `a` to `b`, starting `at` seconds into the chapter. */
function fade(c, ids, at, [a, b], dur = 0.5) {
  const t = c.start + at;
  for (const id of ids) c.get(id).alpha.push({ t, v: a }, { t: t + dur, v: b });
  c.end = Math.max(c.end, t + dur);
}

/** One lamp lit at `v` for a step of `dur` seconds from absolute time `t`. */
function pulse(c, id, t, dur, v) {
  c.get(id).alpha.push({ t, v: 0 }, { t: t + 0.04, v }, { t: t + dur - 0.08, v }, { t: t + dur - 0.04, v: 0 });
  c.end = Math.max(c.end, t + dur);
}

const STEP = 0.34;
/** One sweep of the tester through lines 1-8 and G; returns the relative end time. */
function sweep(c, at, pattern) {
  pattern.forEach((s, k) => {
    const t = c.start + at + k * STEP;
    if (s.main !== null) pulse(c, LAMPS_M[s.main], t, STEP, 1);
    for (const r of s.remote) pulse(c, LAMPS_R[r], t, STEP, s.dim ? 0.32 : 1);
  });
  return at + pattern.length * STEP;
}

/** Pick a tool up off the mat, carry it high over the kit and bring it to `to`. */
function fetch(c, id, at, from, to, { lift = 60, dur = 2.2 } = {}) {
  c.path(id, [
    { at, p: from.p, q: from.q },
    { at: at + dur * 0.3, p: add3(from.p, [0, 0, lift]), q: from.q },
    { at: at + dur * 0.75, p: add3(to.p, [0, 0, lift * 0.5]), q: to.q },
    { at: at + dur, p: to.p, q: to.q, e: 'out' },
  ]);
  return at + dur;
}

/** Slide in a straight line, ending at rest. */
function slide(c, id, at, dur, from, to, highlight = true) {
  c.path(id, [{ at, p: from.p, q: from.q }, { at: at + dur, p: to.p, q: to.q, e: 'out' }], { highlight });
  return at + dur;
}

/** The crimper's jaw from one opening to another (radians, 0 is closed). */
function jaw(c, at, dur, a, b) {
  const q = (angle) => qaxis([0, 1, 0], -angle);
  c.path('crimp.jaw', [{ at, p: CRIMPER.pivot, q: q(a) }, { at: at + dur, p: CRIMPER.pivot, q: q(b), e: 'inOut' }], { highlight: false });
  return at + dur;
}

const at = (p, q = ID_Q) => ({ p, q });
const pinsUp = [0, 0, PLUG.pinLift];

// Wire tips in the device frame of the wire states (the cable frame).
const tipOf = (i, y = TRIM_TIP) => [(i - 3.5) * PIN_PITCH, y, 0];

// ---------------------------------------------------------------- chapters

const KIT = ['crimp.crimper', 'crimp.stripper', 'crimp.main', 'crimp.remote', 'crimp.switch', 'crimp.plugG', 'crimp.shield', 'crimp.boot', 'crimp.jacket', 'crimp.slug'];
const PIECES = LEADS.map((_, i) => `crimp.cut${i}`);
const lamp = (unit, k) => [LED_X[k] - unit.centre[0], unit.ledY - unit.centre[1], 13.4];

export const CRIMP_CHAPTERS = [
  {
    id: 'crimp-plan', section: 'Ethernet leads', title: 'Five short leads', view: 'crimp-plan',
    text: `Short leads you crimp yourself replace the long loose ones. Practise on a spare cable first. Then cut five pieces: ${cutList()}. Each loses about 2 cm at each end on its way to done.`,
    tags: LEADS.map((l, i) => ({ text: `${l.name} · cut ${cm(l.cut)}`, node: PIECES[i], at: [l.cut / 2, 0, 2], side: 'e', from: 1.4 + i * 0.5, until: 9.2 })),
    script(c) {
      c.show(['crimp.mat']);
      PIECES.forEach((id, i) => {
        c.showAt([id], 0.6 + i * 0.5);
        c.move(id, 0.6 + i * 0.5, 1.3, { from: [-50, 0, 0] });
      });
      fade(c, PIECES, 9.2, [1, 0], 0.7);
    },
  },
  {
    id: 'crimp-kit', title: 'The kit', view: 'crimp-kit',
    text: 'Everything is in your bswjdz case and the yellow box: the crimper, the yellow stripper, the 468 tester and its remote, RJ45 plugs and coloured boots. The coax stripper and the KD-1 punch-down tool stay in the case; the keystone couplers need no punching.',
    tags: [
      { text: 'Crimper', node: 'crimp.crimperLow', at: [130, 0, -18], side: 's', from: 1.4 },
      { text: 'Yellow stripper', node: 'crimp.stripper', at: [0, 0, 26], side: 'n', from: 2.0 },
      { text: '468 tester', node: 'crimp.main', at: [0, 20, 13], side: 'n', from: 2.6 },
      { text: 'Remote', node: 'crimp.remote', at: [40, 0, 13], side: 'e', from: 3.0 },
      { text: 'Plugs', node: 'crimp.shield', at: [0, -8, 4], side: 's', from: 3.6 },
      { text: 'Boot', node: 'crimp.boot', at: [0, -12, 6], side: 'se', from: 4.0 },
      { text: 'Cable', node: 'crimp.jacket', at: [0, -70, 3], side: 'w', from: 4.4 },
    ],
    script(c) {
      KIT.forEach((id, i) => {
        c.showAt([id], 0.5 + i * 0.25);
        c.move(id, 0.5 + i * 0.25, 1.1, { from: [0, 0, 24], via: [0, 0, 4] });
      });
      c.end = Math.max(c.end, c.start + 9.6);
    },
  },
  {
    id: 'crimp-plugs', title: 'Clear or metal plugs', view: 'crimp-plugs',
    text: 'Use the clear plugs: your patch cables are ordinary unshielded cable. The metal plugs are for shielded cable, which has foil and a bare drain wire under the jacket, folded back so the metal tab grips them. No foil, no drain wire: clear plugs.',
    tags: [
      { text: 'Clear: ordinary cable', node: 'crimp.plug', at: [0, -10, 4], side: 'nw', from: 1.6 },
      { text: 'Metal: shielded cable only', node: 'crimp.shield', at: [0, -12, 4], side: 'ne', from: 3.0 },
      { text: 'Clip', node: 'crimp.plug', at: [0, -14, -4.6], side: 'sw', from: 5.0 },
    ],
    script(c) {
      [['crimp.plugG', PLUG_KIT], ['crimp.shield', SHIELD_KIT]].forEach(([id, kit], j) => {
        const t = HOLD_IN + j * 0.4;
        const up = add3(kit.p, [0, 0, 16]);
        const steps = [{ at: t, p: kit.p, q: kit.q }, { at: t + 1, p: up, q: kit.q }];
        for (let k = 1; k <= 4; k++) steps.push({ at: t + 1 + k * 1.5, p: up, q: turnZ((k * Math.PI) / 2, kit.q), e: 'linear' });
        steps.push({ at: t + 8.2, p: kit.p, q: kit.q });
        c.path(id, steps, { highlight: false });
      });
    },
  },
  {
    id: 'crimp-boot', title: 'Boot on first', view: 'crimp-boot',
    text: 'Slide a boot onto the cable before anything else, wide end towards the cut, and push it well back: it cannot go on once the plug is crimped. Blue boots for the node leads, yellow for keystone 1 and green for keystone 2, like the leads in the rack.',
    tags: [
      { text: 'Wide end towards the cut', node: 'crimp.boot', at: [0, 0, 7], side: 'n', from: 3.2, until: 6.2 },
      { text: 'Pushed well back', node: 'crimp.boot', at: [0, -14, 6], side: 'n', from: 6.4 },
    ],
    script(c) {
      const t = fetch(c, 'crimp.boot', HOLD_IN, BOOT_KIT, at(W([0, 60, 0])), { lift: 40 });
      slide(c, 'crimp.boot', t + 0.3, 2.4, at(W([0, 60, 0])), at(W([0, BOOT_PARKED, 0])));
    },
  },
  {
    id: 'crimp-strip', title: 'Strip 3 cm of jacket', view: 'crimp-strip',
    text: 'Slide the yellow stripper on 3 cm from the end, squeeze gently and turn it two or three times, then pull the jacket off. Only the jacket is cut: if a coloured wire is nicked, cut the end off and strip again. Snip off any string or plastic cross inside.',
    tags: [
      { text: '3 cm from the end', node: 'crimp.stripper', at: [0, 0, 12], side: 'n', from: 3.4, until: 5.0 },
      { text: 'Turn it two or three times', node: 'crimp.stripper', at: [0, 0, -30], side: 'e', from: 5.0, until: 7.4 },
      { text: 'Jacket off, wires unharmed', node: 'crimp.pairs', at: [0, -12, 3], side: 'n', from: 8.6 },
    ],
    script(c) {
      const S = 'crimp.stripper';
      const on = W([0, JACKET_END, 0]);
      let t = fetch(c, S, HOLD_IN, STRIPPER_KIT, at(W([0, 30, 0])), { lift: 50 });
      t = slide(c, S, t + 0.2, 1.1, at(W([0, 30, 0])), at(on));
      const turns = [];
      for (let k = 1; k <= 12; k++) turns.push({ at: t + 0.2 + k * 0.18, p: on, q: qaxis([0, 1, 0], (k * Math.PI) / 2), e: 'linear' });
      c.path(S, [{ at: t + 0.2, p: on, q: ID_Q }, ...turns]);
      t += 0.2 + 12 * 0.18 + 0.2;
      c.showAt(['crimp.pairs'], t);
      slide(c, S, t, 1.2, at(on), at(W([0, JACKET_END + 38, 0])));
      slide(c, 'crimp.slug', t, 1.2, at(WORK), at(W([0, 38, 0])), false);
      fade(c, ['crimp.slug'], t + 1.4, [1, 0], 0.5);
      fetch(c, S, t + 1.5, at(W([0, JACKET_END + 38, 0])), STRIPPER_KIT, { lift: 50, dur: 2 });
    },
  },
  {
    id: 'crimp-untwist', title: 'Untwist and line up', view: 'crimp-wires', legend: 't568b',
    text: 'Untwist all four pairs back to the jacket and straighten each wire between finger and thumb. Lay them flat side by side in the T568B order at the top, left to right: white-orange, orange, white-green, blue, white-blue, green, white-brown, brown.',
    tags: [
      { text: '1 · white-orange', node: 'crimp.fan', at: [-5.1, -1, 0.5], side: 'nw', from: 2.8 },
      { text: '8 · brown', node: 'crimp.fan', at: [5.1, -1, 0.5], side: 'ne', from: 3.3 },
      { text: 'Green either side of the blue pair', node: 'crimp.fan', at: [2.2, -8, 0.5], side: 'se', from: 4.6 },
    ],
    script(c) {
      fade(c, ['crimp.pairs'], HOLD_IN + 0.4, [1, 0], 1.4);
      fade(c, ['crimp.fan'], HOLD_IN + 0.4, [0, 1], 1.4);
      c.end = Math.max(c.end, c.start + 9.4);
    },
  },
  {
    id: 'crimp-trim', title: 'Trim to 13 mm', view: 'crimp-trim', legend: 't568b',
    text: 'Pinch the row flat and in order right up to the jacket. Cut straight across with the blade between the crimper’s handles, leaving 13 mm of wire out of the jacket and all eight ends level.',
    tags: [
      { text: '13 mm out of the jacket', node: 'crimp.flat', at: [0, JACKET_END + TRIM / 2, 1], side: 'nw', from: 1.8, until: 5.3 },
      { text: 'Blade between the handles', node: 'crimp.crimperUp', at: [40, -1, 12], side: 'n', from: 4.2, until: 6.2 },
      { text: 'All eight ends level', node: 'crimp.trimmed', at: [0, TRIM_TIP, 1], side: 'nw', from: 6.6 },
    ],
    script(c) {
      fade(c, ['crimp.fan'], HOLD_IN, [1, 0], 0.8);
      fade(c, ['crimp.flat'], HOLD_IN, [0, 1], 0.8);
      const T = 'crimp.crimper';
      const trim = at(W([-CRIMPER.blade[0], TRIM_TIP, -CRIMPER.blade[2]]));
      const before = at(add3(trim.p, [0, 34, 0]));
      jaw(c, HOLD_IN + 0.6, 0.8, 0, CRIMPER.open);
      let t = fetch(c, T, HOLD_IN + 0.4, CRIMPER_KIT, before, { lift: 90, dur: 2.4 });
      t = slide(c, T, t + 0.1, 1.0, before, trim);
      const cut = jaw(c, t + 0.2, 0.45, CRIMPER.open, 0);
      fade(c, ['crimp.flat'], cut - 0.06, [1, 0], 0.06);
      fade(c, ['crimp.trimmed', 'crimp.offcut'], cut - 0.06, [0, 1], 0.06);
      c.path('crimp.offcut', [
        { at: cut + 0.1, p: WORK, q: ID_Q },
        { at: cut + 0.9, p: W([0, 6, -12]), q: qaxis([1, 0, 0], 0.5), e: 'in' },
      ], { highlight: false });
      fade(c, ['crimp.offcut'], cut + 0.7, [1, 0], 0.4);
      jaw(c, cut + 0.3, 0.4, 0, CRIMPER.open);
      t = slide(c, T, cut + 0.8, 0.8, trim, before, false);
      fetch(c, T, t + 0.1, before, CRIMPER_KIT, { lift: 90, dur: 2.2 });
      jaw(c, t + 1.8, 0.5, CRIMPER.open, 0);
    },
  },
  {
    id: 'crimp-plug', title: 'Into the plug', view: 'crimp-plug', legend: 't568b',
    text: 'Hold a clear plug with the clip underneath and the gold contacts on top: white-orange is then on the left. Slide the flat row in, keeping the order, until all eight wires touch the far end and the jacket is inside the plug.',
    tags: [
      { text: 'Gold contacts on top', node: 'crimp.pins', at: [0, -3.6, 3.6], side: 'n', from: 1.6, until: 3.4 },
      { text: 'Clip underneath', node: 'crimp.plug', at: [0, -15, -5], side: 's', from: 1.9, until: 3.4 },
      { text: 'White-orange on the left', node: 'crimp.trimmed', at: tipOf(0, TRIM_TIP - 6), side: 'w', from: 5.6 },
      { text: 'All eight at the far end', node: 'crimp.trimmed', at: tipOf(7), side: 'ne', from: 6.0 },
      { text: 'Jacket inside', node: 'crimp.jacket', at: [0, PLUG.rear + 3, 3], side: 'e', from: 6.6 },
    ],
    script(c) {
      const G = 'crimp.plugG';
      const start = at(W([0, 46, 0]));
      const t = fetch(c, G, HOLD_IN, PLUG_KIT, start, { lift: 30 });
      slide(c, G, t + 0.4, 2.2, start, at(W([0, PLUG.front, 0])));
      c.end = Math.max(c.end, c.start + 9.2);
    },
  },
  {
    id: 'crimp-check', title: 'Look before you crimp', view: 'crimp-check',
    text: 'Check from the end: eight copper dots against the end wall, none short. Check from above: the colours still in order and the jacket inside. If anything is off, pull the wires out and trim again. Once crimped, a plug cannot be undone.',
    tags: [
      { text: 'Eight copper dots at the wall', node: 'crimp.trimmed', at: tipOf(3.5), side: 'n', from: 1.2 },
      { text: 'Jacket inside the plug', node: 'crimp.jacket', at: [0, PLUG.rear + 3, -1], side: 's', from: 2.6 },
    ],
    script(c) {
      c.end = Math.max(c.end, c.start + 6.6);
    },
  },
  {
    id: 'crimp-press', title: 'Crimp', view: 'crimp-press',
    text: 'Push the plug into the crimper’s 8P hole, the largest one, until it stops, still pushing the cable in. Squeeze the handles fully closed in one firm press, then let go. The gold contacts are now pressed down into the wires and the plug grips the jacket.',
    tags: [
      { text: '8P hole', node: 'crimp.crimperLow', at: [0, -6.6, -2.2], side: 'sw', from: 3.2, until: 5.4 },
      { text: 'Squeeze until it stops', node: 'crimp.crimperUp', at: [150, 0, 26], side: 'n', from: 5.6, until: 8.0 },
      { text: 'Contacts pressed down', node: 'crimp.pins', at: [0, -3.6, 3.6], side: 'n', from: 9.4 },
    ],
    script(c) {
      const T = 'crimp.crimper';
      const die = at(W([0, PLUG.front - 3.6 - 2.8, 0]));
      const before = at(add3(die.p, [0, 40, 0]));
      jaw(c, HOLD_IN + 0.6, 0.8, 0, CRIMPER.open);
      let t = fetch(c, T, HOLD_IN + 0.4, CRIMPER_KIT, before, { lift: 90, dur: 2.4 });
      t = slide(c, T, t + 0.1, 1.2, before, die);
      const shut = jaw(c, t + 0.5, 1.1, CRIMPER.open, 0);
      c.path('crimp.pins', [{ at: shut - 0.45, p: pinsUp, q: ID_Q }, { at: shut, p: [0, 0, 0], q: ID_Q, e: 'out' }]);
      jaw(c, shut + 0.6, 0.6, 0, CRIMPER.open);
      t = slide(c, T, shut + 1.3, 0.9, die, before, false);
      fetch(c, T, t + 0.1, before, CRIMPER_KIT, { lift: 90, dur: 2.2 });
      jaw(c, t + 1.8, 0.5, CRIMPER.open, 0);
    },
  },
  {
    id: 'crimp-boot-on', title: 'Boot over, then the other end', view: 'crimp-boot-on',
    text: 'Slide the boot forward over the back of the plug until it covers the base of the clip. Then make the other end exactly the same way, in the same T568B order: the same order at both ends makes a normal straight-through lead.',
    tags: [{ text: 'Boot over the back of the plug', node: 'crimp.boot', at: [0, -4, 7], side: 'n', from: 3.4 }],
    script(c) {
      slide(c, 'crimp.boot', HOLD_IN + 0.3, 2.2, at(W([0, BOOT_PARKED, 0])), at(W([0, BOOT_ON, 0])));
      c.end = Math.max(c.end, c.start + 8.2);
    },
  },
  {
    id: 'crimp-test', title: 'Test with the 468', view: 'crimp-test',
    text: 'Plug one end into the tester and the other into its remote, and slide the switch to ON (S steps slowly). A good lead lights lamps 1 to 8 one after another on both, together. The remote’s G stays dark on unshielded cable; that is fine.',
    tags: [
      { text: 'Switch to ON', node: 'crimp.switch', at: [0, 0, 1], side: 'n', from: 3.0, until: 5.0 },
      { text: 'Tester', node: 'crimp.main', at: [-46, 18, 13], side: 'nw', from: 3.4 },
      { text: 'Remote', node: 'crimp.remote', at: [-42, 0, 13], side: 'w', from: 3.6 },
      { text: 'Same lamp on both', node: 'crimp.remote', at: lamp(REMOTE, 4), side: 's', from: 5.4, until: 9.6 },
      { text: 'G dark: no shield, fine', node: 'crimp.remote', at: lamp(REMOTE, 8), side: 'se', from: 9.8 },
    ],
    script(c) {
      fade(c, ['crimp.jacket', 'crimp.trimmed', 'crimp.plugG', 'crimp.boot'], HOLD_IN - 0.4, [1, 0], 0.6);
      c.showAt(['crimp.lead'], HOLD_IN + 0.4);
      slide(c, 'crimp.lead', HOLD_IN + 0.4, 1.6, at(K([34, 0, 0])), at(BENCH));
      const sw = MAIN.switch;
      slide(c, 'crimp.switch', HOLD_IN + 2.4, 0.5, at(K([sw.x.OFF, sw.y, TESTER_TOP + 0.8])), at(K([sw.x.ON, sw.y, TESTER_TOP + 0.8])));
      const t = sweep(c, HOLD_IN + 3.4, LAMP_PATTERNS.good);
      sweep(c, t + 0.3, LAMP_PATTERNS.good);
    },
  },
  {
    id: 'crimp-faults', title: 'When the lamps are wrong', view: 'crimp-faults',
    text: 'A lamp dark on both: that wire has no contact. Remote lamps out of order, say 1 4 3 2: wires swapped at one end. Two remote lamps faint together: those wires touch. For any fault, cut the plug off and crimp a new one. Never test a cable that is plugged into anything powered.',
    tags: [
      { text: 'Lamp 3 dark on both: no contact', node: 'crimp.remote', at: lamp(REMOTE, 2), side: 's', from: HOLD_IN, until: HOLD_IN + 3.3 },
      { text: 'Remote 4 with main 2: swapped', node: 'crimp.remote', at: lamp(REMOTE, 3), side: 's', from: HOLD_IN + 3.6, until: HOLD_IN + 6.9 },
      { text: '4 and 5 faint together: touching', node: 'crimp.remote', at: lamp(REMOTE, 4), side: 's', from: HOLD_IN + 7.2, until: HOLD_IN + 10.5 },
    ],
    script(c) {
      let t = sweep(c, HOLD_IN, LAMP_PATTERNS.open3);
      t = sweep(c, t + 0.3, LAMP_PATTERNS.swap24);
      t = sweep(c, t + 0.3, LAMP_PATTERNS.short45);
      const sw = MAIN.switch;
      slide(c, 'crimp.switch', t + 0.3, 0.4, at(K([sw.x.ON, sw.y, TESTER_TOP + 0.8])), at(K([sw.x.OFF, sw.y, TESTER_TOP + 0.8])), false);
      fade(c, ['crimp.mat', 'crimp.crimper', 'crimp.stripper', 'crimp.main', 'crimp.remote', 'crimp.switch', 'crimp.shield', 'crimp.lead'], t + 2.6, [1, 0], 0.8);
    },
  },
];

const box = (lo, hi) => [K(lo), K(hi)];
const wbox = (lo, hi) => [W(lo), W(hi)];

/** Camera framing of each crimping chapter, as in stage.js. */
export const CRIMP_VIEWS = {
  'crimp-plan': { box: box([-262, -172, 0], [262, 10, 10]), view: { azimuth: 0, elevation: 1.0 } },
  'crimp-kit': { box: box([-240, -150, 0], [262, 170, 30]), view: { azimuth: -0.12, elevation: 0.82 } },
  'crimp-plugs': { box: box([30, -10, 0], [150, 40, 30]), view: { azimuth: -0.3, elevation: 0.5 } },
  'crimp-boot': { box: wbox([-14, -130, -14], [14, 70, 14]), view: { azimuth: -0.75, elevation: 0.5 } },
  'crimp-strip': { box: wbox([-30, -60, -30], [30, 50, 40]), view: { azimuth: -0.55, elevation: 0.42 } },
  'crimp-wires': { box: wbox([-16, -38, -6], [16, 6, 6]), view: { azimuth: 0, elevation: 1.02 } },
  'crimp-trim': { box: wbox([-90, -40, -30], [150, 45, 55]), view: { azimuth: -0.12, elevation: 0.38 } },
  'crimp-plug': { box: wbox([-18, -48, -10], [18, 50, 10]), view: { azimuth: -0.22, elevation: 0.9 } },
  'crimp-check': { box: wbox([-14, -46, -9], [14, -10, 9]), view: { azimuth: 2.75, elevation: 0.3 } },
  'crimp-press': { box: wbox([-55, -50, -45], [195, 50, 60]), view: { azimuth: -0.12, elevation: 0.32 } },
  'crimp-boot-on': { box: wbox([-14, -125, -14], [14, -8, 14]), view: { azimuth: -0.75, elevation: 0.5 } },
  'crimp-test': { box: box([60, 30, 0], [262, 165, 30]), view: { azimuth: -0.05, elevation: 0.98 } },
  'crimp-faults': { box: box([70, 55, 10], [175, 125, 30]), view: { azimuth: 0, elevation: 1.15 } },
};

/** Wire a finished lead is checked against: the T568B order, both ends. Used by the tests. */
export const CRIMP_IDS = /^crimp\./;
