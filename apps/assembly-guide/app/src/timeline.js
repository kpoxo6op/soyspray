// Deterministic assembly timeline. Every visible state is a pure function of time, so seeking,
// pausing and reverse playback all read the same keyframes. Coordinates are rack millimetres
// (x left -> right, y front -> rear, z up), offsets are expressed in the parent node's frame.

import { add3, scale3, qfromTo, lerp3, slerp, EASE, clamp } from './math.js';

export const FADE = 0.6; // new parts fade in during the last 0.6 s of the previous chapter
export const HOLD_IN = 0.9; // pause on the staged parts before anything moves
export const HOLD_OUT = 1.7; // pause on the finished step

const ID_Q = [0, 0, 0, 1];
const SCREW_AXIS = [0, 1, 0]; // screw model: head at the origin, shaft along +Y

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

// ---------------------------------------------------------------- build + evaluate

export function buildTimeline(data, chapterDefs, devices = []) {
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
    add(node(it.id, parentOf(it.group), 'part', { mesh: it.part, final: { p: it.p, q: it.q } }));
  }
  for (const s of data.screws) {
    add(node(s.id, parentOf(s.group), 'screw', {
      mesh: s.type, dir: s.dir, out: s.out, final: { p: s.head, q: s.q ?? qfromTo(SCREW_AXIS, s.dir) },
    }));
  }
  // A device may ride in a group (its centre is then in the group's frame), like a part.
  for (const d of devices) {
    add(node(d.id, d.group ? parentOf(d.group) : null, 'device', { mesh: d.model, device: d, final: { p: d.centre, q: d.q || ID_Q } }));
  }

  const chapters = [];
  let t = 0;
  for (const def of chapterDefs) {
    const c = new Chapter(nodes, t, chapters.length);
    def.script(c);
    const end = Math.round((c.end + HOLD_OUT)*1e9)/1e9;
    chapters.push({
      index: chapters.length, id: def.id, title: def.title, text: def.text, start: t, end, view: def.view, tags: def.tags || [],
      section: def.section || null, legend: def.legend || null,
    });
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
