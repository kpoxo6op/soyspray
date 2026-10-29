// v3 cords in rack millimetres, each drawn at its real length. A stock cord keeps all of it: the
// spare is wound into a strapped loop, and the loop's size is solved so that the drawn centreline
// matches the cord less its plug bodies. Crimped Ethernet leads are cut to their route.
//
// A cord is laid in parts, each shown with the chapter that lays it: a Lenovo cord is looped in
// the base before the deck goes on and plugged into its node once the nodes are in. `ends` name
// the ports a cord joins (`device.port`, or null for a loose end). TIES are the straps.

import { PORTS, CONNECTORS, seatedPose, exitPoint } from '../ports.js';
import { add3, sub3, scale3, normalize3, qrotate } from '../math.js';
import { spline, hermite, polyLength } from '../cablepath.js';
import { DEVICE_BY_ID, PORTS_V3, BRICK_X, BOARD, MAST, FLOOR_Z, TUB } from './rack.js';

const ID_Q = [0, 0, 0, 1];
const X = [1, 0, 0];
const NX = [-1, 0, 0];
const Y = [0, 1, 0];
const NY = [0, -1, 0];
const Z = [0, 0, 1];
const NZ = [0, 0, -1];

// Nominal lengths (mm, end to end; the Lenovo DC cord from its strain relief) and outside
// diameters of the stock cords.
export const STOCK = {
  dc: { length: 1800, od: 4.5 },
  mains: { length: 1000, od: 7 },
  adapter: { length: 1500, od: 3.5 },
  usb: { length: 460, od: 4.5 },
  extension: { length: 1500, od: 4 },
};
// The extension runs on inside the mast: along the foot channel and up the back slot to its socket.
export const MAST_RUN = 32 + 90;

export function portFrameV3(deviceId, portId) {
  const d = DEVICE_BY_ID[deviceId];
  if (!d) throw new Error(`unknown device ${deviceId}`);
  const port = (PORTS_V3[d.model] || PORTS[d.model])?.[portId];
  if (!port) throw new Error(`unknown port ${deviceId}.${portId}`);
  const q = d.q || ID_Q;
  return { type: port.type, pos: add3(d.centre, qrotate(q, port.pos)), n: qrotate(q, port.n), u: qrotate(q, port.u) };
}

/** A plug seated in a port: its pose, the cable exit and the direction the cable leaves in. */
function plugAt(deviceId, portId) {
  const f = portFrameV3(deviceId, portId);
  const pose = seatedPose(f.type, f);
  return { type: f.type, pose, exit: exitPoint(f.type, pose), dir: f.n, at: `${deviceId}.${portId}` };
}

/** A cord that leaves a device without a plug (moulded strain relief). */
function fixedEnd(deviceId, portId) {
  const f = portFrameV3(deviceId, portId);
  return { type: null, exit: f.pos, dir: f.n, at: `${deviceId}.${portId}` };
}

/** Drawn length of a stock cord: its nominal length less the plug bodies at its ends. */
const drawn = (kind, ...ends) => STOCK[kind].length - ends.reduce((s, e) => s + (e.type ? CONNECTORS[e.type].len : 0), 0);

/** Point runs joined end to start, each repeated join point dropped. */
function chain(...runs) {
  const out = [];
  for (const run of runs) {
    for (const p of run) {
      const last = out.at(-1);
      if (!last || Math.hypot(p[0] - last[0], p[1] - last[1], p[2] - last[2]) > 1e-6) out.push(p);
    }
  }
  return out;
}

const lay = (points, startDir, endDir, lead = 12) => spline(points, { startDir, endDir, lead });
const bend = (a, da, b, db) => hermite(a, da, b, db, 2);

/**
 * A cord wound round a stadium: straights of length `a` between semicircles of radius `r`, in the
 * plane of unit axes u (along the straights) and v. Arclength 0 is the start of the +v straight,
 * which runs along +u; the cord then rounds the +u end towards -v. The winding steps `pitch`
 * along w per turn, from `centre` at arclength s0.
 */
