import { test } from 'node:test';
import assert from 'node:assert/strict';
import { buildTimeline, evaluate, chapterAt, FADE } from '../src/timeline.js';
import { qrotate } from '../src/math.js';
import { placements } from './helpers.mjs';

const tl = buildTimeline(placements);
const renderable = [...tl.nodes.values()].filter((n) => n.kind !== 'group');

function snapshot(t) {
  const out = new Map();
  for (const [id, s] of evaluate(tl, t)) out.set(id, { p: [...s.p], q: [...s.q], alpha: s.alpha, glow: s.glow });
  return out;
}

// World position of a node's origin, composing parent groups (pivot-centred) like the renderer does.
function worldPos(states, id) {
  const n = tl.nodes.get(id);
  const s = states.get(id);
  let p = s.p;
  let parentId = n.parent;
  while (parentId) {
    const pn = tl.nodes.get(parentId);
    const ps = states.get(parentId);
    const local = pn.kind === 'group' ? [p[0] - pn.pivot[0], p[1] - pn.pivot[1], p[2] - pn.pivot[2]] : p;
    const r = qrotate(ps.q, local);
    p = [r[0] + ps.p[0], r[1] + ps.p[1], r[2] + ps.p[2]];
    parentId = pn.parent;
  }
  return p;
}

test('chapters tile the timeline without gaps', () => {
  assert.equal(tl.chapters[0].start, 0);
  for (let i = 1; i < tl.chapters.length; i++) assert.equal(tl.chapters[i].start, tl.chapters[i - 1].end);
  assert.equal(tl.chapters.at(-1).end, tl.duration);
  const sum = tl.chapters.reduce((a, c) => a + (c.end - c.start), 0);
  assert.ok(Math.abs(sum - tl.duration) < 1e-9);
  for (const c of tl.chapters) {
    assert.ok(c.end - c.start >= 4.5, `${c.title} long enough to follow`);
  }
});

test('chapter markers resolve exactly at their boundaries', () => {
  for (const c of tl.chapters) {
    assert.equal(chapterAt(tl, c.start), c.index);
    assert.equal(chapterAt(tl, c.start + 0.001), c.index);
    if (c.index > 0) assert.equal(chapterAt(tl, c.start - 0.001), c.index - 1);
  }
  assert.equal(chapterAt(tl, tl.duration), tl.chapters.length - 1);
  // Scrubber segments are sized by duration, so marker fractions equal start / duration.
  const fractions = tl.chapters.map((c) => c.start / tl.duration);
  for (let i = 1; i < fractions.length; i++) assert.ok(fractions[i] > fractions[i - 1]);
});

test('state is a pure function of time (seek order does not matter)', () => {
  const times = [0, 3.3, 17.2, 31.05, 64.4, 90, 118.7, tl.duration];
  const fresh = times.map((t) => snapshot(t));
  // Visit the same times in reverse and interleaved order.
  const reordered = [...times].reverse().map((t) => [t, snapshot(t)]);
  for (const [t, snap] of reordered) {
    const ref = fresh[times.indexOf(t)];
    for (const [id, s] of snap) assert.deepEqual(s, ref.get(id), `${id} at ${t}`);
  }
});

test('start shows only the first chapter; end shows everything assembled', () => {
  const start = snapshot(0);
  const visible = renderable.filter((n) => start.get(n.id).alpha > 0.01).map((n) => n.id).sort();
  assert.deepEqual(visible, ['new.rectB.xF', 'new.rectB.xR', 'new.rectB.yL', 'new.rectB.yR']);
  const end = snapshot(tl.duration);
  for (const n of renderable) {
    const s = end.get(n.id);
    assert.ok(s.alpha > 0.999, `${n.id} visible at end`);
    assert.ok(s.glow < 1e-6, `${n.id} settled at end`);
    for (let k = 0; k < 3; k++) assert.ok(Math.abs(s.p[k] - n.final.p[k]) < 1e-6, `${n.id} final position`);
  }
  for (const id of ['new', 'new.rectT', 'old', 'old.rectT']) {
    const g = tl.nodes.get(id);
    const s = end.get(id);
    for (let k = 0; k < 3; k++) assert.ok(Math.abs(s.p[k] - g.final.p[k]) < 1e-6, `${id} final position`);
  }
});

