// Soyrack (v3) layout in rack millimetres: x left -> right, y front -> rear, z up, z = 0 on top
// of the base deck. cad/soyrack.scad uses the same frame, and the browser meshes in
// data/v3/meshes.bin keep their rack positions, so each part's mesh centre is its pose.
// The v1/v2 node trays hang on the same hole grid: x 18.97 and 234.03, z = 25 + 10k.

import { qaxis } from '../math.js';
import { buildSlimBoard, buildCharger, buildKeystone, buildDongle } from './models.js';

const ID_Q = [0, 0, 0, 1];
const TURN = [0, 0, 1, 0]; // half a turn about z

export const CX = 126.5;
export const DEPTH = 209;
export const FLOOR_Z = -90; // underside of the silicone pads
export const RODS = { FL: [12, 19], FR: [241, 19], RL: [12, 190], RR: [241, 190] };
export const HOLE_X = [18.97, 234.03];
export const LOWER_BASE = [23.5, 73.5, 123.5]; // node tray floors on holes 1, 6 and 11
export const SHELF_TOP = { drive: 172.9, switch: 232.9, router: 272.9 };
export const BRICK_X = [40, 83, 126];
export const BRICK_Y = 82; // centre of the 112 mm bricks, y 26..138
export const TUB_FLOOR = -81.6;
export const BOARD = { centre: [123, 221, TUB_FLOOR + 25], outlets: [-72, -24, 24, 72] };
export const KEYSTONE_X = [174.5, 142.5, 110.5, 78.5]; // slots 1..4, numbered from the left seen from behind
export const KEYSTONE_Z = 245;
export const PANEL_Y = 207.2; // middle of the 2.4 mm keystone panel
export const MAST = [-950, 60]; // Zigbee mast, about 1 m from the nearest router antenna

const ON_EDGE = qaxis([0, 1, 0], Math.PI / 2);

const node = (i) => ({
  id: `node${i}`, model: 'm920q', label: `node-${i}`, size: [179, 183, 37], centre: [124.5, 95, LOWER_BASE[i] + 18.5],
});

export const DEVICES = [
  ...[0, 1, 2].map(node),
  { id: 'usbA', model: 'seagate', size: [78, 114.8, 11.7], centre: [79.5, 69.4, SHELF_TOP.drive + 5.85] },
  { id: 'usbB', model: 'touro', size: [80, 112, 20.5], centre: [172.5, 68, SHELF_TOP.drive + 10.25] },
  { id: 'switch', model: 'switch', size: [158, 101, 26], centre: [CX, 60.5, SHELF_TOP.switch + 13] },
  // Antennas stand upright through the top cap.
  { id: 'router', model: 'router', size: [148, 100.5, 30], centre: [CX, 60.25, SHELF_TOP.router + 15], antennaTilt: 0 },
  ...BRICK_X.map((x, i) => ({ id: `brick${i}`, model: 'brick', size: [46, 112, 29], centre: [x, BRICK_Y, TUB_FLOOR + 23], q: ON_EDGE })),
  // HPM D105/1 class board on its side in the rear trough, outlets facing forward.
  { id: 'board', model: 'slimBoard', size: [230, 25, 50], centre: BOARD.centre, build: buildSlimBoard },
  // Two-port USB-C charger in the fourth outlet: router PD and the switch's PD trigger lead.
  { id: 'charger', model: 'charger', size: [44, 30, 44], centre: [BOARD.centre[0] + BOARD.outlets[3], 193.5, BOARD.centre[2]], q: TURN, build: buildCharger },
  ...KEYSTONE_X.map((x, i) => ({
    id: `key${i + 1}`, model: i < 2 ? 'keystone' : 'keyBlank', size: i < 2 ? [16.5, 36, 19] : [15, 4, 17],
    centre: [x, i < 2 ? PANEL_Y : PANEL_Y + 3.2, KEYSTONE_Z], build: buildKeystone,
  })),
  { id: 'dongle', model: 'dongle', size: [26, 11, 52], centre: [MAST[0], MAST[1], FLOOR_Z + 140 + 26], build: buildDongle, room: true },
];

export const DEVICE_BY_ID = Object.fromEntries(DEVICES.map((d) => [d.id, d]));

