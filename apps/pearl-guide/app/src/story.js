// Stage 0 as seven chapters of short beats. Each beat has one caption, a camera, optional labels and an act(u, k)
// that poses the cast for progress u (0..1) or k seconds into the beat. Nothing keeps state between frames:
// every frame resets the cast and replays the chapter up to the playhead, so scrubbing and rewinding are exact.

import { Vector3 } from 'three';
import { clamp, drop, easeIn, easeInOut, easeOut, lerp, mix3, smooth, span } from './anim.js';
import { buildTimeline as timelineOf } from './director.js';
export { makeDirector } from './director.js';
import { PARK_AT, PURGE_AT } from './p1s.js';

const MM = 0.001;
const TAU = Math.PI * 2;
const v3 = (x, y, z) => new Vector3(x, y, z);

// ---------------------------------------------------------------- shared positions (metres, bench top y = 0)
const MAT_Y = 0.002;
const FLOAT_Y = 0.9; // Pearl's pod floor while it floats in chapter 1
const BAL_C = 0.3183; // balloon centre above the pod floor (pearl.glb)
const BAL_R = 0.28;
const PLATE = { x: 0, z: 0, top: 0.0012 };
const PRINT_AT = {
  print_shell: [-0.07, -0.05],
  print_collar: [0.03, -0.05],
  print_tail: [0.1, -0.05],
  print_hatch: [-0.07, 0.05],
  print_duct: [0.0, 0.055],
  print_duct2: [0.05, 0.055],
};
const STAND = [0.0, -0.19];
const BOARD = { x: 0.0, y: 0.0046, z: 0.02 }; // practice board resting on its resistor
const PAD_TOP = BOARD.y + 1.65 * MM;
const J1 = [BOARD.x - 3.81 * MM, PAD_TOP, BOARD.z - 1.27 * MM];
const J2 = [BOARD.x + 6.35 * MM, PAD_TOP, BOARD.z - 1.27 * MM];
const TANK = [0.4, -0.12];
const NOZZLE = [TANK[0] + 0.078, 0.428, TANK[1]];
const SCALE_AT = [-0.16, 0.06];
const SWITCH_LEVER = [-0.006, -0.0032, 0.0018]; // the switch lever's tip under the hatch (pod_v3.SWITCH_X)

const spin = (t, rps = 7) => (t * rps * TAU) % TAU;

function cupOnThread(S, top, cupY) {
  S.a('thread').show().obj.userData.setEnds(top, v3(top.x, cupY + 81 * MM, top.z));
  S.a('cup').show().at(top.x, cupY, top.z);
}

// ---------------------------------------------------------------- chapter 1
const meet = {
  id: 'meet',
  title: 'Meet Pearl',
  goal: 'What you are building, in half a minute.',
  work: '1 min',
  bench: false,
  setup(S, k) {
    S.internals(false);
    const yaw = 0.42 + 0.22 * Math.sin(k * 0.21);
    S.a('pearl').show().at(0, FLOAT_Y + 0.006 * Math.sin(k * 1.1), 0).turn(yaw);
    for (const p of ['propL', 'propR', 'propT']) S.a(p).spin(spin(S.t));
  },
  beats: [
    {
      d: 9,
      text: 'This is Pearl: a white helium orb 56 cm across, with a camera pod about the size of a computer mouse.',
      cam: { p: [1.1, 0.74, 1.3], t: [0, 1.13, 0], fov: 32 },
      cam2: { p: [0.98, 0.8, 1.38], t: [0, 1.13, 0], fov: 32 },
    },
    {
      d: 9,
      text: 'Two side fans steer it, a lift fan holds its height and the camera looks straight ahead.',
      cam: { p: [0.21, 0.865, 0.2], t: [-0.004, 0.918, 0], fov: 30 },
      labels: (S) => [
        { id: 'cam', text: 'camera', at: S.node('pearl', 'A pod camera'), side: 'r' },
        { id: 'fanR', text: 'side fan', at: S.node('pearl', 'A pod side fan R'), side: 'b' },
        { id: 'fanL', text: 'side fan', at: S.node('pearl', 'A pod side fan L'), side: 'l' },
        { id: 'lift', text: 'lift fan', at: S.node('pearl', 'A pod lift fan'), side: 'l' },
        { id: 'lock', text: 'twist lock', at: S.node('pearl', 'A pod twist lock'), side: 't' },
      ],
    },
    {
      d: 8,
      text: 'Coins in the hatch trim it to sink very slowly. If anything stops, Pearl drifts gently down.',
      cam: { p: [0.13, 0.82, 0.21], t: [-0.012, 0.904, 0], fov: 30 },
      act(S, u) {
        const o = smooth(span(u, 0.1, 0.4)) * (1 - smooth(span(u, 0.86, 1))); // opens, then shuts again
        S.a('hatch').at(0, -0.016 * o, 0);
        S.a('coins').at(0, -0.016 * o, 0);
        if (u < 1) S.internals(o > 0);
      },
      labels: (S, u) => (u > 0.35 && u < 0.86 ? [{ id: 'coins', text: 'trim coins', at: S.node('coins'), side: 'l' }] : []),
    },
    {
      d: 9,
      text: 'A slide switch on the hatch turns Pearl off. Its lever pokes through the floor, so the hatch stays shut.',
      cam: { p: [0.1, 0.8, 0.16], t: [-0.006, 0.9, 0], fov: 28 },
      labels: (S, u) => (u > 0.25 ? [{ id: 'sw', text: 'power switch', at: S.node('hatch', null, SWITCH_LEVER), side: 'b', strong: true }] : []),
    },
    {
      d: 8,
      text: 'Stage 0 gets you ready: buy the tools, print the pod, learn to solder and float your first orb.',
      cam: { p: [-0.95, 0.86, 1.42], t: [0, 1.12, 0], fov: 32 },
      cam2: { p: [-0.82, 0.9, 1.5], t: [0, 1.12, 0], fov: 32 },
    },
    {
      d: 9,
      text: "Stage 1 puts the same parts on a breadboard with Pearl's code, and checks the battery pin with the meter.",
      cam: { p: [-0.82, 0.9, 1.5], t: [0, 1.12, 0], fov: 32 },
      cam2: { p: [-0.7, 0.95, 1.58], t: [0, 1.12, 0], fov: 32 },
    },
  ],
};

