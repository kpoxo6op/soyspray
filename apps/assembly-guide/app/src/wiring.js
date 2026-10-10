// Every lead in the installation: where it plugs in, the path it is dressed along, where its
// spare length lives and which zip ties hold it. Coordinates are rack millimetres.
//
// Stock leads keep their real length; only Ethernet is crimped to fit. Data runs down behind
// the rear-left rail; the Lenovo DC leads come down, and the two adapter leads go up, behind the
// rear-right rail; mains runs down the outside of the right-hand frame to the board; the uplink
// and the Zigbee extension follow the skirting. Lanes are ordered so no lead crosses another.

import { DEVICE_BY_ID, DEVICES, FLOOR_Z, ROOM, SERVICE } from './layout.js';
import { portFrame, seatedPose, exitPoint } from './ports.js';
import { add3, scale3, sub3, normalize3, qaxis, basisQuat } from './math.js';
import { spline, cumulative, polyLength, cableCentreline } from './cablepath.js';

const ID_Q = [0, 0, 0, 1];

// ---------------------------------------------------------------- peripherals and fixtures

const board = DEVICE_BY_ID.board;

function onBoardOutlet(outlet, standOff) {
  const f = portFrame('board', outlet, board.centre, board.q || ID_Q);
  return { p: add3(f.pos, scale3(f.n, standOff)), q: basisQuat(f.n, f.u) };
}

const psuSwitchPose = onBoardOutlet('L1', 20.5);
const psuRouterPose = onBoardOutlet('L3', 15.5);

// Double wall socket on the service wall (indicative position from the house model).
export const WALL = { faceY: ROOM.wallY, plate: [300, ROOM.wallY - 14.5, -258], plateSize: [114, 12, 74] };
const powerlinePose = { p: [328, WALL.plate[1] - 6 - 21, WALL.plate[2] - 30], q: basisQuat([0, -1, 0], [0, 0, 1]) };

// Proposed console; the feet sit on its top and the service bay stays open-backed.
export const TV = { x0: -60, x1: 1740, y0: -60, y1: 390, top: FLOOR_Z };
const zigEndPose = { p: [1270, 388, TV.top + 5], q: qaxis([0,0,1],Math.PI) };
const zigPose = { p: [1270, 342, TV.top + 5.5], q: qaxis([0,0,1],Math.PI) };

export const PERIPHERALS = [
  { id: 'psuSwitch', model: 'psuSwitch', size: [46, 40, 62], centre: psuSwitchPose.p, q: psuSwitchPose.q },
  { id: 'psuRouter', model: 'psuRouter', size: [44, 30, 44], centre: psuRouterPose.p, q: psuRouterPose.q },
  { id: 'wallSocket', model: 'wallSocket', size: WALL.plateSize, centre: WALL.plate, q: ID_Q, room: true },
  { id: 'powerline', model: 'powerline', size: [60, 42, 110], centre: powerlinePose.p, q: powerlinePose.q, room: true },
  { id: 'zigbeeEnd', model: 'zigbeeEnd', size: [18, 40, 10], centre: zigEndPose.p, q: zigEndPose.q, room: true },
  { id: 'zigbee', model: 'zigbee', size: [26, 64, 11], centre: zigPose.p, q: zigPose.q, room: true },
];

// Integral mains plugs occupy sockets just as detachable leads do.
export const INTEGRAL_PLUGS = [
  { device: 'psuSwitch', type: 'nz', at: ['board', 'L1'] },
  { device: 'psuRouter', type: 'nz', at: ['board', 'L3'] },
  { device: 'powerline', type: 'nz', at: ['wallSocket', 'R'] },
];

export const POSES = Object.fromEntries(
  [...DEVICES, ...PERIPHERALS].map((d) => [d.id, { p: d.centre, q: d.q || ID_Q, model: d.model, size: d.size }]),
);

function frame(device, port) {
  const d = POSES[device];
  return portFrame(d.model, port, d.p, d.q);
}

// ---------------------------------------------------------------- cable helpers

const UP = [0, 0, 1];
const DOWN = [0, 0, -1];
const P = (x, y, z) => [x, y, z];
const onFloor = (r) => FLOOR_Z + r + 0.5;

/** Coil from `entry`, leaving along `heading`, centre towards `toCentre`, turns advancing along `stack`. */
function coil(entry, heading, toCentre, stack, r, pitch, { b = r, tight = 0.9 } = {}) {
  return {
    entry,
    U: normalize3(scale3(toCentre, -1)),
    V: normalize3(heading),
    AX: normalize3(stack),
    a: r,
    b,
    aTight: r * tight,
    bTight: b * tight,
    pitch,
    theta0: 0,
  };
}

