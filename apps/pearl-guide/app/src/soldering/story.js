// The soldering page: six chapters, 39 beats, about six minutes a loop (design-teaching.md section 3). Each beat
// has one caption, a camera, optional labels and an act(S, u, k) that poses the cast for progress u (0..1) or k
// seconds into the beat. Nothing keeps state between frames: every frame resets the cast and replays the chapter up
// to the playhead, so scrubbing and rewinding are exact.
//
// Conventions: the iron always comes from the right and the solder from the left; no drawn hands, the grip is a
// label; the tip glows only while the iron is on; smoke rises only while solder or flux is on heat; counting is one
// strong label that changes text. The practice board stands in for his traffic-light kit until it is measured.
//
// Must import in plain Node (tools/extract-guides.mjs, the tests): nothing touches document or window up here.

import { Vector3 } from 'three';
import { clamp, drop, easeInOut, easeOut, lerp, mix3, smooth, span } from '../anim.js';
import { buildTimeline } from '../story.js'; // moves to '../director.js' with the seam

export const GUIDE = {
  slug: 'soldering',
  title: 'Soldering, first joints',
  summary: 'Set up the pen iron, make and fix your first joints, build the traffic-light kit, join two wires and solder Pearl-size pads.',
  section: 'First joints',
  lede: 'Six short chapters for the bench, about 6 minutes a loop. Each one ends at a checkpoint and a fine place to stop.',
};

const MM = 0.001;
const TAU = Math.PI * 2;
const v3 = (a) => new Vector3(a[0], a[1], a[2]);
const add3 = (a, b) => [a[0] + b[0], a[1] + b[1], a[2] + b[2]];

// ---------------------------------------------------------------- bench layout (metres, bench top y = 0)
const MAT_Y = 0.002;
const TH = [0, 0, -0.03]; // helping hands base
const METER = [-0.145, MAT_Y, -0.035];
const STAND = [0.135, -0.07];
const STAND_YAW = 0.5;
const REST_PITCH = 0.816; // along the stand's spring
const KIT_AT = [-0.01, MAT_Y, 0.07]; // the practice board lying on the mat
const AIR = [0.085, 0.08, -0.005]; // where the iron is held to tin and wipe, in front of the stand

/** A point in the stand's own millimetres, as world metres. */
function standPt(x, y, z) {
  const c = Math.cos(STAND_YAW);
  const s = Math.sin(STAND_YAW);
  return [STAND[0] + (x * c + z * s) * MM, y * MM, STAND[1] + (-x * s + z * c) * MM];
}
const IRON_REST = standPt(15, 21, 0);
const SPONGE = standPt(-25, 23.5, 0);
const REST = { p: IRON_REST, yaw: STAND_YAW, pitch: REST_PITCH };

/** A point on the iron: `along` mm from the tip's end up its axis, `up` mm towards the screen side. */
function ironPt(pose, along, up = 0) {
  const { p, yaw, pitch } = pose;
  const cy = Math.cos(yaw);
  const sy = Math.sin(yaw);
  const ax = [Math.cos(pitch) * cy, Math.sin(pitch), -Math.cos(pitch) * sy];
  const nu = [-Math.sin(pitch) * cy, Math.cos(pitch), Math.sin(pitch) * sy];
  return [p[0] + (ax[0] * along + nu[0] * up) * MM, p[1] + (ax[1] * along + nu[1] * up) * MM, p[2] + (ax[2] * along + nu[2] * up) * MM];
}

function ironTo(S, pose) {
  return S.iron(pose.p, pose.yaw, pose.pitch);
}

function mixIron(a, b, t) {
  return { p: mix3(a.p, b.p, t), yaw: lerp(a.yaw, b.yaw, t), pitch: lerp(a.pitch, b.pitch, t) };
}

/** The iron hot and on its stand, the screen at 330 °C. */
function ironOn(S, tin = 1) {
  ironTo(S, REST);
  S.tip({ tin, heat: 1 });
  S.screen('330');
}

// ---------------------------------------------------------------- the work-holding frame (see scene.js)
// In the helping hands the board's short edges sit in the two back clips, about 75 mm up, tilted 20° towards the
// camera about the line between the clips. Frame millimetres: x to the right, y up off the board's underside,
// z towards the camera. The practice board's pads are on top (y 1.65 mm), parts hang underneath.
const TILT = 0.35;
const FRAME = { p: [0, 0.0752, -0.037], rx: TILT };
const FLIP = { p: FRAME.p, rx: TILT + Math.PI }; // component side up
const ON_MAT = { p: [KIT_AT[0], MAT_Y + 0.0017, KIT_AT[2]], rx: Math.PI }; // lying on the mat, component side up
const PAD = 1.65;

/** Frame millimetres to world metres for a frame pose (pure maths, for cameras). */
function fw(x, y, z, f = FRAME) {
  const c = Math.cos(f.rx);
  const s = Math.sin(f.rx);
  return [f.p[0] + x * MM, f.p[1] + (y * c - z * s) * MM, f.p[2] + (y * s + z * c) * MM];
}
const fwa = (a, f) => fw(a[0], a[1], a[2], f);

function setFrame(S, f) {
  S.a('frame').at(f.p[0], f.p[1], f.p[2]).turn(0, f.rx, 0);
}

function blendFrame(a, b, t, lift = 0) {
  const p = mix3(a.p, b.p, t);
  p[1] += lift * Math.sin(Math.PI * clamp(t));
  return { p, rx: lerp(a.rx, b.rx, t) };
}

/** A camera looking at frame point J from frame offset d (mm). */
function fcam(J, d, fov = 28, f = FRAME) {
  return { p: fwa(add3(J, d), f), t: fwa(J, f), fov };
}

/** In-frame placement: S.a(name) at frame millimetres. */
function put(S, name, x, y, z, a = 1) {
  return S.a(name).show(a).at(x * MM, y * MM, z * MM);
}

function board(S, f = FRAME) {
  setFrame(S, f);
  put(S, 'practice_board', 0, 0, 0).turn(Math.PI / 2);
  S.a('third_hand').show().at(...TH);
}

// first joint: a resistor across holes 10.16 mm apart, its legs up through the pads
const RES = [1.27, -1.25, -1.27];
const J1 = [-3.81, PAD, -1.27];
const J2 = [6.35, PAD, -1.27];
const CONE = 2.0; // joint height (1.55 mm profile drawn at 1.3)
const LEG_CUT = PAD + CONE + 1.25; // a trimmed leg, mm above the resistor's axis

/** The iron's tip on a pad with the side of the tip against the leg, the handle up and to the right. */
function ironOnPad(S, J) {
  const p = S.W(J[0] + 0.75, J[1] + 0.45, J[2] + 0.5);
  return { p: [p.x, p.y, p.z], yaw: -0.55, pitch: 0.62 };
}
function ironOffPad(S, J) {
  const on = ironOnPad(S, J);
  return { ...on, p: add3(on.p, [0.03, 0.035, 0.02]) };
}

/** Solder wire tip at world p, arriving from the left. */
function solderAt(S, p, rz = 0.45) {
  S.a('solder').show().at(p[0], p[1], p[2]).turn(Math.PI, 0, rz);
}
function solderPad(S, J, f) {
  // touches the pad on the far side of the leg from the iron; f 0 is 18 mm out
  const near = S.W(J[0] - 0.75, J[1] + 0.35, J[2] - 0.35);
  const far = S.W(J[0] - 14, J[1] + 9, J[2] - 3);
  return mix3([far.x, far.y, far.z], [near.x, near.y, near.z], f);
}

function joint(S, name, J, g, size = 1) {
  if (g <= 0) return;
  put(S, name, J[0], J[1] - 0.05, J[2]).size([size * (0.35 + 0.65 * g), size * Math.max(0.02, g), size * (0.35 + 0.65 * g)]);
}

const count = (u, a, b, c) => (u > a && u < c ? (u < b ? 'one' : 'two') : null);

function L(id, text, at, side = 'r', strong = false) {
  return { id, text, at, side, strong };
}

function smokeAt(S, p, strength, k) {
  S.smoke(p.isVector3 ? p : v3(p), strength, k);
}

// ---------------------------------------------------------------- the meter and its probes
function probes(S, a, red, black) {
  S.a('multimeter').show().at(...METER);
  const up = 0.03 * (1 - a);
  const tilt = (p, rz) => [p[0], p[1] + 0.0004 + up, p[2], rz];
  const tops = [];
  for (const [n, [x, y, z, rz]] of [['probeR', tilt(red, 0.3)], ['probeB', tilt(black, -0.3)]]) {
    S.a(n).show().at(x, y, z).turn(0, -0.35, rz);
    tops.push(v3([x - 0.08 * Math.sin(rz), y + 0.08 * Math.cos(rz) * Math.cos(0.35), z - 0.08 * Math.cos(rz) * Math.sin(0.35)]));
  }
  const jack = (dx) => v3([METER[0] + dx, MAT_Y + 0.036, METER[2] + 0.058]);
  S.a('cordR').show().obj.userData.setEnds(tops[0], jack(0.006));
  S.a('cordB').show().obj.userData.setEnds(tops[1], jack(-0.018));
}
const meterKnobAt = (S) => S.node('multimeter', null, [0, 0.042, 0.014]);
const meterSideAt = (S) => S.node('multimeter', null, [0.026, 0.037, -0.039]); // right edge of the screen