function stadium({ centre, u, v, w, a, r, pitch }, s0) {
  const P = 2 * a + 2 * Math.PI * r;
  const at = (s) => {
    const k = ((s % P) + P) % P;
    let x;
    let y;
    if (k < a) [x, y] = [k - a / 2, r];
    else if (k < a + Math.PI * r) [x, y] = [a / 2 + r * Math.sin((k - a) / r), r * Math.cos((k - a) / r)];
    else if (k < 2 * a + Math.PI * r) [x, y] = [a / 2 - (k - a - Math.PI * r), -r];
    else [x, y] = [-a / 2 - r * Math.sin((k - 2 * a - Math.PI * r) / r), -r * Math.cos((k - 2 * a - Math.PI * r) / r)];
    const h = (pitch * (s - s0)) / P;
    return [0, 1, 2].map((i) => centre[i] + u[i] * x + v[i] * y + w[i] * h);
  };
  const tangent = (s) => normalize3(sub3(at(s + 0.5), at(s - 0.5)));
  const points = (s1, step = 2.5) => {
    const n = Math.max(2, Math.ceil((s1 - s0) / step));
    return Array.from({ length: n + 1 }, (_, i) => at(s0 + ((s1 - s0) * i) / n));
  };
  return { P, w, s0, at, tangent, points };
}

/**
 * The smallest whole number of turns, then the loop size between 0 and 1, at which `build`
 * draws `length`. `build(turns, size)` returns { parts } and is longer for more of either.
 */
function solve(id, length, build, maxTurns = 12) {
  const total = (b) => b.parts.reduce((s, p) => s + polyLength(p), 0);
  for (let n = 0; n <= maxTurns; n++) {
    if (total(build(n, 1)) < length) continue;
    if (total(build(n, 0)) > length) throw new Error(`${id}: ${length} mm does not wind into whole turns`);
    let lo = 0;
    let hi = 1;
    for (let i = 0; i < 48; i++) {
      const mid = (lo + hi) / 2;
      if (total(build(n, mid)) < length) lo = mid;
      else hi = mid;
    }
    return { ...build(n, (lo + hi) / 2), turns: n };
  }
  throw new Error(`${id}: ${length} mm is more than its loop holds`);
}

/** A strap round every turn of a loop where it passes arclength s. */
function strap(loop, s1, s, od, chapter) {
  const first = loop.s0 + ((((s - loop.s0) % loop.P) + loop.P) % loop.P);
  const at = [];
  for (let k = first; k <= s1 + 1e-6; k += loop.P) at.push(loop.at(k));
  const lo = at[0];
  const hi = at.at(-1);
  const spread = sub3(hi, lo);
  const along = loop.tangent(first);
  return { chapter, centre: scale3(add3(lo, hi), 0.5), along, spread: loop.w, size: [Math.hypot(...spread) + od + 1, od + 1] };
}

const CABLES = [];
const TIES = [];
const DECK_UNDER = TUB.z[1];
const BRICK_TOP = TUB.z[0] + 46;
const BOARD_TOP = BOARD.centre[2] + 25;

// ---------------------------------------------------------------- base: mains cords
// Each brick's own mains cord leaves its inlet at the rear, loops forward over the brick on edge and
// comes back down to the outlet behind it. Two straps hold each loop.
const MAINS = STOCK.mains.od;
const MAINS_LOOP = { zBot: BRICK_TOP + MAINS / 2 + 1.5, zTop: DECK_UNDER - MAINS / 2 - 1.5, rear: 181, front: 16, pitch: MAINS + 0.4 };

BRICK_X.forEach((x, i) => {
  const inlet = plugAt(`brick${i}`, 'c5');
  const outlet = plugAt('board', `o${i + 1}`);
  const { zBot, zTop, rear, front, pitch } = MAINS_LOOP;
  const r = (zTop - zBot) / 2;
  const aMax = rear - front - 2 * r;
  let loop;
  let s1;
  const cord = solve(`mains${i}`, drawn('mains', inlet, outlet), (n, size) => {
    const a = aMax * size;
    const P = 2 * a + 2 * Math.PI * r;
    const s0 = 2 * a + 1.5 * Math.PI * r; // rear end, going up
    s1 = s0 + (n + 1) * P - 0.5 * Math.PI * r; // rear end of the lower straight, heading back
    const adv = (pitch * (s1 - s0)) / P;
    loop = stadium({ centre: [x - adv / 2, rear - r - a / 2, (zTop + zBot) / 2], u: NY, v: Z, w: X, a, r, pitch }, s0);
    return {
      parts: [chain(bend(inlet.exit, Y, loop.at(s0), loop.tangent(s0)), loop.points(s1), bend(loop.at(s1), loop.tangent(s1), outlet.exit, Y))],
      a,
    };
  });
  CABLES.push({
    id: `mains${i}`, colour: 0x1b1c1f, od: MAINS, length: drawn('mains', inlet, outlet), turns: cord.turns,
    parts: [{ chapter: 'mains-cords', points: cord.parts[0], plugs: [inlet, outlet] }], ends: [inlet.at, outlet.at],
  });
  const top = cord.a / 2; // middle of the upper straight
  TIES.push(strap(loop, s1, top, MAINS, 'mains-cords'), strap(loop, s1, top + cord.a + Math.PI * r, MAINS, 'mains-cords'));
});

