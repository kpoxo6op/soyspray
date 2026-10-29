// Deterministic assembly timeline. Every visible state is a pure function of time, so seeking,
// pausing and reverse playback all read the same keyframes. Coordinates are rack millimetres
// (x left -> right, y front -> rear, z up), offsets are expressed in the parent node's frame.

import { add3, scale3, qaxis, qfromTo, lerp3, slerp, EASE, clamp } from './math.js';
import { DRILLED } from './variant.js';
import { DEVICES, ANTENNA_TILT } from './layout.js';
import { CABLES, PERIPHERALS } from './wiring.js';

export const FADE = 0.6; // new parts fade in during the last 0.6 s of the previous chapter
export const HOLD_IN = 0.9; // pause on the staged parts before anything moves
export const HOLD_OUT = 1.7; // pause on the finished step

const ID_Q = [0, 0, 0, 1];
const SCREW_AXIS = [0, 1, 0]; // screw model: head at the origin, shaft along +Y
const RECT_LIFT = 322; // the second rectangle is built this far above the bottom one (clears the rails when turned)

const ANTENNA_X = [-62, 0, 62];
const ANTENNA_FOLDED = -90 * (Math.PI / 180);

function node(id, parent, kind, extra) {
  return { id, parent, kind, keys: [], alpha: [], glow: [], ...extra };
}

class Chapter {
  constructor(nodes, start, index) {
    this.nodes = nodes;
    this.start = start;
    this.index = index;
    this.end = start + HOLD_IN;
  }

  get(id) {
    const n = this.nodes.get(id);
    if (!n) throw new Error(`unknown node ${id}`);
    return n;
  }

  /** Visible from the start of this chapter (fading in just before it). */
  show(ids) {
    for (const id of ids) {
      const n = this.get(id);
      if (this.index === 0) n.alpha.push({ t: -1, v: 1 });
      else n.alpha.push({ t: this.start - FADE, v: 0 }, { t: this.start, v: 1 });
      n.shownAt = this.start;
    }
  }

  /** Visible from `at` seconds into this chapter (short fade). */
  showAt(ids, at) {
    const t = this.start + at;
    for (const id of ids) {
      const n = this.get(id);
      n.alpha.push({ t: t - 0.45, v: 0 }, { t, v: 1 });
      n.shownAt = t;
    }
  }

  /** Move from final + offset (optionally rotated) through an optional approach point to the final pose. */
  move(id, at, dur, { from = [0, 0, 0], fromQ = null, via = null, viaAt = 0.62 } = {}) {
    const n = this.get(id);
    const t0 = this.start + at;
    const t1 = t0 + dur;
    const fp = n.final.p;
    const fq = n.final.q;
    n.keys.push({ t: t0, p: add3(fp, from), q: fromQ || fq, e: 'linear' });
    if (via) {
      n.keys.push({ t: t0 + dur * viaAt, p: add3(fp, via), q: fq, e: 'inOut' });
      n.keys.push({ t: t1, p: fp, q: fq, e: 'smooth' });
    } else {
      n.keys.push({ t: t1, p: fp, q: fq, e: 'inOut' });
    }
    this.glow(n, t0, t1);
    this.end = Math.max(this.end, t1);
    return at + dur;
  }

  /** Explicit pose path: steps are { at, p, q, e }. */
  path(id, steps, { highlight = true } = {}) {
    const n = this.get(id);
    let last = 0;
    for (const s of steps) {
      n.keys.push({ t: this.start + s.at, p: s.p, q: s.q, e: s.e || 'inOut' });
      last = Math.max(last, s.at);
    }
    if (highlight) this.glow(n, this.start + steps[0].at, this.start + last);
    this.end = Math.max(this.end, this.start + last);
    return last;
  }

  /** Screws drive in along their axis, one after another. Returns the relative end time. */
  screws(ids, at, { dur = 0.8, stagger = 0.14 } = {}) {
    let end = at;
    ids.forEach((id, i) => {
      const n = this.get(id);
      const t0 = this.start + at + i * stagger;
      const t1 = t0 + dur;
      n.keys.push({ t: t0, p: add3(n.final.p, scale3(n.dir, -n.out)), q: n.final.q, e: 'linear' });
      n.keys.push({ t: t1, p: n.final.p, q: n.final.q, e: 'inOut' });
      n.alpha.push({ t: t0 - 0.3, v: 0 }, { t: t0, v: 1 });
      this.end = Math.max(this.end, t1);
      end = Math.max(end, at + i * stagger + dur);
    });
    return end;
  }

