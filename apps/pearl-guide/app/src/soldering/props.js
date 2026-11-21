// Props the soldering page draws in code, at real size in metres: the CXG E60WT pen iron, cut-away joints, braid,
// LEDs, flux smoke, the meter's screen and the few small parts bench.glb does not have.
//
// Performance rules these follow (plan-build.md section 4): one mesh per material inside a prop (merged geometry),
// standard materials with no new feature set (no maps except the two canvas screens, which match pocketScale's, no
// DoubleSide, no instancing), no lights (the hot tip and the LEDs use emissive colour), and setters that read the
// mesh's material when they run, because Cast.add gives every mesh a cloned material.
//
// Sizes marked "about" are working figures until Boris sends photos of his iron, stand, kit and meter.

import {
  BoxGeometry,
  CanvasTexture,
  CapsuleGeometry,
  CatmullRomCurve3,
  Color,
  CylinderGeometry,
  DoubleSide,
  Euler,
  Group,
  LatheGeometry,
  Matrix4,
  Mesh,
  MeshBasicMaterial,
  MeshStandardMaterial,
  Object3D,
  PlaneGeometry,
  Quaternion,
  Shape,
  ShapeGeometry,
  SphereGeometry,
  SRGBColorSpace,
  TubeGeometry,
  Vector2,
  Vector3,
} from 'three';
import { mergeGeometries } from 'three/examples/jsm/utils/BufferGeometryUtils.js';
import { MAT } from '../props.js';

const MM = 0.001;
const std = (color, roughness = 0.5, metalness = 0) => new MeshStandardMaterial({ color, roughness, metalness });

/** Materials only this page uses. Same class and features as props.js MAT: colours are uniforms, no new programs. */
export const SMAT = {
  handle: std(0x8e1d1d, 0.42), // his CXG E60WT is red
  grip: std(0x2a2c2f, 0.88),
  button: std(0x5d6168, 0.5),
  tip: std(0x6e7175, 0.55, 0.85), // a dull tip; tipState() lerps it to bright tin
  fr4: std(0xb7b27a, 0.7), // the cut face of a board: glass fibre and resin
  epoxy: std(0x111214, 0.4),
  sleeve: std(0x23305a, 0.45),
  stripe: std(0xb9bec6, 0.5),
  nylon: std(0xe6dfcc, 0.6),
  // sawn faces of metal: a flat mirror would only show the dark room behind the camera, so they are drawn matte
  solderCut: std(0xd5d8dc, 0.45, 0.25),
  steelCut: std(0xa9adb2, 0.5, 0.25),
  solderColdCut: std(0x9fa3a7, 0.6, 0.25),
};

export const TIN = new Color(0xe6e9ec);
export const DULL = new Color(0x6e7175);
export const BLACK_TIP = new Color(0x2a2522);
export const GLOW = new Color(0xff7a2e);

function mesh(geo, mat, cast = true) {
  const m = new Mesh(geo, mat);
  m.castShadow = cast;
  m.receiveShadow = true;
  return m;
}

const tmpM = new Matrix4();
const tmpQ = new Quaternion();
const tmpV = new Vector3();
const tmpE = new Euler();
const tmpS = new Vector3();
/** Place a geometry: position p (mm), Euler r (radians, XYZ), scale s. Returns the geometry. */
function put(geo, p = [0, 0, 0], r = [0, 0, 0], s = [1, 1, 1]) {
  tmpQ.setFromEuler(tmpE.set(r[0], r[1], r[2], 'XYZ'));
  tmpM.compose(tmpV.set(p[0] * MM, p[1] * MM, p[2] * MM), tmpQ, tmpS.set(s[0], s[1], s[2]));
  return geo.applyMatrix4(tmpM);
}

/** Merge geometries that share one material; mixed indexed and non-indexed inputs are all de-indexed. */
function merge(list) {
  const mixed = list.some((g) => !g.index);
  const out = mergeGeometries(mixed ? list.map((g) => (g.index ? g.toNonIndexed() : g)) : list);
  if (!out) throw new Error('merge failed');
  return out;
}

/** A lathe from [r, y] pairs in mm, turned about y. */
const lathe = (pts, seg = 32, phiStart = 0, phiLength = Math.PI * 2) =>
  new LatheGeometry(pts.map(([r, y]) => new Vector2(Math.max(r, 1e-4) * MM, y * MM)), seg, phiStart, phiLength);

function textCanvas(w, h) {
  const c = document.createElement('canvas');
  c.width = w;
  c.height = h;
  const t = new CanvasTexture(c);
  t.colorSpace = SRGBColorSpace;
  return { c, g: c.getContext('2d'), t };
}

const MONO = 'ui-monospace, SFMono-Regular, Menlo, Consolas, monospace';

// ---------------------------------------------------------------- the iron

/**
 * CXG E60WT pen iron, 60 W. Origin at the tip's end, the handle along +x, the screen facing +y. Working figures
 * (about): 250 mm overall; handle 150 mm long and 24 mm across with a softer grip over its front 45 mm; steel barrel
 * 6.5 mm across and 55 mm long; a 900M-style conical tip with 17 mm showing; a seven-segment screen about 20 × 10 mm
 * and two buttons on the handle; the cord leaves the back. CXG's E-series irons show the set temperature on the
 * handle and change it with two buttons; the exact layout waits for Boris's photo.
 *
 * userData: setReading(text) ('' blanks the screen), tipMesh (read .material when setting), back (local metres of
 * the cord's exit), grip and tipEnd (Object3D anchors for labels), screenAt (anchor on the screen).
 */
