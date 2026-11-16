// Dimensions and wire layouts for the crimping chapters, kept free of three.js so tests can read them.
//
// Cable frame: the cable runs along y with its cut end at y = 0, the plug's gold contacts up (+z) and
// its clip down. Looking along the cable towards the cut end, pin 1 is on the left (-x): the T568B
// order then reads left to right, as on the plug's own contact side with the clip away from you.
// Bench frame: millimetres from the front left of the work mat's centre line, x right, y rear, z up
// from the floor the mat lies on.

export const ORANGE = 0xf07d1c;
export const GREEN = 0x2ea84f;
export const BLUE = 0x2f6fe0;
export const BROWN = 0x7b4a2b;
export const WIRE_COLOURS = { white: 0xf1f0ea, orange: ORANGE, green: GREEN, blue: BLUE, brown: BROWN };

/** T568B, pin 1 to pin 8. A white wire carries its pair's colour as bands. */
export const T568B = [
  { pin: 1, name: 'white-orange', colour: ORANGE, white: true, pair: 'orange' },
  { pin: 2, name: 'orange', colour: ORANGE, white: false, pair: 'orange' },
  { pin: 3, name: 'white-green', colour: GREEN, white: true, pair: 'green' },
  { pin: 4, name: 'blue', colour: BLUE, white: false, pair: 'blue' },
  { pin: 5, name: 'white-blue', colour: BLUE, white: true, pair: 'blue' },
  { pin: 6, name: 'green', colour: GREEN, white: false, pair: 'green' },
  { pin: 7, name: 'white-brown', colour: BROWN, white: true, pair: 'brown' },
  { pin: 8, name: 'brown', colour: BROWN, white: false, pair: 'brown' },
];

export const CABLE_R = 2.75; // Cat5e patch cable, 5.5 mm across
export const WIRE_R = 0.48; // each insulated wire, about 1 mm across
export const PIN_PITCH = 1.02; // the plug's eight channels
export const STRIP = 30; // jacket stripped off the end
export const TRIM = 13; // wire left out of the jacket after the trim
export const JACKET_END = -STRIP;
export const TRIM_TIP = JACKET_END + TRIM;

/**
 * Clear 8P8C plug in its own frame: front face at the origin, body back along -y. `front` is where
 * that face sits on the cable once the wires touch its end wall; the jacket reaches 7 mm inside.
 */
export const PLUG = {
  size: [11.7, 21, 6.6],
  centreZ: 0.4,
  pinTop: 3.7,
  pinLift: 0.9, // how far the contacts stand above the body before the crimp
  front: TRIM_TIP + 1,
  jacketEnd: JACKET_END,
};
PLUG.rear = PLUG.front - PLUG.size[1];
export const BOOT = { length: 28, overlap: 6, colour: 0x2f6fe0 };
/** Where the boot's nose ends up on the cable: over the back of the plug. */
export const BOOT_ON = PLUG.rear + BOOT.overlap;
/** Where it waits while the end is made: well back along the cable. */
export const BOOT_PARKED = -95;

// ---------------------------------------------------------------- wires in each state

const PAIRS = {
  orange: { c: [-1.25, 0], pitch: 10, phase: 0.3 },
  brown: { c: [1.25, 0], pitch: 14, phase: 1.9 },
  green: { c: [0, 1.25], pitch: 12, phase: 2.8 },
  blue: { c: [0, -1.25], pitch: 9, phase: 4.1 },
};
// Each wire leaves the jacket beside its pair partner, on the side of its place in the row.
const START_SIDE = [-1, 1, -1, -1, 1, 1, -1, 1];
// Wire ends as the stripper left them: not quite level, which is why the row is trimmed.
const RAGGED = [0.6, -0.4, 0.9, 0.2, -0.7, 0.5, -0.2, 0.8];

const startOf = (i) => {
  const w = T568B[i];
  const [cx, cz] = PAIRS[w.pair].c;
  return [cx + START_SIDE[i] * 0.5, JACKET_END - 0.5, cz];
};

const rowX = (i, pitch) => (i - 3.5) * pitch;

function twisted(i) {
  const w = T568B[i];
  const pair = PAIRS[w.pair];
  const partner = T568B.findIndex((o, k) => k !== i && o.pair === w.pair);
  const phase = pair.phase + (i < partner ? 0 : Math.PI);
  const pts = [];
  for (let y = JACKET_END - 0.5; y <= 0.001; y += 0.6) {
    const u = (y - JACKET_END) / STRIP;
    const splay = 1 + 0.9 * Math.max(0, u) ** 1.5;
    const a = phase + (2 * Math.PI * (y - JACKET_END)) / pair.pitch;
    pts.push([pair.c[0] * splay + 0.5 * Math.cos(a), y, pair.c[1] * splay + 0.5 * Math.sin(a)]);
  }
  return pts;
}

function untwisted(i, pitch, meet, tip, wave = 0) {
  const s = startOf(i);
  const x = rowX(i, pitch);
  const pts = [s, [s[0] * 1.05, s[1] + 1.2, s[2] * 0.9], [x * 0.65 + s[0] * 0.35, (s[1] + meet) / 2 + 0.6, s[2] * 0.3], [x, meet, 0]];
  for (let y = meet + 2.5; y < tip - 0.8; y += 2.5) pts.push([x + wave * Math.sin(y * 0.9 + i * 1.7), y, 0]);
  pts.push([x, tip, 0]);
  return pts;
}

