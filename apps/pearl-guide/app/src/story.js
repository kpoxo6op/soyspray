// Stage 0 as six chapters of short beats. Each beat has one caption, a camera, optional labels and an act(u, k)
// that poses the cast for progress u (0..1) or k seconds into the beat. Nothing keeps state between frames:
// every frame resets the cast and replays the chapter up to the playhead, so scrubbing and rewinding are exact.

import { Vector3 } from 'three';
import { clamp, drop, easeInOut, easeOut, lerp, mix3, smooth, span } from './anim.js';
import { mixPose } from './stage.js';

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
const STATION = [-0.17, -0.2];
const BOARD = { x: 0.0, y: 0.0046, z: 0.02 }; // practice board resting on its resistor
const PAD_TOP = BOARD.y + 1.65 * MM;
const J1 = [BOARD.x - 3.81 * MM, PAD_TOP, BOARD.z - 1.27 * MM];
const J2 = [BOARD.x + 6.35 * MM, PAD_TOP, BOARD.z - 1.27 * MM];
const TANK = [0.4, -0.12];
const NOZZLE = [TANK[0] + 0.078, 0.428, TANK[1]];
const SCALE_AT = [-0.16, 0.06];

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
      d: 8,
      text: 'Stage 0 gets you ready: buy the tools, print the pod, learn to solder and float your first orb.',
      cam: { p: [-0.95, 0.86, 1.42], t: [0, 1.12, 0], fov: 32 },
      cam2: { p: [-0.82, 0.9, 1.5], t: [0, 1.12, 0], fov: 32 },
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
const JAYCAR = [
  ['station', STATION[0], 0, STATION[1], 0],
  ['stand', 0.06, 0, -0.205, 0],
  ['third_hand', 0.28, 0, -0.2, -0.3],
  ['multimeter', -0.13, MAT_Y, 0.02, 0],
  ['iron', -0.05, MAT_Y + 0.0098, -0.08, 0],
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
  goal: 'Order the online parts first, then make one trip to Jaycar.',
  work: '1 hour, then 1 to 3 weeks of post',
  bench: true,
  setup(S) {
    S.a('mat').show(0);
  },
  beats: [
    {
      d: 9,
      text: 'Order these online today: a 0.01 g scale, balloons, motors, props, a small battery, leads and fine wire.',
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
      text: 'One trip to Jaycar: a temperature-controlled iron, solder, flux, a multimeter, hand tools and a practice kit.',
      cam: { p: [0.03, 0.74, 0.62], t: [0.04, 0, -0.06], fov: 32 },
      act(S, u) {
        lay(S, ONLINE, 1);
        S.a('mat').show(smooth(u * 3));
        lay(S, JAYCAR, u * 1.12, 0.045);
      },
      labels: (S, u) =>
        u > 0.75
          ? [
              { id: 'st', text: 'soldering station', at: S.node('station'), side: 't' },
              { id: 'mm', text: 'multimeter', at: S.node('multimeter'), side: 'l' },
              { id: 'kit', text: 'practice kit', at: S.node('practice_board'), side: 'r' },
              { id: 'th', text: 'third hand', at: S.node('third_hand'), side: 't' },
            ]
          : [],
    },
    {
      d: 9,
      text: 'Then a helium tank from Spotlight and a spool of matte white PLA. Coins, a cup and thread come from home.',
      cam: { p: [0.56, 0.86, 0.98], t: [0.42, 0.12, -0.03], fov: 32 },
      act(S, u) {
        lay(S, ONLINE, 1);
        S.a('mat').show();
        lay(S, JAYCAR, 1);
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
      text: 'About $530 in all, and the tools last the whole build. Open Kit for every link and price.',
      cam: { p: [0.02, 1.3, 1.18], t: [0.02, 0.06, -0.06], fov: 34 },
      act(S) {
        lay(S, ONLINE, 1);
        S.a('mat').show();
        lay(S, JAYCAR, 1);
        lay(S, OTHER, 1);
      },
      check: true,
    },
  ],
};

// ---------------------------------------------------------------- chapter 3
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
      text: 'Print all six on one plate. It takes about four hours and 40 g of filament, most of it support.',
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
      text: 'Weigh each part and write it down. The shell is about 6 g and all six together about 16 g.',
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
        S.a('scale').obj.userData.setReading('16.20');
      },
      check: true,
    },
  ],
};

// ---------------------------------------------------------------- chapter 4
function ironAt(S, p, yaw = -0.5, tilt = 0.72) {
  S.a('iron').show().at(p[0], p[1], p[2]).turn(yaw, 0, tilt);
}
const IRON_REST = [STAND[0] + 0.004, 0.034, STAND[1]];
const SPONGE = [STAND[0] - 0.025, 0.024, STAND[1]];

