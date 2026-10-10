// Equipment layout in rack millimetres: x left -> right, y front -> rear, z up.
// Origin is the front-left-bottom corner of the lower frame. Tray bases come from the
// derived tray poses (base top = lowest ear hole - 1.5 mm). Every tray has an 8 mm front lip
// at y 0..3 and a 12 mm back lip at y 187..190, so rear plugs must either clear the lip or,
// on the node trays, the lip is trimmed away behind the ports.

export const FLOOR_Z = -18; // underside of the rackFeet
export const FRAME_TOP_Z = 400;
export const TOP_Z = 400;
export const HOUSE_FLOOR_Z = -518; // cabinet is 500 mm high; rack feet land at -18
export const SERVICE = { x0: -35, x1: 415, y0: -15, y1: 385, floor: -393, roof: -43, hole: [215, 290], holeRadius: 40 };
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

// Three full-size bricks sit on the compartment floor, secured by removable straps.
export const BRICK_X = [65, 175, 285];
const brick = (i) => ({
  id: `brick${i}`, model: 'brick', size: [46, 112, 29],
  centre: [BRICK_X[i], 150, SERVICE.floor + 14.5], room: true,
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
  { id:'board',model:'board',size:[90,250,55],centre:[310,335,-225],q:[Math.SQRT1_2,0,0,Math.SQRT1_2],room:true },
  { id:'spareBoard',model:'spareBoard',size:[60,360,40],centre:[950,200,-373],q:[0,0,Math.SQRT1_2,Math.SQRT1_2],room:true },
];

export const ANTENNA_TILT = 65; // authentic top plate blocks upright outer antennas; tilted rods clear below the rear bar

export const DEVICE_BY_ID = Object.fromEntries(DEVICES.map((d) => [d.id, d]));

// ---------------------------------------------------------------- living room
// House model axes (metres): X across the plan, Y from the kitchen to the garden end.
// The rack stands against the service wall (house X = 1.2), front to the room, so
// rack +x = house +Y, rack +y = house -X. ROOM.X0/Y0 place the rack origin.
export const ROOM = {
  X0: 1.66, // house X of the rack front plane (y = 0)
  Y0: 6.4, // house Y of the rack's left side (x = 0)
  wallY: 460, // service wall face in rack y (house X 1.200)
  skirting: { depth: 16, height: 70 },
};

/** House metres -> rack millimetres. */
export function houseToRack([X, Y, Z]) {
  return [(Y - ROOM.Y0) * 1000, (ROOM.X0 - X) * 1000, Z * 1000 + HOUSE_FLOOR_Z];
}