/**
 * The eight wires of a state, in the cable frame: `pairs` straight after stripping, `fan` untwisted and
 * spread out in order, `flat` pinched into a tight flat row, `trimmed` cut level 13 mm out of the
 * jacket, `offcut` the bits the trim takes off.
 */
export function wirePaths(state) {
  return T568B.map((wire, i) => {
    const tip = -0.5 + RAGGED[i];
    if (state === 'pairs') return { wire, points: twisted(i), caps: true };
    if (state === 'fan') return { wire, points: untwisted(i, 1.45, JACKET_END + 6, tip, 0.22), caps: true };
    if (state === 'flat') return { wire, points: untwisted(i, PIN_PITCH, JACKET_END + 2.6, tip), caps: true };
    if (state === 'trimmed') return { wire, points: untwisted(i, PIN_PITCH, JACKET_END + 2.6, TRIM_TIP), caps: true };
    if (state === 'offcut') {
      const x = rowX(i, PIN_PITCH);
      return { wire, points: [[x, tip, 0], [x, (tip + TRIM_TIP) / 2, 0], [x, TRIM_TIP, 0]], caps: true };
    }
    throw new Error(`unknown wire state ${state}`);
  });
}

// ---------------------------------------------------------------- 468 tester on the bench

export const MAT = { size: [520, 340, 2] };
const TOP = MAT.size[2];
/** Lamp positions along x, 1 to 8 then G, the same on both units so lamp k sits above lamp k. */
export const LED_X = Array.from({ length: 9 }, (_, k) => 84 + k * 9);
export const MAIN = {
  centre: [120, 125, TOP + 13], size: [110, 62, 26], label: [96, 46], labelAt: [-4, 0], x0: 68, ledRow: 33, ledY: 115,
  heading: 'RJ45 + RJ11',
  port: 175,
  switch: { y: 140, x: { OFF: 159, ON: 163.5, S: 168 } },
};
MAIN.extra = (g) => {
  g.font = '700 3.2px sans-serif';
  g.textAlign = 'left';
  g.fillText('CABLE TESTER', 6, 8);
  g.font = '600 2.4px sans-serif';
  g.textAlign = 'center';
  for (const [k, x] of Object.entries(MAIN.switch.x)) g.fillText(k, x - MAIN.x0, 4.6);
  g.fillStyle = '#1b2a1c';
  g.fillRect(MAIN.switch.x.OFF - MAIN.x0 - 3, 148 - MAIN.switch.y - 1.6, MAIN.switch.x.S - MAIN.switch.x.OFF + 6, 3.2);
};
export const REMOTE = {
  centre: [120, 70, TOP + 13], size: [100, 32, 26], label: [90, 26], labelAt: [-5, 0], x0: 70, ledRow: 13, ledY: 70,
  heading: 'REMOTE · RJ45 + RJ11',
  port: 170,
};
export const TESTER_TOP = TOP + 26;

const PORT_Z = TOP + 14.6; // the wire plane of a plug seated in either socket
const SEATED = 12; // how far a plug's front goes into a socket
const INTO_PORT = [0, 0, Math.SQRT1_2, Math.SQRT1_2]; // plug front (+y) turned to face -x

/** The finished lead for the tester: one plug in each socket, the cable looped round to the right. */
export const LEAD = {
  ends: [
    { front: [MAIN.port - SEATED, MAIN.centre[1], PORT_Z], q: INTO_PORT },
    { front: [REMOTE.port - SEATED, REMOTE.centre[1], PORT_Z], q: INTO_PORT },
  ],
};
{
  const tail = (e) => e.front[0] + PLUG.size[1] - BOOT.overlap + BOOT.length - 2;
  const [a, b] = LEAD.ends;
  LEAD.points = [
    [tail(a), a.front[1], PORT_Z], [tail(a) + 12, a.front[1], PORT_Z - 1], [236, 118, 9],
    [249, 97.5, TOP + CABLE_R], [236, 77, 9], [tail(b) + 12, b.front[1], PORT_Z - 1], [tail(b), b.front[1], PORT_Z],
  ];
}

// ---------------------------------------------------------------- what the lamps do

/**
 * The 468 steps through lines 1-8 and G. Each step lights one main lamp and the remote lamps wired to
 * that line. `remote` lists remote lamps (0-based) per step, `dim` marks a short, which lights them
 * faintly. Unshielded cable has no G line, so the remote's G stays dark. From the kit leaflet.
 */
const step = (main, remote, dim = false) => ({ main, remote, dim });
const GOOD = [...Array.from({ length: 8 }, (_, k) => step(k, [k])), step(8, [])];
export const LAMP_PATTERNS = {
  good: GOOD,
  open3: GOOD.map((s) => (s.main === 2 ? step(null, []) : s)),
  swap24: GOOD.map((s) => (s.main === 1 ? step(1, [3]) : s.main === 3 ? step(3, [1]) : s)),
  short45: GOOD.map((s) => (s.main === 3 || s.main === 4 ? step(s.main, [3, 4], true) : s)),
};