export function penIron() {
  const g = new Group();
  // the handle's outline along x, as [r, x] in mm, turned about the x axis
  const toX = [0, 0, -Math.PI / 2]; // lathe y axis -> +x
  const grip = lathe([[3.4, 72], [7.5, 74], [10.5, 79], [11.4, 90], [11.8, 105], [12, 117]], 28);
  const body = lathe([[12, 117], [12, 150], [11.8, 196], [11.2, 212], [8, 220], [5.2, 222], [5, 236], [3.6, 250], [0, 250]], 28);
  // the screen's bezel sits flat on top of the handle
  const bezel = put(new BoxGeometry(22 * MM, 2.2 * MM, 12 * MM), [140, 11.6, 0]);
  g.add(mesh(put(grip, [0, 0, 0], toX), SMAT.grip));
  g.add(mesh(merge([put(body, [0, 0, 0], toX), bezel]), SMAT.handle));
  const barrel = put(lathe([[2.4, 16.5], [3.25, 17.5], [3.25, 60], [4.6, 60.5], [4.6, 71], [3.6, 72]], 20), [0, 0, 0], toX);
  g.add(mesh(barrel, MAT.steel));
  // 900M conical tip: 4.5 mm at the base, a 1 mm rounded point
  const tipPts = [[0, 0], [0.32, 0.06], [0.48, 0.25], [0.55, 0.6], [1.2, 5], [1.9, 11], [2.25, 15.5], [2.25, 17]];
  const tip = mesh(put(lathe(tipPts, 20), [0, 0, 0], toX), SMAT.tip, false);
  g.add(tip);
  const buttons = merge([
    put(new BoxGeometry(5 * MM, 2 * MM, 7 * MM), [159, 12.2, 0]),
    put(new BoxGeometry(5 * MM, 2 * MM, 7 * MM), [168, 12.2, 0]),
  ]);
  g.add(mesh(buttons, SMAT.button, false));

  const scr = textCanvas(128, 64);
  const screen = mesh(new PlaneGeometry(20 * MM, 10 * MM), new MeshBasicMaterial({ map: scr.t, toneMapped: false }), false);
  screen.rotation.x = -Math.PI / 2; // reads along the handle, upright to someone in front of it
  screen.position.set(140 * MM, 12.75 * MM, 0);
  g.add(screen);
  let shown = null;
  g.userData.setReading = (text) => {
    if (text === shown) return;
    shown = text;
    const c = scr.g;
    c.fillStyle = '#0b0a0a';
    c.fillRect(0, 0, 128, 64);
    if (text) {
      c.fillStyle = '#ff5a36';
      c.font = `700 40px ${MONO}`;
      c.textAlign = 'right';
      c.textBaseline = 'middle';
      c.fillText(text, 100, 34);
      c.font = `700 16px ${MONO}`;
      c.fillText('°C', 124, 22);
    }
    scr.t.needsUpdate = true;
  };
  g.userData.setReading('');
  g.userData.tipMesh = tip;
  g.userData.back = new Vector3(250 * MM, 0, 0);
  const anchor = (x, y, z = 0) => {
    const a = new Object3D();
    a.position.set(x * MM, y * MM, z * MM);
    g.add(a);
    return a;
  };
  g.userData.grip = anchor(95, 12);
  g.userData.hot = anchor(45, 4);
  g.userData.tipEnd = anchor(0, 0);
  g.userData.tipSide = anchor(6, 1.6);
  g.userData.screenAt = anchor(127, 13);
  g.userData.buttonsAt = anchor(163, 13);
  g.userData.barrelAt = anchor(40, 3.3);
  return g;
}

/**
 * Boris's iron rest (21 Nov 2026): his iron came without a stand, so it rests on an old board. Origin on the bench
 * under the board, the iron's axis along +x (tip towards -x). Board 170 × 110 × 18 mm, x -35 to 135. Two blocks near
 * the front edge leave a 14 mm slot that cradles the grip, so the iron cannot roll and all its metal hangs in the air
 * past the edge; the back of the handle rests on the board. A piece of cellulose sponge sits beside the handle.
 * userData.slot is an anchor at the cradle for labels.
 */
export function restBoard() {
  const g = new Group();
  const wood = std(0x5e4c3b, 0.85); // old, darker than the oak bench
  const block = std(0x463829, 0.85);
  g.add(mesh(put(new BoxGeometry(170 * MM, 18 * MM, 110 * MM), [50, 9, 0]), wood));
  g.add(mesh(merge([
    put(new BoxGeometry(20 * MM, 22 * MM, 15 * MM), [-25, 29, 14.5]),
    put(new BoxGeometry(20 * MM, 22 * MM, 15 * MM), [-25, 29, -14.5]),
  ]), block));
  const sponge = std(0xd9c27a, 0.95);
  sponge.name = 'sponge';
  g.add(mesh(put(new BoxGeometry(60 * MM, 12 * MM, 30 * MM), [60, 24, 36]), sponge));
  const slot = new Object3D();
  slot.position.set(-25 * MM, 40 * MM, 0);
  g.add(slot);
  g.userData.slot = slot;
  return g;
}

/**
 * Boris's JCD solder reel (21 Nov photos): a white plastic reel about 50 mm across and 22 mm tall with a navy, red and
 * white label, 0.8 mm wire wound on its hub. Lies flat; origin at its centre.
 */