// ---------------------------------------------------------------- chapter 1
const LAYOUT = [
  ['third_hand', ...TH, 0],
  ['multimeter', ...METER, 0],
  ['stand', STAND[0], 0, STAND[1], STAND_YAW],
  ['solder_tube', -0.185, MAT_Y + 0.0075, 0.06, 0],
  ['flux_pen', -0.185, MAT_Y + 0.007, 0.085, 0],
  ['practice_board', KIT_AT[0], KIT_AT[1], KIT_AT[2], Math.PI / 2],
  ['cutters', 0.03, MAT_Y + 0.004, 0.06, 0],
  ['tweezers', 0.03, MAT_Y + 0.0004, 0.088, 0],
  ['braid', 0.165, MAT_Y, 0.025, Math.PI],
];
const IRON_MAT = { p: [-0.05, MAT_Y + 0.012, 0.113], yaw: 0, pitch: 0 }; // lying on the mat, cold

/** The board is in the frame, so on the mat it is posed through the frame. */
function lay(S, list, u, stagger = 0.06) {
  list.forEach(([name, x, y, z, ry = 0], i) => {
    const local = clamp((u - i * stagger) / 0.35);
    if (local <= 0) return;
    const { dy, alpha } = drop(local, 0.06);
    if (name === 'practice_board') {
      setFrame(S, { p: [x, y + dy, z], rx: 0 });
      put(S, 'practice_board', 0, 0, 0, alpha).turn(ry);
    } else S.a(name).show(alpha).at(x, y + dy, z).turn(ry);
  });
  const local = clamp((u - list.length * stagger) / 0.35);
  if (local > 0) {
    const { dy, alpha } = drop(local, 0.06);
    S.iron(add3(IRON_MAT.p, [0, dy, 0]), IRON_MAT.yaw, IRON_MAT.pitch, alpha);
  }
}

const bench = {
  id: 'bench',
  title: 'Set up the bench',
  goal: 'A safe bench and an iron at 330 °C.',
  work: '10 minutes',
  bench: true,
  beats: [
    {
      d: 10,
      text: 'Lay the tools on the silicone mat. Keep food and drink off the bench: this solder contains lead.',
      cam: { p: [0.02, 0.46, 0.4], t: [0.0, 0.0, 0.01], fov: 34 },
      cam2: { p: [0.0, 0.44, 0.43], t: [0.0, 0.0, 0.01], fov: 34 },
      act(S, u) {
        lay(S, LAYOUT, u * 1.2);
      },
      labels: (S, u) =>
        u > 0.72
          ? [
              L('iron', 'pen iron', S.a('iron').obj.userData.grip, 'b'),
              L('solder', '60/40 solder, 0.8 mm', S.node('solder_tube'), 't'),
              L('flux', 'flux pen', S.node('flux_pen'), 'b'),
              L('hands', 'helping hands', S.node('third_hand'), 't'),
              L('kit', 'practice kit', S.F(0, 2, 0), 't'),
            ]
          : [],
    },
    {
      d: 9,
      text: 'Put glasses on and open a window. The smoke is burnt flux and should drift away from your face.',
      cam: { p: [-0.05, 0.13, 0.42], t: [-0.03, 0.035, 0.0], fov: 32 },
      act(S, u, k) {
        const { dy, alpha } = drop(span(u, 0.05, 0.4), 0.05);
        S.a('glasses').show(alpha).at(-0.075, MAT_Y + dy, 0.122);
        // one wisp from where the tip will be, bending away from you
        smokeAt(S, ironPt(IRON_MAT, 0, 0), smooth(span(u, 0.35, 0.55)), k);
      },
      labels: (S, u) =>
        u > 0.4
          ? [
              L('glasses', 'glasses on', S.node('glasses'), 't', true),
              L('window', 'window open', v3([-0.2, 0.17, -0.25]), 'r'),
            ]
          : [],
    },
    {
      d: 10,
      text: 'Stand the iron in its holder with the cord clear of your arms. It rests there whenever you put it down.',
      cam: { p: [0.33, 0.2, 0.25], t: [0.12, 0.04, -0.06], fov: 32 },
      cam2: { p: [0.4, 0.24, -0.02], t: [0.12, 0.04, -0.07], fov: 32 },
      act(S, u) {
        const up = easeInOut(span(u, 0.05, 0.35));
        const into = easeInOut(span(u, 0.35, 0.65));
        const lift = { p: add3(IRON_REST, [-0.03, 0.12, 0.05]), yaw: STAND_YAW, pitch: REST_PITCH };
        ironTo(S, into > 0 ? mixIron(lift, REST, into) : mixIron(IRON_MAT, lift, up));
      },
      labels: (S, u) =>
        u > 0.68
          ? [
              L('stand', 'iron stand', S.node('stand', null, [-0.03, 0.02, 0.035]), 'b', true),
              L('cord', 'cord behind', S.a('cord').obj, 't'),
            ]
          : [],
    },
    {
      d: 9,
      text: 'Wet the sponge and squeeze it out, or use the brass wool. It should be damp with no water running off.',
      cam: { p: add3(SPONGE, [-0.05, 0.1, 0.11]), t: SPONGE, fov: 30 },
      act(S, u) {
        S.sponge(smooth(span(u, 0.15, 0.6)));
      },
      labels: (S, u) => (u > 0.6 ? [L('damp', 'damp, not dripping', v3(SPONGE), 't', true)] : []),
    },
    {
      d: 9,
      text: 'Plug the iron in and press the buttons on its handle until the screen reads 330 °C. Wait for it to settle.',
      cam: { p: add3(ironPt(REST, 145, 12), [0.034, 0.1, 0.062]), t: ironPt(REST, 148, 12), fov: 30 },
      act(S, u) {
        const on = span(u, 0.08, 0.2);
        if (on <= 0) return;
        // room temperature to 330 °C, then it holds
        const rise = easeInOut(span(u, 0.2, 0.75));
        S.screen(String(Math.round(lerp(22, 330, rise))));
        S.tip({ tin: 0, heat: rise });
      },
      labels: (S, u) =>
        u > 0.12
          ? [
              L('set', u > 0.75 ? '330 °C' : 'heating', S.a('iron').obj.userData.screenAt, 'l', u > 0.75),
              L('btn', 'buttons', S.a('iron').obj.userData.buttonsAt, 'r'),
            ]
          : [],
    },
    {
      d: 10,
      text: 'Hold the iron like a pen by the grip only. Metal ahead of the grip burns. Unplug the iron if you stop here.',
      cam: { p: [-0.07, 0.17, 0.3], t: [0.06, 0.08, 0.03], fov: 32 },
      cam2: { p: [0.02, 0.15, 0.33], t: [0.06, 0.08, 0.03], fov: 32 },
      act(S, u) {
        const out = easeInOut(span(u, 0.05, 0.45));
        const hold = { p: [KIT_AT[0] + 0.005, 0.03, KIT_AT[2] - 0.004], yaw: 0.4, pitch: 0.785 };
        ironTo(S, mixIron(REST, hold, out));
      },
      labels: (S, u) =>
        u > 0.45
          ? [
              L('grip', 'hold here', S.a('iron').obj.userData.grip, 't', true),
              L('hot', 'hot: never touch', S.a('iron').obj.userData.hot, 'b'),
            ]
          : [],
      check: true,
    },
  ],
};

/** The bench after chapter 1: tools in place, no iron on the mat. */
function benchSet(S, { meter = false, kit = false } = {}) {
  S.a('stand').show().at(STAND[0], 0, STAND[1]).turn(STAND_YAW);
  S.a('third_hand').show().at(...TH);
  if (meter) S.a('multimeter').show().at(...METER);
  if (kit) {
    setFrame(S, { p: KIT_AT, rx: 0 });
    put(S, 'practice_board', 0, 0, 0).turn(Math.PI / 2);
  }
}

// ---------------------------------------------------------------- chapter 2
const TIP_CAM = { p: add3(AIR, [-0.035, 0.03, 0.075]), t: add3(AIR, [-0.004, -0.004, 0]), fov: 30 };
const AIR_POSE = { p: AIR, yaw: 0.35, pitch: 0.5 };

/** Lift the iron to the air, touch solder to its tip, wipe it once and hold it back up. */
function tinTip(S, u, k, { from = 0, to = 1, black = 0 } = {}) {
  const up = easeInOut(span(u, 0.0, 0.2));
  const wipe = span(u, 0.62, 0.8);
  const back = easeInOut(span(u, 0.82, 0.98));
  const sponge = { p: add3(SPONGE, [0.006, 0.003, 0]), yaw: 0.35, pitch: 0.5 };
  let pose = mixIron(REST, AIR_POSE, up);
  if (wipe > 0) pose = mixIron(AIR_POSE, sponge, easeInOut(span(wipe, 0, 0.3)) * (1 - easeInOut(span(wipe, 0.7, 1))));
  if (back > 0) pose = mixIron(AIR_POSE, AIR_POSE, back);
  if (wipe > 0 && wipe < 1) pose = { ...pose, p: add3(pose.p, [0, 0, 0.012 * Math.sin(wipe * TAU)]) };
  ironTo(S, pose);
  const feed = span(u, 0.25, 0.58);
  const tin = lerp(from, to, smooth(span(u, 0.35, 0.55)));
  S.tip({ tin, black, heat: 1 });
  if (feed > 0 && feed < 1) {
    const end = ironPt(AIR_POSE, 2, 1.3);
    solderAt(S, mix3(add3(end, [-0.03, 0.006, 0]), end, easeOut(feed * 1.6)), 0.35);
    smokeAt(S, end, smooth(span(feed, 0.3, 0.5)) * (1 - smooth(span(feed, 0.85, 1))), k);
  }
}

