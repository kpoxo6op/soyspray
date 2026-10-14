// Every lead in the installation: where it plugs in, the path it is dressed along, where its
// spare length lives and which ONE-WRAP ties hold it. Coordinates are rack millimetres.
//
// Stock leads remain intact; only Ethernet is crimped to fit. Rear bundles lie against
// the rail posts. v1 uses the optional drilled hole; v2 rises entirely outside the back.
// Magnetic hooks carry coils and the Zigbee extension on steel faces.

import { DRILLED } from './variant.js';
import { DEVICE_BY_ID, DEVICES, ROOM, UNIT } from './layout.js';
import { portFrame, seatedPose, exitPoint } from './ports.js';
import { add3, scale3, normalize3, qaxis, basisQuat } from './math.js';
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
export const WALL = { faceY: ROOM.wallY, plate: [220, ROOM.wallY - 14.5, -378], plateSize: [114, 12, 74] };
const powerlinePose = { p: [248, WALL.plate[1] - 6 - 21, WALL.plate[2] - 30], q: basisQuat([0, -1, 0], [0, 0, 1]) };

export const TV = { x0: UNIT.x0, x1: UNIT.x1, y0: UNIT.y0, y1: UNIT.y1, top: UNIT.top };
const zigEndPose = { p: [1105, 218, TV.top + 7], q: qaxis([0,0,1],Math.PI) };
const zigPose = { p: [1105, 172, TV.top + 7.5], q: qaxis([0,0,1],Math.PI) };
export const ZIGBEE_SEPARATION_MM = 940; // maximum useful spacing on the provisional top, below 1 m