  glow(n, t0, t1) {
    const shown = n.shownAt ?? this.start;
    if (!n.glow.length) n.glow.push({ t: shown - FADE, v: 0 }, { t: shown, v: 0.4 });
    n.glow.push({ t: t0, v: 0.4 }, { t: t0 + 0.3, v: 1 }, { t: t1, v: 1 }, { t: t1 + 1.2, v: 0 });
  }
}

// ---------------------------------------------------------------- chapter scripts

function rectangle(c, prefix) {
  const parts = ['xF', 'xR', 'yL', 'yR'].map((k) => `${prefix}.${k}`);
  c.show(parts);
  c.move(`${prefix}.xF`, HOLD_IN, 1.8, { from: [0, -60, 0] });
  c.move(`${prefix}.xR`, HOLD_IN, 1.8, { from: [0, 60, 0] });
  const y0 = HOLD_IN + 2.1;
  c.move(`${prefix}.yL`, y0, 2.6, { from: [-55, 0, 55], via: [0, 0, 24] });
  const yEnd = c.move(`${prefix}.yR`, y0 + 0.3, 2.6, { from: [55, 0, 55], via: [0, 0, 24] });
  return c.screws(['sFL', 'sFR', 'sRL', 'sRR'].map((k) => `${prefix}.${k}`), yEnd + 0.3);
}

/** A tray slides in on its rails and is screwed on, then its devices slide in one by one. */
export function tier(c, trayId, items) {
  c.show([trayId]);
  const trayEnd = c.move(trayId, HOLD_IN, 2.1, { from: [0, -190, 0] });
  const sEnd = c.screws(['sLlo', 'sLhi', 'sRlo', 'sRhi'].map((k) => `${trayId}.${k}`), trayEnd + 0.2);
  let at = sEnd + 0.5;
  let end = at;
  for (const it of items) {
    c.showAt([it.id], at);
    // Slide in level at the approach height, then set down: clears the tray lip and the bay above.
    const via = it.via ?? [0, 0, 12];
    end = c.move(it.id, at + 0.35, it.dur ?? 2.4, { from: [0, -200, via[2]], via, viaAt: 0.72 });
    at += it.stagger ?? 0.55;
  }
  return end;
}