export function solderSpool() {
  const g = new Group();
  const reel = std(0xf1efe9, 0.55);
  const navy = std(0x1f2a5c, 0.5);
  const red = std(0xc3283a, 0.5);
  const wire = std(0xb9bcc0, 0.35, 0.8);
  g.add(mesh(merge([
    put(new CylinderGeometry(25 * MM, 25 * MM, 1.6 * MM, 40), [0, 10.2, 0]),
    put(new CylinderGeometry(25 * MM, 25 * MM, 1.6 * MM, 40), [0, -10.2, 0]),
  ]), reel));
  g.add(mesh(put(new CylinderGeometry(19 * MM, 19 * MM, 18.8 * MM, 40), [0, 0, 0]), wire));
  // the label on top: navy half and a red wedge, with the white reel showing between
  g.add(mesh(put(new CylinderGeometry(17 * MM, 17 * MM, 0.3 * MM, 40, 1, false, 0, Math.PI), [0, 11.1, 0]), navy, false));
  g.add(mesh(put(new CylinderGeometry(17 * MM, 17 * MM, 0.3 * MM, 40, 1, false, Math.PI * 1.25, Math.PI * 0.45), [0, 11.1, 0]), red, false));
  g.add(mesh(put(new CylinderGeometry(7 * MM, 7 * MM, 0.5 * MM, 32), [0, 11.2, 0]), std(0x2a2522, 0.9), false));
  return g;
}

const SKIN = std(0xd6a183, 0.72);
const SLEEVE = std(0x30343a, 0.85);

/**
 * A simple hand holding a thin object in a pen grip, so tools never float (Boris, 21 Nov). Hand frame: the held object
 * runs along +x through the origin (the tip is towards -x), +y is up. `r` is the held object's radius in mm. Index
 * finger on top, thumb on the near side, middle finger underneath, the palm above and behind the grip, and a forearm
 * in a dark sleeve rising back towards the person. `left` mirrors it.
 */
export function hand({ r = 10, left = false } = {}) {
  const g = new Group();
  const cap = (rad, len, p, rot) => put(new CapsuleGeometry(rad * MM, len * MM, 4, 10), p, rot);
  const along = (deg) => [0, 0, -Math.PI / 2 + (deg * Math.PI) / 180];
  const skin = merge([
    cap(7.5, 46, [8, r + 6.5, -2], along(-6)), // index finger on top
    cap(8.5, 40, [16, 2, -(r + 7.5)], [0.35, 0, -Math.PI / 2 - 0.25]), // thumb on the near side
    cap(7.5, 36, [12, -(r + 4), 4], along(4)), // middle finger underneath
    cap(7, 26, [44, -(r - 2), 22], [0.9, 0, -Math.PI / 2]), // ring finger, curled
    cap(6.2, 20, [52, -(r - 6), 34], [1.1, 0, -Math.PI / 2]), // little finger, curled
    put(new SphereGeometry(1, 20, 14), [62, r + 14, 14], [0.2, 0, 0.32], [48 * MM, 20 * MM, 40 * MM]), // palm
  ]);
  g.add(mesh(skin, SKIN));
  // wrist and forearm rise back towards the elbow
  g.add(mesh(cap(27, 150, [175, r + 52, 18], [0, 0, -Math.PI / 2 + 0.42]), SLEEVE));
  g.add(mesh(cap(22, 30, [106, r + 26, 16], [0, 0, -Math.PI / 2 + 0.42]), SKIN));
  if (left) g.scale.z = -1;
  return g;
}

/** Tip state: tin 0 (dull grey) to 1 (bright tin), black 0..1 (a dirty tip), heat 0..1 (a faint orange glow). */
export function tipState(iron, { tin = 0, black = 0, heat = 0 } = {}) {
  const m = iron.userData.tipMesh.material;
  m.color.copy(DULL).lerp(TIN, tin).lerp(BLACK_TIP, black);
  m.roughness = 0.55 - 0.4 * tin + 0.3 * black;
  m.metalness = 0.85 - 0.45 * tin - 0.6 * black; // tin reads silver-white, oxide reads black, not mirrors of the room
  // the glow reads only on a clean tip: a black, oxidised tip stays black even when hot, and a tinned one stays silver
  m.emissive.copy(GLOW).multiplyScalar(0.1 * heat * (1 - black) * (0.25 + 0.75 * (1 - tin)));
}

// ---------------------------------------------------------------- joints cut in half

// Profiles in mm as [r, y], y = 0 at the pad's top face. Closed outlines, counter-clockwise in the (r, y) plane.
const PAD_R = 1.15; // 2.3 mm pad
const HOLE_R = 0.45; // 0.9 mm hole
const PLATE = 0.08; // hole plating, drawn thicker than its real 0.025 mm so it reads
const LEG_R = 0.3; // 0.6 mm leg
const BOARD_T = 1.6;
const CU = 0.14; // pad copper, drawn at 0.14 mm (real 0.035 mm) so it reads
const CUT = {
  good: {
    solder: [[LEG_R, 1.45], [LEG_R, -BOARD_T - CU], [HOLE_R, -BOARD_T - CU], [HOLE_R, 0], [PAD_R, 0], [1.0, 0.12], [0.72, 0.38], [0.52, 0.78], [0.4, 1.18]],
    top: 1.5,
  },
  cold: {
    // a ball on top of the pad: it touches the pad over a narrow ring and rings the leg with a 0.1 mm gap
    solder: [[0.4, 0.2], [0.5, 0.05], [0.62, 0.0], [0.82, 0.03], [1.0, 0.3], [1.1, 0.72], [1.0, 1.18], [0.72, 1.5], [0.4, 1.62]],
    top: 1.75,
  },
};

