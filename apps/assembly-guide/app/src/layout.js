// Equipment layout in rack millimetres: x left -> right, y front -> rear, z up.
// Origin is the front-left-bottom corner of the lower frame. Tray bases come from the
// derived tray poses (base top = lowest ear hole - 1.5 mm). Every tray has an 8 mm front lip
// at y 0..3 and a 12 mm back lip at y 187..190, so rear plugs must either clear the lip or,
// on the node trays, the lip is trimmed away behind the ports.

import { DRILLED } from './variant.js';

export const FLOOR_Z = -18; // underside of the rackFeet
export const FRAME_TOP_Z = 400;
export const TOP_Z = 400;
export const HOUSE_FLOOR_Z = -620;
// Provisional older Nood locker, not the current Irvine. Rack feet rest on 2 mm loose pads.
export const UNIT = {
  x0: -70, x1: 1130, y0: -155, y1: 245, top: -20, topThickness: 25,
  bodyX0: -65, bodyX1: 1125, front: -150, back: 240, bottom: -520,
  steel: 2, leg: 30, clearance: 100, doorGap: 2.5, shelf: -310,
  partitions: [331.6667, 728.3333],
  ...(DRILLED ? { opening: { x: 150, z: -425, radius: 25 } } : {}),
  rackMassKg: 7, topRatingKg: 20, wallGap: DRILLED ? 180 : 110,
};
export const SERVICE = { x0: -63, x1: 328, y0: -148, y1: 238, floor: -518, roof: -45 };
export const PROVISIONAL = [
  'Unit 1200 × 400 × 600 mm; top 25 mm, overhang 5 mm.',
  'Four 30 mm square corner legs; floor clearance 100 mm.',
  'Steel 2 mm; door gaps 2.5 mm; shelf height 310 mm above the floor.',
  ...(DRILLED ? ['v1 only: optional drilled Ø50 mm hole; centre 195 mm above the floor, 220 mm from the left edge. Deburr and fit a 50 mm cable grommet; Co-Mac 900 has a 2.5 mm groove, confirm fit to the measured panel.'] : []),
  `Wall gap ${UNIT.wallGap} mm${DRILLED ? '' : ' (smallest 10 mm step: 62.5 mm adapter projection plus 40 mm lead corridor; floor board leaves 5 mm)'}; socket centre 242 mm above the floor; adapter 60 × 42 × 110 mm and port position assumed.`,
  'Loaded rack mass estimated 7 kg against an assumed 20 kg top rating. Weigh the rack and confirm the rating.',
  'Shelf depth 350 mm with a 30 mm rear gap; grip-mat pad thickness 2 mm; hook projection 28 mm assumed.',
  'Equipment envelopes, stock lead lengths and bend radii are illustrative; check fit before dressing.',
];
export const PADS = [4.5, 204.5].map(y => ({ size: [253, 21, 2], p: [126.5, y, -19] }));
export const RACK = { width: 253, depth: 209, bayHeight: 200 };

// Inner tray area (world): x 34..215, y 3..187.
const TRAY_CX = 124.5;
const TRAY_CY = 95;

export const LOWER_BASE = [23.5, 73.5, 123.5]; // rail holes 1, 6, 11 of the lower bay
export const UPPER_BASE = [223.5, 263.5, 313.5]; // rail holes 1, 5, 10 of the upper bay
export const LIP = { y0: 187, y1: 190, back: 12, front: 8 };

const node = (i) => ({
  id: `node${i}`,
  model: 'm920q',
  label: `node-${i}`,
  size: [179, 183, 37], // published chassis incl. 2.5 mm rubber feet
  centre: [TRAY_CX, TRAY_CY, LOWER_BASE[i] + 18.5],
});

// Bricks rest by gravity: v1 compartment floor, v2 room floor with 49 mm gaps.
export const BRICK_X = DRILLED ? [35, 130, 225] : [80, 175, 270];
const brick = (i) => ({
  id: `brick${i}`, model: 'brick', size: [46, 112, 29],
  centre: [BRICK_X[i], DRILLED ? 45 : 125, (DRILLED ? SERVICE.floor : HOUSE_FLOOR_Z) + 14.5], room: true,
});

export const DEVICES = [
  ...[0, 1, 2].map(node),
  // Lowest upper tray: both USB drives side by side, connectors to the rear, far enough forward
  // that the plug and the lead's rise both sit in front of the 12 mm back lip.
  { id: 'usbA', model: 'seagate', size: [78, 114.8, 11.7], centre: [77, 77.6, UPPER_BASE[0] + 5.85] },
  { id: 'usbB', model: 'touro', size: [80, 112, 20.5], centre: [172, 79, UPPER_BASE[0] + 10.25] },
  // Middle tray: the white 8-port switch, ports to the rear and pulled forward of the lip.
  { id: 'switch', model: 'switch', size: [158, 101, 26], centre: [TRAY_CX, 79.5, UPPER_BASE[1] + 13] },
  // Top tray: router pulled forward, antennas tilted behind the rack, clear of the authentic top plate.
  { id: 'router', model: 'router', size: [148, 100.5, 30], centre: [TRAY_CX, 70, UPPER_BASE[2] + 15] },
  ...[0, 1, 2].map(brick),
  // Six sockets are established by the clear June hardware photo. Use this board,
  // with the hidden-count black board retained unpowered as a spare.
  { id:'board',model:'board',size:[90,250,55],centre:DRILLED ? [190,30,UNIT.shelf + 27.5] : [480,225,HOUSE_FLOOR_Z + 27.5],q:DRILLED ? [0,0,0,1] : [0,0,1,0],room:true },
  { id:'spareBoard',model:'spareBoard',size:[60,360,40],centre:DRILLED ? [940,25,SERVICE.floor + 20] : [940,125,HOUSE_FLOOR_Z + 20],q:[0,0,Math.SQRT1_2,Math.SQRT1_2],room:true },
];

export const ANTENNA_TILT = 65; // authentic top plate blocks upright outer antennas; tilted rods clear below the rear bar

export const DEVICE_BY_ID = Object.fromEntries(DEVICES.map((d) => [d.id, d]));

// ---------------------------------------------------------------- living room
// Illustrative room context, independent of the unit fit.
export const ROOM = {
  X0: 1.66,
  Y0: 6.4,
  wallY: UNIT.y1 + UNIT.wallGap,
  skirting: { depth: 16, height: 70 },
};

/** House metres -> rack millimetres. */
export function houseToRack([X, Y, Z]) {
  return [(Y - ROOM.Y0) * 1000, (ROOM.X0 - X) * 1000, Z * 1000 + HOUSE_FLOOR_Z];
}