export const CHAPTERS = [
  {
    id: 'bottom-rectangle',
    title: 'Bottom rectangle',
    text: 'Two M3 nuts in each yBar end. Lower yBarLeft and yBarRight onto the xBars, tall end blocks up and forward. One M3×16 per corner.',
    script: (c) => rectangle(c, 'new.rectB'),
  },
  {
    id: 'rails',
    title: 'Rails',
    text: 'A mainRail in each corner socket, holed face outward, flange on the outside. One M3×16 through each rail foot.',
    script(c) {
      const rails = [['FL', -1, -1], ['FR', 1, -1], ['RL', -1, 1], ['RR', 1, 1]];
      c.show(rails.map(([k]) => `new.rail${k}`));
      let end = 0;
      rails.forEach(([k, sx, sy], i) => {
        end = c.move(`new.rail${k}`, HOLD_IN + i * 0.3, 2.3, { from: [sx * 28, sy * 28, 120], via: [0, 0, 28] });
      });
      c.screws(rails.map(([k]) => `new.rail${k}.sB`), end + 0.3);
    },
  },
  {
    id: 'second-rectangle',
    title: 'Second rectangle',
    text: 'Build a second rectangle exactly like the first: yBarLeft left, yBarRight right, tall end blocks up and forward.',
    script: (c) => rectangle(c, 'new.rectT'),
  },
  {
    id: 'close-frame',
    title: 'Close the frame',
    text: 'Turn it over sideways so the end blocks face down and stay forward. Seat it on the rails, one M3×16 per rail.',
    script(c) {
      const g = c.get('new.rectT');
      const stage = [g.pivot[0], g.pivot[1], g.pivot[2] + RECT_LIFT];
      const flipped = g.final.q;
      const above = add3(g.final.p, [0, 0, 26]);
      const t0 = HOLD_IN;
      const end = c.path('new.rectT', [
        { at: t0, p: stage, q: ID_Q, e: 'linear' },
        { at: t0 + 2.6, p: stage, q: flipped, e: 'inOut' },
        { at: t0 + 2.9, p: stage, q: flipped, e: 'linear' },
        { at: t0 + 5.0, p: above, q: flipped, e: 'inOut' },
        { at: t0 + 5.9, p: g.final.p, q: flipped, e: 'smooth' },
      ]);
      c.screws(['FL', 'FR', 'RL', 'RR'].map((k) => `new.rail${k}.sT`), end + 0.3);
    },
  },
  {
    id: 'xy-plates',
    title: 'xyPlates',
    text: 'Four M3 nuts in the yBar plate pockets, top and bottom. Bottom plate from below, top plate from above, four M3×12 each.',
    script(c) {
      c.show(['new.plateB', 'new.plateT']);
      // slides in under the frame, then up into the plate pockets
      const b = c.move('new.plateB', HOLD_IN, 2.3, { from: [0, -150, -9], via: [0, 0, -9], viaAt: 0.7 });
      const bs = c.screws([0, 1, 2, 3].map((i) => `new.plateB.s${i}`), b + 0.2);
      const t = c.move('new.plateT', bs + 0.4, 1.9, { from: [0, 0, 80] });
      c.screws([0, 1, 2, 3].map((i) => `new.plateT.s${i}`), t + 0.2);
    },
  },
  {
    id: 'feet',
    title: 'Feet',
    text: 'Two M3 nuts in each foot. Set the frame down onto both feet, front and rear, then two M3×12 per foot from the outside.',
    script(c) {
      // The frame lifts clear, the feet slide under it along the floor, and the frame sets down on them.
      c.show(['foot.F', 'foot.R']);
      const f = c.get('new');
      const up = add3(f.final.p, [0, 0, 26]);
      const t0 = HOLD_IN;
      c.path('new', [
        { at: t0, p: f.final.p, q: f.final.q, e: 'linear' },
        { at: t0 + 1.1, p: up, q: f.final.q, e: 'inOut' },
        { at: t0 + 3.9, p: up, q: f.final.q, e: 'linear' },
        { at: t0 + 5.0, p: f.final.p, q: f.final.q, e: 'inOut' },
      ], { highlight: false });
      c.move('foot.F', t0 + 1.2, 2.3, { from: [0, -70, 0] });
      c.move('foot.R', t0 + 1.4, 2.3, { from: [0, 70, 0] });
      c.screws(['foot.F.sL', 'foot.F.sR', 'foot.R.sL', 'foot.R.sR'], t0 + 5.3);
    },
  },
  {
    id: 'joiners',
    title: 'Joiners',
    text: 'Two M3 nuts in each joiner. Plug one into each top corner socket and fix it with one M3×12 through the side.',
    script(c) {
      const ids = ['FL', 'FR', 'RL', 'RR'];
      c.show(ids.map((k) => `joiner.${k}`));
      let end = 0;
      ids.forEach((k, i) => {
        end = c.move(`joiner.${k}`, HOLD_IN + i * 0.25, 1.9, { from: [0, 0, 85], via: [0, 0, 16] });
      });
      c.screws(ids.map((k) => `joiner.${k}.slo`), end + 0.3);
    },
  },
  {
    id: 'replacement-frame',
    title: 'Matching upper frame',
    text: 'Assemble the matching replacement frame with the same rectangle, rail and plate steps. Lower it onto the joiners, end blocks forward. One M3×12 through the side into each joiner.',
    script(c) {
      c.show(['old']);
      const end = c.move('old', HOLD_IN, 3.0, { from: [0, 0, 85], via: [0, 0, 18], viaAt: 0.7 });
      c.screws(['FL', 'FR', 'RL', 'RR'].map((k) => `joiner.${k}.sup`), end + 0.3);
    },
  },
  {
    id: 'node-0',
    title: 'node-0',
    text: 'Open the rear lip between the corner ribs for the plugs. Fit the ventilated tray on holes 1 and 5, then slide node-0 in.',
    script: (c) => tier(c, 'tray.L0', [{ id: 'node0' }]),
  },
  {
    id: 'node-1',
    title: 'node-1',
    text: 'Repeat the tray lip cut-out. Fit the ventilated tray on holes 6 and 10 with four M4×12, then slide node-1 in.',
    script: (c) => tier(c, 'tray.L1', [{ id: 'node1' }]),
  },
  {
    id: 'node-2',
    title: 'node-2',
    text: 'Repeat the tray lip cut-out. Fit the ventilated tray on holes 11 and 15 with four M4×12, then slide node-2 in.',
    script: (c) => tier(c, 'tray.L2', [{ id: 'node2' }]),
  },
  {
    id: 'usb-drives', title: 'USB drives',
    text: 'Solid tray on upper holes 1 and 4. Place the Seagate and Touro side by side, with their USB sockets at the back.',
    script: (c) => tier(c, 'tray.U0', [{ id: 'usbA', via: [0, 0, 12] }, { id: 'usbB', via: [0, 0, 12] }]),
  },
  {
    id: 'switch', title: 'Eight-port switch',
    text: 'Solid tray on upper holes 5 and 8. Set the switch forward on the tray so the rear plugs and their bends have room.',
    script: (c) => tier(c, 'tray.U1', [{ id: 'switch', via: [0, 0, 10] }]),
  },
  {
    id: 'openwrt-one',
    title: 'OpenWrt One',
    text: 'Solid tray on rail holes 10 and 13, four M4×12. Slide OpenWrt One in with its antennas folded back, then tilt them behind the rack, below the top plate.',
    script(c) {
      const end = tier(c, 'tray.U2', [{ id: 'router', via: [0, 0, 10] }]);
      ANTENNA_X.forEach((_, i) => {
        const a = c.get(`router.ant${i}`);
        c.path(a.id, [
          { at: end + 0.3 + i * 0.2, p: a.final.p, q: qaxis([1, 0, 0], ANTENNA_FOLDED), e: 'linear' },
          { at: end + 1.6 + i * 0.2, p: a.final.p, q: a.final.q, e: 'inOut' },
        ]);
      });
    },
  },
  { id: 'living-placement', title: 'Onto the loose pads',
  text: 'Lower the rack onto loose grip-mat pads, rear feet 30 mm from the edge. Estimated load 7 kg; top rating assumed 20 kg. Confirm both. No screws or adhesive.', view: 'installation',
  script(c) { c.show(['zigbeeEnd', 'zigbee','spareBoard']); c.move('spareBoard',HOLD_IN,2.3,{from:[0,-380,25]}); c.end = c.start + 4.8; } },
  {
    id: 'power-bricks', title: DRILLED ? 'Bricks in the service bay' : 'Power under the unit', view: 'service',
    text: DRILLED ? 'v1 only: one drilled Ø50 mm hole in the left back panel. Deburr it and fit a 50 mm cable grommet. Rest the bricks on the steel floor, with gaps.' : 'Rest the three Lenovo bricks on the room floor under the rear half. Leave gaps between them. All doors stay shut; nothing goes through the unit.',
    script(c) {
      ['brick0', 'brick1', 'brick2'].forEach((id, i) => { c.showAt([id], 1 + i * 0.65); c.move(id, 1.2 + i * 0.65, 2.1, { from: [0, DRILLED ? -160 : 120, DRILLED ? 30 : 6], via: [0, 0, DRILLED ? 12 : 6] }); });
    },
  },
  {
    id: 'power-board',
    title: 'Power board', view: 'service',
    text: DRILLED ? 'v1 only: rest the six-outlet board on the steel shelf, switch toward the door. Plug the adapters into its end outlets.' : 'Rest the six-outlet board on the room floor, switch reachable from behind. Its two adapters sit clear of the bricks. Keep the cupboards empty of connected equipment.',
    script(c) {
      c.show(['board', 'wallSocket', 'powerline']);
      c.move('board', HOLD_IN, 2.4, { from: [45, DRILLED ? -120 : -80, 0] });
      ['psuSwitch', 'psuRouter'].forEach((id, i) => { c.showAt([id], 3.8 + i * 1.3); c.move(id, 4 + i * 1.3, 1.2, { from: [60, DRILLED ? -40 : 40, DRILLED ? 35 : 8] }); });
    },
  },
];