// ---------------------------------------------------------------- chapter 2
const ONLINE = [
  ['balloon_flat', -0.58, 0.0, 0.0006, 0],
  ['scale', -0.4, 0.0, -0.17, 0],
  ['motor1', -0.41, 0.003, -0.05, 0, 0, Math.PI / 2],
  ['motor2', -0.41, 0.003, -0.025, 0, 0, Math.PI / 2],
  ['prop1', -0.335, 0, -0.07, 0],
  ['prop2', -0.3, 0, -0.07, 0.6],
  ['prop3', -0.335, 0, -0.035, 1.1],
  ['prop4', -0.3, 0, -0.035, 1.9],
  ['battery', -0.41, 0, 0.035, 0],
  ['lead1', -0.29, 0.0022, 0.03, 0],
  ['lead2', -0.29, 0.0022, 0.045, 0],
  ['driver1', -0.42, 0, 0.1, 0],
  ['driver2', -0.395, 0, 0.1, 0],
  ['driver3', -0.37, 0, 0.1, 0],
  ['wires', -0.33, 0, 0.1, 0],
  ['stripper', -0.42, 0.004, 0.16, 0],
];
const POSTED = [
  ['stand', 0.06, 0, -0.205, 0],
  ['third_hand', 0.28, 0, -0.2, -0.3],
  ['multimeter', -0.13, MAT_Y, 0.02, 0],
  ['iron', -0.05, MAT_Y + 0.012, -0.08, 0],
  ['solder_tube', -0.04, MAT_Y + 0.0075, -0.035, 0],
  ['flux_pen', -0.04, MAT_Y + 0.007, -0.005, 0],
  ['braid', 0.15, MAT_Y, -0.03, 0],
  ['cutters', -0.04, MAT_Y + 0.004, 0.045, 0],
  ['tweezers', -0.04, MAT_Y + 0.0004, 0.09, 0],
  ['practice_board', 0.14, MAT_Y, 0.05, 0.2],
  ['shrink', 0.14, MAT_Y, 0.105, 0],
];
const OTHER = [
  ['helium_tank', 0.5, 0, -0.16, -0.5],
  ['spool', 0.5, 0, 0.11, 0],
  ['cup', 0.36, 0, 0.02, 0],
  ['coin1', 0.37, 0, 0.16, 0],
  ['coin2', 0.37, 0.0027, 0.16, 0],
  ['coin3', 0.37, 0.0054, 0.16, 0],
  ['coin4', 0.395, 0, 0.17, 0],
  ['coin5', 0.395, 0.0027, 0.17, 0],
  ['coin6', 0.395, 0.0054, 0.17, 0],
  ['coin7', 0.42, 0, 0.16, 0],
  ['coin8', 0.42, 0.0016, 0.16, 0],
];

function lay(S, list, u, stagger = 0.045) {
  list.forEach(([name, x, y, z, ry = 0, rx = 0, rz = 0], i) => {
    const local = clamp((u - i * stagger) / 0.35);
    if (local <= 0) return;
    const { dy, alpha } = drop(local, 0.06);
    S.a(name).show(alpha).at(x, y + dy, z).turn(ry, rx, rz);
  });
}

const buy = {
  id: 'buy',
  title: 'Buy the kit',
  goal: 'Everything came by post except a few things still to buy.',
  work: '30 minutes to unpack and order the rest',
  bench: true,
  setup(S) {
    S.a('mat').show(0);
  },
  beats: [
    {
      d: 9,
      text: 'These came by post: a 0.01 g scale, balloons, motors, props, a small battery, leads and fine wire.',
      cam: { p: [-0.42, 0.62, 0.42], t: [-0.43, 0, -0.01], fov: 32 },
      act(S, u) {
        lay(S, ONLINE, u * 1.15, 0.04);
      },
      labels: (S, u) =>
        u > 0.7
          ? [
              { id: 'b', text: 'white 32-inch balloon', at: S.node('balloon_flat'), side: 'l' },
              { id: 's', text: '0.01 g scale', at: S.node('scale'), side: 't' },
              { id: 'm', text: 'motors and props', at: S.node('motor2'), side: 'r' },
              { id: 'bat', text: '1S battery', at: S.node('battery'), side: 'r' },
            ]
          : [],
    },
    {
      d: 9,
      text: 'The soldering tools came by post: a pen iron, solder, flux, a meter, hand tools and a practice kit.',
      cam: { p: [0.03, 0.74, 0.62], t: [0.04, 0, -0.06], fov: 32 },
      act(S, u) {
        lay(S, ONLINE, 1);
        S.a('mat').show(smooth(u * 3));
        lay(S, POSTED, u * 1.12, 0.045);
      },
      labels: (S, u) =>
        u > 0.75
          ? [
              { id: 'pen', text: 'pen iron', at: S.node('iron'), side: 't' },
              { id: 'mm', text: 'multimeter', at: S.node('multimeter'), side: 'l' },
              { id: 'kit', text: 'practice kit', at: S.node('practice_board'), side: 'r' },
              { id: 'th', text: 'helping hands', at: S.node('third_hand'), side: 't' },
            ]
          : [],
    },
    {
      d: 10,
      text: 'Still to buy: a helium tank from Spotlight, matte white PLA, glasses, switches and resistors. The rest is from home.',
      cam: { p: [0.56, 0.86, 0.98], t: [0.42, 0.12, -0.03], fov: 32 },
      act(S, u) {
        lay(S, ONLINE, 1);
        S.a('mat').show();
        lay(S, POSTED, 1);
        lay(S, OTHER, u * 1.2, 0.05);
      },
      labels: (S, u) =>
        u > 0.6
          ? [
              { id: 'he', text: 'helium', at: S.node('helium_tank'), side: 'l' },
              { id: 'pla', text: 'matte white PLA', at: S.node('spool'), side: 'r' },
            ]
          : [],
    },
    {
      d: 8,
      text: 'All of Stage 0 on one mat. Open Kit to tick what you have and to see what is still to buy.',
      cam: { p: [0.02, 1.3, 1.18], t: [0.02, 0.06, -0.06], fov: 34 },
      act(S) {
        lay(S, ONLINE, 1);
        S.a('mat').show();
        lay(S, POSTED, 1);
        lay(S, OTHER, 1);
      },
      check: true,
    },
  ],
};

// ---------------------------------------------------------------- chapter 3
// The P1S stands where the mat was. Beats write what they want into S.L; after() applies it once per frame, so
// the filament and PTFE tube are rebuilt only when something they follow has moved.
const BED_PRINT = 280.6; // bed top (mm) for the first layer: the nozzle tip less the plate and one layer
const DUCT_H = 0.012; // the side duct prints 12 mm tall
const p1sOf = (S) => S.a('p1s').obj.userData.p1s;
const coilOf = (S) => S.a('petg_coil').obj.userData.coil;
const READY = { title: 'Ready', line: 'External spool', buttons: ['Load', 'Unload'], sel: null };