const first = {
  id: 'first',
  title: 'Your first joint',
  goal: 'One resistor soldered and clipped.',
  work: '15 minutes',
  bench: true,
  setup(S) {
    benchSet(S);
    ironOn(S, 0);
    setFrame(S, ON_MAT);
    put(S, 'practice_board', 0, 0, 0).turn(Math.PI / 2);
  },
  beats: [
    {
      d: 10,
      text: 'Touch solder to the tip until it turns silver, then wipe it once. A silver tip passes heat, a black tip does not.',
      cam: TIP_CAM,
      act(S, u, k) {
        tinTip(S, u, k);
      },
      labels: (S, u) => (u > 0.55 ? [L('tin', 'tinned tip', S.a('iron').obj.userData.tipSide, 'l', true)] : []),
    },
    {
      d: 10,
      text: 'Push a resistor through the board, bend its legs apart and clip the board in the helping hands, legs facing up.',
      cam: { p: [0.06, 0.2, 0.32], t: [0.0, 0.035, 0.015], fov: 32 },
      move: 2,
      act(S, u) {
        ironOn(S);
        const into = easeOut(span(u, 0.05, 0.3));
        put(S, 'resistor', RES[0], RES[1] - 25 * (1 - into), RES[2], smooth(into * 2));
        const move = easeInOut(span(u, 0.38, 0.8));
        setFrame(S, blendFrame(ON_MAT, FRAME, move, 0.05));
        put(S, 'practice_board', 0, 0, 0).turn(Math.PI / 2);
      },
      labels: (S, u) => {
        if (u > 0.2 && u < 0.38) return [L('legs', 'legs bent: it stays put', S.F(RES[0], 5.5, RES[2]), 't')];
        if (u > 0.82) return [L('clips', 'clips on the board edges', S.node('third_hand', null, [-0.026, 0.078, -0.007]), 'l')];
        return [];
      },
    },
    {
      d: 10,
      text: 'Lay the side of the tip against the pad and the leg together and count to two. The point alone heats neither.',
      cam: fcam(J1, [7, 9, 40], 28),
      act(S, u) {
        const w = easeInOut(span(u, 0.05, 0.4));
        ironTo(S, mixIron(REST, ironOnPad(S, J1), w));
      },
      labels: (S, u) => {
        if (u < 0.4) return [];
        const out = [
          L('pad', 'pad', S.F(J1[0] - 1.1, PAD, J1[2] + 0.6), 'l'),
          L('leg', 'leg', S.F(J1[0], PAD + 3.6, J1[2]), 't'),
          L('side', 'side of the tip', S.a('iron').obj.userData.tipSide, 'r', true),
        ];
        const c = count(u, 0.45, 0.7, 0.97);
        if (c) out.push(L('count', c, S.F(J1[0] - 2, PAD + 6, J1[2]), 't', true));
        return out;
      },
    },
    {
      d: 9,
      text: 'Feed solder to the pad on the far side of the leg, never onto the tip. It melts and runs around the leg.',
      cam: fcam(J1, [7, 9, 40], 28),
      cam2: fcam(J1, [-8, 10, 39], 28),
      act(S, u, k) {
        ironTo(S, ironOnPad(S, J1));
        solderAt(S, solderPad(S, J1, easeInOut(span(u, 0.05, 0.3))));
        const g = smooth(span(u, 0.28, 0.75));
        joint(S, 'jointA', J1, g * 0.8);
        S.wet('jointA', 1);
        smokeAt(S, S.W(...J1), smooth(span(u, 0.28, 0.4)), k);
      },
      labels: (S, u) =>
        u > 0.15
          ? [
              L('here', 'solder here', S.F(J1[0] - 0.9, PAD + 0.2, J1[2] - 0.4), 'l', true),
              L('stays', 'iron stays', S.a('iron').obj.userData.tipSide, 'r'),
            ]
          : [],
    },
    {
      d: 9,
      text: 'Stop after about 3 mm of solder. The pad is covered and the leg still shows through a small cone.',
      cam: fcam(J1, [-8, 10, 39], 28),
      act(S, u, k) {
        ironTo(S, ironOnPad(S, J1));
        solderAt(S, solderPad(S, J1, 1));
        joint(S, 'jointA', J1, 0.8 + 0.2 * smooth(span(u, 0.05, 0.5)));
        S.wet('jointA', 1);
        smokeAt(S, S.W(...J1), 1 - smooth(span(u, 0.6, 0.9)), k);
        // 3 mm of wire beside the solder, ending where it melts
        const end = solderPad(S, J1, 1);
        const dir = [-Math.cos(0.45), Math.sin(0.45), 0];
        const perp = [Math.sin(0.45), Math.cos(0.45), 0];
        const c = add3(end, [(dir[0] * 1.5 + perp[0] * 1.3) * MM, (dir[1] * 1.5 + perp[1] * 1.3) * MM, 0]);
        S.a('dim3').show(smooth(span(u, 0.1, 0.25))).at(c[0], c[1], c[2]).turn(Math.PI, 0, 0.45);
      },
      labels: (S, u) =>
        u > 0.2
          ? [
              L('mm', 'about 3 mm', S.node('dim3', null, [0, 0.0012, 0]), 't', true),
              ...(u > 0.5 ? [L('cone', 'cone, not a ball', S.F(J1[0], PAD + 2.2, J1[2]), 'r')] : []),
            ]
          : [],
    },
    {
      d: 10,
      text: 'Take the solder away first and the iron a second later. Hold everything still for 2 seconds while it sets.',
      cam: fcam(J1, [-4, 11, 42], 28),
      act(S, u) {
        const sOut = easeInOut(span(u, 0.05, 0.25));
        if (sOut < 1) solderAt(S, mix3(solderPad(S, J1, 1), solderPad(S, J1, 0), sOut));
        const iOut = easeInOut(span(u, 0.32, 0.55));
        ironTo(S, mixIron(ironOnPad(S, J1), ironOffPad(S, J1), iOut));
        joint(S, 'jointA', J1, 1);
        S.wet('jointA', 1 - smooth(span(u, 0.6, 0.95)));
      },
      labels: (S, u) => {
        const out = [];
        if (u > 0.05) out.push(L('s1', '1 solder away', S.F(J1[0] - 6, PAD + 5, J1[2] - 2), 'l'));
        if (u > 0.32) out.push(L('s2', '2 iron away', S.F(J1[0] + 6, PAD + 6, J1[2] + 2), 'r'));
        if (u > 0.58) out.push(L('s3', '3 hold still, 2 s', S.F(J1[0], PAD + 2.2, J1[2]), 't', true));
        return out;
      },
    },
    {
      d: 10,
      text: "Hold the leg and cut it level with the top of the cone, cutters' flat side down. Cut legs fly: glasses on.",
      cam: fcam(J1, [-12, 22, 62], 30),
      act(S, u) {
        const inn = easeInOut(span(u, 0.05, 0.4));
        const tip = S.W(J1[0] + 0.4, PAD + CONE + 0.2, J1[2] + 0.2);
        S.a('cutters').show().at(tip.x + 0.03 * (1 - inn), tip.y + 0.012 * (1 - inn), tip.z - 0.02 * (1 - inn)).turn(0.6, TILT, 0);
        if (u > 0.5) {
          S.cutLeg('resistor', 0, LEG_CUT);
          // the cut piece stays in your fingers: show the right way, not the flying piece
          put(S, 'legCut', J1[0], PAD + CONE + 0.6 + 4 * easeOut(span(u, 0.5, 0.75)), J1[2]).size([1, (5.35 - PAD - CONE) / 12, 1]);
        }
        if (u > 0.85) S.a('cutters').show(0);
      },
      labels: (S, u) =>
        u > 0.3
          ? [
              L('flat', 'flat side down', S.node('cutters', null, [0.03, 0.004, 0]), 'r'),
              L('holdleg', 'hold the leg', S.F(J1[0], PAD + 5.5, J1[2]), 't', true),
              ...(u < 0.5 ? [L('cut', 'cut here', S.F(J1[0] - 0.4, PAD + CONE, J1[2]), 'l')] : []),
            ]
          : [],
    },
    {
      d: 10,
      text: 'One shiny cone and one cut leg. Do the other leg the same way, then tin the tip and rest the iron.',
      cam: fcam([1.27, PAD, -1.27], [10, 18, 46], 30),
      cam2: fcam([1.27, PAD, -1.27], [-14, 16, 45], 30),
      act(S, u, k) {
        // the second joint at double speed
        const on = easeInOut(span(u, 0.05, 0.18));
        const off = easeInOut(span(u, 0.45, 0.6));
        const home = easeInOut(span(u, 0.62, 0.9));
        let pose = mixIron(ironOffPad(S, J1), ironOnPad(S, J2), on);
        if (off > 0) pose = mixIron(ironOnPad(S, J2), ironOffPad(S, J2), off);
        if (home > 0) pose = mixIron(ironOffPad(S, J2), REST, home);
        ironTo(S, pose);
        const feed = span(u, 0.2, 0.42);
        if (feed > 0 && feed < 1) solderAt(S, solderPad(S, J2, easeInOut(span(feed, 0, 0.4)) * (1 - easeInOut(span(feed, 0.8, 1)))));
        joint(S, 'jointA2', J2, smooth(span(u, 0.25, 0.4)));
        smokeAt(S, S.W(...J2), smooth(span(u, 0.25, 0.3)) * (1 - smooth(span(u, 0.4, 0.5))), k);
        if (u > 0.7) S.cutLeg('resistor', 1, LEG_CUT);
        if (u < 1) S.a('legCut').show(0);
      },
      labels: (S, u) => (u > 0.1 ? [L('shiny', 'shiny cone', S.F(J1[0], PAD + 2.2, J1[2]), 't', true)] : []),
      check: true,
    },
  ],
};

