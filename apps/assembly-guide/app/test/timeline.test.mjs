import { test } from 'node:test';
import assert from 'node:assert/strict';
import { evaluate, chapterAt, FADE } from '../src/timeline.js';
import { buildSoyrackTimeline } from '../src/soyrack/index.js';
import { meshes } from './helpers.mjs';

const tl = buildSoyrackTimeline(meshes);
const renderable = [...tl.nodes.values()].filter((n) => n.kind !== 'group');

function snapshot(t) {
  const out = new Map();
  for (const [id, s] of evaluate(tl, t)) out.set(id, { p: [...s.p], q: [...s.q], alpha: s.alpha, glow: s.glow });
  return out;
}

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
  const times = [0, 3.3, 17.2, 31.05, 64.4, 90, 118.7, 175.5, tl.duration];
  const fresh = times.map((t) => snapshot(t));
  const reordered = [...times].reverse().map((t) => [t, snapshot(t)]);
  for (const [t, snap] of reordered) {
    const ref = fresh[times.indexOf(t)];
    for (const [id, s] of snap) assert.deepEqual(s, ref.get(id), `${id} at ${t}`);
  }
});

// Contract: whatever a chapter brings in is in its place when the chapter ends, so the next
// chapter starts from a finished step.
test('each chapter leaves the parts it introduces in their place', () => {
  for (const c of tl.chapters) {
    const before = snapshot(Math.max(0, c.start - FADE - 0.01));
    const settled = snapshot(c.end - FADE - 0.01);
    const atEnd = snapshot(c.end - 0.001);
    for (const n of renderable) {
      const b = before.get(n.id);
      const e = settled.get(n.id);
      if (e.alpha > 0.5 && (b.alpha < 0.01 || c.index === 0)) {
        const p = atEnd.get(n.id).p;
        const d = Math.hypot(p[0] - n.final.p[0], p[1] - n.final.p[1], p[2] - n.final.p[2]);
        assert.ok(d < 0.01, `${n.id} in place by the end of "${c.title}" (off by ${d.toFixed(3)} mm)`);
      }
    }
  }
});

test('visible parts move continuously: no jumps while shown, forward or backward', () => {
  const dt = 1 / 60;
  let prev = snapshot(0);
  let worst = { v: 0, id: '', t: 0 };
  for (let t = dt; t <= tl.duration; t += dt) {
    const cur = snapshot(t);
    for (const n of renderable) {
      const a = prev.get(n.id);
      const b = cur.get(n.id);
      if (a.alpha > 0.02 && b.alpha > 0.02) {
        const step = Math.hypot(b.p[0] - a.p[0], b.p[1] - a.p[1], b.p[2] - a.p[2]);
        if (step > worst.v) worst = { v: step, id: n.id, t };
      }
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