CHAPTERS.push({id:'retainer-kit',title:'Retainer kit',view:'kit',text:'Thread a ONE-WRAP tie around the rail and cable, pull snug, then wrap the surplus tail back onto itself and press closed. Snap a Magnet Source hook onto steel. No tools.',script(c){c.end=c.start+8.6;}});

export const WIRE_COPY = {
  spareCord:['Spare board and cord','Store the unused board with its full cord loosely coiled in the neighbouring compartment. A ONE-WRAP coil keeper hangs on a Magnet Source hook. Its plug stays disconnected.'],
  eth2: ['node-2 Ethernet', 'Plug the third node into the switch. Dress the cable down the rear-left rail with ONE-WRAP ties, then seat its rear RJ45 plug.'],
  eth1: ['node-1 Ethernet', 'Run the second node cable alongside the first. ONE-WRAP rail ties keep it flat; leave a gentle bend at both plugs.'],
  eth0: ['node-0 Ethernet', 'Connect node-0 to the switch, following ONE-WRAP rail ties to the lowest tray.'],
  lan: ['Router to switch', 'Connect OpenWrt LAN to the switch. Both sockets are at the rear; the cable bends clear of the trays.'],
  usbSeagate: ['Seagate USB', 'Plug the stock USB 3 lead into the Seagate and node-0. A ONE-WRAP coil keeper wraps the spare and the rear-left rail.'],
  usbTouro: ['Touro USB', 'Connect the second stock USB lead to the Touro and another rear USB port on node-0. A ONE-WRAP coil keeper holds it to the rear-left rail.'],
  dc0: ['node-0 power lead', 'Pay out the full Lenovo DC lead from its coil. Magnet Source hooks carry it through the drilled Ø50 mm hole (v1 only); ONE-WRAP rail ties hold it on the right rail. Seat the slim-tip plug in node-0.'],
  dc1: ['node-1 power lead', 'Keep the second Lenovo lead intact. Its spare hangs on a Magnet Source hook while the slim tip travels to node-1.'],
  dc2: ['node-2 power lead', 'Route the third full DC lead through the drilled Ø50 mm hole (v1 only) and ONE-WRAP rail ties; connect node-2.'],
  ac0: ['First mains lead', 'Connect the first NZ mains lead to the board and the brick’s cloverleaf inlet. Hang the spare with a ONE-WRAP coil keeper on a Magnet Source hook.'],
  ac1: ['Second mains lead', 'Connect the second stock mains lead, with a ONE-WRAP coil keeper and Magnet Source hook inside the steel compartment.'],
  ac2: ['Third mains lead', 'Connect the third stock mains lead. Hang the spare with a ONE-WRAP coil keeper on its Magnet Source hook.'],
  swPower: ['Switch power', 'Unwind the switch adapter’s full lead from its Magnet Source hook and seat the barrel plug at the switch’s rear.'],
  routerPower: ['Router power', 'Connect the full USB-C lead through the drilled Ø50 mm hole (v1 only). Magnet Source hooks and ONE-WRAP rail ties carry it to the router.'],
  boardCord: ['Wall power', 'Run the board’s full mains cord to the wall. Use the drilled Ø50 mm hole (v1 only); hang the spare with a ONE-WRAP coil keeper on a Magnet Source hook.'],
  wan: ['House uplink', 'Place the powerline adapter directly in the wall socket. Connect its Ethernet port to OpenWrt WAN straight up the wall gap.'],
  zigbee: ['Zigbee extension', 'Rest the Zigbee dongle at the far end of the top. Magnet Source hooks carry its extension. About 940 mm from the nearest antenna here: the maximum useful spacing, below 1 m.'],
};
if(!DRILLED) Object.assign(WIRE_COPY, {
  spareCord:['Spare board and cord','Park the unused board under the right rear end, unplugged. Its full cord has one ONE-WRAP coil keeper on an outside Magnet Source hook.'],
  dc0:['node-0 power lead','Pay out the full Lenovo DC lead. Outside Magnet Source hooks carry it up the wall gap and over the back edge; ONE-WRAP rail ties hold it at node-0.'],
  dc1:['node-1 power lead','Keep the second Lenovo lead intact. Its ONE-WRAP coil keeper hangs on an outside Magnet Source hook; the lead rolls over the back edge to node-1.'],
  dc2:['node-2 power lead','Route the full DC lead up the outside Magnet Source hooks and over the back edge. Close the ONE-WRAP rail ties, then connect node-2.'],
  ac1:['Second mains lead','Connect the second stock mains lead below the unit. A ONE-WRAP coil keeper and outside Magnet Source hook carry its spare.'],
  routerPower:['Router power','Run the full USB-C lead up the outside Magnet Source hooks, over the back edge and through ONE-WRAP rail ties to the router.'],
  boardCord:['Wall power','Run the full board cord through the wall gap to the socket. An outside Magnet Source hook and ONE-WRAP coil keeper carry its spare. Nothing enters the cupboards.'],
});
const roomCables = new Set(['boardCord', 'wan', 'zigbee', 'spareCord']);
for (const cable of CABLES.filter((c) => !roomCables.has(c.id))) {
  const [title, text] = WIRE_COPY[cable.id];
  CHAPTERS.push({ id: `wire-${cable.id}`, title, text, wire: cable.id, view: cable.kind==='ac' ? 'service' : 'rear', script(c) { c.end = c.start + 6.1; } });
}
for (const cable of CABLES.filter((c) => roomCables.has(c.id))) {
  const [title, text] = WIRE_COPY[cable.id];
  CHAPTERS.push({ id: `wire-${cable.id}`, title, text, wire: cable.id, view: cable.kind==='ac' ? 'service' : 'rear', script(c) { c.end = c.start + 6.1; } });
}
CHAPTERS.push({ id: 'snug-ties', title: 'Snug the ties',
  text: 'Press each ONE-WRAP rail tie closed without crushing the bundle. One ONE-WRAP coil keeper per stock lead; Magnet Source hooks carry the spare coils. Bricks rest by gravity.', view: 'rear',
  script(c) { c.end = c.start + 6.2; } });