function straight(a, dir, d, step = 3) {
  const out = [];
  const n = Math.max(1, Math.ceil(d / step));
  for (let i = 0; i <= n; i++) out.push(add3(a, scale3(dir, (d * i) / n)));
  return out;
}

const join = (a, b) => [...a, ...b.slice(1)];

/**
 * A cable runs: plug or fixed end A -> aLead control points -> coil -> route control points ->
 * plug B. Plug ends leave and arrive straight along their port normal for `hover` mm, the
 * distance the plug travels while it is pushed home.
 */
function cable(def) {
  const out = { ...def, plugs: {} };
  let aExit;
  let aDir;
  let aStraight;
  if (def.a.fixed) {
    const f = frame(...def.a.fixed);
    aExit = f.pos;
    aDir = f.n;
    aStraight = 6;
    out.aFixed = { device: def.a.fixed[0], port: def.a.fixed[1] };
  } else {
    const f = frame(...def.a.at);
    if (f.type !== def.a.plug) throw new Error(`${def.id}: A plug ${def.a.plug} does not fit ${f.type}`);
    aExit = exitPoint(def.a.plug, seatedPose(def.a.plug, f));
    aDir = f.n;
    aStraight = def.a.hover;
    out.plugs.a = { id: `${def.id}.a`, type: def.a.plug, port: def.a.at, frame: f, hover: def.a.hover };
  }
  const aStart = straight(aExit, aDir, aStraight);
  out.aLead = join(aStart, spline([aStart.at(-1), ...def.aLead, def.coil.entry], { startDir: aDir, endDir: def.coil.V }));
  out.aCum = cumulative(out.aLead);
  const fb = def.b.free || frame(...def.b.at);
  if (fb.type !== def.b.plug) throw new Error(`${def.id}: B plug ${def.b.plug} does not fit ${fb.type}`);
  const bExit = exitPoint(def.b.plug, seatedPose(def.b.plug, fb));
  const hover = add3(bExit, scale3(fb.n, def.b.hover));
  const curve = spline([...def.route, hover], { endDir: scale3(fb.n, -1) });
  out.routeB = join(curve, straight(hover, scale3(fb.n, -1), def.b.hover));
  out.routeCum = cumulative(out.routeB);
  out.plugs.b = { id: `${def.id}.b`, type: def.b.plug, port: def.b.at || null, frame: fb, hover: def.b.hover };
  return out;
}

// ---------------------------------------------------------------- anchors

const NODE_Z = [42, 92, 142]; // node centres
const RJ_Z = NODE_Z.map((z) => z - 8.1);
const ROW_Z = NODE_Z.map((z) => z - 6.6);
const DATA_X = [18, 25, 32]; // eth0..eth2 in the data channel, behind the rear-left rail
const DATA_Y = 228;
const DC_X = [237, 231, 225]; // dc0..dc2 behind the rear-right rail
const DC_Y = 226;
const ADP_X = { sw: 214, rt: 205 }; // adapter leads, inside the DC channel
const ADP_Y = 246;
const AC_X = [286, 276, 266]; // brick0..2 leads down the outside of the right-hand frame
const AC_Y = [246, 236, 226];
const LANE = { sw: 275, rt: 287, wan: 299, zig: 319 }; // along the skirting

// ---------------------------------------------------------------- data

function nodeEthernet(i, port, laneY, laneZ) {
  const f = frame('switch', port);
  const x = f.pos[0];
  const dropY = DATA_Y + i * 10;
  return cable({
    id: `eth${i}`, kind: 'data', colour: 0xe6e5e0, od: 6, custom: true,
    a: { plug: 'rj45', at: ['switch', port], hover: 20 },
    aLead: [P(x, 186, f.pos[2] + 7), P(x, 196, laneZ - 2)],
    coil: coil(P(x - 18, laneY, laneZ), [-1, 0, 0], DOWN, [0, -1, 0], 26, 6.4, {tight:1}),
    route: [
      P(DATA_X[i] + 18, laneY + 2, laneZ),
      P(DATA_X[i] + 2, dropY - 4, laneZ - 16),
      P(DATA_X[i], dropY, laneZ - 50),
      P(DATA_X[i], dropY, RJ_Z[i] + 60),
      P(DATA_X[i] + 6, dropY + 6, RJ_Z[i] + 16),
      P(40, 242, RJ_Z[i] + 2),
    ],
    b: { plug: 'rj45', at: [`node${i}`, 'rj45'], hover: 24 },
  });
}