/** The section face of a closed (r, y) outline, mirrored to both sides of the axis, facing +z, plus the back half of
 * the solid turned through 180° behind it (z < 0). */
function halfSolid(outline, seg = 24, parts = false) {
  const shape = (sign) => {
    const s = new Shape();
    const pts = sign > 0 ? outline : [...outline].reverse();
    pts.forEach(([r, y], i) => (i ? s.lineTo(sign * r * MM, y * MM) : s.moveTo(sign * r * MM, y * MM)));
    return new ShapeGeometry(s);
  };
  // closed outline turned: LatheGeometry wants an open path; close it by repeating the first point
  const ring = [...outline, outline[0]];
  // phi from pi/2 to 3pi/2 is the z < 0 half (lathe x = r sin phi, z = r cos phi)
  const back = lathe(ring, seg, Math.PI / 2, Math.PI);
  if (parts) return { face: merge([shape(1), shape(-1)]), back };
  return merge([shape(1), shape(-1), back]);
}

/**
 * A through-hole joint sawn in half: a coupon of 1.6 mm board, copper pads top and bottom, the plated hole, a 0.6 mm
 * leg and the solder. `good` wets pad and leg and fills the hole; `cold` sits on top as a ball with a gap around the
 * leg and an empty hole. Drawn at `size` times real size (1.3, like the joints in props.js). The cut face looks
 * along +z. Origin at the pad's top face on the axis. userData.gap and userData.fill: label anchors.
 */
export function jointCut(kind = 'good', size = 1.3) {
  const k = CUT[kind];
  const g = new Group();
  const W = 4; // coupon half width, mm
  const D = 3.2; // coupon depth behind the cut, mm
  const r0 = HOLE_R + PLATE;
  const box = (x0, x1, z0, z1) => put(new BoxGeometry((x1 - x0) * MM, BOARD_T * MM, (z1 - z0) * MM), [(x0 + x1) / 2, -CU - BOARD_T / 2, (z0 + z1) / 2]);
  const board = merge([box(-W, -r0, -D, 0), box(r0, W, -D, 0), box(-r0, r0, -D, -r0)]);
  g.add(mesh(board, SMAT.fr4, false));
  // pads and plating as one copper outline: top pad, wall, bottom pad
  const yb = -CU - BOARD_T;
  const copper = [[HOLE_R, yb - CU], [PAD_R, yb - CU], [PAD_R, yb], [r0, yb], [r0, -CU], [PAD_R, -CU], [PAD_R, 0], [HOLE_R, 0]];
  g.add(mesh(halfSolid(copper), MAT.copper, false));
  const leg = [[0, -5], [LEG_R, -5], [LEG_R, k.top], [0, k.top]];
  const legParts = halfSolid(leg, 16, true);
  g.add(mesh(legParts.back, MAT.steel, false), mesh(legParts.face, SMAT.steelCut, false));
  const solder = halfSolid(k.solder, 24, true);
  g.add(mesh(solder.back, kind === 'cold' ? MAT.tinDull : MAT.tin, false));
  g.add(mesh(solder.face, kind === 'cold' ? SMAT.solderColdCut : SMAT.solderCut, false));
  g.scale.setScalar(size);
  const anchor = (x, y) => {
    const a = new Object3D();
    a.position.set(x * MM, y * MM, 0.05 * MM);
    g.add(a);
    return a;
  };
  g.userData.gap = anchor(-0.36, 0.9);
  g.userData.fill = anchor(-0.38, -0.9);
  g.userData.top = anchor(0, k.top + 0.2);
  return g;
}

// ---------------------------------------------------------------- braid, LEDs, small parts

/** 1.5 mm desolder braid: a 40 mm strip along +x, 0.25 mm thick. Its first 6 mm turns silver as it soaks up a
 * bridge: userData.setSoak(0..1). Origin at the middle of that first 6 mm, on the strip's underside. */
export function braidStrip() {
  const g = new Group();
  g.add(mesh(put(new BoxGeometry(40 * MM, 0.25 * MM, 1.5 * MM), [17, 0.125, 0]), MAT.copper, false));
  const soak = mesh(put(new BoxGeometry(6 * MM, 0.27 * MM, 1.52 * MM), [0, 0.125, 0]), MAT.tin, false);
  g.add(soak);
  g.userData.setSoak = (f) => soak.scale.set(Math.max(0.001, f), 1, 1);
  g.userData.setSoak(0);
  return g;
}

export const LED_COLORS = { red: 0xd42a1e, amber: 0xf2a516, green: 0x29b34a };

/** A 5 mm LED standing on its rim at y = 0: dome 5.0 mm across and 8.6 mm tall with a round top, rim 5.8 mm across
 * and 1 mm tall with a flat on the cathode side (-x). Legs 0.5 mm square, 2.54 mm apart, the anode (+x) 27 mm and
 * the cathode 25 mm. userData.domeMesh: set its emissive to light it (ledState). */
export function led(color = 'red') {
  const g = new Group();
  const pts = [[0, 0], [2.9, 0], [2.9, 1], [2.5, 1], [2.5, 6.1]];
  for (let i = 1; i <= 8; i++) {
    const a = (i / 8) * (Math.PI / 2);
    pts.push([2.5 * Math.cos(a), 6.1 + 2.5 * Math.sin(a)]);
  }
  const geo = lathe(pts, 28);
  const p = geo.attributes.position;
  for (let i = 0; i < p.count; i++) if (p.getY(i) < 1.01 * MM && p.getX(i) < -2.2 * MM) p.setX(i, -2.2 * MM); // the flat
  geo.computeVertexNormals();
  const dome = mesh(geo, new MeshStandardMaterial({ color: LED_COLORS[color], roughness: 0.18, metalness: 0 }));
  g.add(dome);
  const legs = merge([
    put(new BoxGeometry(0.5 * MM, 27 * MM, 0.5 * MM), [1.27, -13.5, 0]),
    put(new BoxGeometry(0.5 * MM, 25 * MM, 0.5 * MM), [-1.27, -12.5, 0]),
  ]);
  g.add(mesh(legs, MAT.steel, false));
  g.userData.domeMesh = dome;
  g.userData.color = new Color(LED_COLORS[color]);
  return g;
}

