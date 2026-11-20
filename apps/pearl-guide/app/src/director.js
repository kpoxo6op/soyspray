import { clamp } from './anim.js';
import { mixPose } from './stage.js';

/** Absolute times for chapters and beats. */
export function buildTimeline(chapters) {
  let t = 0;
  const out = chapters.map((c, ci) => {
    const start = t;
    const beats = c.beats.map((b, bi) => {
      const bs = t;
      t += b.d;
      return { ...b, start: bs, end: t, index: bi };
    });
    return { ...c, index: ci, start, end: t, beats, text: c.beats[0].text };
  });
  return { chapters: out, duration: t };
}

/** Pose the cast, camera and labels for playhead time t. Returns the beat on screen. */
export function makeDirector(stage, S, timeline) {
  const { chapters, duration } = timeline;
  let lastChapter = -1;
  return function apply(t) {
    const tt = clamp(t, 0, duration);
    let ci = chapters.findIndex((c) => tt < c.end);
    if (ci < 0) ci = chapters.length - 1;
    const c = chapters[ci];
    let bi = c.beats.findIndex((b) => tt < b.end);
    if (bi < 0) bi = c.beats.length - 1;
    const beat = c.beats[bi];
    S.t = tt;
    S.reset();
    stage.setBench(c.bench);
    const k = tt - c.start;
    c.setup?.(S, k);
    for (let i = 0; i <= bi; i++) {
      const b = c.beats[i];
      const local = i < bi ? b.d : tt - b.start;
      b.act?.(S, clamp(local / b.d), local);
    }
    c.after?.(S);
    S.commit();
    // camera: cut at a new chapter, glide between beats, drift within a beat
    const kb = tt - beat.start;
    const u = clamp(kb / beat.d);
    const target = beat.cam2 ? mixPose(beat.cam, beat.cam2, u) : beat.cam;
    let pose = target;
    if (bi > 0) {
      const prev = c.beats[bi - 1];
      const from = prev.cam2 || prev.cam;
      pose = mixPose(from, target, clamp(kb / (beat.move ?? 1.6)));
    }
    if (ci !== lastChapter) {
      lastChapter = ci;
      stage.setPristine(true);
    }
    stage.setPose(pose);
    stage.setLabels(beat.labels ? beat.labels(S, u) : []);
    return { chapter: c, beat, u };
  };
}
