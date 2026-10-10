// Connector bodies and device ports. Everything is in millimetres.
//
// Connector frame: origin at the centre of the mating face, +y towards the cable exit, +z the
// connector's "up" (latch or wide face). A seated connector has its front `depth` mm inside
// the port, so its cable exit sits at port + normal * (len - depth).
// Port frame: `pos` is the centre of the opening on the device face, `n` the outward face
// normal and `u` the connector up direction, all in the device's local frame.

import { qrotate, add3, scale3, basisQuat } from './math.js';

export const CONNECTORS = {
  rj45: { len: 37, depth: 14, w: 13.5, h: 11 }, // plug 21 mm + strain-relief boot
  usbA: { len: 38, depth: 12, w: 16, h: 8 },
  microB3: { len: 26, depth: 6.5, w: 22, h: 8 }, // USB 3.0 Micro-B (drive end)
  usbC: { len: 28, depth: 6.6, w: 12, h: 6.5 },
  slim: { len: 35, depth: 9, w: 14, h: 9 }, // Lenovo slim tip
  barrel: { len: 30, depth: 9.5, w: 10, h: 10 },
  c5: { len: 42, depth: 10, w: 31, h: 17 }, // IEC C5 "cloverleaf"
  nz: { len: 40, depth: 17, w: 34, h: 28 }, // AS/NZS 3112 plug, cord out of the back
  usbAf: { len: 40, depth: 0, w: 18, h: 10 }, // extension lead's socket end
};

const Y = [0, 1, 0];
const NY = [0, -1, 0];
const Z = [0, 0, 1];

// Lenovo M920q rear row, read off the PSREF rear figure (179 mm panel = 754 px): looking at the
// front, RJ45 is at the rear left and the slim-tip power jack at the rear right. Heights are
// above the 2.5 mm feet: ports centred 9.4 mm above the chassis floor, RJ45 7.9 mm.
const NODE_REAR = 91.5;
const NODE_ROW = -16 + 9.4;
const NODE_PORTS = {
  rj45: { type: 'rj45', pos: [-65.0, NODE_REAR, -16 + 7.9], n: Y, u: Z },
  usbG2b: { type: 'usbA', pos: [-47.2, NODE_REAR, NODE_ROW], n: Y, u: Z },
  usbG2a: { type: 'usbA', pos: [-30.5, NODE_REAR, NODE_ROW], n: Y, u: Z },
  usbG1b: { type: 'usbA', pos: [-13.4, NODE_REAR, NODE_ROW], n: Y, u: Z },
  usbG1a: { type: 'usbA', pos: [25.5, NODE_REAR, NODE_ROW], n: Y, u: Z },
  power: { type: 'slim', pos: [67.6, NODE_REAR, NODE_ROW], n: Y, u: Z },
};

// Board: trapezoid section, 90 mm base, 30 mm top, 55 mm tall; three outlets on each slope.
const SLOPE = Math.atan2(30, 55); // tilt of each face from vertical
const BN = [Math.cos(SLOPE), Math.sin(SLOPE)];
const boardOutlet = (side, y) => ({
  type: 'nz',
  pos: [side * 30, y, 0],
  n: [side * BN[0], 0, BN[1]],
  u: [-side * BN[1], 0, BN[0]],
});

export const PORTS = {
  m920q: NODE_PORTS,
  seagate: { usb: { type: 'microB3', pos: [0, 57.4, 0], n: Y, u: Z } },
  touro: { usb: { type: 'microB3', pos: [0, 56, -1], n: Y, u: Z } },
  // Port face to the rear: DC jack at the right end, then ports 1..8 right to left.
  switch: {
    dc: { type: 'barrel', pos: [69, 50.5, -1], n: Y, u: Z },
    ...Object.fromEntries(
      [1, 2, 3, 4, 5, 6, 7, 8].map((k) => [`p${k}`, { type: 'rj45', pos: [55 - (k - 1) * 14.5, 50.5, -3.5], n: Y, u: Z }]),
    ),
  },
  // OpenWrt One rear: 2.5G WAN, 1G LAN and USB-C power; antennas sit above the ports.
  router: {
    host: { type: 'usbA', pos: [55, -50.25, -5], n: NY, u: Z },
    console: { type: 'usbC', pos: [-8, -50.25, -5], n: NY, u: Z },
    // Official PCB top silkscreen: 1G left, 2.5G right, PD15V further right.
    wan: { type: 'rj45', pos: [39, 50.25, -5], n: Y, u: Z },
    lan: { type: 'rj45', pos: [-39, 50.25, -5], n: Y, u: Z },
    power: { type: 'usbC', pos: [55, 50.25, -6], n: Y, u: Z },
  },
  brick: {
    c5: { type: 'c5', pos: [0, 56, 0], n: Y, u: Z },
    dcOut: { type: 'fixed', pos: [0, -68, 0], n: NY, u: Z }, // end of the moulded strain relief
  },
  board: {
    L1:boardOutlet(-1,-60),L2:boardOutlet(-1,0),L3:boardOutlet(-1,60),
    R1:boardOutlet(1,-60),R2:boardOutlet(1,0),R3:boardOutlet(1,60),
    cordOut:{type:'fixed',pos:[0,136,-14],n:Y,u:Z},
  },
  spareBoard:{cordOut:{type:'fixed',pos:[0,190,-7],n:Y,u:Z}},
  psuSwitch: { dcOut: { type: 'fixed', pos: [0, 4, -33], n: [0, 0, -1], u: Y } },
  psuRouter: { usbc: { type: 'usbC', pos: [0, 15, 4], n: Y, u: Z } },
  // Ethernet port on the underside, towards the room side of the body (assumed position).
  powerline: { eth: { type: 'rj45', pos: [0, 10, -55], n: [0, 0, -1], u: NY } },
  zigbeeEnd: { cordOut: { type: 'fixed', pos: [0, -20, 0], n: NY, u: Z } },
  wallSocket: {
    L: { type: 'nz', pos: [-28, -6, -2], n: NY, u: Z },
    R: { type: 'nz', pos: [28, -6, -2], n: NY, u: Z },
  },
};

/** World frame of a port on a device with world pose (p, q). */
export function portFrame(model, portId, p, q) {
  const port = PORTS[model]?.[portId];
  if (!port) throw new Error(`unknown port ${model}.${portId}`);
  return {
    type: port.type,
    pos: add3(p, qrotate(q, port.pos)),
    n: qrotate(q, port.n),
    u: qrotate(q, port.u),
  };
}

/** Pose of a connector seated in a port frame, pulled `out` mm back along the normal. */
export function seatedPose(type, frame, out = 0) {
  const c = CONNECTORS[type];
  const p = add3(frame.pos, scale3(frame.n, out - c.depth));
  return { p, q: basisQuat(frame.n, frame.u) };
}

/** World position of a connector's cable exit given its pose. */
export function exitPoint(type, pose) {
  return add3(pose.p, qrotate(pose.q, [0, CONNECTORS[type].len, 0]));
}