/** Light an LED: 0 off, 1 fully on. */
export function ledState(l, on = 0) {
  const ud = l.userData;
  ud.domeMesh.material.emissive.copy(ud.color).multiplyScalar(3 * on);
}

/** An 8-pin DIP chip, 9.6 × 6.4 × 3.3 mm, notch at -x, legs down through 7.62 mm rows. Origin under its body. */
export function dip() {
  const g = new Group();
  g.add(mesh(put(new BoxGeometry(9.6 * MM, 3.3 * MM, 6.4 * MM), [0, 2.15, 0]), SMAT.epoxy));
  g.add(mesh(put(new CylinderGeometry(0.9 * MM, 0.9 * MM, 0.1 * MM, 16, 1, false, 0, Math.PI), [-4.75, 3.82, 0], [0, -Math.PI / 2, 0]), SMAT.button, false));
  const legs = [];
  for (const z of [-3.81, 3.81]) for (let i = 0; i < 4; i++) legs.push(put(new BoxGeometry(0.5 * MM, 5 * MM, 0.3 * MM), [-3.81 + i * 2.54, 0, z]));
  g.add(mesh(merge(legs), MAT.steel, false));
  g.userData.notch = (() => {
    const a = new Object3D();
    a.position.set(-4.8 * MM, 3.8 * MM, 0);
    g.add(a);
    return a;
  })();
  return g;
}

/** An electrolytic capacitor, 5 mm across and 11 mm tall, with the light minus stripe on -x and legs 2 mm apart. */
export function cap() {
  const g = new Group();
  g.add(mesh(put(new CylinderGeometry(2.5 * MM, 2.5 * MM, 11 * MM, 24, 1, false, Math.PI * 0.25, Math.PI * 1.5), [0, 5.7, 0]), SMAT.sleeve));
  g.add(mesh(put(new CylinderGeometry(2.51 * MM, 2.51 * MM, 11 * MM, 8, 1, true, -Math.PI * 0.25, Math.PI * 0.5), [0, 5.7, 0], [0, Math.PI, 0]), SMAT.stripe, false));
  g.add(mesh(merge([
    put(new CylinderGeometry(2.3 * MM, 2.3 * MM, 0.3 * MM, 24), [0, 11.25, 0]),
    put(new CylinderGeometry(0.25 * MM, 0.25 * MM, 5 * MM, 6), [1, -2.2, 0]),
    put(new CylinderGeometry(0.25 * MM, 0.25 * MM, 5 * MM, 6), [-1, -2.2, 0]),
  ]), MAT.steel, false));
  g.userData.stripe = (() => {
    const a = new Object3D();
    a.position.set(-2.6 * MM, 7 * MM, 0);
    g.add(a);
    return a;
  })();
  return g;
}

/** A 28 AWG wire along +x from 0 to `length` mm with `strip` mm bare at the far end and `strip0` mm at the near end.
 * userData.copper and userData.copper0 are the two bare ends' meshes (read .material to tin them). */
export function wire2(color = 'red', length = 45, strip = 3, strip0 = 3) {
  const g = new Group();
  const ins = mesh(put(new CylinderGeometry(0.45 * MM, 0.45 * MM, (length - strip - strip0) * MM, 12), [(strip0 + (length - strip) ) / 2, 0, 0], [0, 0, Math.PI / 2]), MAT[color] || MAT.red, false);
  const cu = mesh(put(new CylinderGeometry(0.22 * MM, 0.22 * MM, strip * MM, 8), [length - strip / 2, 0, 0], [0, 0, Math.PI / 2]), MAT.copper, false);
  const cu0 = mesh(put(new CylinderGeometry(0.22 * MM, 0.22 * MM, strip0 * MM, 8), [strip0 / 2, 0, 0], [0, 0, Math.PI / 2]), MAT.copper, false);
  g.add(ins, cu, cu0);
  g.userData.copper = cu;
  g.userData.copper0 = cu0;
  return g;
}

/** Tin a bare end: 0 copper, 1 silver. */
export function tinWire(m, f) {
  m.material.color.copy(COPPER).lerp(TIN, f);
}
const COPPER = new Color(0xc9773f);

/**
 * A JST-PH 2.0 socket lead with its two wires splayed so the bare ends sit 20 mm apart (a LiPo lead must never
 * short). Socket at the origin, open towards -x (the battery's plug goes in from -x); the wires run 60 mm along +x.
 * userData.redEnd and blackEnd: local metres of the two bare tips.
 */