// ---------------------------------------------------------------- chapter 3
// a row of practice faults on the board's front row, 2.54 mm apart
const ROW = 3.81;
const FA = [-8.89, PAD, ROW]; // dull joint, fixed with flux
const FB = [-3.81, PAD, ROW]; // starved joint
const FC = [1.27, PAD, ROW]; // a good one to compare
const FD = [7.62, PAD, ROW]; // the bridge between two pads

/** Chapters 3 and on: the resistor from chapter 2, soldered and trimmed. */
function firstJointDone(S) {
  put(S, 'resistor', ...RES);
  S.cutLeg('resistor', 0, LEG_CUT);
  S.cutLeg('resistor', 1, LEG_CUT);
  joint(S, 'jointA', J1, 1);
  joint(S, 'jointA2', J2, 1);
}

const fix = {
  id: 'fix',
  title: 'Read the joint and fix it',
  goal: 'Name each fault and repair it.',
  work: '15 minutes',
  bench: true,
  setup(S) {
    benchSet(S);
    ironOn(S);
    board(S);
    firstJointDone(S);
    put(S, 'jCold', ...FA);
    put(S, 'jFix3', ...FB).size(0.55);
    put(S, 'jFix4', ...FC);
    put(S, 'jBridge', ...FD);
  },
  beats: [
    {
      d: 10,
      text: 'Compare your joint with these, cut in half. Good solder wets the pad and the leg. Cold solder sits on top as a ball.',
      cam: { p: fw(6, 5, 58), t: fw(0, 0.5, 0), fov: 26 },
      cam2: { p: fw(-8, 6, 57), t: fw(0, 0.5, 0), fov: 26 },
      act(S, u) {
        if (u >= 1) return;
        for (const n of ['practice_board', 'resistor', 'jointA', 'jointA2', 'jCold', 'jFix3', 'jFix4', 'jBridge']) S.a(n).show(0);
        put(S, 'cutGood', -8.5, PAD, 0);
        put(S, 'cutCold', 8.5, PAD, 0);
      },
      labels: (S, u) => {
        if (u >= 1) return [];
        const g = S.a('cutGood').obj.userData;
        const c = S.a('cutCold').obj.userData;
        return [
          L('good', 'good: shiny cone', g.top, 't', true),
          L('cold', 'cold: dull ball', c.top, 't'),
          L('fill', 'solder fills the hole', g.fill, 'l'),
          L('gap', 'gap: no contact', c.gap, 'b'),
        ];
      },
    },
    {
      d: 10,
      text: 'Dab flux on a dull joint and reheat it for 2 seconds, never more than 5. It slumps into a shiny cone.',
      cam: fcam(FA, [6, 10, 40], 28),
      act(S, u, k) {
        const pen = easeInOut(span(u, 0.04, 0.2)) * (1 - easeInOut(span(u, 0.25, 0.38)));
        if (pen > 0) {
          const tip = S.W(FA[0] - 0.8, FA[1] + 2.2, FA[2] - 0.3);
          S.a('flux_pen').show().at(tip.x - 0.03 * (1 - pen), tip.y + 0.02 * (1 - pen), tip.z).turn(Math.PI, 0, 0.6);
        }
        const on = easeInOut(span(u, 0.35, 0.48));
        const off = easeInOut(span(u, 0.78, 0.92));
        ironTo(S, off > 0 ? mixIron(ironOnPad(S, FA), REST, off) : mixIron(REST, ironOnPad(S, FA), on));
        const m = smooth(span(u, 0.5, 0.72));
        if (m < 1) put(S, 'jCold', ...FA).size([1, Math.max(0.02, 1 - m), 1]);
        else S.a('jCold').show(0);
        if (m > 0) put(S, 'jFix1', ...FA).size([0.6 + 0.4 * m, m, 0.6 + 0.4 * m]);
        smokeAt(S, S.W(...FA), smooth(span(u, 0.45, 0.52)) * (1 - smooth(span(u, 0.72, 0.8))), k);
      },
      labels: (S, u) => {
        const out = [];
        if (u > 0.08 && u < 0.35) out.push(L('flux', 'flux', S.F(FA[0] - 1.5, FA[1] + 2.5, FA[2]), 'l'));
        if (u > 0.48) out.push(L('2s', '2 s', S.F(FA[0], FA[1] + 2.4, FA[2]), 't', true));
        if (u > 0.55) out.push(L('5s', '5 s or more lifts the pad', S.F(FA[0] - 1.2, FA[1], FA[2] + 1), 'b'));
        return out;
      },
    },
    {
      d: 10,
      text: 'Lay braid across a bridge and press the iron on the braid. Hold the braid 30 mm back: copper carries heat.',
      cam: fcam(add3(FD, [8, 0, 0]), [2, 22, 48], 30),
      act(S, u, k) {
        const lay = easeInOut(span(u, 0.04, 0.22));
        const lift = easeInOut(span(u, 0.8, 0.95));
        const y = PAD + 2.95 + 8 * (1 - lay) + 6 * lift;
        put(S, 'braidStrip', FD[0], y, FD[2], u < 1 ? 1 : 0).turn(-0.2);
        const press = { ...ironOnPad(S, FD), p: (() => { const p = S.W(FD[0] + 0.4, y + 0.6, FD[2] + 0.3); return [p.x, p.y, p.z]; })(), yaw: -0.9 };
        const on = easeInOut(span(u, 0.22, 0.34));
        ironTo(S, lift > 0 ? mixIron(press, REST, lift) : mixIron(REST, press, on));
        const soak = smooth(span(u, 0.38, 0.72));
        S.soak(soak);
        S.bridgeWeb(1 - soak);
        smokeAt(S, S.W(FD[0], y, FD[2]), smooth(span(u, 0.36, 0.42)) * (1 - smooth(span(u, 0.7, 0.78))), k);
      },
      labels: (S, u) => {
        const out = [];
        if (u < 0.3) out.push(L('bridge', 'bridge', S.F(FD[0], PAD + 2.2, FD[2] + 1), 'b'));
        if (u > 0.15 && u < 0.98) out.push(L('braid', 'braid, 1.5 mm', S.F(FD[0] + 16, PAD + 3.5, FD[2] - 3.5), 't'));
        if (u > 0.34 && u < 0.8) out.push(L('on', 'iron on the braid', S.a('iron').obj.userData.tipSide, 'r', true));
        if (u > 0.2 && u < 0.98) out.push(L('back', 'fingers 30 mm back', S.F(FD[0] + 29, PAD + 3.5, FD[2] - 6), 'b'));
        return out;
      },
    },
    {
      d: 9,
      text: 'Where the pad shows or there is a hole beside the leg, reheat and feed 1 mm more. The cone closes up.',
      cam: fcam(FB, [5, 10, 38], 28),
      act(S, u, k) {
        const on = easeInOut(span(u, 0.3, 0.42));
        const off = easeInOut(span(u, 0.78, 0.92));
        ironTo(S, off > 0 ? mixIron(ironOnPad(S, FB), REST, off) : mixIron(REST, ironOnPad(S, FB), on));
        const feed = span(u, 0.42, 0.72);
        if (feed > 0 && feed < 1) solderAt(S, solderPad(S, FB, easeInOut(span(feed, 0, 0.4)) * (1 - easeInOut(span(feed, 0.75, 1)))));
        const g = smooth(span(u, 0.48, 0.7));
        put(S, 'jFix3', ...FB).size(0.55 + 0.45 * g);
        smokeAt(S, S.W(...FB), smooth(span(u, 0.45, 0.5)) * (1 - smooth(span(u, 0.68, 0.75))), k);
      },
      labels: (S, u) =>
        u < 0.45
          ? [
              L('little', 'too little', S.F(FB[0], PAD + 1.6, FB[2]), 't'),
              L('bare', 'bare pad', S.F(FB[0] - 1.05, PAD, FB[2] + 0.5), 'l'),
            ]
          : [],
    },
    {
      d: 9,
      text: 'When solder rolls off the tip in balls, the tip is dirty. Wipe it and tin it until it is silver again.',
      cam: TIP_CAM,
      act(S, u, k) {
        // a black tip: solder will not wet it, so a bead rolls off and drops
        const up = easeInOut(span(u, 0.0, 0.12));
        if (u < 0.4) {
          ironTo(S, mixIron(REST, AIR_POSE, up));
          S.tip({ tin: 0, black: 1, heat: 1 });
          const roll = span(u, 0.15, 0.38);
          if (roll > 0 && roll < 1) {
            const end = ironPt(AIR_POSE, 3 - 3 * roll, 1.5);
            const fall = Math.max(0, roll - 0.6) / 0.4;
            S.a('bead').show().at(end[0], end[1] - 0.03 * fall * fall, end[2]);
          }
          return;
        }
        // wipe, then tin until silver
        const t = span(u, 0.4, 1);
        const sponge = { p: add3(SPONGE, [0.006, 0.003, 0]), yaw: 0.35, pitch: 0.5 };
        const go = easeInOut(span(t, 0, 0.15)) * (1 - easeInOut(span(t, 0.3, 0.45)));
        let pose = mixIron(AIR_POSE, sponge, go);
        const wipe = span(t, 0.12, 0.33);
        if (wipe > 0 && wipe < 1) pose = { ...pose, p: add3(pose.p, [0, 0, 0.012 * Math.sin(wipe * TAU)]) };
        ironTo(S, pose);
        S.tip({ tin: smooth(span(t, 0.55, 0.85)), black: 1 - smooth(span(t, 0.15, 0.45)), heat: 1 });
        if (t > 0.5 && t < 0.85) {
          const end = ironPt(AIR_POSE, 2, 1.3);
          solderAt(S, mix3(add3(end, [-0.03, 0.006, 0]), end, easeOut(span(t, 0.5, 0.6))), 0.35);
          smokeAt(S, end, smooth(span(t, 0.55, 0.6)) * (1 - smooth(span(t, 0.78, 0.85))), k);
        }
      },
      labels: (S, u) => {
        if (u > 0.08 && u < 0.4) return [L('black', 'black: dirty', S.a('iron').obj.userData.tipSide, 'l')];
        if (u > 0.86) return [L('silver', 'silver: ready', S.a('iron').obj.userData.tipSide, 'l', true)];
        return [];
      },
    },
    {
      d: 9,
      text: 'Four faults, four fixes: dull, bridged, starved, dirty tip. Tin the tip and rest the iron. Fine place to stop.',
      cam: { p: fw(0, 62, 40), t: fw(0, PAD, ROW - 2), fov: 30 },
      cam2: { p: fw(-6, 60, 44), t: fw(0, PAD, ROW - 2), fov: 30 },
      act(S) {
        ironOn(S);
      },
      check: true,
    },
  ],
};