CHAPTERS.push({ id: 'installed', title: 'Connected',
  text: DRILLED ? 'v1: full leads pass through one drilled Ø50 mm hole, deburred and fitted with a cable grommet. Doors shut; no lead in a door gap. Optional modification.' : 'v2: all plugs seated and full leads intact. Power stays on the room floor; Magnet Source hooks carry leads outside and over the back edge. Doors shut. No holes or leads through the unit.', view: 'installation',
  script(c) { c.end = c.start + 4.8; } });
CHAPTERS.push({ id: 'room-view', title: 'Living room',
  text: 'The rack and TV unit face the sofa. Rotate the view, pause anywhere, or rewind a chapter to inspect the wiring.', view: 'room',
  script(c) { c.end = c.start + 4.8; } });

// ---------------------------------------------------------------- build + evaluate

export function buildTimeline(data, chapterDefs = CHAPTERS, devices = [...DEVICES, ...PERIPHERALS]) {
  const nodes = new Map();
  const add = (n) => {
    if (nodes.has(n.id)) throw new Error(`duplicate node ${n.id}`);
    nodes.set(n.id, n);
    return n;
  };
  const parentOf = (g) => (g === 'world' ? null : g);

  for (const [id, g] of Object.entries(data.groups)) {
    add(node(id, parentOf(g.parent), 'group', { pivot: g.pivot, final: { p: g.p, q: g.q } }));
  }
  for (const it of data.instances) {
    const finish = it.group.startsWith('old') ? 'old' : 'new';
    add(node(it.id, parentOf(it.group), 'part', { mesh: it.part, finish, final: { p: it.p, q: it.q } }));
  }
  for (const s of data.screws) {
    add(node(s.id, parentOf(s.group), 'screw', {
      mesh: s.type, dir: s.dir, out: s.out, final: { p: s.head, q: qfromTo(SCREW_AXIS, s.dir) },
    }));
  }
  for (const d of devices) {
    add(node(d.id, null, 'device', { mesh: d.model, device: d, final: { p: d.centre, q: d.q || ID_Q } }));
    if (d.model === 'router') {
      const [, dp, h] = d.size;
      const tilt = -(d.antennaTilt ?? ANTENNA_TILT) * (Math.PI / 180); // tilted back from vertical
      ANTENNA_X.forEach((x, i) => {
        add(node(`router.ant${i}`, d.id, 'device', {
          mesh: 'antenna', final: { p: [x, dp / 2 + 3, h / 2 - 6], q: qaxis([1, 0, 0], tilt) },
        }));
      });
    }
  }

  const chapters = [];
  let t = 0;
  for (const def of chapterDefs) {
    const c = new Chapter(nodes, t, chapters.length);
    def.script(c);
    const end = Math.round((c.end + HOLD_OUT)*1e9)/1e9;
    chapters.push({ index: chapters.length, id: def.id, title: def.title, text: def.text, start: t, end, wire: def.wire, view: def.view });
    t = end;
  }

  for (const n of nodes.values()) {
    n.keys.sort((a, b) => a.t - b.t);
    n.alpha.sort((a, b) => a.t - b.t);
    n.glow.sort((a, b) => a.t - b.t);
    if (!n.keys.length) n.keys.push({ t: 0, p: n.final.p, q: n.final.q, e: 'linear' });
  }

  // Parents before children, so world transforms can be composed in one pass.
  const order = [];
  const seen = new Set();
  const visit = (n) => {
    if (seen.has(n.id)) return;
    if (n.parent) visit(nodes.get(n.parent));
    seen.add(n.id);
    order.push(n.id);
  };
  for (const n of nodes.values()) visit(n);

  // Every renderable node must be hidden until some chapter introduces it.
  for (const n of nodes.values()) {
    if (n.kind === 'group') continue;
    let a = n;
    while (a && !a.alpha.length) a = a.parent ? nodes.get(a.parent) : null;
    if (!a) throw new Error(`node ${n.id} is never introduced by a chapter`);
  }

  return { duration: t, chapters, nodes, order };
}