const loadPrinter = {
  id: 'load',
  title: 'Load the printer',
  goal: 'Feed the leftover PETG into your P1S and print one side duct.',
  work: '30 min, plus 18 minutes of printing',
  bench: true,
  setup(S) {
    S.a('mat').show(0);
    S.a('p1s').show().at(0, 0, 0);
    S.L = { door: 0, head: [...PARK_AT], bed: 150, feed: 0, purge: 0, route: 0, coil: 0, plate: null, duct: null, screen: READY };
  },
  after(S) {
    const L = S.L;
    const P = p1sOf(S);
    P.door(L.door);
    P.bed(L.bed);
    P.head(L.head[0], L.head[1]);
    P.feed(L.feed);
    P.purge(L.purge);
    P.screen(L.screen);
    if (L.coil) {
      const c = typeof L.coil === 'number' ? { alpha: L.coil, dy: 0 } : L.coil;
      S.a('petg_coil').show(c.alpha).at(0, c.dy, 0);
      coilOf(S).route(L.route);
    }
    const plate = L.plate === 'bed' ? [0, L.bed * MM, 0, 0] : L.plate;
    if (plate) {
      S.a('plate').show().at(plate[0], plate[1], plate[2]).turn(0, 0, plate[3]);
      if (L.duct) S.a('petg_duct').show(L.duct.alpha ?? 1).at(plate[0], plate[1] + PLATE.top + (L.duct.dy ?? 0), plate[2]);
      if (L.duct?.clip != null) S.clip(plate[1] + PLATE.top + L.duct.clip);
    }
  },
  beats: [
    {
      d: 9,
      text: 'Your P1S has no AMS. Filament goes in by hand, through the PTFE tube at the back, to the toolhead.',
      cam: { p: [-0.74, 1.06, -0.84], t: [-0.03, 0.29, -0.06], fov: 32 },
      cam2: { p: [-0.66, 1.1, -0.9], t: [-0.03, 0.29, -0.06], fov: 32 },
      labels: (S) => {
        const a = p1sOf(S).anchors;
        return [
          { id: 'tube', text: 'PTFE tube', at: a.inlet, side: 'l' },
          { id: 'head', text: 'toolhead', at: a.head, side: 't' },
          { id: 'chute', text: 'purge chute', at: a.chute, side: 'l' },
        ];
      },
    },
    {
      d: 9,
      text: 'Measure your PETG and write it down. About 2 m is enough for one side duct, with plenty to spare.',
      cam: { p: [-0.5, 0.44, -1.02], t: [-0.09, 0.05, -0.33], fov: 32 },
      act(S, u) {
        S.L.coil = drop(clamp(u / 0.35), 0.08);
      },
      labels: (S, u) => (u > 0.45 ? [{ id: 'len', text: 'about 2 m of PETG', at: v3(-0.138, 0.006, -0.326), side: 't', strong: true }] : []),
    },
    {
      d: 8,
      text: 'Snip the end at a slant with side cutters, then straighten the first 10 cm.',
      cam: { p: [0.15, 0.14, -0.29], t: [0.03, 0.0, -0.397], fov: 28 },
      act(S, u) {
        S.L.coil = 1;
        if (u >= 1) return; // the offcut and the cutters are put away
        // the jaws close across the strand 6 mm from its end; the offcut springs off and lands beside it
        const reach = easeInOut(span(u, 0.08, 0.34)) * (1 - easeInOut(span(u, 0.6, 0.85)));
        S.a('cutters').show().at(0.0248, 0.004 + 0.002 * (1 - reach), -0.402 + 0.006 + 0.08 * (1 - reach)).turn(-Math.PI / 2 + 0.25 * (1 - reach));
        const fall = easeOut(span(u, 0.42, 0.62));
        S.a('offcut').show(1 - smooth(span(u, 0.86, 1))).at(0.0278 + 0.012 * fall, 0.0009 + 0.007 * Math.sin(fall * Math.PI), -0.402 - 0.006 * fall).turn(0.2 * fall);
      },
      labels: (S, u) => (u > 0.4 && u < 0.95 ? [{ id: 'snip', text: 'cut at a slant', at: v3(0.025, 0.002, -0.402), side: 't', strong: true }] : []),
    },
    {
      d: 11,
      text: 'Push the end into the PTFE tube at the back. Keep pushing until it stops at the extruder.',
      cam: { p: [-0.7, 0.98, -0.82], t: [-0.06, 0.3, -0.12], fov: 32 },
      act(S, u) {
        S.L.coil = 1;
        S.L.route = easeInOut(span(u, 0.0, 0.3));
        S.L.feed = easeInOut(span(u, 0.32, 0.92));
      },
      labels: (S, u) => {
        const a = p1sOf(S).anchors;
        if (u < 0.35) return [{ id: 'tube', text: 'PTFE tube', at: a.inlet, side: 'l' }];
        return u > 0.9 ? [{ id: 'ext', text: 'stops at the extruder', at: a.head, side: 't', strong: true }] : [];
      },
    },
    {
      d: 9,
      text: 'Choose Load on the screen. The nozzle heats to 250 °C, so keep your fingers out of the printer.',
      cam: { p: [-0.05, 0.47, 0.52], t: [-0.09, 0.415, 0.2], fov: 26 },
      act(S, u) {
        const heat = span(u, 0.25, 0.9);
        const go = easeInOut(span(u, 0.25, 0.6)); // the toolhead moves over the purge chute while it heats
        S.L.head = [lerp(PARK_AT[0], PURGE_AT[0], go), lerp(PARK_AT[1], PURGE_AT[1], go)];
        if (u < 0.25) S.L.screen = { ...READY, sel: u > 0.1 ? 'Load' : null };
        else S.L.screen = { title: 'Heating', line: 'Load filament', nozzle: lerp(25, 250, smooth(heat)), target: 250, bar: heat };
      },
      labels: (S, u) => (u > 0.9 ? [{ id: 'hot', text: '250 °C', at: p1sOf(S).anchors.screen, side: 't', strong: true }] : []),
    },
    {
      d: 9,
      text: 'At 250 °C push again. The extruder grips the PETG and pulls it down to the nozzle.',
      cam: { p: [0.06, 0.8, 0.22], t: [-0.13, 0.35, -0.15], fov: 28 },
      act(S, u) {
        S.L.feed = 1 + easeInOut(span(u, 0.15, 0.85));
        S.L.screen = { title: 'Loading', line: 'Feeding', nozzle: 250, target: 250 };
      },
      labels: (S, u) => (u > 0.2 ? [{ id: 'ext', text: 'extruder', at: p1sOf(S).anchors.head, side: 't' }] : []),
    },
    {
      d: 10,
      text: 'PETG flows out of the nozzle and down the chute. Choose Done, or Retry if nothing comes out.',
      cam: { p: [-0.01, 0.33, 0.5], t: [-0.135, 0.285, -0.14], fov: 24 },
      act(S, u) {
        S.L.purge = u < 1 ? easeOut(span(u, 0.1, 0.7)) : 0;
        S.L.screen = u < 0.7 ? { title: 'Loading', line: 'Purging', nozzle: 250, target: 250 } : { title: 'Purged', line: 'Check the nozzle', nozzle: 250, target: 250, buttons: ['Done', 'Retry'], sel: 'Done' };
      },
      labels: (S, u) => {
        const a = p1sOf(S).anchors;
        const out = [];
        if (u > 0.3 && u < 0.98) out.push({ id: 'purge', text: 'PETG out of the nozzle', at: a.nozzle, side: 'r', strong: true });
        return out;
      },
    },
    {
      d: 10,
      text: 'In Bambu Studio choose Generic PETG under Prepare, and set the external spool to it under Device.',
      cam: { p: [0.2, 0.5, 0.72], t: [0.0, 0.27, -0.01], fov: 30 },
      act(S, u) {
        S.L.screen = { ...READY, line: 'External spool: PETG' };
        S.L.head = [lerp(PURGE_AT[0], PARK_AT[0], easeInOut(span(u, 0.0, 0.4))), lerp(PURGE_AT[1], PARK_AT[1], easeInOut(span(u, 0.0, 0.4)))];
        S.L.bed = lerp(150, BED_PRINT, easeInOut(span(u, 0.05, 0.45)));
        S.L.plate = 'bed';
        S.L.duct = { alpha: 0.25 + 0.2 * smooth(span(u, 0.4, 0.7)) };
      },
      labels: (S, u) => {
        if (u < 0.5) return [];
        const a = p1sOf(S).anchors;
        return [
          { id: 'fil', text: 'Generic PETG', at: S.node('petg_duct'), side: 'r', strong: true },
          { id: 'noz', text: 'nozzle 255 °C', at: a.head, side: 'l' },
          { id: 'bed', text: 'plate 70 °C', at: v3(0.1, BED_PRINT * MM, 0.12), side: 'r' },
        ];
      },
    },
    {
      d: 11,
      text: 'Open the door and print one side duct: about 0.55 m of PETG and 18 minutes, plus 14 cm to start.',
      cam: { p: [0.26, 0.5, 0.66], t: [0.0, 0.285, 0.0], fov: 30 },
      act(S, u, k) {
        S.L.door = easeInOut(span(u, 0.0, 0.2));
        const p = span(u, 0.24, 0.92);
        const h = DUCT_H * easeInOut(p);
        S.L.bed = BED_PRINT - h / MM;
        S.L.plate = 'bed';
        S.L.screen = { title: 'Printing', line: 'Side duct', nozzle: 255, target: 255, bed: 70, bedTarget: 70, bar: p };
        if (u >= 0.95) {
          S.L.duct = { alpha: 1 };
          S.L.head = [...PARK_AT];
          return; // printed: no clipping, toolhead back out of the way
        }
        S.L.duct = { alpha: u < 0.24 ? 0.45 : 1, clip: u < 0.24 ? null : h + 0.0004 };
        if (u >= 0.24) S.L.head = [24 * Math.sin(k * 3.1), 2 + 22 * Math.cos(k * 2.3)];
      },
      labels: (S, u) => (u > 0.06 && u < 0.3 ? [{ id: 'door', text: 'door open', at: p1sOf(S).anchors.door, side: 'r', strong: true }] : []),
    },
    {
      d: 9,
      text: 'Let the plate cool, then lift it out and flex it. The duct pops off.',
      cam: { p: [0.22, 0.56, 1.06], t: [0.0, 0.24, 0.24], fov: 30 },
      cam2: { p: [0.16, 0.42, 0.98], t: [0.0, 0.07, 0.38], fov: 30 },
      act(S, u) {
        const y0 = (BED_PRINT * MM) - DUCT_H;
        S.L.bed = y0 / MM;
        const out = easeInOut(span(u, 0.05, 0.35));
        const down = easeInOut(span(u, 0.35, 0.55));
        const flex = Math.sin(span(u, 0.6, 0.85) * Math.PI);
        S.L.plate = [0, lerp(y0, 0, down), lerp(0, 0.34, out) + 0.06 * down, 0.06 * flex];
        S.L.duct = { dy: 0.01 * Math.sin(span(u, 0.66, 0.88) * Math.PI) };
        S.L.screen = { title: 'Finished', line: 'Side duct', nozzle: 40, target: 0, bed: 35, bedTarget: 0 };
      },
      labels: (S, u) => (u > 0.86 ? [{ id: 'duct', text: 'side duct', at: S.node('petg_duct'), side: 'r', strong: true }] : []),
    },
    {
      d: 9,
      text: 'Choose Unload and pull the rest out at the back. One PETG side duct: good place to stop.',
      cam: { p: [0.78, 0.82, 0.95], t: [0.0, 0.2, 0.15], fov: 32 },
      act(S, u) {
        S.L.bed = BED_PRINT - DUCT_H / MM;
        S.L.plate = [0, 0, 0.4, 0];
        S.L.duct = {};
        S.L.feed = 2 * (1 - easeInOut(span(u, 0.05, 0.55)));
        S.L.route = 1 - easeInOut(span(u, 0.55, 0.8));
        S.L.screen = u < 0.55 ? { title: 'Unloading', line: 'Pull it out at the back', nozzle: 250, target: 250 } : READY;
      },
      check: true,
    },
  ],
};

