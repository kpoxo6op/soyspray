// Soyrack layout in rack millimetres: x left -> right, y front -> rear, z up, z = 0 on top
// of the base deck. cad/soyrack.scad uses the same frame, and the browser meshes in
// data/v3/meshes.bin keep their rack positions, so each part's mesh centre is its pose.
// The three ventilated node trays from the old rack (mesh in data/trays.bin) hang on the same
// hole grid: x 18.97 and 234.03, z = 25 + 10k.

import { qaxis, qfromTo, qmul, basisQuat } from '../math.js';
import { buildSlimBoard, buildKeystone, buildDongle, buildPad } from './models.js';

const ID_Q = [0, 0, 0, 1];
const TURN = [0, 0, 1, 0]; // half a turn about z

export const CX = 126.5;
export const DEPTH = 209;
export const FLOOR_Z = -106; // underside of the silicone pads under the base
// Corner screws: one through each post foot (down into the base, up through the mid deck) and one
// down through the top cap into each upper post.
export const JOINTS = { FL: [14, 32], FR: [239, 32], RL: [14, 177], RR: [239, 177] };
export const CAP_BOLTS = { FL: [12, 20], FR: [241, 20], RL: [12, 189], RR: [241, 189] };
export const HOLE_X = [18.97, 234.03];
// Tray screw holes that take a nut: node trays and drive tray on the front lower posts, the switch
// shelf on the front upper posts and the keystone panel on the rear ones.
export const NUT_HOLES = { lower: [1, 5, 6, 10, 11, 15, 16, 18], upper: [1, 3] };
export const LOWER_BASE = [23.5, 73.5, 123.5]; // node tray floors on holes 1, 6 and 11
export const SHELF_TOP = { drive: 172.9, switch: 232.9 };
export const CAP_TOP = 282;
export const BRICK_X = [40, 83, 126];
export const BRICK_Y = 82; // centre of the 112 mm bricks, y 26..138
export const TUB_FLOOR = -101.6;
// Inside of the power base: the main bay ends at the trough rib (y 203), the trough runs to 237.6.
export const TUB = { x: [6.4, 246.6], y: [2.4, 237.6], z: [TUB_FLOOR, -8] };
export const BASE_SLOT = { x: [161, 221], y: [186, 200] }; // right rear slot in the base deck
// The board lies on 6 mm rails, so the switch adapter in its right-hand outlet stands on the floor.
export const BOARD = { centre: [123, 221, TUB_FLOOR + 31], outlets: [-72, -24, 24, 72] };
export const KEYSTONE_X = [174.5, 142.5, 110.5, 78.5]; // slots 1..4, numbered from the left seen from behind
export const KEYSTONE_Z = 245;
export const PANEL_Y = 207.2; // middle of the 2.4 mm keystone panel
export const MAST = [-950, 60]; // Zigbee mast, 1 m or more from every USB 3 port

const ON_EDGE = qaxis([0, 1, 0], Math.PI / 2);
// Board outlets face forward with the earth slot at the top.
const OUTLET_UP = [0, 0, -1];

const node = (i) => ({
  id: `node${i}`, model: 'm920q', label: `node-${i}`, size: [179, 183, 37], centre: [124.5, 95, LOWER_BASE[i] + 18.5],
});

export const DEVICES = [
  ...[0, 1, 2].map(node),
  { id: 'usbA', model: 'seagate', size: [78, 114.8, 11.7], centre: [79.5, 69.4, SHELF_TOP.drive + 5.85] },
  { id: 'usbB', model: 'touro', size: [80, 112, 20.5], centre: [172.5, 68, SHELF_TOP.drive + 10.25] },
  { id: 'switch', model: 'switch', size: [158, 101, 26], centre: [CX, 60.5, SHELF_TOP.switch + 13] },
  ...BRICK_X.map((x, i) => ({ id: `brick${i}`, model: 'brick', size: [46, 112, 29], centre: [x, BRICK_Y, TUB_FLOOR + 23], q: ON_EDGE })),
  // HPM D105/1 class board on its side in the rear trough, outlets facing forward.
  { id: 'board', model: 'slimBoard', size: [230, 25, 50], centre: BOARD.centre, build: buildSlimBoard },
  // The switch's own plug-in adapter in the fourth outlet; its 1.5 m cord leaves the earth-pin end, at the top.
  { id: 'psuSwitch', model: 'psuSwitch', size: [46, 40, 62], centre: [BOARD.centre[0] + BOARD.outlets[3], BOARD.centre[1] - 12.5 - 20.5, BOARD.centre[2]],
    q: basisQuat([0, -1, 0], OUTLET_UP) },
  ...KEYSTONE_X.map((x, i) => ({
    id: `key${i + 1}`, model: i < 2 ? 'keystone' : 'keyBlank', size: i < 2 ? [16.5, 36, 19] : [15, 4, 17],
    centre: [x, i < 2 ? PANEL_Y : PANEL_Y + 3.2, KEYSTONE_Z], build: buildKeystone,
  })),
  { id: 'dongle', model: 'dongle', size: [26, 11, 52], centre: [MAST[0], MAST[1], FLOOR_Z + 140 + 26], build: buildDongle, room: true },
  // A silicone pad under each corner of the base.
  ...Object.entries({ FL: [16, 16], FR: [237, 16], RL: [16, 224], RR: [237, 224] }).map(([k, [x, y]]) => ({
    id: `pad.${k}`, model: 'pad', size: [20, 20, 2], centre: [x, y, FLOOR_Z + 1], build: buildPad,
  })),
];