// Ports of the v3-only equipment, in the same frame convention as ports.js.
const Y = [0, 1, 0];
const NY = [0, -1, 0];
const Z = [0, 0, 1];
export const PORTS_V3 = {
  slimBoard: Object.fromEntries(BOARD.outlets.map((x, i) => [`o${i + 1}`, { type: 'nz', pos: [x, -12.5, 0], n: NY, u: Z }])),
  charger: { c1: { type: 'usbC', pos: [-9, 15, 6], n: Y, u: Z }, c2: { type: 'usbC', pos: [9, 15, 6], n: Y, u: Z } },
  keystone: { in: { type: 'rj45', pos: [0, -18, 0], n: NY, u: Z }, out: { type: 'rj45', pos: [0, 18, 0], n: Y, u: Z } },
};

// ---------------------------------------------------------------- printed parts and fasteners

const turned = (p) => [2 * CX - p[0], DEPTH - p[1], p[2]];

/**
 * Groups, part instances and fasteners in the shape of data/placements.json, for buildTimeline.
 * `meshes` are the decoded v3 meshes; `v2` supplies the three node trays, which carry over.
 */
export function soyrackPlacements(meshes, v2) {
  const mesh = (name) => {
    if (!meshes[name]) throw new Error(`missing mesh ${name}`);
    return meshes[name];
  };
  const centre = (name) => mesh(name).centre;
  const onFloor = (name, x, y) => [x, y, FLOOR_Z + mesh(name).size[2] / 2];
  const instances = [];
  const put = (id, part, p, q = ID_Q) => instances.push({ id, group: 'world', part, p, q });

  // Test pieces stand in a row where the base will go.
  put('coupon.post', 'coupon_post', onFloor('coupon_post', 30, 80));
  put('coupon.corner', 'coupon_corner', onFloor('coupon_corner', 85, 80));
  put('coupon.nut', 'coupon_nut', onFloor('coupon_nut', 140, 80));
  put('coupon.keystone', 'coupon_keystone', onFloor('coupon_keystone', 205, 80));

  for (const name of ['base_tub', 'base_deck', 'mid_deck', 'top_cap', 'drive_tray', 'switch_shelf', 'router_shelf', 'keystone_panel']) {
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
  // The foot mesh sits under the front-left rod; the right-hand feet are turned half a turn.
  const f = centre('foot');
  const [fx, fy] = RODS.FL;
  for (const [k, [x, y]] of Object.entries(RODS)) {
    const right = x > CX;
    put(`foot.${k}`, 'foot', [right ? x - (f[0] - fx) : x + (f[0] - fx), right ? y - (f[1] - fy) : y + (f[1] - fy), f[2]], right ? TURN : ID_Q);
  }
  put('zigbee_mast', 'zigbee_mast', onFloor('zigbee_mast', ...MAST));

  for (const it of v2.instances.filter((i) => /^tray\.L[0-2]$/.test(i.id))) put(it.id, it.part, it.p, it.q);

  const screws = [];
  const screw = (id, type, head, dir, out) => screws.push({ id, group: 'world', type, head, dir, out });
  for (const [k, [x, y]] of Object.entries(RODS)) {
    screw(`nut.${k}`, 'm5nut', [x, y, -81.4], [0, 0, 1], 30);
    screw(`rod.${k}`, 'm5rod', [x, y, 218.6], [0, 0, -1], 330);
    screw(`washer.${k}`, 'm5washer', [x, y, 206], [0, 0, -1], 50);
    screw(`coupler.${k}`, 'm5coupler', [x, y, 236], [0, 0, -1], 50);
    screw(`capscrew.${k}`, 'm5x90', [x, y, 320], [0, 0, -1], 60);
  }
  for (const s of v2.screws.filter((s) => /^tray\.L[0-2]\./.test(s.id))) screws.push({ ...s });
  for (const [id, holes] of [['drive_tray', [175, 195]], ['switch_shelf', [235, 255]], ['router_shelf', [275, 295]]]) {
    for (const [side, x] of [['L', HOLE_X[0]], ['R', HOLE_X[1]]]) {
      holes.forEach((z, j) => screw(`${id}.s${side}${j ? 'hi' : 'lo'}`, 'm4x12', [x, 0, z], [0, 1, 0], 24));
    }
  }
  for (const [side, x] of [['L', HOLE_X[0]], ['R', HOLE_X[1]]]) {
    [235, 255].forEach((z, j) => screw(`keystone_panel.s${side}${j ? 'hi' : 'lo'}`, 'm4x12', [x, 208.4, z], [0, -1, 0], 24));
  }
  return { groups: {}, instances, screws };
}