// ---------------------------------------------------------------- chapter 4
// The traffic-light kit, drawn on the practice board until his kit is measured: three resistors, three LEDs, a chip
// and a capacitor. Component side is frame y < 0 (up when the frame is flipped).
const RES_T = [['resT1', -1.27], ['resT2', -6.35], ['resT3', -11.43]]; // body centred at x 1.27
const LED_X = [['ledR', -11.43], ['ledA', -1.27], ['ledG', 8.89]];
const LED_Z = 7.62; // legs at z 6.35 (cathode) and 8.89 (anode)
const CHIP = [-15.24, -5.08];
const CAP = [15.24, -5.08];
const JT1 = [-3.81, PAD, -1.27]; // resT1's first leg
const JT2 = [-11.43, PAD, LED_Z + 1.27]; // red LED, anode
const JT3 = [-11.43, PAD, LED_Z - 1.27]; // red LED, cathode
const POWER = [[-21.59, PAD, -11.43], [-21.59, PAD, -13.97]];

function placeRes(S, name, z, a = 1, proud = 0) {
  put(S, name, 1.27, -1.25 - proud, z, a);
}
function placeLed(S, name, x, drop = 0, a = 1, twist = 0) {
  put(S, name, x, -drop, LED_Z, a).turn(-Math.PI / 2 + twist, Math.PI, 0);
}
function placeChip(S, drop = 0, a = 1) {
  put(S, 'chip', CHIP[0], -drop, CHIP[1], a).turn(0, Math.PI, 0);
  put(S, 'cap', CAP[0], -drop, CAP[1], a).turn(0, Math.PI, 0);
}

/** Flip the board from component side up to solder side up (or back) over the window [a, b] of the beat. */
function flipFrame(S, u, toSolder, a = 0, b = 0.16) {
  const t = easeInOut(span(u, a, b));
  setFrame(S, toSolder ? blendFrame(FLIP, FRAME, t) : blendFrame(FRAME, FLIP, t));
}

/** The traffic light with every part fitted and soldered (chapter 4's end, and the tidy bench). */
function trafficDone(S, f = FLIP) {
  board(S, f);
  for (const [n, z] of RES_T) placeRes(S, n, z);
  for (const [n, x] of LED_X) placeLed(S, n, x);
  placeChip(S);
  joint(S, 'jT1', JT1, 1);
  joint(S, 'jT2', JT2, 1);
  joint(S, 'jT3', JT3, 1);
}

const COMP_CAM = { p: fw(0, -95, -55, FLIP), t: fw(0, -3, -1, FLIP), fov: 30 };