export function splitLead() {
  const g = new Group();
  g.add(mesh(put(new BoxGeometry(6 * MM, 4.4 * MM, 6 * MM), [3, 2.2, 0]), SMAT.nylon, false));
  const wireGeo = (side, bare) => {
    const pts = [];
    for (let i = 0; i <= 10; i++) {
      const s = i / 10;
      pts.push(new Vector3((6 + s * 54) * MM, 2.2 * MM, side * (1 + 9 * s * s) * MM));
    }
    const curve = new CatmullRomCurve3(pts);
    if (!bare) return new TubeGeometry(curve, 24, 0.45 * MM, 8);
    const end = curve.getPoint(1);
    const dir = curve.getTangent(1);
    const geo = new CylinderGeometry(0.22 * MM, 0.22 * MM, 3 * MM, 8);
    geo.applyQuaternion(new Quaternion().setFromUnitVectors(new Vector3(0, 1, 0), dir));
    geo.translate(end.x + dir.x * 1.5 * MM, end.y + dir.y * 1.5 * MM, end.z + dir.z * 1.5 * MM);
    return geo;
  };
  g.add(mesh(wireGeo(-1), MAT.red, false));
  g.add(mesh(wireGeo(1), MAT.black, false));
  g.add(mesh(merge([wireGeo(-1, true), wireGeo(1, true)]), MAT.tin, false));
  g.userData.redEnd = [61.5 * MM, 2.2 * MM, -10.5 * MM];
  g.userData.blackEnd = [61.5 * MM, 2.2 * MM, 10.5 * MM];
  return g;
}

/** A clipped-off leg: 0.6 mm across and 12 mm long, standing along y from the origin. */
export function cutLeg() {
  return mesh(put(new CylinderGeometry(0.3 * MM, 0.3 * MM, 12 * MM, 8), [0, 6, 0]), MAT.steel, false);
}

// ---------------------------------------------------------------- smoke and screens

/** Three thin wisps of flux smoke rising about 30 mm and leaning away along -z by `drift` mm at the top.
 * setFlow(phase 0..1, strength 0..1). Same material settings as props.js airflow(). */
export function smoke(height = 30, drift = 8) {
  const g = new Group();
  // a soft streak: the falloff is in alpha, so the edges and ends fade to nothing over any background
  const { g: ctx, t } = textCanvas(32, 128);
  const img = ctx.createImageData(32, 128);
  for (let y = 0; y < 128; y++) {
    for (let x = 0; x < 32; x++) {
      const dx = (x - 15.5) / 9;
      const v = Math.exp(-dx * dx) * Math.sin((Math.PI * (y + 0.5)) / 128) * 255;
      const i = (y * 32 + x) * 4;
      img.data[i] = img.data[i + 1] = img.data[i + 2] = 255;
      img.data[i + 3] = v;
    }
  }
  ctx.putImageData(img, 0, 0);
  t.needsUpdate = true;
  const wisps = [];
  for (let i = 0; i < 3; i++) {
    const mat = new MeshBasicMaterial({ map: t, color: 0xb9bbbd, transparent: true, opacity: 0, depthWrite: false, side: DoubleSide, toneMapped: false });
    const s = new Mesh(new PlaneGeometry(4 * MM, 14 * MM), mat);
    s.castShadow = false;
    s.userData.offset = i / 3;
    s.userData.x = (i - 1) * 0.9 * MM;
    s.rotation.y = i * 1.1;
    wisps.push(s);
    g.add(s);
  }
  g.userData.setFlow = (phase, strength) => {
    for (const s of wisps) {
      const k = (phase + s.userData.offset) % 1;
      // read the material now: the cast swapped in its own clone
      // brightest just above the joint, thinning as it climbs; most close-ups only see the first 10 mm
      s.material.opacity = 0.9 * strength * (1 - k) ** 1.2 * Math.min(1, k * 5);
      s.position.set(s.userData.x + Math.sin((k + s.userData.offset) * 6) * 0.6 * MM, (5 + k * height) * MM, -k * k * drift * MM);
      s.scale.y = 0.6 + k;
    }
  };
  g.userData.setFlow(0, 0);
  return g;
}

/**
 * The multimeter's reading, as a canvas plane laid on the LCD of bench.glb's multimeter (52 × 34 mm window at
 * y 35.8 mm, centred 39 mm towards its top end). Add it as a child of the meter before the cast adopts it.
 * Returns the plane; plane.userData.setReading(text, unit).
 */
export function meterScreen() {
  const scr = textCanvas(256, 96);
  const m = mesh(new PlaneGeometry(46 * MM, 25 * MM), new MeshBasicMaterial({ map: scr.t, toneMapped: false }), false);
  m.rotation.x = -Math.PI / 2;
  m.position.set(0, 36.0 * MM, -39 * MM);
  let shown = null;
  m.userData.setReading = (text = '', unit = '') => {
    const key = `${text}|${unit}`;
    if (key === shown) return;
    shown = key;
    const c = scr.g;
    c.fillStyle = '#a9b59a';
    c.fillRect(0, 0, 256, 96);
    c.fillStyle = '#1b1f1a';
    c.textAlign = 'right';
    c.textBaseline = 'middle';
    c.font = `600 60px ${MONO}`;
    if (text) c.fillText(text, 200, 52);
    c.font = `600 28px ${MONO}`;
    if (unit) c.fillText(unit, 246, 60);
    scr.t.needsUpdate = true;
  };
  m.userData.setReading('', '');
  return m;
}

/** A small bead of molten solder (a sphere 1.8 mm across). */
export function bead() {
  return mesh(new SphereGeometry(0.9 * MM, 14, 10), MAT.tin, false);
}

/** A measurement bar `length` mm long along x, centred on the origin, with 2 mm end ticks. */
export function dimBar(length, tick = 2) {
  const t = 0.15;
  const geo = merge([
    new BoxGeometry(length * MM, t * MM, t * MM),
    put(new BoxGeometry(t * MM, tick * MM, t * MM), [-length / 2, 0, 0]),
    put(new BoxGeometry(t * MM, tick * MM, t * MM), [length / 2, 0, 0]),
  ]);
  const m = new Mesh(geo, new MeshBasicMaterial({ color: 0xffd28a, toneMapped: false }));
  m.castShadow = false;
  const g = new Group();
  g.add(m);
  return g;
}