// ---------------------------------------------------------------- chapter 4
const PRINTS = Object.keys(PRINT_AT);

function placePrints(S, alpha = 1) {
  for (const name of PRINTS) {
    const [x, z] = PRINT_AT[name];
    S.a(name).show(alpha).at(PLATE.x + x, PLATE.top, PLATE.z + z);
  }
}

const print = {
  id: 'print',
  title: 'Print the pod',
  goal: 'Six parts on your P1S, weighed and test-fitted.',
  work: '1 evening, plus 4 hours of printing',
  bench: true,
  setup(S) {
    S.a('mat').show(0);
    S.a('plate').show().at(PLATE.x, 0, PLATE.z);
    S.clip(null);
  },
  beats: [
    {
      d: 10,
      text: 'In Bambu Studio choose PLA Matte, the 0.12 mm Fine preset, Arachne walls and tree supports. The files are under Files.',
      cam: { p: [0.2, 0.3, 0.33], t: [0.01, 0.01, 0.0], fov: 30 },
      act(S, u) {
        placePrints(S, 0.22 + 0.18 * smooth(u * 2));
      },
      labels: (S) => [
        { id: 'sh', text: 'shell', at: S.node('print_shell'), side: 'l' },
        { id: 'cap', text: 'pole cap', at: S.node('print_collar'), side: 't' },
        { id: 'ha', text: 'hatch', at: S.node('print_hatch'), side: 'l' },
        { id: 'du', text: 'side ducts', at: S.node('print_duct2'), side: 'r' },
        { id: 'ta', text: 'lift duct', at: S.node('print_tail'), side: 'r' },
      ],
    },
    {
      d: 10,
      text: 'Print all six on one plate with the door open. It takes about four hours and 40 g of filament, most of it support.',
      cam: { p: [0.17, 0.16, 0.24], t: [0.0, 0.015, -0.005], fov: 30 },
      cam2: { p: [0.22, 0.2, 0.2], t: [0.0, 0.015, -0.005], fov: 30 },
      act(S, u, k) {
        placePrints(S);
        const h = 0.0372 * easeInOut(span(u, 0.05, 0.92));
        if (u >= 0.95) return; // printed: nothing clipped, toolhead parked out of shot
        S.clip(PLATE.top + h);
        // the toolhead hops between parts at the current layer, as a time-lapse would show it
        const stops = PRINTS.map((n) => PRINT_AT[n]);
        const f = (k * 2.2) % stops.length;
        const i = Math.floor(f);
        const a = stops[i];
        const b = stops[(i + 1) % stops.length];
        const w = smooth((f - i) * 1.8);
        S.a('head').show().at(lerp(a[0], b[0], w) + 0.012 * Math.sin(k * 9), PLATE.top + h + 0.0004, lerp(a[1], b[1], w) + 0.01 * Math.cos(k * 7));
      },
    },
    {
      d: 9,
      text: 'Let the plate cool, then flex it and the parts pop off. Pull the supports out of the shell and the cap.',
      cam: { p: [0.18, 0.2, 0.26], t: [0.0, 0.02, 0.0], fov: 30 },
      act(S, u) {
        placePrints(S);
        const flex = Math.sin(span(u, 0.08, 0.4) * Math.PI);
        S.a('plate').turn(0, 0, 0.06 * flex);
        PRINTS.forEach((n, i) => {
          const hop = Math.sin(span(u, 0.12 + i * 0.06, 0.32 + i * 0.06) * Math.PI);
          const [x, z] = PRINT_AT[n];
          S.a(n).at(PLATE.x + x, PLATE.top + 0.01 * hop, PLATE.z + z);
        });
      },
    },
    {
      d: 8,
      text: 'Weigh each part and write it down. The shell is about 6 g and all six together about 16.5 g.',
      cam: { p: [-0.22, 0.2, 0.3], t: [-0.16, 0.03, 0.06], fov: 30 },
      act(S, u) {
        S.a('plate').show(1 - smooth(u * 4));
        S.a('scale').show().at(SCALE_AT[0], 0, SCALE_AT[1]);
        const sc = S.a('scale').obj.userData;
        const w = easeInOut(span(u, 0.08, 0.4));
        const from = [PLATE.x + PRINT_AT.print_shell[0], PLATE.top, PLATE.z + PRINT_AT.print_shell[1]];
        const to = [SCALE_AT[0], sc.panTop, SCALE_AT[1] + sc.panZ];
        const p = mix3(from, to, w);
        S.a('print_shell').show().at(p[0], p[1] + 0.05 * Math.sin(w * Math.PI), p[2]);
        sc.setReading(u > 0.45 ? '6.31' : '0.00');
        for (const n of PRINTS) if (n !== 'print_shell') S.a(n).show(1 - smooth(u * 3));
      },
      labels: (S, u) => (u > 0.5 ? [{ id: 'w', text: '6.31 g', at: S.node('scale'), side: 'r', strong: true }] : []),
    },
    {
      d: 9,
      text: 'Hold the shell up to a lamp. An even glow is fine. If you can see your fingers through it, tell Claude.',
      cam: { p: [0.0, 0.16, 0.34], t: [0.0, 0.14, 0.0], fov: 30 },
      act(S, u) {
        S.a('lamp').show(smooth(u * 3)).at(0, 0.15, -0.16);
        S.a('print_shell').show().at(0, 0.12, 0.0).turn(0.3 * Math.sin(u * 2.4), -0.25, 0);
        S.glow('print_shell', u < 1 ? 0.9 * smooth(span(u, 0.1, 0.4)) : 0);
      },
    },
    {
      d: 9,
      text: "Push the shell's spigot into the cap and turn it until it clicks. The lock should hold the shell's weight.",
      cam: { p: [0.1, 0.15, 0.19], t: [0.0, 0.035, 0.0], fov: 30 },
      act(S, u) {
        const down = easeInOut(span(u, 0.08, 0.45));
        const twist = easeInOut(span(u, 0.5, 0.7));
        const lift = easeInOut(span(u, 0.78, 1));
        // as on Pearl: the shell hangs from the cap, so the cap goes on top, socket down over the spigot
        S.a('print_shell').show().at(0, 0.03 * lift, 0);
        S.a('print_collar').show().at(0, lerp(0.1, 0.0425, down) + 0.03 * lift, 0).turn(0.44 * twist, Math.PI, 0);
      },
      labels: (S, u) => (u > 0.66 && u < 0.85 ? [{ id: 'click', text: 'click', at: v3(0.0, 0.045, 0.036), side: 'r', strong: true }] : []),
    },
    {
      d: 8,
      text: 'Six white parts, weighed, and a twist lock that clicks and holds. Good place to stop.',
      cam: { p: [0.06, 0.3, 0.36], t: [0.02, 0.02, 0.03], fov: 30 },
      act(S) {
        S.a('scale').show().at(SCALE_AT[0], 0, SCALE_AT[1]);
        const layout = { print_hatch: [0.1, -0.01], print_duct: [-0.02, 0.085], print_duct2: [0.035, 0.085], print_tail: [0.1, 0.075] };
        for (const [n, [x, z]] of Object.entries(layout)) S.a(n).show().at(x, 0, z);
        S.a('print_shell').show().at(0, 0, 0);
        S.a('print_collar').show().at(0, 0.0425, 0).turn(0.44, Math.PI, 0);
        S.a('scale').obj.userData.setReading('16.48');
      },
      check: true,
    },
  ],
};

