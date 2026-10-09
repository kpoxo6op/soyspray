// Equipment layout in rack millimetres: x left -> right, y front -> rear, z up.
// Origin is the front-left-bottom corner of the lower frame. Tray bases come from the
// derived tray poses (base top = lowest ear hole - 1.5 mm); device sizes follow the
// Soyspray assembly.scad fit-study models.

export const FLOOR_Z = -18; // underside of the rackFeet
export const RACK = { width: 253, depth: 209, bayHeight: 200 };

// Inner tray area (world): x 34..215, y 3..187 (3 mm walls, 187 x 190 mm tray).
const TRAY_CX = 124.5;
const TRAY_CY = 95;

const lowerBase = [23.5, 73.5, 123.5]; // rail holes 1, 6, 11 of the lower bay
const upperBase = [223.5, 263.5, 313.5]; // rail holes 1, 5, 10 of the upper bay

export const DEVICES = [
  // Lenovo ThinkCentre M920q Tiny: 179 x 183 x 37 mm including rubber feet.
  ...[0, 1, 2].map((i) => ({
    id: `node${i}`,
    model: 'm920q',
    label: `node-${i}`,
    size: [179, 183, 37],
    centre: [TRAY_CX, TRAY_CY, lowerBase[i] + 18.5],
  })),
  // Lenovo power bricks, side by side on the lowest upper tray.
  ...[0, 1, 2].map((i) => ({
    id: `brick${i}`,
    model: 'brick',
    size: [46, 112, 29],
    centre: [TRAY_CX + (i - 1) * 61, 125, upperBase[0] + 14.5],
  })),
  // Switch front-left with ports forward; two USB drives stacked on the right.
  { id: 'switch', model: 'switch', size: [112, 70, 25], centre: [94, 39, upperBase[1] + 12.5] },
  { id: 'usbA', model: 'usbA', size: [78, 112, 15], centre: [173, 130.5, upperBase[1] + 7.5] },
  { id: 'usbB', model: 'usbB', size: [78, 112, 15], centre: [173, 130.5, upperBase[1] + 22.5] },
  // OpenWrt One on the top tray, antennas swung back to clear the top plate.
  { id: 'router', model: 'router', size: [148, 100.5, 30], centre: [TRAY_CX, 121.25, upperBase[2] + 15] },
  // External power board on the floor, outside the right side of the rack.
  { id: 'board', model: 'board', size: [55, 205, 30], centre: [310.5, 104.5, FLOOR_Z + 15] },
];

export const DEVICE_BY_ID = Object.fromEntries(DEVICES.map((d) => [d.id, d]));