// ---------------------------------------------------------------- base: switch adapter cord
// The switch adapter's cord lies in a flat coil on top of the board, under the board straps, and
// stands up through the right rear slot of the base deck. Once the switch is in, it rises behind
// the nodes and through the mid deck to the switch.
const ADAPTER = STOCK.adapter.od;
const ADAPTER_COIL = { r: 10, left: 30, right: 236, in: 196, out: 172, pitch: ADAPTER + 0.3 };
const RISER = [164, 193];
{
  const start = fixedEnd('psuSwitch', 'dcOut');
  const plug = plugAt('switch', 'dc');
  const { r, left, right, pitch } = ADAPTER_COIL;
  const aMin = right - r - ADAPTER_COIL.out + 2;
  const aMax = right - left - 2 * r;
  const wait = [...RISER, 10];
  let loop;
  let s1;
  const cord = solve('switchPower', drawn('adapter', plug), (n, size) => {
    const a = aMin + (aMax - aMin) * size;
    const xc = right - r - a / 2;
    const P = 2 * a + 2 * Math.PI * r;
    const along = (x) => a + Math.PI * r + a / 2 - (x - xc); // front straight, running -x
    const s0 = along(ADAPTER_COIL.in);
    s1 = along(ADAPTER_COIL.out) + n * P;
    loop = stadium({ centre: [xc, BOARD.centre[1], BOARD_TOP + ADAPTER / 2], u: X, v: Y, w: Z, a, r, pitch }, s0);
    const leadIn = lay([start.exit, [195, 190, -31], [195, 207, -32], loop.at(s0)], Z, loop.tangent(s0), 6);
    const end = loop.at(s1);
    const leadOut = lay([end, [RISER[0], 205, end[2] + 1], [RISER[0], RISER[1], -22], wait], NX, Z, 5);
    const up = lay([wait, [...RISER, 214], [176, 176, 230], [plug.exit[0], 152, plug.exit[2]], plug.exit], Z, NY, 8);
    return { parts: [chain(leadIn, loop.points(s1), leadOut), up] };
  });
  CABLES.push({
    id: 'switchPower', colour: 0x2a2c31, od: ADAPTER, length: drawn('adapter', plug), turns: cord.turns,
    parts: [{ chapter: 'mains-cords', points: cord.parts[0], plugs: [] }, { chapter: 'power-leads', points: cord.parts[1], plugs: [plug] }],
    ends: [start.at, plug.at],
  });
  // Two straps hold the board down on its rails; the right-hand one closes over the coil.
  for (const x of [75, 228]) {
    let top = BOARD_TOP;
    for (let k = loop.s0; k <= s1; k += 1) if (Math.abs(loop.at(k)[0] - x) < 6) top = Math.max(top, loop.at(k)[2] + ADAPTER / 2);
    const y = [BOARD.centre[1] + 12.5, BOARD.centre[1] - 12.5];
    const z = [TUB.z[0] - 2.4, top];
    TIES.push({ chapter: 'mains-cords', centre: [x, (y[0] + y[1]) / 2, (z[0] + z[1]) / 2], along: X, spread: Y, size: [y[0] - y[1], z[1] - z[0]], round: 3 });
  }
}