// ---------------------------------------------------------------- chapter 5
function ironAt(S, p, yaw = -0.5, tilt = 0.72) {
  S.a('iron').show().at(p[0], p[1], p[2]).turn(yaw, 0, tilt);
}
const IRON_REST = [STAND[0] + 0.004, 0.034, STAND[1]];
const SPONGE = [STAND[0] - 0.025, 0.024, STAND[1]];

// The switched battery lead, laid along +x from its plug: the lead's red wire ends at a switch pin and a new red
// wire leaves from the next pin, as in Pearl's pod. The two free ends splay apart so the divider spans them.
const LEAD = { x: -0.175, z: 0.098 }; // lead3's plug end; its wires run 70 mm towards +x
const WIRE_Y = MAT_Y + 0.0022; // the lead's wires above the mat
const RED_Z = LEAD.z + 0.00175; // the lead's red wire (black is the mirror image)
const BLACK_Z = LEAD.z - 0.00175;
const TAIL = 0.03; // new wires, metres
const SPLAY = 0.284; // radians each side: the ends land two resistor spans (20.3 mm) apart
const SW = { x: LEAD.x + 0.0725, z: RED_Z + 0.00385 }; // pins face the red wire
const METER = [-0.12, MAT_Y, -0.06];

function switchedLead(S, a = 1) {
  S.a('lead3').show(a).at(LEAD.x, WIRE_Y, LEAD.z).turn(Math.PI);
  S.a('switch').show(a).at(SW.x, WIRE_Y - 0.00175, SW.z).turn(Math.PI);
  const redStart = [SW.x, WIRE_Y, RED_Z];
  const blackStart = [LEAD.x + 0.07, WIRE_Y, BLACK_Z];
  S.a('swRed').show(a).at(...redStart).turn(-SPLAY);
  S.a('swBlack').show(a).at(...blackStart).turn(SPLAY);
  const end = (p, yaw) => [p[0] + TAIL * Math.cos(yaw), p[1], p[2] - TAIL * Math.sin(yaw)];
  const redEnd = end(redStart, -SPLAY);
  const blackEnd = end(blackStart, SPLAY);
  if (a > 0.5) {
    S.a('jS1').show().at(SW.x - 0.0025, WIRE_Y - 0.0003, RED_Z);
    S.a('jS2').show().at(SW.x, WIRE_Y - 0.0003, RED_Z);
    S.a('jS3').show().at(blackStart[0], WIRE_Y - 0.0003, BLACK_Z);
  }
  return {
    redLead: [LEAD.x + 0.06, WIRE_Y, RED_Z],
    redOut: end(redStart, -SPLAY).map((v, i) => lerp(redStart[i], v, 0.45)),
    redEnd,
    blackEnd,
    mid: mix3(redEnd, blackEnd, 0.5),
  };
}