const solder = {
  id: 'solder',
  title: 'Learn to solder',
  goal: 'Practise until every joint looks like the good one.',
  work: '1 to 2 evenings',
  bench: true,
  setup(S) {
    S.a('station').show().at(STATION[0], 0, STATION[1]).turn(0.25);
    S.a('stand').show().at(STAND[0], 0, STAND[1]);
    S.a('practice_board').show().at(BOARD.x, BOARD.y, BOARD.z);
    S.a('resistor').show().at(BOARD.x + 1.27 * MM, 0.00645, BOARD.z - 1.27 * MM).turn(0, Math.PI, 0);
    S.a('solder_tube').show().at(0.1, MAT_Y + 0.0075, -0.07).turn(0.4);
    S.a('flux_pen').show().at(0.11, MAT_Y + 0.007, -0.045).turn(0.4);
    S.a('braid').show().at(0.15, MAT_Y, 0.095);
    ironAt(S, IRON_REST, 0, 0.47);
  },
  beats: [
    {
      d: 8,
      text: 'Set the iron to 330 °C. Wet the sponge, open a window and put your glasses on.',
      cam: { p: [0.05, 0.36, 0.5], t: [-0.03, 0.03, -0.07], fov: 32 },
      labels: (S) => [
        { id: 'knob', text: '330 °C', at: S.node('station', null, [-0.018, 0.052, 0.062]), side: 't', strong: true },
        { id: 'sp', text: 'wet sponge', at: S.node('stand', null, [-0.025, 0.024, 0]), side: 't' },
      ],
    },
    {
      d: 9,
      text: 'Tin the tip: melt a little solder onto it, then wipe it on the sponge. A shiny tip passes heat well.',
      cam: { p: [0.1, 0.115, 0.02], t: [0.03, 0.08, -0.09], fov: 30 },
      act(S, u) {
        const up = easeInOut(span(u, 0.0, 0.25));
        const wipe = easeInOut(span(u, 0.62, 0.8));
        const back = easeInOut(span(u, 0.85, 1));
        const air = [0.03, 0.08, -0.09];
        let p = mix3(IRON_REST, air, up);
        p = mix3(p, [SPONGE[0] + 0.006, SPONGE[1] + 0.002, SPONGE[2]], wipe);
        p = mix3(p, air, back);
        ironAt(S, p, lerp(0, -0.5, up), lerp(0.47, 0.7, up));
        if (wipe > 0 && wipe < 1) S.a('iron').obj.position.z += 0.012 * Math.sin(span(u, 0.62, 0.8) * TAU * 1.5);
        const feed = span(u, 0.28, 0.55);
        if (feed > 0 && feed < 1) {
          const tip = mix3([air[0] - 0.03, air[1] + 0.004, air[2]], [air[0] - 0.0012, air[1] + 0.0006, air[2]], easeOut(feed * 1.6));
          S.a('solder').show().at(tip[0], tip[1], tip[2]).turn(Math.PI, 0, 0.35);
          S.a('bead').show().at(air[0] + 0.0004, air[1] + 0.0002, air[2]).size(0.4 + 0.8 * span(feed, 0.4, 1));
        }
      },
    },
    {
      d: 8,
      text: 'Touch the iron to the pad and the lead together, and count one second while they heat.',
      cam: { p: [0.045, 0.06, 0.07], t: [J1[0], J1[1] + 0.001, J1[2]], fov: 28 },
      act(S, u) {
        const w = easeInOut(span(u, 0.05, 0.4));
        ironAt(S, mix3([0.04, 0.07, -0.03], [J1[0] + 0.0009, J1[1] + 0.0008, J1[2]], w), -0.5, 0.72);
      },
      labels: (S, u) => (u > 0.45 ? [{ id: 'pl', text: 'pad and lead', at: v3(J1[0], J1[1], J1[2]), side: 'l' }] : []),
    },
    {
      d: 8,
      text: 'Feed solder into the joint, not onto the iron. Take the solder away first, then the iron.',
      cam: { p: [0.04, 0.05, 0.065], t: [J1[0], J1[1] + 0.001, J1[2]], fov: 28 },
      act(S, u) {
        const away = easeInOut(span(u, 0.7, 0.92));
        ironAt(S, mix3([J1[0] + 0.0009, J1[1] + 0.0008, J1[2]], [0.04, 0.07, -0.03], away), -0.5, 0.72);
        const feed = easeInOut(span(u, 0.08, 0.35));
        const out = easeInOut(span(u, 0.5, 0.68));
        const tip = mix3(mix3([J1[0] - 0.02, J1[1] + 0.01, J1[2]], [J1[0] - 0.0012, J1[1] + 0.0009, J1[2]], feed), [J1[0] - 0.02, J1[1] + 0.012, J1[2]], out);
        if (out < 1) S.a('solder').show().at(tip[0], tip[1], tip[2]).turn(Math.PI, 0, 0.45);
        const g = smooth(span(u, 0.25, 0.55));
        S.a('jointA').show(g > 0 ? 1 : 0).at(J1[0], PAD_TOP - 0.0001, J1[2]).size([0.3 + 0.7 * g, Math.max(0.01, g), 0.3 + 0.7 * g]);
      },
    },
    {
      d: 9,
      text: 'Compare yours with these. Reheat a dull joint with a dab of flux. Soak up extra solder with braid.',
      cam: { p: [0.0, 0.07, 0.065], t: [0.0, PAD_TOP, BOARD.z + 0.008], fov: 30 },
      act(S) {
        S.a('jointA').show().at(J1[0], PAD_TOP - 0.0001, J1[2]);
        const row = BOARD.z + 1.27 * MM + 2.54 * 3 * MM;
        S.a('jGood').show().at(BOARD.x - 8.89 * MM, PAD_TOP, row);
        S.a('jCold').show().at(BOARD.x - 3.81 * MM, PAD_TOP, row);
        S.a('jBlob').show().at(BOARD.x + 1.27 * MM, PAD_TOP, row);
        S.a('jBridge').show().at(BOARD.x + 7.62 * MM, PAD_TOP, row);
      },
      labels: (S) => {
        const row = BOARD.z + 1.27 * MM + 2.54 * 3 * MM;
        return [
          { id: 'g', text: 'good: shiny cone', at: v3(BOARD.x - 8.89 * MM, PAD_TOP + 0.002, row), side: 't', strong: true },
          { id: 'c', text: 'cold: dull lump', at: v3(BOARD.x - 3.81 * MM, PAD_TOP + 0.002, row), side: 'b' },
          { id: 'b', text: 'too much', at: v3(BOARD.x + 1.27 * MM, PAD_TOP + 0.003, row), side: 't' },
          { id: 'br', text: 'bridge', at: v3(BOARD.x + 7.62 * MM, PAD_TOP + 0.002, row), side: 'b' },
        ];
      },
    },
    {
      d: 11,
      text: 'Splice two wires: heatshrink on first, twist the bare ends, solder them, then slide it over and shrink it.',
      cam: { p: [0.0, 0.07, 0.15], t: [0.0, 0.02, 0.08], fov: 28 },
      act(S, u) {
        const y = 0.02;
        const z = 0.08;
        const meet = easeInOut(span(u, 0.0, 0.2));
        S.a('wireL').show().at(lerp(-0.055, -0.047, meet), y, z);
        S.a('wireR').show().at(lerp(0.055, 0.047, meet), y, z).turn(Math.PI);
        const slide = easeInOut(span(u, 0.72, 0.88));
        const shrink = smooth(span(u, 0.88, 1));
        S.a('shrinkS').show().at(lerp(-0.025, 0.0, slide), y, z).size([1, 1, 1].map((s, i) => (i === 1 ? 1 : 1 - 0.38 * shrink)));
        S.a('shrinkS').obj.rotation.set(0, 0, Math.PI / 2);
        const sol = smooth(span(u, 0.35, 0.6));
        if (sol > 0) S.a('spliceJoint').show().at(0, y, z).size([1, sol, sol]);
        const iron = span(u, 0.3, 0.68);
        if (iron > 0 && iron < 1) ironAt(S, [0.0015, y + 0.0012, z], -0.5, 0.72);
        const feed = span(u, 0.38, 0.6);
        if (feed > 0 && feed < 1) S.a('solder').show().at(-0.0015, y + 0.0012, z + 0.001).turn(Math.PI + 0.4, 0, 0.5);
      },
    },
    {
      d: 9,
      text: "Pearl's joints are this small: 28 AWG wire on a 1 mm pad. Practise four of them on a spare driver board.",
      cam: { p: [0.03, 0.045, 0.05], t: [-0.1, 0.004, 0.03], fov: 26 },
      act(S, u) {
        const d = S.a('driver1').show().at(-0.1, MAT_Y, 0.03).turn(Math.PI / 2);
        const pad = S.node('driver1', 'A driver VIN').getWorldPosition(new Vector3());
        d.obj.updateMatrixWorld(true);
        const lay = easeInOut(span(u, 0.05, 0.3));
        S.a('wireP').show().at(pad.x + 0.029 + 0.03 * (1 - lay), pad.y + 0.0004, pad.z).turn(Math.PI);
        const heat = span(u, 0.35, 0.75);
        if (heat > 0 && heat < 1) ironAt(S, [pad.x - 0.0006, pad.y + 0.0007, pad.z], 2.4, 0.8);
        const g = smooth(span(u, 0.45, 0.7));
        S.a('jointP').show(g > 0 ? 1 : 0).at(pad.x, pad.y - 0.0002, pad.z).size([0.5 + 0.5 * g, Math.max(0.01, g * 0.7), 0.5 + 0.5 * g]);
      },
    },
    {
      d: 9,
      text: 'Ten joints that match the good one, two splices and four wires on a driver board. Good place to stop.',
      cam: { p: [0.1, 0.25, 0.36], t: [0.0, 0.01, 0.0], fov: 32 },
      act(S) {
        S.a('jointA').show().at(J1[0], PAD_TOP - 0.0001, J1[2]);
        S.a('jointA2').show().at(J2[0], PAD_TOP - 0.0001, J2[2]);
        S.a('driver1').show().at(-0.1, MAT_Y, 0.03).turn(Math.PI / 2);
      },
      check: true,
    },
  ],
};

// ---------------------------------------------------------------- chapter 5
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

// ---------------------------------------------------------------- chapter 6
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

export const CHAPTERS = [meet, buy, print, solder, float, spinFan];

/** Absolute times for chapters and beats. */
export function buildTimeline(chapters = CHAPTERS) {
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