let bandTexture = null;
/** One canvas of colour bands (brown, black, orange, gold: 10 kΩ), shared by every resistor this page draws. */
function bands() {
  if (bandTexture) return bandTexture;
  const { g, t } = textCanvas(8, 64);
  g.fillStyle = '#c9b18a';
  g.fillRect(0, 0, 8, 64);
  // canvas y runs down the cylinder from its top (+y) end: the body lies along x, so top is the +x end
  [['#6b3f1f', 10], ['#111111', 19], ['#d0661c', 28], ['#d4af37', 46]].forEach(([c, y]) => {
    g.fillStyle = c;
    g.fillRect(0, y, 8, 6);
  });
  bandTexture = t;
  return t;
}

/**
 * A 1/4 W resistor for through-hole work, legs up: body 6.2 mm long and 2.5 mm across along x at the origin, the
 * legs bent up at x = ±5.08 mm and rising `rise` mm. Mounted under a board (component side down) the legs come up
 * through the holes. userData.cut(i, height): trim leg i (0: -x, 1: +x) to `height` mm above the body's axis.
 * Three meshes: the banded body (one canvas map, like the screens) and one per leg.
 */
export function resistorT(rise = 6.6) {
  const g = new Group();
  const body = mesh(put(new CylinderGeometry(1.25 * MM, 1.25 * MM, 6.2 * MM, 20), [0, 0, 0], [0, 0, -Math.PI / 2]), new MeshStandardMaterial({ map: bands(), roughness: 0.55 }), false);
  g.add(body);
  const legs = [-1, 1].map((s) => {
    const bend = new CatmullRomCurve3([new Vector3(s * 3.1 * MM, 0, 0), new Vector3(s * 4.6 * MM, 0.1 * MM, 0), new Vector3(s * 5.08 * MM, 1 * MM, 0), new Vector3(s * 5.08 * MM, 1.6 * MM, 0)]);
    const up = put(new CylinderGeometry(0.3 * MM, 0.3 * MM, rise * MM, 8), [s * 5.08, rise / 2, 0]);
    const m = mesh(merge([new TubeGeometry(bend, 8, 0.3 * MM, 8), up]), MAT.steel, false);
    g.add(m);
    return m;
  });
  g.userData.legs = legs;
  g.userData.rise = rise;
  g.userData.cut = (i, h) => legs[i].scale.set(1, Math.max(0.05, h / rise), 1);
  return g;
}

/**
 * The traffic-light board's printed component side, as one canvas on a plane just under the board (the practice
 * board's underside is its component side). Built in the board's own millimetres: bench.glb's practice_board is
 * 39.6 (x) by 49.8 (z) mm, and the story turns it a quarter turn into the frame, so frame x is board z and frame z is
 * board -x. The marks sit where story.js places the parts (RES_T, LED_X, LED_Z, CHIP, CAP, POWER): three resistor
 * outlines with their value (the resistors' bands read 10k), an outline with a flat and a + by each LED's anode hole,
 * the chip's outline with its notch and the capacitor's circle with the striped side shaded. The real kit's print
 * waits for Boris's photo.
 */
export function trafficPrint() {
  const W = 396; // 10 px per mm across the board's 39.6 mm
  const H = 498;
  const { g, t } = textCanvas(W, H);
  const px = (fx, fz) => [(0.5 - fz / 39.6) * W, (0.5 - fx / 49.8) * H]; // board x = -frame z, board z = frame x
  const mm = 10;
  g.fillStyle = '#1d6b3c'; // the same plain green board as its other face
  g.fillRect(0, 0, W, H);
  // no hole grid: his kit board is a printed board with holes only where parts go, not a perforated board
  g.strokeStyle = '#f4f1ea';
  g.fillStyle = '#f4f1ea';
  g.lineWidth = 0.28 * mm;
  g.textAlign = 'center';
  g.textBaseline = 'middle';
  const text = (s, fx, fz, size = 1.7) => {
    const [x, y] = px(fx, fz);
    g.save();
    g.translate(x, y);
    g.rotate(-Math.PI / 2); // reads along frame x, the board's long side
    g.font = `700 ${size * mm}px ${MONO}`;
    g.fillText(s, 0, 0);
    g.restore();
  };
  const rect = (fx0, fz0, fx1, fz1) => {
    const [x0, y0] = px(fx0, fz0);
    const [x1, y1] = px(fx1, fz1);
    g.strokeRect(Math.min(x0, x1), Math.min(y0, y1), Math.abs(x1 - x0), Math.abs(y1 - y0));
  };
  // resistors: body centred at x 1.27, legs at -3.81 and 6.35
  for (const z of [-1.27, -6.35, -11.43]) {
    rect(-2.1, z - 1.35, 4.64, z + 1.35);
    text('10k', 1.27, z, 1.5);
  }
  // LEDs: 5 mm outline, flat on the cathode (z 6.35) side, + by the anode hole (z 8.89)
  for (const x of [-11.43, -1.27, 8.89]) {
    const [cx, cy] = px(x, 7.62);
    const r = 2.9 * mm;
    const flat = 2.2 * mm; // the flat's distance from the centre, towards frame -z (canvas +x)
    const a = Math.acos(flat / r);
    g.beginPath();
    g.arc(cx, cy, r, a, Math.PI * 2 - a); // the long way round, leaving the flat open on the right
    g.closePath();
    g.stroke();
    text('+', x, 7.62 + 4.6, 2.4);
  }
  // the chip: 9.6 by 6.4 mm, notch at its -x end
  rect(-15.24 - 4.9, -5.08 - 3.3, -15.24 + 4.9, -5.08 + 3.3);
  {
    const [nx, ny] = px(-15.24 - 4.9, -5.08);
    g.beginPath();
    g.arc(nx, ny, 1.1 * mm, -Math.PI / 2, Math.PI / 2, true);
    g.stroke();
  }
  // the capacitor: a 5 mm circle, its striped (-x) half shaded
  {
    const [cx, cy] = px(15.24, -5.08);
    g.beginPath();
    g.arc(cx, cy, 2.7 * mm, 0, Math.PI * 2);
    g.stroke();
    g.save();
    g.beginPath();
    g.arc(cx, cy, 2.7 * mm, 0, Math.PI * 2);
    g.clip();
    g.globalAlpha = 0.75;
    g.fillRect(cx - 3 * mm, cy, 6 * mm, 3 * mm); // canvas +y is frame -x
    g.restore();
  }
  // the power pads
  rect(-21.59 - 1.6, -13.97 - 1.6, -21.59 + 1.6, -11.43 + 1.6);
  t.needsUpdate = true;
  const m = mesh(new PlaneGeometry(39.6 * MM, 49.8 * MM), new MeshStandardMaterial({ map: t, roughness: 0.75 }), false);
  m.rotation.x = Math.PI / 2; // faces -y, the underside
  m.position.y = -0.03 * MM;
  m.name = 'board_print';
  return m;
}