function divider(S, L, a) {
  if (a <= 0) return;
  // each resistor stands on its legs, 10.16 mm apart, across one half of the gap
  const yaw = Math.atan2(-(L.blackEnd[2] - L.redEnd[2]), L.blackEnd[0] - L.redEnd[0]);
  const lift = (1 - a) * 0.03;
  for (const [n, f] of [['resA', 0.25], ['resB', 0.75]]) {
    const p = mix3(L.redEnd, L.blackEnd, f);
    S.a(n).show(Math.min(1, a * 2)).at(p[0], p[1] + 0.0035 + lift, p[2]).turn(yaw);
  }
  if (a >= 1) for (const [n, p] of [['jS4', L.redEnd], ['jS5', L.blackEnd], ['jS6', L.mid]]) S.a(n).show().at(p[0], p[1] - 0.0003, p[2]);
}

function battery(S, a) {
  // the battery's plug (bench.glb anchor at its +x end) pushes into the lead's socket
  const plug = S.node('battery', 'A battery plug').position;
  S.a('battery').show().at(LEAD.x - 0.006 - plug.x - 0.012 * (1 - a), MAT_Y, LEAD.z - plug.z);
}

function probes(S, a, red, black) {
  S.a('multimeter').show().at(...METER);
  const up = 0.03 * (1 - a);
  const tilt = (p, rz) => [p[0], p[1] + 0.0004 + up, p[2], rz];
  const tops = [];
  for (const [n, [x, y, z, rz]] of [['probeR', tilt(red, 0.3)], ['probeB', tilt(black, -0.3)]]) {
    S.a(n).show().at(x, y, z).turn(0, -0.35, rz);
    // the handle's top, 80 mm up the probe after the roll (rz) and the lean back (-0.35)
    tops.push(v3(x - 0.08 * Math.sin(rz), y + 0.08 * Math.cos(rz) * Math.cos(0.35), z - 0.08 * Math.cos(rz) * Math.sin(0.35)));
  }
  const jack = (dx) => v3(METER[0] + dx, MAT_Y + 0.041, METER[2] + 0.035); // V and COM sockets on the meter's face
  S.a('cordR').show().obj.userData.setEnds(tops[0], jack(0.0));
  S.a('cordB').show().obj.userData.setEnds(tops[1], jack(-0.028));
}

// The practice driver board from the soldering page's last chapter: one red wire soldered to its VIN pad.
function practiceDriver(S) {
  const d = S.a('driver1').show().at(-0.1, MAT_Y, 0.03).turn(Math.PI / 2);
  d.obj.updateMatrixWorld(true);
  const pad = S.node('driver1', 'A driver VIN').getWorldPosition(new Vector3());
  S.a('wireP').show().at(pad.x + 0.029, pad.y + 0.0004, pad.z).turn(Math.PI);
  S.a('jointP').show().at(pad.x, pad.y - 0.0002, pad.z);
}

const solder = {
  id: 'solder',
  title: 'Solder the switched lead',
  goal: 'Put a switch in a spare battery lead, add a divider, and check both with the meter.',
  work: 'After the switches and 10 kΩ resistors arrive',
  bench: true,
  setup(S) {
    S.a('stand').show().at(STAND[0], 0, STAND[1]);
    S.a('practice_board').show().at(BOARD.x, BOARD.y, BOARD.z);
    S.a('resistor').show().at(BOARD.x + 1.27 * MM, 0.00645, BOARD.z - 1.27 * MM).turn(0, Math.PI, 0);
    S.a('jointA').show().at(J1[0], PAD_TOP - 0.0001, J1[2]);
    S.a('jointA2').show().at(J2[0], PAD_TOP - 0.0001, J2[2]);
    S.a('solder_tube').show().at(0.1, MAT_Y + 0.0075, -0.07).turn(0.4);
    S.a('flux_pen').show().at(0.11, MAT_Y + 0.007, -0.045).turn(0.4);
    S.a('braid').show().at(0.15, MAT_Y, 0.095);
    ironAt(S, IRON_REST, 0, 0.47);
    practiceDriver(S);
  },
  beats: [
    {
      d: 8,
      text: 'Learn on the soldering page first: 39 short steps that end with wires on a spare driver board.',
      link: { href: '../soldering/', text: 'Open the soldering page' },
      cam: { p: [0.06, 0.34, 0.44], t: [-0.03, 0.02, -0.07], fov: 32 },
      labels: (S) => [
        { id: 'pen', text: 'pen iron', at: S.a('iron').obj.userData.grip, side: 'b' },
        { id: 'drv', text: 'spare driver board', at: S.node('driver1'), side: 'l' },
      ],
    },
    {
      d: 10,
      text: 'Solder a slide switch into the red wire of a spare lead. The meter beeps through it only when the switch is on.',
      cam: { p: [SW.x + 0.02, 0.085, LEAD.z + 0.1], t: [SW.x - 0.004, 0.004, LEAD.z], fov: 28 },
      act(S, u) {
        const L = switchedLead(S, easeInOut(span(u, 0.0, 0.3)));
        const on = u > 0.62 && u < 1;
        S.a('switch').obj.userData.lever.position.x = (on ? 1 : -1) * MM;
        if (u >= 1) return;
        const p = easeInOut(span(u, 0.32, 0.5));
        probes(S, p, L.redLead, L.redOut);
      },
      labels: (S, u) => (u > 0.66 && u < 0.97 ? [{ id: 'beep', text: 'on: beep', at: S.node('switch', null, [0, 0.006, 0]), side: 't', strong: true }] : u > 0.36 && u < 0.6 ? [{ id: 'off', text: 'off: silent', at: S.node('switch', null, [0, 0.006, 0]), side: 't' }] : []),
    },
    {
      d: 11,
      text: 'Solder two 10 kΩ resistors in a row from red to black. With the battery in, the middle reads half its voltage.',
      cam: { p: [-0.05, 0.3, 0.3], t: [-0.11, 0.0, -0.005], fov: 34 },
      act(S, u) {
        const L = switchedLead(S, 1);
        S.a('switch').obj.userData.lever.position.x = MM;
        divider(S, L, easeInOut(span(u, 0.0, 0.3)));
        if (u >= 1) return; // unplugged and put away before the checkpoint
        battery(S, easeInOut(span(u, 0.3, 0.45)));
        probes(S, easeInOut(span(u, 0.45, 0.6)), L.mid, L.blackEnd);
      },
      labels: (S, u) =>
        u > 0.62 && u < 0.97
          ? [
              { id: 'v', text: '1.90 V: half of 3.80 V', at: S.node('multimeter', null, [0.02, 0.042, -0.05]), side: 'r', strong: true },
              { id: 'r', text: 'two 10 kΩ', at: S.node('resA', null, [0, 0.005, 0]), side: 't' },
            ]
          : [],
    },
    {
      d: 9,
      text: 'A lead that beeps only when switched on, and a divider that reads half the battery. Good place to stop.',
      cam: { p: [-0.05, 0.16, 0.25], t: [-0.1, 0.0, 0.07], fov: 32 },
      act(S) {
        divider(S, switchedLead(S, 1), 1);
        S.a('switch').obj.userData.lever.position.x = -MM;
      },
      check: true,
    },
  ],
};