const light = {
  id: 'light',
  title: 'Build the traffic light',
  goal: 'The practice kit soldered and lit.',
  work: '1 evening',
  bench: true,
  setup(S) {
    benchSet(S);
    ironOn(S);
    board(S, FLIP);
  },
  beats: [
    {
      d: 9,
      text: 'Fit the lowest parts first: the resistors. Match each one to the value printed on the board.',
      cam: COMP_CAM,
      act(S, u) {
        RES_T.forEach(([n, z], i) => {
          const t = easeOut(span(u, 0.08 + i * 0.18, 0.3 + i * 0.18));
          if (t > 0) placeRes(S, n, z, smooth(t * 2), (1 - t) * 18);
        });
      },
      labels: (S, u) =>
        u > 0.3
          ? [
              L('first', 'resistors first', S.node('resT1', null, [0, -0.0014, 0]), 'l', true),
              L('value', 'value printed here', S.F(1.27, -0.05, -3.81), 'r'),
            ]
          : [],
    },
    {
      d: 10,
      text: 'Solder one leg of each part and check it sits flat. One leg can still be reheated and the part pressed down.',
      cam: fcam(JT1, [10, 22, 48], 30),
      cam2: { p: fw(JT1[0] + 34, -1, JT1[2] + 34), t: fw(JT1[0] + 4, -1.5, JT1[2]), fov: 30 },
      move: 1.2,
      act(S, u, k) {
        flipFrame(S, u, true);
        const reheat = smooth(span(u, 0.72, 0.84));
        placeRes(S, 'resT1', -1.27, 1, 1 - reheat);
        const on = easeInOut(span(u, 0.2, 0.3));
        const off = easeInOut(span(u, 0.5, 0.58));
        const on2 = easeInOut(span(u, 0.66, 0.72));
        const off2 = easeInOut(span(u, 0.86, 0.96));
        let pose = mixIron(REST, ironOnPad(S, JT1), on);
        if (off > 0) pose = mixIron(ironOnPad(S, JT1), REST, off);
        if (on2 > 0) pose = mixIron(REST, ironOnPad(S, JT1), on2);
        if (off2 > 0) pose = mixIron(ironOnPad(S, JT1), REST, off2);
        if (u > 0.18) ironTo(S, pose);
        const feed = span(u, 0.3, 0.48);
        if (feed > 0 && feed < 1) solderAt(S, solderPad(S, JT1, easeInOut(span(feed, 0, 0.4)) * (1 - easeInOut(span(feed, 0.75, 1)))));
        joint(S, 'jT1', JT1, smooth(span(u, 0.33, 0.46)));
        smokeAt(S, S.W(...JT1), smooth(span(u, 0.32, 0.36)) * (1 - smooth(span(u, 0.46, 0.52))), k);
      },
      labels: (S, u) => {
        const out = [];
        if (u > 0.4) out.push(L('one', 'one leg first', S.F(JT1[0], PAD + 2.4, JT1[2]), 't', true));
        if (u > 0.84) out.push(L('flat', 'flat on the board', S.F(1.27, -0.1, -1.27 + 1.4), 'b'));
        return out;
      },
    },
    {
      d: 10,
      text: "Fit each LED with its long leg in the hole marked +. The flat on the LED's rim goes on the other side.",
      cam: fcam([-11.43, -10, LED_Z], [8, -18, -46], 28, FLIP),
      act(S, u) {
        flipFrame(S, u, false);
        const turn = easeInOut(span(u, 0.2, 0.45));
        const down = easeInOut(span(u, 0.6, 0.85));
        placeLed(S, 'ledR', -11.43, 16 * (1 - down), smooth(span(u, 0.12, 0.25)), 1.3 * (1 - turn));
        const rest = smooth(span(u, 0.86, 1));
        if (rest > 0) for (const [n, x] of LED_X.slice(1)) placeLed(S, n, x, 10 * (1 - rest), rest);
      },
      labels: (S, u) =>
        u > 0.45 && u < 0.98
          ? [
              L('long', 'long leg: +', S.node('ledR', null, [1.27 * MM, -12 * MM, 0]), 'r', true),
              L('flatrim', 'flat on the rim: −', S.node('ledR', null, [-2.5 * MM, 0.6 * MM, 0]), 'l'),
              L('plus', '+ on the board', S.F(-11.43, -0.05, LED_Z + 1.27), 'r'),
            ]
          : [],
    },
    {
      d: 9,
      text: 'Solder each LED leg in 2 seconds and let it cool before the next. Slow heat is what kills an LED.',
      cam: fcam([-11.43, PAD, LED_Z], [14, 26, 50], 30),
      act(S, u, k) {
        flipFrame(S, u, true);
        const steps = [[JT2, 0.18, 0.42, 'jT2'], [JT3, 0.6, 0.84, 'jT3']];
        let pose = REST;
        for (const [J, a, b, n] of steps) {
          const on = easeInOut(span(u, a - 0.06, a));
          const off = easeInOut(span(u, b, b + 0.08));
          if (u > a - 0.06) pose = off > 0 ? mixIron(ironOnPad(S, J), REST, off) : mixIron(REST, ironOnPad(S, J), on);
          const feed = span(u, a + 0.02, b - 0.04);
          if (feed > 0 && feed < 1) solderAt(S, solderPad(S, J, easeInOut(span(feed, 0, 0.4)) * (1 - easeInOut(span(feed, 0.75, 1)))));
          joint(S, n, J, smooth(span(u, a + 0.05, b - 0.06)));
          smokeAt(S, S.W(...J), smooth(span(u, a + 0.04, a + 0.08)) * (1 - smooth(span(u, b - 0.05, b))), k);
        }
        ironTo(S, pose);
      },
      labels: (S, u) => {
        const out = [L('2s', '2 s a leg', S.F(-11.43, PAD + 7, LED_Z), 't', true)];
        const c = count(u, 0.18, 0.3, 0.42) || count(u, 0.6, 0.72, 0.84);
        if (c) out.push(L('count', c, S.F(-14, PAD + 3, LED_Z - 3), 'l', true));
        return out;
      },
    },
    {
      d: 10,
      text: "Fit the tallest parts last. A chip's notch and a capacitor's stripe must match the marks on the board.",
      cam: COMP_CAM,
      act(S, u) {
        flipFrame(S, u, false);
        const t = easeOut(span(u, 0.15, 0.45));
        placeChip(S, 16 * (1 - t), smooth(t * 2));
      },
      labels: (S, u) =>
        u > 0.45
          ? [
              L('notch', 'notch to notch', S.a('chip').obj.userData.notch, 'l'),
              L('stripe', 'stripe to the shaded side', S.a('cap').obj.userData.stripe, 'r'),
            ]
          : [],
    },
    {
      d: 10,
      text: 'Turn the meter to the beep setting and touch the probes together. The beep is the sound of a connection.',
      cam: { p: add3(METER, [0.11, 0.21, 0.2]), t: add3(METER, [0.03, 0.03, 0.02]), fov: 32 },
      act(S, u) {
        if (u >= 1) return;
        const meet = add3(METER, [0.065, 0.03, 0.085]);
        const t = easeInOut(span(u, 0.25, 0.55));
        probes(S, 1, add3(meet, [0.012 * (1 - t), 0.0003, 0]), add3(meet, [-0.012 * (1 - t), 0, 0.0004]));
        S.meter(t >= 1 ? '0.00' : 'OL', 'Ω');
      },
      labels: (S, u) => [
        L('cont', 'continuity', meterKnobAt(S), 'l', true),
        ...(u > 0.55 ? [L('beep', 'beep', meterSideAt(S), 'r')] : []),
      ],
    },
    {
      d: 10,
      text: 'Probe the two power pads: silence is right. Then power the kit. Red, amber and green light in turn.',
      cam: { p: [-0.03, 0.17, 0.2], t: [-0.07, 0.05, -0.03], fov: 32 },
      cam2: { p: [-0.005, 0.13, 0.12], t: [-0.005, 0.07, -0.04], fov: 32 },
      act(S, u) {
        const toComp = easeInOut(span(u, 0.5, 0.62));
        setFrame(S, toComp > 0 ? blendFrame(FRAME, FLIP, toComp) : FRAME);
        const land = easeInOut(span(u, 0.08, 0.25)) * (1 - easeInOut(span(u, 0.4, 0.5)));
        if (u < 0.5) {
          const a = S.W(...POWER[0]);
          const b = S.W(...POWER[1]);
          probes(S, land, [a.x, a.y, a.z], [b.x, b.y, b.z]);
          S.meter('OL', 'Ω');
        } else S.a('multimeter').show().at(...METER);
        if (u > 0.66 && u < 1) S.led(Math.floor((u - 0.66) / 0.1) % 3, 1);
      },
      labels: (S, u) => {
        if (u > 0.22 && u < 0.45) return [L('quiet', 'no beep: no bridge', meterSideAt(S), 'r')];
        if (u > 0.7) return [L('works', 'it works', S.node('ledA', null, [0, 9 * MM, 0]), 't', true)];
        return [];
      },
      check: true,
    },
  ],
};

// ---------------------------------------------------------------- chapter 5
// Two clips at the front of the helping hands hold the wires level, 46 mm up. The left wire is the 28 AWG silicone
// wire, the right one the red wire of a JST-PH lead; each is 70 mm with 3 mm bare at both ends.
const WY = 0.046;
const WZ = 0.011;
const WL = -0.068; // the left wire's outer end
const WEND = WL + 0.07; // its inner end, 2 mm past the middle
const SPLICE = [0, WY, WZ];

function wireL(S, dx = 0) {
  S.a('wireL').show().at(WL + dx, WY, WZ - 0.00045);
}
function wireR(S, dx = 0) {
  S.a('wireR').show().at(-WL + dx, WY, WZ + 0.00045).turn(Math.PI);
}

