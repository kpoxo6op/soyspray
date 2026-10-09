// Deterministic assembly timeline. Every visible state is a pure function of time, so seeking,
// pausing and reverse playback all read the same keyframes. Coordinates are rack millimetres
// (x left -> right, y front -> rear, z up), offsets are expressed in the parent node's frame.

import { add3, scale3, qaxis, qfromTo, lerp3, slerp, EASE, clamp } from './math.js';
import { DEVICES } from './layout.js';

export const FADE = 0.6; // new parts fade in during the last 0.6 s of the previous chapter
export const HOLD_IN = 0.9; // pause on the staged parts before anything moves
export const HOLD_OUT = 1.7; // pause on the finished step

const ID_Q = [0, 0, 0, 1];
const SCREW_AXIS = [0, 1, 0]; // screw model: head at the origin, shaft along +Y
const RECT_LIFT = 322; // the second rectangle is built this far above the bottom one (clears the rails when turned)

const ANTENNA_X = [-62, 0, 62];
const ANTENNA_FINAL = -50 * (Math.PI / 180); // tilted back from vertical
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

function tier(c, trayId, items) {
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
    id: 'frame-2024',
    title: '2024 frame on top',
    text: 'Lower the 2024 frame onto the joiners, end blocks forward. One M3×12 through the side into each joiner.',
    script(c) {
      c.show(['old']);
      const end = c.move('old', HOLD_IN, 3.0, { from: [0, 0, 85], via: [0, 0, 18], viaAt: 0.7 });
      c.screws(['FL', 'FR', 'RL', 'RR'].map((k) => `joiner.${k}.sup`), end + 0.3);
    },
  },
  {
    id: 'node-0',
    title: 'node-0',
    text: 'Ventilated tray on front-rail holes 1 and 5 from the bottom, four M4×12 into M4 nuts. Set node-0 on it, front panel forward.',
    script: (c) => tier(c, 'tray.L0', [{ id: 'node0' }]),
  },
  {
    id: 'node-1',
    title: 'node-1',
    text: 'Ventilated tray on rail holes 6 and 10, four M4×12. Set node-1 on it, front panel forward.',
    script: (c) => tier(c, 'tray.L1', [{ id: 'node1' }]),
  },
  {
    id: 'node-2',
    title: 'node-2',
    text: 'Ventilated tray on rail holes 11 and 15, four M4×12. Set node-2 on it, front panel forward.',
    script: (c) => tier(c, 'tray.L2', [{ id: 'node2' }]),
  },
  {
    id: 'power-bricks',
    title: 'Power bricks',
    text: 'Upper bay: solid tray on rail holes 1 and 4, four M4×12. Lay the three power bricks side by side.',
    script: (c) => tier(c, 'tray.U0', [
      { id: 'brick0', via: [0, 0, 10] },
      { id: 'brick1', via: [0, 0, 10] },
      { id: 'brick2', via: [0, 0, 10] },
    ]),
  },
  {
    id: 'switch-drives',
    title: 'Switch and drives',
    text: 'Solid tray on rail holes 5 and 8, four M4×12. Both USB drives stacked at the back right, then the switch front left, ports forward.',
    script: (c) => tier(c, 'tray.U1', [
      { id: 'usbA', via: [0, 0, 10], stagger: 0.75 },
      { id: 'usbB', via: [0, 0, 14], stagger: 0.75 },
      { id: 'switch', via: [0, 0, 10] },
    ]),
  },
  {
    id: 'openwrt-one',
    title: 'OpenWrt One',
    text: 'Solid tray on rail holes 10 and 13, four M4×12. Slide OpenWrt One in with its antennas folded back, then tilt them up behind the rack.',
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
  {
    id: 'power-board',
    title: 'Power board',
    text: 'The power board stays outside the rack, on the right, plugs within reach.',
    script(c) {
      c.show(['board']);
      c.move('board', HOLD_IN, 2.4, { from: [45, -120, 0] });
    },
  },
];

// ---------------------------------------------------------------- build + evaluate

export function buildTimeline(data, chapterDefs = CHAPTERS) {
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
  for (const d of DEVICES) {
    add(node(d.id, null, 'device', { mesh: d.model, device: d, final: { p: d.centre, q: ID_Q } }));
    if (d.model === 'router') {
      const [w, dp, h] = d.size;
      ANTENNA_X.forEach((x, i) => {
        add(node(`router.ant${i}`, d.id, 'device', {
          mesh: 'antenna', final: { p: [x, dp / 2 + 3, h / 2 - 6], q: qaxis([1, 0, 0], ANTENNA_FINAL) },
        }));
      });
      void w;
    }
  }

  const chapters = [];
  let t = 0;
  for (const def of chapterDefs) {
    const c = new Chapter(nodes, t, chapters.length);
    def.script(c);
    const end = c.end + HOLD_OUT;
    chapters.push({ index: chapters.length, id: def.id, title: def.title, text: def.text, start: t, end });
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