// ---------------------------------------------------------------- chapter 6
const ORB_MID = [0.0, 0.62, -0.05];
const ORB_LIFT = 0.8; // orb centre while the cup hangs below it

const float = {
  id: 'float',
  title: 'Float the orb',
  goal: 'Fill one balloon and measure what it can lift. This decides the pod.',
  work: '30 min, then a minute a day',
  bench: true,
  setup(S) {
    S.a('mat').show(0);
    S.a('helium_tank').show().at(TANK[0], 0, TANK[1]);
  },
  beats: [
    {
      d: 8,
      text: "Unfold a balloon. Push the tank's nozzle into its fill tab and hold the two together.",
      cam: { p: [0.0, 0.62, 1.3], t: [0.22, 0.22, -0.05], fov: 32 },
      act(S) {
        S.a('balloon_flat').show().at(0.05, 0.0006, 0.02).turn(-Math.PI / 2);
      },
      labels: (S, u) =>
        u > 0.3
          ? [
              { id: 'tab', text: 'fill tab', at: S.node('balloon_flat', null, [0, 0.006, -0.236]), side: 't' },
              { id: 'n', text: 'foil nozzle', at: v3(...NOZZLE), side: 'r' },
            ]
          : [],
    },
    {
      d: 10,
      text: 'Open the valve gently. Stop when it is round and the creases are gone, before it feels drum-tight.',
      cam: { p: [0.0, 0.7, 1.75], t: [0.3, 0.55, -0.1], fov: 34 },
      act(S, u) {
        const f = easeOut(span(u, 0.05, 0.85));
        S.a('balloon_flat').show(1 - smooth(span(u, 0.0, 0.15))).at(0.05, 0.0006, 0.02).turn(-Math.PI / 2);
        const s = lerp(0.25, 1, f);
        // the orb grows from the nozzle; the bottom pole stays on it
        S.a('orb').show(smooth(span(u, 0.0, 0.12))).at(NOZZLE[0] - 0.02, NOZZLE[1] + BAL_R * s - 0.01, NOZZLE[2]).size([s, s * lerp(0.55, 1, f), s]).turn(0, 0, -0.5 * (1 - f));
      },
    },
    {
      d: 9,
      text: 'Pull the nozzle out and the tab seals itself. Measure the orb across the middle and write it down.',
      cam: { p: [0.0, 0.62, 1.7], t: [0.0, 0.58, -0.05], fov: 32 },
      act(S, u) {
        const m = easeInOut(span(u, 0.0, 0.35));
        S.a('orb').show().at(lerp(NOZZLE[0] - 0.02, ORB_MID[0], m), lerp(NOZZLE[1] + BAL_R - 0.01, ORB_MID[1], m) + 0.005 * Math.sin(u * 6), lerp(NOZZLE[2], ORB_MID[2], m));
        const d = u < 1 ? smooth(span(u, 0.45, 0.6)) : 0;
        S.a('dim').show(d).at(ORB_MID[0], ORB_MID[1], ORB_MID[2] + BAL_R + 0.03).size([Math.max(d, 0.01), 1, 1]);
      },
      labels: (S, u) => (u > 0.6 ? [{ id: 'w', text: 'about 56 cm', at: v3(ORB_MID[0], ORB_MID[1] + 0.03, ORB_MID[2] + 0.3), side: 't', strong: true }] : []),
    },
    {
      d: 12,
      text: 'Tie thread to the tab, hang a paper cup and add coins until it floats level, neither rising nor sinking.',
      cam: { p: [0.5, 0.62, 1.62], t: [0.0, 0.52, -0.05], fov: 34 },
      act(S, u, k) {
        // five $2 coins and two 10c coins go in; each one slows the climb until it hangs still
        const coins = ['coin1', 'coin2', 'coin3', 'coin4', 'coin5', 'coin7', 'coin8'];
        const times = [0.18, 0.3, 0.42, 0.54, 0.66, 0.76, 0.84];
        let rise = 0;
        let vel = 0.012;
        let last = 0;
        for (const tc of times) {
          if (u < tc) break;
          rise += vel * (tc - last);
          vel *= 0.5;
          last = tc;
        }
        rise += vel * Math.max(0, u - last);
        const y = lerp(ORB_MID[1], ORB_LIFT - 0.05, easeInOut(span(u, 0, 0.12))) + rise + 0.003 * Math.sin(k * 1.4) * (u > 0.86 ? 0.3 : 1);
        S.a('orb').show().at(ORB_MID[0], y, ORB_MID[2]);
        const tab = v3(ORB_MID[0], y - BAL_R - 0.012, ORB_MID[2]);
        const cupY = tab.y - 0.3;
        if (u >= 1) return; // the next beat takes the cup down to the scale
        cupOnThread(S, tab, cupY);
        coins.forEach((c, i) => {
          const t0 = times[i];
          if (u < t0 - 0.08) return;
          const f = easeOut(span(u, t0 - 0.08, t0));
          const restY = cupY + 0.002 + i * 0.0026;
          S.a(c).show().at(ORB_MID[0] + (i % 2 ? 0.004 : -0.004), lerp(restY + 0.12, restY, f), ORB_MID[2] + (i % 3) * 0.003);
        });
      },
      labels: (S, u) => (u > 0.88 ? [{ id: 'lv', text: 'hangs still', at: S.node('cup'), side: 'r', strong: true }] : []),
    },
    {
      d: 9,
      text: "Weigh the cup, coins and thread together. That is the orb's lift: 48 g or more is a pass.",
      cam: { p: [-0.1, 0.22, 0.36], t: [SCALE_AT[0] + 0.03, 0.04, SCALE_AT[1] - 0.03], fov: 32 },
      act(S, u) {
        S.a('scale').show().at(SCALE_AT[0], 0, SCALE_AT[1]);
        const sc = S.a('scale').obj.userData;
        const w = easeInOut(span(u, 0.05, 0.4));
        const px = SCALE_AT[0];
        const pz = SCALE_AT[1] + sc.panZ;
        const cupY = lerp(0.1, sc.panTop, w);
        S.a('cup').show().at(px, cupY, pz);
        ['coin1', 'coin2', 'coin3', 'coin4', 'coin5', 'coin7', 'coin8'].forEach((c, i) => S.a(c).show().at(px + (i % 2 ? 0.004 : -0.004), cupY + 0.002 + i * 0.0026, pz + (i % 3) * 0.003));
        sc.setReading(u > 0.45 ? '52.40' : '0.00');
        S.a('orb').show(1 - smooth(u * 4)).at(ORB_MID[0], ORB_LIFT + 0.2 * u, ORB_MID[2]);
        S.a('thread').show(0);
      },
      labels: (S, u) => (u > 0.5 ? [{ id: 'r', text: '52.40 g: a pass', at: S.node('scale'), side: 'r', strong: true }] : []),
    },
    {
      d: 10,
      text: 'The pod weighs about 38 g, so 48 g leaves 10 g of trim. The sums expect about 15 g spare and at worst 1 g.',
      cam: { p: [-0.12, 0.2, 0.3], t: [SCALE_AT[0] + 0.02, 0.03, SCALE_AT[1] - 0.02], fov: 32 },
      labels: (S) => [
        { id: 'r', text: '52.40 g lift', at: S.node('scale'), side: 'r', strong: true },
        { id: 'p', text: 'a 38 g pod leaves 14 g', at: S.node('cup'), side: 'l' },
      ],
    },
    {
      d: 9,
      text: 'Write down the width, the lift and the room temperature. Weigh the lift again each day for two weeks.',
      cam: { p: [0.0, 0.66, 1.75], t: [0.0, 0.55, -0.05], fov: 32 },
      act(S, u, k) {
        S.a('scale').show(0);
        for (const c of ['coin1', 'coin2', 'coin3', 'coin4', 'coin5', 'coin7', 'coin8']) S.a(c).show(0);
        S.a('orb').show().at(ORB_MID[0], ORB_LIFT + 0.004 * Math.sin(k), ORB_MID[2]);
        const tab = v3(ORB_MID[0], ORB_LIFT - BAL_R - 0.012, ORB_MID[2]);
        cupOnThread(S, tab, tab.y - 0.3);
      },
      check: true,
    },
  ],
};