const wires = {
  id: 'wires',
  title: 'Join two wires',
  goal: 'A splice that holds a tug and beeps.',
  work: '20 minutes',
  bench: true,
  setup(S) {
    benchSet(S, { meter: true });
    ironOn(S);
    wireL(S);
  },
  beats: [
    {
      d: 10,
      text: "Strip 3 mm from a 28 AWG wire in the stripper's 28 notch and twist the strands tight. No strand is cut.",
      cam: { p: [WEND + 0.012, WY + 0.016, WZ + 0.032], t: [WEND - 0.004, WY, WZ], fov: 28 },
      act(S, u) {
        const inn = easeInOut(span(u, 0.05, 0.3));
        const pull = easeInOut(span(u, 0.38, 0.62));
        const away = easeInOut(span(u, 0.66, 0.8));
        // from the right: the jaws close just inside the 3 mm, the handles run off to the right, then it pulls
        const x = WEND - 0.0045 + 0.009 * pull + 0.03 * away;
        if (away < 1) S.a('stripper').show().at(x + 0.03 * (1 - inn), WY, WZ + 0.02 * (1 - inn)).turn(-0.35, Math.PI / 2, 0);
        if (u < 0.75) S.a('slug').show(1 - smooth(span(u, 0.55, 0.7))).at(WEND - 0.0015 + 0.009 * pull, WY, WZ - 0.00045);
        if (u > 0.62 && u < 1) S.a('dim3').show(smooth(span(u, 0.62, 0.7))).at(WEND - 0.0015, WY + 0.0025, WZ);
      },
      labels: (S, u) => {
        const out = [];
        if (u > 0.2 && u < 0.62) out.push(L('notch', '28 notch', v3([WEND - 0.0015, WY + 0.0035, WZ]), 't', true));
        if (u > 0.66) out.push(L('3mm', '3 mm', S.node('dim3', null, [0, 0.0012, 0]), 't'));
        if (u > 0.76) out.push(L('tw', 'strands twisted', v3([WEND, WY, WZ]), 'r'));
        return out;
      },
    },
    {
      d: 10,
      text: 'Clip the wire in the helping hands. Hold the iron under the copper and touch solder on top. It turns silver.',
      cam: { p: [WEND + 0.01, WY + 0.02, WZ + 0.045], t: [WEND - 0.004, WY, WZ], fov: 28 },
      act(S, u, k) {
        const under = { p: [WEND - 0.0012, WY - 0.0006, WZ - 0.0002], yaw: -0.7, pitch: -0.5 };
        const on = easeInOut(span(u, 0.08, 0.28));
        const off = easeInOut(span(u, 0.72, 0.92));
        ironTo(S, off > 0 ? mixIron(under, REST, off) : mixIron(REST, under, on));
        const feed = span(u, 0.3, 0.66);
        const top = [WEND - 0.0015, WY + 0.0005, WZ - 0.0004];
        if (feed > 0 && feed < 1) solderAt(S, mix3(add3(top, [-0.012, 0.016, 0]), top, easeInOut(span(feed, 0, 0.35)) * (1 - easeInOut(span(feed, 0.8, 1)))), 1.0);
        S.tinWire(0, smooth(span(u, 0.38, 0.6)));
        smokeAt(S, top, smooth(span(u, 0.36, 0.42)) * (1 - smooth(span(u, 0.6, 0.68))), k);
      },
      labels: (S, u) => {
        const out = [];
        if (u > 0.25 && u < 0.72) out.push(L('under', 'iron under', S.a('iron').obj.userData.tipSide, 'b'));
        if (u > 0.36 && u < 0.66) out.push(L('top', 'solder on top', v3([WEND - 0.002, WY + 0.0012, WZ]), 't'));
        if (u > 0.6) out.push(L('tinned', 'tinned', v3([WEND - 0.0015, WY + 0.0006, WZ]), 't', true));
        return out;
      },
    },
    {
      d: 9,
      text: 'Slide 12 mm of the thinnest heatshrink onto one wire and push it 40 mm away from the heat.',
      cam: { p: [WEND - 0.02, WY + 0.03, WZ + 0.1], t: [WEND - 0.022, WY, WZ], fov: 28 },
      act(S, u) {
        const on = easeInOut(span(u, 0.05, 0.25));
        const slide = easeInOut(span(u, 0.25, 0.6));
        S.a('shrinkS').show(smooth(on * 2)).at(lerp(WEND + 0.03, WEND + 0.004, on) - 0.046 * slide, WY, WZ - 0.00045);
        if (u > 0.6 && u < 1) S.a('dim40').show(smooth(span(u, 0.6, 0.7))).at(WEND - 0.02, WY + 0.004, WZ);
      },
      labels: (S, u) => [
        ...(u > 0.1 ? [L('first', 'heatshrink on first', S.node('shrinkS'), 't', true)] : []),
        ...(u > 0.66 ? [L('40', '40 mm back', S.node('dim40', null, [0, 0.002, 0]), 't')] : []),
      ],
    },
    {
      d: 10,
      text: 'Lay the two tinned ends side by side, 3 mm overlapping, and touch the iron for 1 second. They melt into one.',
      cam: { p: [0.012, WY + 0.018, WZ + 0.036], t: [0.0, WY, WZ], fov: 28 },
      act(S, u, k) {
        const meet = easeInOut(span(u, 0.04, 0.25));
        wireR(S, 0.02 * (1 - meet));
        S.tinWire(1, 1);
        const touch = { p: [0.0012, WY + 0.0007, WZ + 0.0004], yaw: -0.5, pitch: 0.6 };
        const on = easeInOut(span(u, 0.3, 0.4));
        const off = easeInOut(span(u, 0.62, 0.8));
        ironTo(S, off > 0 ? mixIron(touch, REST, off) : mixIron(REST, touch, on));
        const g = smooth(span(u, 0.42, 0.6));
        if (g > 0) S.a('spliceJoint').show().at(...SPLICE).size([1, g, g]);
        smokeAt(S, SPLICE, smooth(span(u, 0.42, 0.46)) * (1 - smooth(span(u, 0.58, 0.64))), k);
      },
      labels: (S, u) => {
        const out = [];
        if (u > 0.22 && u < 0.42) out.push(L('ov', '3 mm overlap', v3([0, WY + 0.0008, WZ]), 't'));
        if (u > 0.42 && u < 0.62) out.push(L('one', 'one', v3([0, WY + 0.003, WZ]), 't', true));
        if (u > 0.62) out.push(L('none', 'no extra solder needed', v3([0, WY + 0.0008, WZ]), 't'));
        return out;
      },
    },
    {
      d: 10,
      text: "Slide the heatshrink over the cooled joint and hold the iron's barrel beside it. It tightens in seconds.",
      cam: { p: [-0.012, WY + 0.018, WZ + 0.075], t: [0.0, WY - 0.003, WZ], fov: 28 },
      act(S, u) {
        const slide = easeInOut(span(u, 0.05, 0.3));
        const shrink = smooth(span(u, 0.5, 0.8));
        S.a('shrinkS').show().at(lerp(WEND + 0.004 - 0.046, 0, slide), WY, WZ).size([1, 1 - 0.38 * shrink, 1 - 0.38 * shrink]);
        // the barrel's middle, 40 mm up from the tip, sits 2 mm below the sleeve
        const yaw = 0.6;
        const at = [0, WY - 0.00075 - 0.002 - 0.00325, WZ];
        const near = { p: [at[0] - Math.cos(yaw) * 0.04, at[1], at[2] + Math.sin(yaw) * 0.04], yaw, pitch: 0 };
        const on = easeInOut(span(u, 0.32, 0.45));
        const off = easeInOut(span(u, 0.82, 0.95));
        ironTo(S, off > 0 ? mixIron(near, REST, off) : mixIron(REST, near, on));
      },
      labels: (S, u) =>
        u > 0.4 && u < 0.9
          ? [
              L('barrel', 'barrel, not the tip', S.a('iron').obj.userData.barrelAt, 'b', true),
              L('close', 'close, not touching', S.node('shrinkS'), 't'),
            ]
          : [],
    },
    {
      d: 9,
      text: 'Tug the splice gently, then put a probe on each end. It holds and the meter beeps. Fine place to stop.',
      cam: { p: [-0.02, 0.2, 0.26], t: [-0.06, 0.03, -0.01], fov: 32 },
      act(S, u) {
        const tug = Math.sin(Math.PI * span(u, 0.05, 0.25)) * 0.001;
        wireL(S, -tug);
        wireR(S, tug);
                const land = easeInOut(span(u, 0.3, 0.5));
        probes(S, land, [WL + 0.0015, WY, WZ - 0.00045], [-WL - 0.0015, WY, WZ + 0.00045]);
        S.meter(land >= 1 ? '0.00' : 'OL', 'Ω');
      },
      labels: (S, u) => {
        const out = [];
        if (u > 0.1 && u < 0.35) out.push(L('holds', 'holds', S.node('shrinkS'), 't'));
        if (u > 0.52) out.push(L('beep', 'beep', meterSideAt(S), 'r', true));
        return out;
      },
      check: true,
    },
  ],
};
/** The splice, finished, in the front clips. */
function spliceDone(S) {
  wireL(S);
  wireR(S);
  S.tinWire(0, 1);
  S.tinWire(1, 1);
  S.a('spliceJoint').show().at(...SPLICE);
  S.a('shrinkS').show().at(0, WY, WZ).size([1, 0.62, 0.62]);
}

// ---------------------------------------------------------------- chapter 6
const D1 = [0.03, MAT_Y, 0.07]; // the practice driver board, pads towards you
const PADS = ['GNDR', 'VIN', 'BOUT1', 'BOUT2'];
const WIRES_P = ['wireP1', 'wireP2', 'wireP3', 'wireP4'];
const JOINTS_P = ['jointP1', 'jointP2', 'jointP3', 'jointP4'];
// pad positions in world metres for D1 turned -90°: local (5.1, 1.8, z) -> world (-z, 1.8, 5.1) mm
const PAD_Z = { GNDR: -8.9, VIN: -6.3, BOUT1: -3.8, BOUT2: -1.3 };
const padAt = (n) => [D1[0] - PAD_Z[n] * MM, D1[1] + 1.8 * MM, D1[2] + 5.1 * MM];
const LEADP = [-0.075, MAT_Y + 0.0003, 0.095]; // the split lead's socket

function driverBoard(S) {
  S.a('driver1').show().at(...D1).turn(-Math.PI / 2);
}
function padIron(n) {
  const p = padAt(n);
  return { p: [p[0] + 0.0008, p[1] + 0.0006, p[2] + 0.0004], yaw: -0.45, pitch: 0.65 };
}
function wireOnPad(S, i, g = 1, lift = 0) {
  const p = padAt(PADS[i]);
  // the wire lies towards you, its bare end on the pad
  S.a(WIRES_P[i]).show().at(p[0], p[1] + 0.0004 + 0.0003 * (1 - g) + lift, p[2] + 0.029).turn(Math.PI / 2);
}
function padJoint(S, i, h) {
  const p = padAt(PADS[i]);
  S.a(JOINTS_P[i]).show().at(p[0], p[1] - 0.0001, p[2]).size([1, Math.max(0.05, h), 1]);
}

function battery(S, a) {
  const plug = S.node('battery', 'A battery plug').position;
  S.a('battery').show().at(LEADP[0] - plug.x - 0.012 * (1 - a), MAT_Y, LEADP[2] - plug.z);
}
const leadEnd = (k) => add3(LEADP, [61.5 * MM, 2.2 * MM, k * 10.5 * MM]);