export const DEVICE_BY_ID = Object.fromEntries(DEVICES.map((d) => [d.id, d]));

// Ports of the slim board and the keystones, in the same frame convention as ports.js.
const Y = [0, 1, 0];
const NY = [0, -1, 0];
const Z = [0, 0, 1];
export const PORTS_V3 = {
  slimBoard: Object.fromEntries(BOARD.outlets.map((x, i) => [`o${i + 1}`, { type: 'nz', pos: [x, -12.5, 0], n: NY, u: OUTLET_UP }])),
  keystone: { in: { type: 'rj45', pos: [0, -18, 0], n: NY, u: Z }, out: { type: 'rj45', pos: [0, 18, 0], n: Y, u: Z } },
};

// ---------------------------------------------------------------- printed parts and fasteners

const turned = (p) => [2 * CX - p[0], DEPTH - p[1], p[2]];
const NZ = [0, 0, -1];
const SLOT_TURN = qaxis(Y, Math.PI / 6);

/** Ids of the nuts behind the tray screw holes in use, `nut.<lower|upper>.<corner>.<hole>`. */
export function trayNutIds() {
  const posts = { lower: ['FL', 'FR'], upper: ['FL', 'FR', 'RL', 'RR'] };
  return Object.entries(posts).flatMap(([kind, ks]) => ks.flatMap((k) => NUT_HOLES[kind].map((n) => `nut.${kind}.${k}.${n}`)));
}

/**
 * Groups, part instances and fasteners for buildTimeline. `meshes` are the decoded rack meshes
 * and the node tray mesh.
 */
export function soyrackPlacements(meshes) {
  const mesh = (name) => {
    if (!meshes[name]) throw new Error(`missing mesh ${name}`);
    return meshes[name];
  };
  const centre = (name) => mesh(name).centre;
  const onFloor = (name, x, y) => [x, y, FLOOR_Z + mesh(name).size[2] / 2];
  const instances = [];
  const put = (id, part, p, q = ID_Q) => instances.push({ id, group: 'world', part, p, q });

  for (const name of ['base_tub', 'base_deck', 'mid_deck', 'top_cap', 'drive_tray', 'switch_shelf', 'keystone_panel']) {
    put(name, name, centre(name));
  }
  for (const kind of ['lower', 'upper']) {
    const a = centre(`post_${kind}_a`);
    const b = centre(`post_${kind}_b`);
    put(`post.${kind}.FL`, `post_${kind}_a`, a);
    put(`post.${kind}.FR`, `post_${kind}_b`, b);
    put(`post.${kind}.RR`, `post_${kind}_a`, turned(a), TURN);
    put(`post.${kind}.RL`, `post_${kind}_b`, turned(b), TURN);
  }
  put('zigbee_mast', 'zigbee_mast', onFloor('zigbee_mast', ...MAST));
  // The node trays carry over, each on holes 1 and 5 of its bay.
  mesh('trayVent');
  LOWER_BASE.forEach((_, i) => put(`tray.L${i}`, 'trayVent', [CX, 95, 45 + 50 * i]));

  const screws = [];
  const screw = (id, type, head, dir, out) => screws.push({ id, group: 'world', type, head, dir, out });
  // A nut is drawn from its underside along `dir`; `slot` turns it so its flats meet the walls of a
  // slot it pushes into sideways.
  const nut = (id, head, dir, slot = false) => screws.push({
    id, group: 'world', type: 'm4nut', head, dir, out: 0, ...(slot && { q: qmul(qfromTo(Y, dir), SLOT_TURN) }),
  });
  for (const [k, [x, y]] of Object.entries(JOINTS)) {
    nut(`nut.base.${k}`, [x, y, -17.2], Z, true);
    screw(`bolt.base.${k}`, 'm4x25', [x, y, 5], NZ, 40);
    screw(`bolt.mid.${k}`, 'm4x25', [x, y, 195], Z, 40);
    nut(`nut.mid.${k}`, [x, y, 209.8], Z);
  }
  for (const [k, [x, y]] of Object.entries(CAP_BOLTS)) {
    nut(`nut.cap.${k}`, [x, y, 263.8], Z);
    screw(`bolt.cap.${k}`, 'm4x25', [x, y, CAP_TOP - 4.4], NZ, 50);
  }
  for (const nutId of trayNutIds()) {
    const [, kind, k, n] = nutId.split('.');
    const rear = k[0] === 'R';
    nut(nutId, [HOLE_X[k[1] === 'L' ? 0 : 1], rear ? 203 : 6, kind === 'lower' ? 15 + 10 * n : 225 + 10 * n], rear ? NY : Y, true);
  }
  for (const [id, holes] of [['tray.L0', [25, 65]], ['tray.L1', [75, 115]], ['tray.L2', [125, 165]], ['drive_tray', [175, 195]], ['switch_shelf', [235, 255]]]) {
    for (const [side, x] of [['L', HOLE_X[0]], ['R', HOLE_X[1]]]) {
      holes.forEach((z, j) => screw(`${id}.s${side}${j ? 'hi' : 'lo'}`, 'm4x12', [x, 0, z], [0, 1, 0], 24));
    }
  }
  for (const [side, x] of [['L', HOLE_X[0]], ['R', HOLE_X[1]]]) {
    [235, 255].forEach((z, j) => screw(`keystone_panel.s${side}${j ? 'hi' : 'lo'}`, 'm4x12', [x, 208.4, z], [0, -1, 0], 24));
  }
  return { groups: {}, instances, screws };
}
