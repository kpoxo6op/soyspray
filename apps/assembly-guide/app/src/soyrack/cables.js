// v3 leads: where each plugs in and the path it is dressed along. Rack millimetres.
// Power rises at the rear right, data at the rear left, both through the deck rear slots.
// `chapter` is the id of the chapter that connects the lead; `ends` name the ports it joins
// (`device.port`, or null for a loose end).

import { PORTS, seatedPose, exitPoint } from '../ports.js';
import { add3, qrotate, scale3 } from '../math.js';
import { spline } from '../cablepath.js';
import { DEVICE_BY_ID, PORTS_V3, LOWER_BASE, BRICK_X, BOARD, MAST, FLOOR_Z } from './rack.js';

const ID_Q = [0, 0, 0, 1];

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

/** A lead that leaves a device without a plug (moulded strain relief), optionally bent at once. */
function fixedEnd(deviceId, portId, dir = null) {
  const f = portFrameV3(deviceId, portId);
  return { type: null, exit: f.pos, dir: dir || f.n, at: `${deviceId}.${portId}` };
}

// A loose end: `dir` points back along the lead, like a port normal.
const free = (p, dir) => ({ type: null, exit: p, dir, at: null });

function lead(id, chapter, colour, od, a, via, b) {
  const points = spline([a.exit, ...via, b.exit], { startDir: a.dir, endDir: scale3(b.dir, -1) });
  return { id, chapter, colour, od, points, ends: [a.at, b.at], plugs: [a, b].filter((p) => p.type) };
}

const nodeZ = (i) => LOWER_BASE[i] + 18.5;
const CABLES = [];

// ---------------------------------------------------------------- power
// Each brick's DC cord leaves its front end, crosses over the bricks, coils in the right half of
// the base and rises through the right rear slot to its node.
BRICK_X.forEach((x, i) => {
  const coil = [195, 52 + 42 * i, -70 + 12 * i];
  const loop = [0, 1, 2, 3, 4, 5, 6].map((k) => {
    const a = (k / 6) * Math.PI * 2;
    return [coil[0] + 26 * Math.cos(a), coil[1] + 15 * Math.sin(a), coil[2] + k * 0.8];
  });
  const jack = nodeZ(i) - 6.6;
  CABLES.push(lead(`dc${i}`, 'power-leads', 0x24252a, 4.5, fixedEnd(`brick${i}`, 'dcOut', [0, -0.45, 1]),
    [[x, 6, -44], [x, 24, -20], [x + 6, 120, -20], [150, 40 + 42 * i, -26], ...loop, [182 + 10 * i, 186, -30], [182 + 10 * i, 194, -2],
      [200 + 6 * i, 203, 20], [200 + 6 * i, 206, jack - 14], [194, 226, jack - 4]],
    plugAt(`node${i}`, 'power')));
  // Short NZ to C5 lead from the board up and over to the brick's inlet.
  CABLES.push(lead(`ac${i}`, 'bricks-board', 0x1b1c1f, 6.5, plugAt('board', `o${i + 1}`),
    [[BOARD.centre[0] + BOARD.outlets[i], 176, -40], [(x + BOARD.centre[0] + BOARD.outlets[i]) / 2, 172, -20], [x, 180, -36]],
    plugAt(`brick${i}`, 'c5')));
});
CABLES.push(lead('swPower', 'power-leads', 0x2a2c31, 4, plugAt('charger', 'c1'),
  [[204, 150, -30], [214, 175, -16], [214, 194, -2], [214, 205, 60], [214, 196, 196], [214, 182, 214], [202, 150, 236]],
  plugAt('switch', 'dc')));
CABLES.push(lead('routerPower', 'power-leads', 0xe8e8e4, 4, plugAt('charger', 'c2'),
  [[186, 150, -30], [208, 176, -16], [208, 194, -2], [208, 205, 60], [208, 196, 196], [208, 182, 214], [206, 170, 262], [186, 152, 276]],
  plugAt('router', 'power')));
CABLES.push(lead('boardCord', 'bricks-board', 0xf1f0ec, 7, free(add3(BOARD.centre, [131, 0, 0]), [1, 0, 0]),
  [[266, 226, -58], [284, 256, -78]], free([300, 330, FLOOR_Z + 4], [0, -1, 0])));

// ---------------------------------------------------------------- Ethernet
const SWITCH_FOR_NODE = ['p7', 'p6', 'p5'];
[0, 1, 2].forEach((i) => {
  const x = 50 + 5 * i;
  CABLES.push(lead(`eth${i}`, 'ethernet', 0x3f7fe0, 6, plugAt(`node${i}`, 'rj45'),
    [[x, 216, nodeZ(i) - 6], [x, 202, nodeZ(i) + 20], [x, 198, 196], [x, 190, 214], [x + 20, 168, 236]],
    plugAt('switch', SWITCH_FOR_NODE[i])));
});
CABLES.push(lead('lan', 'ethernet', 0xa7adb5, 6, plugAt('router', 'lan'), [[84, 152, 270], [80, 152, 252]], plugAt('switch', 'p8')));
CABLES.push(lead('wan', 'ethernet', 0xf0c232, 6, plugAt('router', 'wan'), [[168, 152, 272], [174, 152, 254]], plugAt('key1', 'in')));
CABLES.push(lead('spareLan', 'ethernet', 0x48b36a, 6, plugAt('switch', 'p4'), [[140, 150, 244]], plugAt('key2', 'in')));
CABLES.push(lead('uplink', 'ethernet', 0xf0c232, 6, plugAt('key1', 'out'),
  [[174.5, 262, 226], [176, 272, 60], [180, 300, FLOOR_Z + 30]], free([186, 340, FLOOR_Z + 4], [0, -1, 0])));

// ---------------------------------------------------------------- USB and Zigbee
CABLES.push(lead('usbSeagate', 'usb-zigbee', 0x2a2b30, 4.5, plugAt('usbA', 'usb'),
  [[76, 172, 172], [70, 204, 150], [70, 207, 70], [74, 222, 44]], plugAt('node0', 'usbG2b')));
CABLES.push(lead('usbTouro', 'usb-zigbee', 0x34363c, 4.5, plugAt('usbB', 'usb'),
  [[168, 168, 176], [140, 203, 150], [136, 207, 70], [146, 222, 44]], plugAt('node0', 'usbG1a')));
CABLES.push(lead('zigbee', 'usb-zigbee', 0xeceae4, 4, plugAt('node0', 'usbG1b'),
  [[111, 236, 20], [100, 262, FLOOR_Z + 6], [-200, 262, FLOOR_Z + 2.5], [-700, 240, FLOOR_Z + 2.5], [MAST[0] + 40, MAST[1] + 120, FLOOR_Z + 2.5]],
  free([MAST[0], MAST[1] + 42, FLOOR_Z + 10], [0, 1, 0])));

export { CABLES };
export const CABLE_BY_ID = Object.fromEntries(CABLES.map((c) => [c.id, c]));