function sampleScalar(keys, t, fallback) {
  const n = keys.length;
  if (!n) return fallback;
  if (t <= keys[0].t) return keys[0].v;
  if (t >= keys[n - 1].t) return keys[n - 1].v;
  let i = 1;
  while (keys[i].t < t) i++;
  const a = keys[i - 1];
  const b = keys[i];
  const span = b.t - a.t;
  const s = span > 0 ? EASE.smooth((t - a.t) / span) : 1;
  return a.v + (b.v - a.v) * s;
}

function samplePose(keys, t, out) {
  const n = keys.length;
  if (t <= keys[0].t) {
    out.p = keys[0].p;
    out.q = keys[0].q;
    return out;
  }
  if (t >= keys[n - 1].t) {
    out.p = keys[n - 1].p;
    out.q = keys[n - 1].q;
    return out;
  }
  let i = 1;
  while (keys[i].t < t) i++;
  const a = keys[i - 1];
  const b = keys[i];
  const span = b.t - a.t;
  const s = span > 0 ? EASE[b.e]((t - a.t) / span) : 1;
  out.p = lerp3(a.p, b.p, s, out.pBuf || (out.pBuf = [0, 0, 0]));
  out.q = slerp(a.q, b.q, s, out.qBuf || (out.qBuf = [0, 0, 0, 1]));
  return out;
}

/** Fill `out` (Map id -> state) with the pose, opacity and highlight of every node at time t. */
export function evaluate(tl, time, out = new Map()) {
  const t = clamp(time, 0, tl.duration);
  for (const id of tl.order) {
    const n = tl.nodes.get(id);
    let s = out.get(id);
    if (!s) {
      s = { p: null, q: null, alpha: 1, glow: 0 };
      out.set(id, s);
    }
    samplePose(n.keys, t, s);
    let alpha = sampleScalar(n.alpha, t, 1);
    let glow = sampleScalar(n.glow, t, 0);
    if (n.parent) {
      const ps = out.get(n.parent);
      alpha *= ps.alpha;
      glow = Math.max(glow, ps.glow);
    }
    s.alpha = alpha;
    s.glow = glow;
  }
  return out;
}

export function chapterAt(tl, time) {
  const cs = tl.chapters;
  if (time >= tl.duration) return cs.length - 1;
  let lo = 0;
  let hi = cs.length - 1;
  while (lo < hi) {
    const mid = (lo + hi + 1) >> 1;
    if (cs[mid].start <= time) lo = mid;
    else hi = mid - 1;
  }
  return lo;
}