// ---------------------------------------------------------------- base: Lenovo DC cords
// Each DC cord turns up at the front of its brick, runs along the front into the right half of the
// base and loops there on edge, strapped front and back. It leaves the top of its loop towards the rear and
// stands up behind the board until its node is in: node-0's in front, node-2's at the back.
const DC = STOCK.dc.od;
const DC_LOOP = { zBot: TUB.z[0] + DC / 2 + 1, zTop: DECK_UNDER - DC / 2 - 1, rear: 164, front: 28, x0: 147, gap: 3.5, pitch: DC + 0.3 };
const DC_RUN = { y: 7, z: [-14, -22, -30] };
const LADDER = { x: 192, y: [220, 226, 232], z: [-12, -18, -24], top: 10 };
{
  const { zBot, zTop, rear, front, pitch } = DC_LOOP;
  const r = (zTop - zBot) / 2;
  const aMax = rear - front - 2 * r;
  let xs = DC_LOOP.x0 + DC / 2;
  BRICK_X.forEach((x, i) => {
    const out = fixedEnd(`brick${i}`, 'dcOut');
    const plug = plugAt(`node${i}`, 'power');
    const wait = [LADDER.x, LADDER.y[i], LADDER.top];
    const turn = [LADDER.x, LADDER.y[i], plug.exit[2] - (LADDER.y[i] - plug.exit[1])];
    const toNode = chain([wait, turn], bend(turn, Z, plug.exit, NY));
    let loop;
    let s1;
    let adv;
    const cord = solve(`dc${i}`, drawn('dc', plug), (n, size) => {
      const a = aMax * size;
      const P = 2 * a + 2 * Math.PI * r;
      s1 = n * P + a; // ends where it started its first turn, at the top, one straight further back
      adv = (pitch * s1) / P;
      loop = stadium({ centre: [xs, rear - r - a / 2, (zTop + zBot) / 2], u: Y, v: Z, w: X, a, r, pitch }, 0);
      const up = [x, DC_RUN.y, out.exit[2] + 7];
      const z = DC_RUN.z[i];
      const leadIn = chain(bend(out.exit, NY, up, Z),
        lay([up, [x, DC_RUN.y, z], [xs, DC_RUN.y, z], [xs, DC_RUN.y + 16, z], loop.at(0)], Z, Y, 8));
      const end = loop.at(s1);
      const leadOut = lay([end, [end[0], 172, end[2]], [(end[0] + LADDER.x) / 2, 200, LADDER.z[i]], [LADDER.x, LADDER.y[i], LADDER.z[i]], wait], Y, Z, 8);
      return { parts: [chain(leadIn, loop.points(s1), leadOut), toNode], a };
    });
    CABLES.push({
      id: `dc${i}`, colour: 0x24252a, od: DC, length: drawn('dc', plug), turns: cord.turns,
      parts: [{ chapter: 'dc-cords', points: cord.parts[0], plugs: [] }, { chapter: 'power-leads', points: cord.parts[1], plugs: [plug] }],
      ends: [out.at, plug.at],
    });
    TIES.push(strap(loop, s1, cord.a + 0.5 * Math.PI * r, DC, 'dc-cords'), strap(loop, s1, 2 * cord.a + 1.5 * Math.PI * r, DC, 'dc-cords'));
    xs += adv + DC + DC_LOOP.gap;
  });
}

// ---------------------------------------------------------------- the board's own lead
{
  const from = add3(BOARD.centre, [131, 0, 0]);
  CABLES.push({
    id: 'boardCord', colour: 0xf1f0ec, od: 7, length: null, turns: 0,
    parts: [{ chapter: 'mains-cords', points: lay([from, [262, 228, -74], [268, 248, -96], [270, 264, FLOOR_Z + 3.5], [272, 345, FLOOR_Z + 3.5]], X, Y), plugs: [] }],
    ends: [null, null],
  });
}