// ---------------------------------------------------------------- chapter 7
const RIG = [0.06, 0.03]; // scale position for the thrust test

const spinFan = {
  id: 'spin',
  title: 'Spin a fan',
  goal: 'Solder a motor, fit it in a printed duct and weigh its push.',
  work: '1 evening',
  bench: true,
  setup(S) {
    S.a('braid').show().at(-0.15, MAT_Y, -0.08);
  },
  beats: [
    {
      d: 9,
      text: 'Solder the motor to a battery lead, red to red and blue to black, then cover both joints with heatshrink.',
      cam: { p: [-0.05, 0.14, 0.2], t: [-0.06, 0.003, 0.04], fov: 30 },
      act(S, u) {
        S.a('motor1').show().at(-0.13, MAT_Y + 0.003, 0.04).turn(0, 0, Math.PI / 2);
        const join = easeInOut(span(u, 0.05, 0.3));
        S.a('lead1').show().at(lerp(0.045, 0.0125, join), MAT_Y + 0.0022, 0.04);
        const slide = easeInOut(span(u, 0.55, 0.85));
        S.a('sleeve1').show().at(lerp(-0.035, -0.058, slide), MAT_Y + 0.0013, 0.041).turn(0, 0, Math.PI / 2);
        S.a('sleeve2').show().at(lerp(-0.035, -0.058, slide), MAT_Y + 0.0013, 0.039).turn(0, 0, Math.PI / 2);
      },
    },
    {
      d: 8,
      text: 'Push the motor into a printed side duct and press a prop onto the shaft.',
      cam: { p: [0.12, 0.12, 0.17], t: [RIG[0], 0.02, RIG[1]], fov: 28 },
      act(S, u) {
        S.a('test_duct').show().at(RIG[0], MAT_Y, RIG[1]);
        const m = easeInOut(span(u, 0.05, 0.4));
        // the motor clip sits at the centre of the ring, shaft up
        S.a('motor_rig').show().at(RIG[0], lerp(0.06, 0.0035, m) + MAT_Y, RIG[1]);
        const p = easeInOut(span(u, 0.5, 0.85));
        S.a('prop_rig').show().at(RIG[0], lerp(0.07, 0.0185, p) + MAT_Y, RIG[1]);
      },
    },
    {
      d: 8,
      text: 'Tape the duct to a small block on the scale, prop on top. Press zero so the scale reads 0.00.',
      cam: { p: [0.16, 0.16, 0.26], t: [RIG[0], 0.05, RIG[1]], fov: 30 },
      act(S, u) {
        rig(S, 0, 0);
        S.a('scale').obj.userData.setReading(u > 0.55 ? '0.00' : '31.62');
      },
      labels: (S, u) => (u > 0.6 ? [{ id: 'z', text: 'zeroed', at: S.node('scale'), side: 'r' }] : []),
    },
    {
      d: 9,
      text: 'Plug in the battery for five seconds. The fan blows upwards, so the scale shows how hard it pushes down.',
      cam: { p: [0.2, 0.15, 0.24], t: [RIG[0], 0.06, RIG[1]], fov: 30 },
      act(S, u, k) {
        const on = smooth(span(u, 0.2, 0.3)) * (1 - smooth(span(u, 0.85, 0.95)));
        rig(S, on, k);
        S.a('scale').obj.userData.setReading((4.1 * on).toFixed(2));
        const plug = easeInOut(span(u, 0.05, 0.2));
        S.a('battery').show().at(RIG[0] + 0.1, 0, RIG[1] + 0.07).turn(Math.PI * 0.8);
        S.a('lead2').show().at(lerp(RIG[0] + 0.07, RIG[0] + 0.06, plug), 0.0022, RIG[1] + 0.06).turn(Math.PI * 0.8);
      },
      labels: (S, u) => (u > 0.35 && u < 0.85 ? [{ id: 'th', text: '4.1 g of thrust', at: S.node('scale'), side: 'r', strong: true }] : []),
    },
    {
      d: 8,
      text: "Pearl's lift fan needs about 1.5 g. If the reading drops instead, swap the two motor wires.",
      cam: { p: [0.22, 0.2, 0.3], t: [RIG[0], 0.05, RIG[1]], fov: 30 },
      act(S) {
        rig(S, 0, 0);
        S.a('scale').obj.userData.setReading('4.10');
      },
    },
    {
      d: 9,
      text: "One fan's thrust, written down. Unplug the battery and keep it away from keys and coins. Stage 0 done.",
      cam: { p: [0.3, 0.28, 0.4], t: [0.0, 0.04, 0.0], fov: 32 },
      act(S) {
        rig(S, 0, 0);
        S.a('scale').obj.userData.setReading('0.00');
      },
      check: true,
    },
  ],
};

function rig(S, on, k) {
  const sc = S.a('scale').show().at(RIG[0] - 0.0, 0, RIG[1] + 0.016);
  const top = sc.obj.userData.panTop;
  const z = RIG[1] + 0.016 + sc.obj.userData.panZ;
  S.a('block').show().at(RIG[0], top, z);
  const y = top + 0.03;
  S.a('test_duct').show().at(RIG[0], y, z);
  S.a('motor_rig').show().at(RIG[0], y + 0.0035, z);
  S.a('prop_rig').show().at(RIG[0], y + 0.0185, z).spin(on > 0.01 ? (k * 40) % TAU : 0.4);
  S.a('tape').show().at(RIG[0] - 0.012, y + 0.0004, z + 0.01);
  if (on > 0.01) {
    S.a('air').show().at(RIG[0], y + 0.024, z);
    S.a('air').obj.userData.setFlow((k * 1.6) % 1, on);
  }
}

export const CHAPTERS = [meet, buy, loadPrinter, print, solder, float, spinFan];

export const buildTimeline = (chapters = CHAPTERS) => timelineOf(chapters);

export const GUIDE = {
  title: 'Stage 0: before the pod',
  lede: 'Check the kit, print Pearl’s pod, solder the switched lead and float your first orb. About four evenings of work.',
};