const small = {
  id: 'small',
  title: 'Pearl-size joints, then pack up',
  goal: 'Four wires on a spare driver board and a clean bench.',
  work: '30 minutes',
  bench: true,
  setup(S) {
    benchSet(S);
    ironOn(S);
    driverBoard(S);
  },
  beats: [
    {
      d: 10,
      text: 'Melt a small dome of solder onto one pad of a spare driver board. Keep two boards untouched for Pearl.',
      cam: { p: add3(padAt('VIN'), [0.012, 0.03, 0.035]), t: add3(padAt('VIN'), [-0.004, 0, -0.003]), fov: 30 },
      cam2: { p: add3(padAt('GNDR'), [0.006, 0.024, 0.028]), t: padAt('GNDR'), fov: 30 },
      act(S, u, k) {
        if (u < 1) {
          S.a('driver2').show().at(D1[0] - 0.045, MAT_Y, D1[2] - 0.01).turn(-Math.PI / 2);
          S.a('driver3').show().at(D1[0] - 0.068, MAT_Y, D1[2] - 0.01).turn(-Math.PI / 2);
        }
        const on = easeInOut(span(u, 0.3, 0.42));
        const off = easeInOut(span(u, 0.72, 0.88));
        ironTo(S, off > 0 ? mixIron(padIron('GNDR'), REST, off) : mixIron(REST, padIron('GNDR'), on));
        const feed = span(u, 0.42, 0.7);
        const p = padAt('GNDR');
        if (feed > 0 && feed < 1) solderAt(S, mix3(add3(p, [-0.014, 0.008, -0.002]), add3(p, [-0.0007, 0.0004, -0.0002]), easeInOut(span(feed, 0, 0.4)) * (1 - easeInOut(span(feed, 0.75, 1)))));
        const g = smooth(span(u, 0.48, 0.66));
        if (g > 0) padJoint(S, 0, 0.4 * g);
        smokeAt(S, p, smooth(span(u, 0.46, 0.5)) * (1 - smooth(span(u, 0.64, 0.7))), k);
      },
      labels: (S, u) => [
        ...(u > 0.1 && u < 0.6 ? [L('spare', 'spare board', S.node('driver1'), 'l')] : []),
        ...(u > 0.66 ? [L('tinned', 'tinned pad', v3(add3(padAt('GNDR'), [0, 0.0008, 0])), 't', true)] : []),
      ],
    },
    {
      d: 10,
      text: 'Hold a tinned wire on the dome with tweezers and touch the iron for 1 second. The wire sinks into the solder.',
      cam: { p: add3(padAt('GNDR'), [0.026, 0.022, 0.03]), t: add3(padAt('GNDR'), [0, 0, 0.004]), fov: 30 },
      act(S, u, k) {
        const inn = easeInOut(span(u, 0.05, 0.32));
        const sink = smooth(span(u, 0.5, 0.6));
        wireOnPad(S, 0, sink, 0.01 * (1 - inn));
        const p = padAt('GNDR');
        if (u < 0.85) S.a('tweezers').show().at(p[0] + 0.0004, p[1] + 0.0009 + 0.01 * (1 - inn), p[2] + 0.004).turn(-Math.PI / 2, 0, 0.22);
        const on = easeInOut(span(u, 0.36, 0.46));
        const off = easeInOut(span(u, 0.64, 0.8));
        ironTo(S, off > 0 ? mixIron(padIron('GNDR'), REST, off) : mixIron(REST, padIron('GNDR'), on));
        padJoint(S, 0, 0.4 + 0.3 * sink);
        smokeAt(S, p, smooth(span(u, 0.46, 0.5)) * (1 - smooth(span(u, 0.58, 0.64))), k);
      },
      labels: (S, u) => {
        const out = [];
        if (u > 0.2 && u < 0.85) out.push(L('tw', 'tweezers', S.node('tweezers', null, [0.012, 0.001, 0]), 'r'));
        if (u > 0.46 && u < 0.64) out.push(L('one', 'one', v3(add3(padAt('GNDR'), [0, 0.004, 0])), 't', true));
        if (u > 0.64) out.push(L('sunk', 'wire sunk in', v3(add3(padAt('GNDR'), [0, 0.0009, 0])), 'l'));
        return out;
      },
    },
    {
      d: 9,
      text: 'Solder wires to the next three pads, 2.54 mm apart. Clear copper shows between every pair of joints.',
      cam: { p: add3(padAt('BOUT1'), [0.0, 0.03, 0.045]), t: add3(padAt('BOUT1'), [0.0013, 0, 0]), fov: 30 },
      cam2: { p: add3(padAt('BOUT1'), [0.004, 0.011, 0.05]), t: add3(padAt('BOUT1'), [0.0013, 0.0008, 0]), fov: 26 },
      move: 1.2,
      act(S, u, k) {
        let pose = REST;
        for (let i = 1; i < 4; i++) {
          const a = 0.05 + (i - 1) * 0.18;
          const g = smooth(span(u, a + 0.06, a + 0.12));
          padJoint(S, i, 0.4 + 0.3 * g);
          wireOnPad(S, i, g, 0.01 * (1 - easeInOut(span(u, a, a + 0.06))));
          if (u > a + 0.03 && u < a + 0.16) pose = padIron(PADS[i]);
          smokeAt(S, padAt(PADS[i]), u > a + 0.07 && u < a + 0.13 ? 1 : 0, k);
        }
        ironTo(S, pose);
        if (u > 0.62) {
          const a = padAt('GNDR');
          const b = padAt('VIN');
          S.a('dim254').show(smooth(span(u, 0.62, 0.7))).at((a[0] + b[0]) / 2, a[1] + 0.0022, a[2] - 0.0015);
        }
      },
      labels: (S, u) =>
        u > 0.66
          ? [
              L('pitch', '2.54 mm', S.node('dim254', null, [0, 0.0006, 0]), 't'),
              L('gap', 'gap between joints', v3(mix3(padAt('VIN'), padAt('BOUT1'), 0.5)), 'b', true),
            ]
          : [],
    },
    {
      d: 10,
      text: 'Set the meter to DC volts and plug the battery into a lead. Red probe on red reads about 3.8 V, with no minus sign.',
      cam: { p: [-0.06, 0.25, 0.3], t: [-0.07, 0.01, 0.03], fov: 32 },
      act(S, u) {
        S.a('lead').show().at(...LEADP);
        battery(S, easeInOut(span(u, 0.05, 0.25)));
        if (u >= 1) return; // the probes go back before the next beat
        const land = easeInOut(span(u, 0.32, 0.5));
        probes(S, land, leadEnd(-1), leadEnd(1));
        S.meter(land >= 1 ? '3.80' : '0.00', 'V');
      },
      labels: (S, u) => [
        ...(u > 0.12 ? [L('apart', 'bare ends apart', v3(add3(LEADP, [0.066, 0.003, 0])), 'r')] : []),
        ...(u > 0.5 ? [L('v', '3.80 V', meterSideAt(S), 'r', true)] : []),
        ...(u > 0.66 ? [L('minus', 'a minus sign: lead is backwards', S.node('multimeter', null, [-0.035, 0.03, 0.02]), 't')] : []),
      ],
    },
    {
      d: 9,
      text: 'Unplug the battery. Melt fresh solder onto the tip and leave it there: the coat stops the tip rusting.',
      cam: { p: [0.1, 0.22, 0.33], t: [0.0, 0.02, 0.03], fov: 32 },
      cam2: { p: add3(IRON_REST, [0.03, 0.055, 0.1]), t: add3(IRON_REST, [-0.004, 0, 0]), fov: 30 },
      act(S, u, k) {
        S.a('lead').show().at(...LEADP);
        const out = easeInOut(span(u, 0.04, 0.2));
        if (u < 1) battery(S, 1 - out);
        const up = easeInOut(span(u, 0.28, 0.4));
        const home = easeInOut(span(u, 0.72, 0.92));
        const pose = home > 0 ? mixIron(AIR_POSE, REST, home) : mixIron(REST, AIR_POSE, up);
        ironTo(S, pose);
        const feed = span(u, 0.42, 0.68);
        const end = ironPt(pose, 1.2, 0.9);
        if (feed > 0 && feed < 1) {
          solderAt(S, mix3(add3(end, [-0.03, 0.006, 0]), end, easeOut(feed * 1.6)), 0.35);
          smokeAt(S, end, smooth(span(feed, 0.3, 0.5)) * (1 - smooth(span(feed, 0.85, 1))), k);
        }
        const g = smooth(span(u, 0.5, 0.68));
        if (g > 0) S.a('bead').show().at(...end).size(0.5 + 0.9 * g);
      },
      labels: (S, u) => [
        ...(u > 0.1 && u < 0.32 ? [L('out', 'battery out', S.node('battery'), 't')] : []),
        ...(u > 0.6 ? [L('coat', 'solder left on the tip', S.a('bead').obj, 'l', true)] : []),
      ],
    },
    {
      d: 10,
      text: 'Unplug the iron, leave it in the stand for 10 minutes and wash your hands with soap. Four wires, a clean bench.',
      cam: { p: [0.09, 0.47, 0.5], t: [0.06, 0.05, -0.02], fov: 36 },
      cam2: { p: [0.07, 0.49, 0.53], t: [0.06, 0.05, -0.02], fov: 36 },
      act(S, u) {
        const fade = smooth(span(u, 0.1, 0.95));
        S.tip({ tin: 1, heat: 1 - fade });
        S.screen(u > 0.12 ? '' : '330');
        trafficDone(S);
        spliceDone(S);
        for (let i = 0; i < 4; i++) {
          wireOnPad(S, i);
          padJoint(S, i, 0.7);
        }
      },
      labels: (S, u) => [
        ...(u > 0.12 ? [L('off', 'iron off', S.a('iron').obj.userData.screenAt, 't', true)] : []),
        ...(u > 0.3 ? [L('hot', 'still hot for 10 minutes', S.a('iron').obj.userData.hot, 'l')] : []),
      ],
      link: { href: '../pearl/#solder', text: 'Back to Pearl' },
      check: true,
    },
  ],
};

export const CHAPTERS = [bench, first, fix, light, wires, small];

export const buildSolderTimeline = () => buildTimeline(CHAPTERS);