export const PERIPHERALS = [
  { id: 'psuSwitch', model: 'psuSwitch', size: [46, 40, 62], centre: psuSwitchPose.p, q: psuSwitchPose.q, room:true },
  { id: 'psuRouter', model: 'psuRouter', size: [44, 30, 44], centre: psuRouterPose.p, q: psuRouterPose.q, room:true },
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
  out.aLead = join(aStart, spline([aStart.at(-1), ...def.aLead, def.coil.entry], { startDir: def.a.fixed ? null : aDir, endDir: def.coil.V }));
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
export const RAILS = { left: { x0:12,x1:24,y0:179,y1:206 }, right: { x0:229,x1:241,y0:179,y1:206 } };
const DATA_X = [15, 21, 27];
const DATA_Y = 214;
const DC_X = [233, 229, 225];
// v1 exits through the optional drilled hole. v2 never enters the cupboard.
export function serviceExit(i = 0) {
  if(!DRILLED) {
    const x=225+i*4;
    return [P(x,268,-277),P(x,268,-60),P(x,268,16)];
  }
  const x = UNIT.opening.x + (i - 2) * 4, z = UNIT.opening.z + (i % 2) * 6;
  return [P(x,210,z), P(x,UNIT.back,z), P(x,268,z), P(x,268,z+32),
    P(x,268,-60), P(x,268,16)];
}
export const COIL_MOUNTS = DRILLED ? {
  dc0: {face:'left',centre:[-43,-95,-425],radius:30},
  dc1: {face:'left',centre:[-43,15,-425],radius:30},
  dc2: {face:'left',centre:[-43,145,-425],radius:30},
  ac0: {face:'inside-back',centre:[30,215,-440],radius:30},
  ac1: {face:'inside-back',centre:[130,215,-440],radius:30},
  ac2: {face:'inside-back',centre:[230,215,-440],radius:30},
  swPower: {face:'inside-back',centre:[215,215,-355],radius:20},
  routerPower: {face:'inside-back',centre:[65,215,-355],radius:20},
  boardCord: {face:'partition',centre:[308,155,-425],radius:25},
  spareCord: {face:'inside-back',centre:[925,215,-380],radius:35},
  zigbee: {face:'back',centre:[1040,253,-85],radius:25},
} : {
  dc0:{face:'back',centre:[40,260,-425],radius:30},
  dc1:{face:'back',centre:[130,260,-425],radius:30},
  dc2:{face:'back',centre:[220,260,-425],radius:30},
  ac0:{face:'back',centre:[350,260,-440],radius:30},
  ac1:{face:'back',centre:[430,260,-440],radius:30},
  ac2:{face:'back',centre:[510,260,-440],radius:30},
  swPower:{face:'back',centre:[330,260,-355],radius:20},
  routerPower:{face:'back',centre:[420,260,-355],radius:20},
  boardCord:{face:'back',centre:[600,260,-425],radius:25},
  spareCord:{face:'back',centre:[925,260,-380],radius:35},
  zigbee:{face:'back',centre:[1040,253,-85],radius:25},
};
function mountedCoil(id, pitch) {
  const m=COIL_MOUNTS[id], [x,y,z]=m.centre, r=m.radius;
  if (m.face==='left' || m.face==='partition')
    return coil(P(x,y-r,z), UP, [0,1,0], [m.face==='left'?1:-1,0,0], r, pitch, {tight:1});
  return coil(P(x-r,y,z), UP, [1,0,0], [0,m.face==='back'?1:-1,0], r, pitch, {tight:1});
}

// ---------------------------------------------------------------- data

function nodeEthernet(i, port, laneY, laneZ) {
  const f = frame('switch', port);
  const x = f.pos[0];
  const dropY = DATA_Y + i * 4;
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

const eth = [nodeEthernet(2, 'p2', 222, 311), nodeEthernet(1, 'p3', 218, 299), nodeEthernet(0, 'p4', 214, 287)];

const lan = cable({
  id: 'lan', kind: 'data', colour: 0x2f6fd6, od: 6, custom: true,
  a: { plug: 'rj45', at: ['router', 'lan'], hover: 16 },
  aLead: [P(85.5, 186, 338), P(88, 198, 352)],
  coil: coil(P(108, 210, 355), [1, 0, -0.2], DOWN, [0, 1, 0], 26, 6.4, {tight:1}),
  route: [P(150, 218, 345), P(178, 216, 318), P(179.5, 182, 293)],
  b: { plug: 'rj45', at: ['switch', 'p1'], hover: 20 },
});

// WAN stays outside the unit: straight up the wall gap from the wall adapter.
const wan = cable({
  id:'wan',kind:'data',colour:0xf0c232,od:6,custom:true,room:true,
  a:{plug:'rj45',at:['router','wan'],hover:16},
  aLead:[P(163.5,186,338),P(200,222,350)],
  coil:coil(P(220,244,350),[1,0,0],DOWN,[0,1,0],16,6.4,{tight:1}),
  route:DRILLED ? [P(248,292,330),P(248,310,260),P(248,310,-510),P(248,340,-545),P(248,373.5,-545)] : [P(248,285,330),P(248,285,260),P(248,285,-565),P(248,ROOM.wallY-51.5,-565)],
  b:{plug:'rj45',at:['powerline','eth'],hover:24},
});

// ---------------------------------------------------------------- USB

function driveUsb(id, drive, nodePort, zCoil) {
  const f=frame(drive,'usb'), nx=frame('node0',nodePort).pos[0];
  return cable({
    id,kind:'data',colour:0x1b1c1f,od:4.5,stock:460,
    a:{plug:'microB3',at:[drive,'usb'],hover:16},
    aLead:[P(f.pos[0]-20,190,f.pos[2]+3)],
    coil:coil(P(18,214,zCoil),[-1,0,0],[0,0,1],[0,1,0],10,4.8,{tight:1}),
    route:[P(18,220,zCoil),P((18+nx)/2,245,(zCoil+ROW_Z[0])/2),P(nx,265,ROW_Z[0]+12)],
    b:{plug:'usbA',at:['node0',nodePort],hover:22},
  });
}
const usbSeagate=driveUsb('usbSeagate','usbA','usbG2b',245);
const usbTouro=driveUsb('usbTouro','usbB','usbG1a',120);

// The extension hangs on magnetic hooks on the steel back, then rolls over the edge.
const zigbee=cable({
  id:'zigbee',kind:'data',colour:0xeceae4,od:4,stock:1500,room:true,
  a:{fixed:['zigbeeEnd','cordOut']},
  aLead:[P(1105,262,-13),P(1105,270,-60),P(1060,253,-75)],
  coil:mountedCoil('zigbee',4.5),
  route:[P(990,253,-60),P(760,253,-60),P(430,253,-60),P(111.1,266,-60),P(111.1,266,5),P(111.1,266,35.4)],
  b:{plug:'usbA',at:['node0','usbG1b'],hover:22},
});

// ---------------------------------------------------------------- supported stock power leads
function brickDc(i) {
  const x=DEVICE_BY_ID[`brick${i}`].centre[0];
  return cable({
    id:`dc${i}`,kind:'dc',colour:0x24252a,od:4.5,stock:1800,
    a:{fixed:[`brick${i}`,'dcOut']},
    aLead:DRILLED ? [P(x,-110,-500),P(-43,-135,-480),P(-43,-135,-430)] : [P(x,20,-605.5),P(x-30,260,-590),P(x-30,260,-445)],
    coil:mountedCoil(`dc${i}`,5.2),
    route:[...(DRILLED ? [P(-25,220,-425)] : [P(COIL_MOUNTS[`dc${i}`].centre[0],300,-385)]),...serviceExit(i),
      P(DC_X[i],245,20),P(DC_X[i],218,ROW_Z[i]+15),P(DC_X[i],218,ROW_Z[i]+45),P(DC_X[i],252,ROW_Z[i]+45),P(206,266,ROW_Z[i]+22),P(192.1,266,ROW_Z[i])],
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
    aLead:DRILLED ? [P(280,f.pos[1],-260),P(300,222,-280),P(290,222,-395)] : [P(555,f.pos[1],-570),P(555,300,-575),P(COIL_MOUNTS[`ac${i}`].centre[0]-30,260,-475)],
    coil:mountedCoil(`ac${i}`,8),
    route:DRILLED ? [P(x,170,-465),P(x,160,-495)] : [P(COIL_MOUNTS[`ac${i}`].centre[0],300,-480),P(x,300,-585),P(x,245,-605.5)],
    b:{plug:'c5',at:[`brick${i}`,'c5'],hover:20},
  });
}
const ac=[0,1,2].map(brickAc);
const swPower=cable({
  id:'swPower',kind:'dc',colour:0xefeee9,od:3.5,stock:1500,
  a:{fixed:['psuSwitch','dcOut']},
  aLead:DRILLED ? [P(115,-10,-304),P(120,220,-295),P(195,222,-335)] : [P(380,65,-603),P(380,300,-585),P(310,260,-385)],
  coil:mountedCoil('swPower',4.1),
  route:[...(DRILLED ? [P(150,222,-380)] : [P(300,300,-320)]),...serviceExit(3),
    P(237,248,26),P(237,218,120),P(237,218,240),P(210,225,290)],
  b:{plug:'barrel',at:['switch','dc'],hover:20},
});
const routerPower=cable({
  id:'routerPower',kind:'dc',colour:0x303136,od:4,stock:1500,
  a:{plug:'usbC',at:['psuRouter','usbc'],hover:16},
  aLead:DRILLED ? [P(80,220,-270),P(45,222,-335)] : [P(430,220,-570),P(430,300,-560),P(400,260,-385)],
  coil:mountedCoil('routerPower',4.6),
  route:[...(DRILLED ? [P(150,222,-380)] : [P(390,300,-320)]),...serviceExit(4),
    P(241,248,26),P(241,222,120),P(241,222,310),P(210,232,347)],
  b:{plug:'usbC',at:['router','power'],hover:16},
});
const boardCord=cable({
  id:'boardCord',kind:'ac',colour:0xefeee9,od:7.5,stock:1500,room:true,
  a:{fixed:['board','cordOut']},
  aLead:DRILLED ? [P(190,220,-296),P(307,222,-365)] : [P(480,300,-606.5),P(575,300,-470)],
  coil:mountedCoil('boardCord',8.2),
  route:DRILLED ? [P(290,220,-425),P(150,222,-425),P(150,UNIT.back,-425),P(150,255,-425),P(192,310,-405),P(192,330,-395)] : [P(580,300,-400),P(192,280,-400),P(192,ROOM.wallY-95,-380)],
  b:{plug:'nz',at:['wallSocket','L'],hover:22},
});
const spareCord=cable({
  id:'spareCord',kind:'ac',colour:0x27282c,od:7.5,stock:1500,room:true,
  a:{fixed:['spareBoard','cordOut']},
  aLead:DRILLED ? [P(745,120,-485),P(815,200,-440)] : [P(735,125,-607),P(735,300,-580),P(890,260,-420)],
  coil:mountedCoil('spareCord',8.2),
  route:DRILLED ? [P(1020,170,-460),P(1040,120,-475)] : [P(1020,300,-470),P(1040,300,-565)],
  b:{plug:'nz',free:{type:'nz',pos:DRILLED ? [1060,90,-480] : [1060,300,-600],n:[-1,0,0],u:UP},hover:12},
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