/** Safety glasses folded on the mat: a dark frame, two tinted lenses and the arms folded flat behind them. */
export function glasses() {
  const g = new Group();
  const frame = merge([
    put(new BoxGeometry(140 * MM, 5 * MM, 3 * MM), [0, 40, 0]),
    put(new BoxGeometry(3 * MM, 38 * MM, 3 * MM), [-68.5, 21, 0]),
    put(new BoxGeometry(3 * MM, 38 * MM, 3 * MM), [68.5, 21, 0]),
    put(new BoxGeometry(12 * MM, 8 * MM, 3 * MM), [0, 33, 0]),
    put(new BoxGeometry(128 * MM, 2.5 * MM, 3 * MM), [-4, 1.5, -9]),
    put(new BoxGeometry(128 * MM, 2.5 * MM, 3 * MM), [4, 4.5, -14]),
  ]);
  g.add(mesh(frame, SMAT.handle));
  const lens = new MeshStandardMaterial({ color: 0x9fc3da, roughness: 0.08, transparent: true, opacity: 0.45, depthWrite: false });
  const lenses = merge([
    put(new BoxGeometry(60 * MM, 36 * MM, 1.4 * MM), [-35, 21, 0.5]),
    put(new BoxGeometry(60 * MM, 36 * MM, 1.4 * MM), [35, 21, 0.5]),
  ]);
  const l = mesh(lenses, lens, false);
  l.renderOrder = 2;
  g.add(l);
  g.userData.bridge = (() => {
    const a = new Object3D();
    a.position.set(0, 44 * MM, 0);
    g.add(a);
    return a;
  })();
  return g;
}

/**
 * A precision wire stripper (Pro'sKit 8PK-3001D style, about): two steel jaws with a row of sized notches, blue
 * handles. Posed to close across a wire running along x: the jaws point at -z from the origin (their tip), one jaw
 * above the wire and one below, the notches open along x. userData.notch28 is the 28 AWG notch, 8.6 mm back from the
 * tip and 1.6 mm along +x.
 */
export function stripper() {
  const outer = new Group();
  const g = new Group();
  // built with the jaws along +x, flat in xz; turned so x -> -z, y -> +x, z -> -y
  g.quaternion.setFromRotationMatrix(new Matrix4().makeBasis(new Vector3(0, 0, -1), new Vector3(1, 0, 0), new Vector3(0, -1, 0)));
  outer.add(g);
  const jaw = merge([
    put(new BoxGeometry(34 * MM, 3 * MM, 7 * MM), [17, 1.6, 3.6]),
    put(new BoxGeometry(34 * MM, 3 * MM, 7 * MM), [17, 1.6, -3.6]),
    put(new BoxGeometry(10 * MM, 4 * MM, 16 * MM), [38, 1.6, 0]),
  ]);
  g.add(mesh(jaw, MAT.steel));
  // the notches: dark half-rounds along the jaws' meeting line, smallest (30 AWG) at the tip
  const notches = [];
  for (let i = 0; i < 6; i++) notches.push(put(new CylinderGeometry((0.35 + i * 0.14) * MM, (0.35 + i * 0.14) * MM, 3.2 * MM, 10), [4 + i * 4.6, 1.6, 0]));
  g.add(mesh(merge(notches), SMAT.epoxy, false));
  const handles = merge([
    put(new BoxGeometry(86 * MM, 6 * MM, 9 * MM), [84, 1.6, 9], [0, 0.12, 0]),
    put(new BoxGeometry(86 * MM, 6 * MM, 9 * MM), [84, 1.6, -9], [0, -0.12, 0]),
  ]);
  g.add(mesh(handles, SMAT.sleeve));
  g.userData.notch28 = (() => {
    const a = new Object3D();
    a.position.set(8.6 * MM, 1.6 * MM, 0);
    g.add(a);
    return a;
  })();
  outer.userData.notch28 = g.userData.notch28;
  return outer;
}