test('each chapter introduces its parts and leaves them assembled', () => {
  for (const c of tl.chapters.filter(c => !c.wire && !['zip-ties','installed','room-view'].includes(c.id))) {
    const before = snapshot(Math.max(0, c.start - FADE - 0.01));
    // Sample before the next chapter's parts start fading in.
    const settled = snapshot(c.end - FADE - 0.01);
    const atEnd = snapshot(c.end - 0.001);
    let introduced = 0;
    for (const n of renderable) {
      const b = before.get(n.id);
      const e = settled.get(n.id);
      if (e.alpha > 0.5 && (b.alpha < 0.01 || c.index === 0)) {
        introduced++;
        // Introduced during this chapter: by the end it sits in its final place within its parent
        // (the second rectangle is then turned over as a whole in the next chapter).
        const p = atEnd.get(n.id).p;
        const d = Math.hypot(p[0] - n.final.p[0], p[1] - n.final.p[1], p[2] - n.final.p[2]);
        assert.ok(d < 0.01, `${n.id} final by end of "${c.title}" (off by ${d.toFixed(3)} mm)`);
      }
    }
    assert.ok(introduced > 0 || c.id === 'close-frame', `"${c.title}" introduces parts`);
    for (const g of ['new', 'new.rectT', 'old']) {
      const n = tl.nodes.get(g);
      const last = n.keys.at(-1).t;
      if (last > c.start && last <= c.end) {
        const q = atEnd.get(g).p;
        assert.ok(Math.hypot(q[0] - n.final.p[0], q[1] - n.final.p[1], q[2] - n.final.p[2]) < 0.01, `${g} seated by end of "${c.title}"`);
      }
    }
  }
});

test('visible parts move continuously: no jumps while shown, forward or backward', () => {
  const dt = 1 / 60;
  let prev = snapshot(0);
  let prevW = new Map(renderable.map((n) => [n.id, worldPos(prev, n.id)]));
  let worst = { v: 0, id: '', t: 0 };
  for (let t = dt; t <= tl.duration; t += dt) {
    const cur = snapshot(t);
    for (const n of renderable) {
      const a = prev.get(n.id).alpha;
      const b = cur.get(n.id).alpha;
      const w = worldPos(cur, n.id);
      if (a > 0.02 && b > 0.02) {
        const pw = prevW.get(n.id);
        const step = Math.hypot(w[0] - pw[0], w[1] - pw[1], w[2] - pw[2]);
        if (step > worst.v) worst = { v: step, id: n.id, t };
      }
      prevW.set(n.id, w);
    }
    prev = cur;
  }
  // 60 fps step limit: about 9 mm per frame (~540 mm/s), well below a teleport.
  assert.ok(worst.v < 9, `largest per-frame step ${worst.v.toFixed(2)} mm (${worst.id} at ${worst.t.toFixed(2)} s)`);
});

test('reverse playback retraces forward playback exactly', () => {
  const ts = [];
  for (let t = 0; t <= tl.duration; t += 0.37) ts.push(t);
  const forward = ts.map((t) => snapshot(t));
  const backward = [...ts].reverse().map((t) => snapshot(t)).reverse();
  forward.forEach((f, i) => {
    for (const [id, s] of f) assert.deepEqual(backward[i].get(id), s);
  });
});

test('the second rectangle is turned over about the front-rear axis', () => {
  const g = tl.nodes.get('new.rectT');
  // final rotation = 180 degrees about +y (front-rear) in rack coordinates
  assert.ok(Math.abs(Math.abs(g.final.q[1]) - 1) < 1e-6);
  const c = tl.chapters.find((x) => x.id === 'close-frame');
  const mid = snapshot(c.start + 0.9 + 1.3);
  const q = mid.get('new.rectT').q;
  assert.ok(Math.abs(q[0]) < 1e-6 && Math.abs(q[2]) < 1e-6, 'rotation stays about y');
  assert.ok(Math.abs(q[1]) > 0.3 && Math.abs(q[1]) < 0.95, 'half way through the turn');
});

test('trays land with their ear holes on the documented rail holes', () => {
  const holes = placements.trayHoles;
  const tray = (id) => tl.nodes.get(id).final.p[2];
  // Tray mesh centre z = lowest ear hole - 1.5 (base top) + centre offset of the mesh.
  const ventCentre = placements.parts.trayVent.centre[2];
  const upCentre = placements.parts.trayUpper.centre[2];
  holes.lower.forEach((k, i) => assert.ok(Math.abs(tray(`tray.L${i}`) - (25 + 10 * (k - 1) - 1.5 + ventCentre)) < 1e-3));
  holes.upper.forEach((k, i) => assert.ok(Math.abs(tray(`tray.U${i}`) - (225 + 10 * (k - 1) - 1.5 + upCentre)) < 1e-3));
  const lowerTexts = tl.chapters.filter((c) => c.id.startsWith('node-')).map((c) => c.text);
  assert.match(lowerTexts[0], /holes 1 and 5/);
  assert.match(lowerTexts[1], /holes 6 and 10/);
  assert.match(lowerTexts[2], /holes 11 and 15/);
  const upperTexts = ['usb-drives', 'switch', 'openwrt-one'].map((id) => tl.chapters.find((c) => c.id === id).text);
  assert.match(upperTexts[0], /holes 1 and 4/);
  assert.match(upperTexts[1], /holes 5 and 8/);
  assert.match(upperTexts[2], /holes 10 and 13/);
});