// ---------------------------------------------------------------- Ethernet
// Crimped to length: the nodes rise at the rear left, beside the plugs above them and through the
// mid deck, to switch ports 7, 6 and 5. Port 1 goes to keystone 1 (out to the router on the wall),
// port 4 to keystone 2.
const ETH = 6;
const ethernet = (id, colour, a, via, b, chapter = 'ethernet', lead = 6) => CABLES.push({
  id, colour, od: ETH, length: null, turns: 0,
  parts: [{ chapter, points: lay([a.exit, ...via, b.exit], a.dir, scale3(b.dir, -1), lead), plugs: [a, b].filter((p) => p.type) }],
  ends: [a.at, b.at],
});
['p7', 'p6', 'p5'].forEach((port, i) => {
  const a = plugAt(`node${i}`, 'rj45');
  const b = plugAt('switch', port);
  const x = [36, 45, 59.5][i];
  const z = a.exit[2];
  ethernet(`eth${i}`, 0x3f7fe0, a, [[a.exit[0], 220, z + 10], [x, 194, z + 30], [x, 194, 200], [x, 190, 216], [75 + 20 * i, 166, 236], [b.exit[0], 150, b.exit[2]]], b);
});
ethernet('uplink', 0xf0c232, plugAt('switch', 'p1'), [], plugAt('key1', 'in'));
ethernet('spareLan', 0x48b36a, plugAt('switch', 'p4'), [], plugAt('key2', 'in'));
{
  const a = plugAt('key1', 'out');
  CABLES.push({
    id: 'routerLink', colour: 0xf0c232, od: ETH, length: null, turns: 0,
    parts: [{ chapter: 'ethernet', points: lay([a.exit, [174.5, 262, 232], [176, 270, 120], [178, 278, FLOOR_Z + 30], [182, 345, FLOOR_Z + ETH / 2]], Y, Y), plugs: [a] }],
    ends: [a.at, null],
  });
}

// ---------------------------------------------------------------- USB and Zigbee
// Each drive lead runs back over node-2 and down behind the nodes into node-0, its spare in one
// loop hanging behind node-1.
const USB = STOCK.usb.od;
const USB_LOOP = { y: 228, z: 118, r: [8, 46], pitch: USB + 0.5 };
[['usbSeagate', 'usbA', 'usbG2b', 78, 0x2a2b30], ['usbTouro', 'usbB', 'usbG1a', 150, 0x34363c]].forEach(([id, drive, port, x, colour]) => {
  const a = plugAt(drive, 'usb');
  const b = plugAt('node0', port);
  const cord = solve(id, drawn('usb', a, b), (n, size) => {
    const r = USB_LOOP.r[0] + (USB_LOOP.r[1] - USB_LOOP.r[0]) * size;
    const loop = stadium({ centre: [x - r, USB_LOOP.y, USB_LOOP.z], u: NZ, v: X, w: Y, a: 0, r, pitch: USB_LOOP.pitch }, 0);
    const s1 = n * loop.P;
    const leadIn = lay([a.exit, [a.exit[0], 214, a.exit[2]], [x, USB_LOOP.y, a.exit[2] - 12], loop.at(0)], Y, NZ, 6);
    const end = loop.at(s1);
    const turn = [x, end[1], b.exit[2] + end[1] - b.exit[1]];
    return { parts: [chain(leadIn, loop.points(s1), [turn], bend(turn, NZ, b.exit, NY))] };
  }, 2);
  CABLES.push({
    id, colour, od: USB, length: drawn('usb', a, b), turns: cord.turns,
    parts: [{ chapter: 'usb-zigbee', points: cord.parts[0], plugs: [a, b] }], ends: [a.at, b.at],
  });
});

// The Zigbee extension drops behind the base to the unit top and runs along it to the mast, its
// spare in a wide curve; it carries on up inside the mast to the socket under the dongle.
{
  const EXT = STOCK.extension.od;
  const a = plugAt('node0', 'usbG1b');
  const length = drawn('extension', a, { type: 'usbAf' }) - MAST_RUN;
  const z = FLOOR_Z + EXT / 2;
  const foot = [MAST[0], MAST[1] + 42, FLOOR_Z + 10];
  const cord = solve('zigbee', length, (n, size) => {
    const bulge = 160 * size;
    return { parts: [lay([a.exit, [111, 238, 34], [111, 250, 8], [110, 252, z + 16], [96, 258, z], [-300, 262 + bulge, z],
      [-760, 236 + 0.6 * bulge, z], [-930, 172, z], [MAST[0], foot[1] + 28, z], foot], Y, NY, 6)] };
  }, 0);
  CABLES.push({
    id: 'zigbee', colour: 0xeceae4, od: EXT, length, turns: 0,
    parts: [{ chapter: 'usb-zigbee', points: cord.parts[0], plugs: [a] }], ends: [a.at, null],
  });
}

export { CABLES, TIES };
export const CABLE_BY_ID = Object.fromEntries(CABLES.map((c) => [c.id, c]));