const eth = [nodeEthernet(2, 'p2', 244, 311), nodeEthernet(1, 'p3', 229, 299), nodeEthernet(0, 'p4', 214, 287)];

const lan = cable({
  id: 'lan', kind: 'data', colour: 0x2f6fd6, od: 6, custom: true,
  a: { plug: 'rj45', at: ['router', 'lan'], hover: 16 },
  aLead: [P(85.5, 186, 338), P(88, 198, 352)],
  coil: coil(P(108, 210, 355), [1, 0, -0.2], DOWN, [0, 1, 0], 26, 6.4, {tight:1}),
  route: [P(150, 218, 345), P(178, 216, 318), P(179.5, 182, 293)],
  b: { plug: 'rj45', at: ['switch', 'p1'], hover: 20 },
});

// WAN descends the data rail, passes through the cable hole and ends at the wall adapter.
const wan = cable({
  id:'wan',kind:'data',colour:0xf0c232,od:6,custom:true,room:true,
  a:{plug:'rj45',at:['router','wan'],hover:16},
  aLead:[P(163.5,186,338),P(169,210,358)],
  coil:coil(P(172,295,359),[-1,0,-0.3],DOWN,[0,1,0],26,6.4,{tight:1}),
  route:[P(170,316,335),P(11,310,286),P(11,289,70),P(40,290,35),P(144,283,18),P(182,292,8),
    P(186,300,-72),P(230,390,-75),P(365,390,-125),P(365,398,-430),P(328,408.5,-420)],
  b:{plug:'rj45',at:['powerline','eth'],hover:24},
});

// ---------------------------------------------------------------- USB

function driveUsb(id, drive, nodePort, xDrop) {
  const f = frame(drive, 'usb');
  const x = f.pos[0];
  const z = f.pos[2];
  const nx = frame('node0', nodePort).pos[0];
  return cable({
    id, kind: 'data', colour: 0x1b1c1f, od: 4.5, stock: 460,
    a: { plug: 'microB3', at: [drive, 'usb'], hover: 16 },
    aLead: [P(x, 182, z + 8), P(x, 194, z + 12), P(x, 222, z + 4)],
    coil: coil(P(x, 236, z - 10), DOWN, [-1, 0, 0], [0, 1, 0], 14, 5),
    route: [P(xDrop, 240, z - 60), P(xDrop, 240, 130), P(xDrop, 240, 72), P(nx, 240, 46)],
    b: { plug: 'usbA', at: ['node0', nodePort], hover: 22 },
  });
}

const usbSeagate = driveUsb('usbSeagate', 'usbA', 'usbG2b', 78);
const usbTouro = driveUsb('usbTouro', 'usbB', 'usbG1a', 158);

// Uncut extension runs in clips along the rear edge, over a metre from the antennas.
const zigbee = cable({
  id:'zigbee',kind:'data',colour:0xeceae4,od:4,stock:1500,room:true,
  a:{fixed:['zigbeeEnd','cordOut']},
  aLead:[P(1270,421,12),P(1235,418,18)],
  coil:coil(P(1190,410,18),[-1,0,0],[0,-1,0],UP,30,4.2),
  route:[P(1135,396,16),P(900,396,10),P(600,396,10),P(330,396,10),P(138,358,25),P(111.1,280,45),P(111.1,246,42)],
  b:{plug:'usbA',at:['node0','usbG1b'],hover:22},
});

// ---------------------------------------------------------------- supported stock power leads
function brickDc(i) {
  const x=DEVICE_BY_ID[`brick${i}`].centre[0];
  return cable({
    id:`dc${i}`,kind:'dc',colour:0x24252a,od:4.5,stock:1800,
    a:{fixed:[`brick${i}`,'dcOut']},
    aLead:[P(x,58,-347),P(x-48,82,-296)],
    coil:coil(P(x-50,120,-205),UP,[1,0,0],[0,-1,0],50,5.2,{tight:1}),
    route:[P(x+20,100,-110-i*25),P(150+i*22,190,-85-i*25),P(DC_X[i],280+i*8,-60-i*25),
      P(DC_X[i],280+i*8,ROW_Z[i]-10),P(DC_X[i],260,ROW_Z[i]+12),P(DC_X[i]-7,248,ROW_Z[i]+18),P(206,242,ROW_Z[i]+3)],
    b:{plug:'slim',at:[`node${i}`,'power'],hover:24},
  });
}
const dc=[0,1,2].map(brickDc);
const AC_OUTLET=['R1','R2','R3'];
function brickAc(i) {
  const x=DEVICE_BY_ID[`brick${i}`].centre[0],f=frame('board',AC_OUTLET[i]);
  return cable({
    id:`ac${i}`,kind:'ac',colour:0x27282c,od:7,stock:1000,
    a:{plug:'nz',at:['board',AC_OUTLET[i]],hover:22},
    aLead:[P(402-i*7,300-i*12,f.pos[2]-35),P(402-i*7,280-i*14,-330-i*15),P(x-45,228+i*14,-345-i*15),P(x-45,266+i*14,-380)],
    coil:coil(P(x-45,310,-382),[0,1,0],[1,0,0],UP,45,8,{tight:1}),
    route:[P(x-10,360,-365),P(x-10,300,-365),P(x,280,-375)],
    b:{plug:'c5',at:[`brick${i}`,'c5'],hover:20},
  });
}
const ac=[0,1,2].map(brickAc);
const swPower=cable({
  id:'swPower',kind:'dc',colour:0xefeee9,od:3.5,stock:1500,
  a:{fixed:['psuSwitch','dcOut']},
  aLead:[P(232,373,-285),P(235,390,-300),P(20,390,-300),P(10,330,-205)],
  coil:coil(P(20,268,-105),UP,[1,0,0],[0,-1,0],45,4.1,{tight:1}),
  route:[P(90,245,-90),P(ADP_X.sw,304,-70),P(ADP_X.sw,304,30),P(ADP_X.sw,ADP_Y,262),P(206,238,299),P(193.5,205,291)],
  b:{plug:'barrel',at:['switch','dc'],hover:20},
});
const routerPower=cable({
  id:'routerPower',kind:'dc',colour:0x303136,od:4,stock:1500,
  a:{plug:'usbC',at:['psuRouter','usbc'],hover:16},
  aLead:[P(235,311,-165),P(132,368,-191)],
  coil:coil(P(130,340,-105),UP,[1,0,0],[0,-1,0],45,4.6,{tight:1}),
  route:[P(180,320,-65),P(ADP_X.rt,318,-50),P(ADP_X.rt,318,30),P(ADP_X.rt,276,318),P(210,266,350),P(194,215,347)],
  b:{plug:'usbC',at:['router','power'],hover:16},
});
const boardCord=cable({
  id:'boardCord',kind:'ac',colour:0xefeee9,od:7.5,stock:1500,room:true,
  a:{fixed:['board','cordOut']},
  aLead:[P(310,381,-65),P(175,405,-70),P(150,432,-180),P(145,432,-350)],
  coil:coil(P(155,418,-268),UP,[1,0,0],[0,-1,0],50,8.2,{tight:1}),
  route:[P(221,408,-184),P(234,380,-220),P(256,392,-220)],
  b:{plug:'nz',at:['wallSocket','L'],hover:22},
});

// Spare board stays unplugged; its complete stock cord and loose NZ plug are stowed.
const spareCord=cable({
  id:'spareCord',kind:'ac',colour:0x27282c,od:7.5,stock:1500,room:true,
  a:{fixed:['spareBoard','cordOut']},
  aLead:[P(735,240,-366),P(850,399,-366),P(1025,380,-378)],
  coil:coil(P(1050,285,-383),[0,-1,0],[1,0,0],UP,50,8.2,{tight:1}),
  route:[P(1150,280,-345),P(1190,295,-345)],
  b:{plug:'nz',free:{type:'nz',pos:[1240,330,-355],n:[-1,0,0],u:UP},hover:12},
});

export const CABLES = [...eth, lan, usbSeagate, usbTouro, ...dc, ...ac, swPower, routerPower, boardCord, wan, zigbee, spareCord];
export const CABLE_BY_ID = Object.fromEntries(CABLES.map((c) => [c.id, c]));

for (const c of CABLES) {
  if (c.custom) {
    // Crimped to the dressed route: A lead, the join through the empty coil and route B.
    c.length = 1;
    const minimum = cableCentreline(c, { sA: 0, sB: polyLength(c.routeB), dress: 1 }).length;
    c.length = Math.ceil((minimum + 80) * 100) / 100;
  } else {
    c.length = c.stock;
  }
}
