// Procedural models for the Ethernet crimping chapters: the cable and its wires in each state, the
// clear and the metal RJ45 plug, the snagless boot, the yellow stripper, the 3-in-1 crimper, the 468
// tester with its remote, and the work mat. Millimetres, rack frame (x right, y rear, z up).
//
// Each model merges its meshes by material, so a crimper or a whole wire fan is one or two draw
// calls. Wire colours ride in vertex colours: a white-orange wire is white with orange bands.

import {
  BoxGeometry, CanvasTexture, Float32BufferAttribute, CatmullRomCurve3, Color, CylinderGeometry, ExtrudeGeometry, Group, LatheGeometry,
  Matrix4, Mesh, MeshStandardMaterial, Path, PlaneGeometry, Quaternion, Shape, SRGBColorSpace, TubeGeometry, Vector2, Vector3,
} from 'three';
import { RoundedBoxGeometry } from 'three/examples/jsm/geometries/RoundedBoxGeometry.js';
import { mergeGeometries } from 'three/examples/jsm/utils/BufferGeometryUtils.js';
import {
  BOOT, CABLE_R, LEAD, LED_X, MAIN, PIN_PITCH, PLUG, REMOTE, T568B, WIRE_COLOURS, WIRE_R, wirePaths,
} from './crimp-layout.js';

const UP = new Vector3(0, 1, 0);

/** Collects geometry by material and merges each material's pieces into one mesh. */
class Builder {
  constructor() {
    this.object = new Group();
    this.buckets = new Map();
    this.materials = [];
  }

  paint(color, { metalness = 0.05, roughness = 0.45, vertexColors = false, opacity = 1, emissive = 0, emissiveIntensity = 0, map = null } = {}) {
    const m = new MeshStandardMaterial({ color, metalness, roughness, vertexColors, emissive, emissiveIntensity, map });
    if (opacity < 1) {
      // The viewer fades parts by opacity; it multiplies by this so a clear plug stays clear.
      m.userData.opacity = opacity;
      m.transparent = true;
      m.opacity = opacity;
      m.depthWrite = false;
    }
    this.materials.push(m);
    this.buckets.set(m, []);
    return m;
  }

  /** Add `geo` (consumed) under `material`, placed by `matrix`. */
  add(geo, material, matrix = null) {
    let g = geo.index ? geo.toNonIndexed() : geo;
    if (g !== geo) geo.dispose();
    g.deleteAttribute('uv');
    if (matrix) g.applyMatrix4(matrix);
    this.buckets.get(material).push(g);
    return g;
  }

  box(size, p, material, { round = 0, q = null } = {}) {
    const geo = round ? new RoundedBoxGeometry(...size, 2, round) : new BoxGeometry(...size);
    return this.add(geo, material, pose(p, q));
  }

  /** A bar of rectangular section from p0 to p1 in the xz plane, `t` thick in z and `w` wide in y. */
  bar(p0, p1, t, w, material, round = 0) {
    const dx = p1[0] - p0[0];
    const dz = p1[1] - p0[1];
    const len = Math.hypot(dx, dz);
    const q = new Quaternion().setFromAxisAngle(new Vector3(0, 1, 0), -Math.atan2(dz, dx));
    const geo = round ? new RoundedBoxGeometry(len, w, t, 3, round) : new BoxGeometry(len, w, t);
    return this.add(geo, material, new Matrix4().compose(new Vector3((p0[0] + p1[0]) / 2, 0, (p0[1] + p1[1]) / 2), q, new Vector3(1, 1, 1)));
  }

  /** Cylinder along `axis` ('x', 'y' or 'z') centred at p. */
  rod(r, length, p, material, axis = 'y', segments = 20) {
    const q = axis === 'y' ? null : new Quaternion().setFromUnitVectors(UP, axis === 'x' ? new Vector3(1, 0, 0) : new Vector3(0, 0, 1));
    return this.add(new CylinderGeometry(r, r, length, segments), material, pose(p, q));
  }

  finish() {
    for (const [material, geos] of this.buckets) {
      if (!geos.length) continue;
      const merged = geos.length === 1 ? geos[0] : mergeGeometries(geos);
      merged.computeBoundingSphere();
      const mesh = new Mesh(merged, material);
      mesh.castShadow = !material.transparent;
      mesh.receiveShadow = true;
      this.object.add(mesh);
    }
    return { object: this.object, materials: this.materials };
  }
}

function pose(p, q) {
  const m = new Matrix4();
  m.compose(new Vector3(...p), q instanceof Quaternion ? q : q ? new Quaternion(...q) : new Quaternion(), new Vector3(1, 1, 1));
  return m;
}

const linear = (hex) => new Color(hex);

/** Paint every vertex of `geo` one colour. */
function tint(geo, hex) {
  const c = linear(hex);
  const n = geo.attributes.position.count;
  const a = new Float32Array(n * 3);
  for (let i = 0; i < n; i++) a.set([c.r, c.g, c.b], i * 3);
  geo.setAttribute('color', new Float32BufferAttribute(a, 3));
  return geo;
}

// ---------------------------------------------------------------- wires

const COPPER = 0xd88a4a;

/**
 * One wire along `points`: a tube in its colour, banded if it is a white one, with the copper end and
 * a ring of insulation drawn at its tip. Returns non-indexed geometries with a colour attribute.
 */
function wireGeometries(points, wire, { caps = true } = {}) {
  const curve = new CatmullRomCurve3(points.map((p) => new Vector3(...p)), false, 'centripetal');
  const length = curve.getLength();
  const segments = Math.max(8, Math.ceil(length / 0.5));
  const radial = 7;
  const tube = new TubeGeometry(curve, segments, WIRE_R, radial, false);
  const base = linear(wire.white ? WIRE_COLOURS.white : wire.colour);
  const band = linear(wire.colour);
  const colours = new Float32Array(tube.attributes.position.count * 3);
  for (let i = 0; i <= segments; i++) {
    const s = (i / segments) * length;
    const c = wire.white && s % 3 < 1.1 ? band : base;
    for (let j = 0; j <= radial; j++) colours.set([c.r, c.g, c.b], (i * (radial + 1) + j) * 3);
  }
  tube.setAttribute('color', new Float32BufferAttribute(colours, 3));
  const out = [tube];
  if (caps) {
    const tip = curve.getPointAt(1);
    const dir = curve.getTangentAt(1);
    const q = new Quaternion().setFromUnitVectors(UP, dir);
    const ring = tint(new CylinderGeometry(WIRE_R, WIRE_R, 0.04, radial + 1), wire.white ? WIRE_COLOURS.white : wire.colour);
    ring.applyMatrix4(new Matrix4().compose(tip, q, new Vector3(1, 1, 1)));
    const copper = tint(new CylinderGeometry(0.26, 0.26, 0.24, 8), COPPER);
    copper.applyMatrix4(new Matrix4().compose(tip.clone().addScaledVector(dir, 0.1), q, new Vector3(1, 1, 1)));
    out.push(ring, copper);
  }
  return out;
}

/** The eight wires of one state, merged into one vertex-coloured mesh. */
export function addWires(b, material, state, matrix = null) {
  for (const { points, wire, caps } of wirePaths(state)) {
    for (const g of wireGeometries(points, wire, { caps })) b.add(g, material, matrix);
  }
}

export function buildWires(spec) {
  const b = new Builder();
  addWires(b, b.paint(0xffffff, { vertexColors: true, roughness: 0.5 }), spec.state);
  return b.finish();
}

// ---------------------------------------------------------------- cable jacket

const JACKET = 0x3f7fe0;

function addTube(b, points, r, material, { radial = 16, step = 2 } = {}) {
  const curve = new CatmullRomCurve3(points.map((p) => new Vector3(...p)), false, 'centripetal');
  const segments = Math.max(4, Math.ceil(curve.getLength() / step));
  b.add(new TubeGeometry(curve, segments, r, radial, false), material);
}

/** A run of jacket along `spec.points`, open at both ends like a cut cable; `spec.cap` closes the far end. */
export function buildJacket(spec) {
  const b = new Builder();
  const blue = b.paint(spec.colour ?? JACKET, { roughness: 0.55 });
  addTube(b, spec.points, CABLE_R, blue, { step: spec.step ?? 2 });
  // The cut face: a dark disc a little inside each open end, so the jacket reads as a sleeve.
  const inner = b.paint(0x1b2430, { roughness: 0.9 });
  for (const [end, next] of [[spec.points[0], spec.points[1]], [spec.points.at(-1), spec.points.at(-2)]]) {
    const dir = new Vector3(...next).sub(new Vector3(...end)).normalize();
    const q = new Quaternion().setFromUnitVectors(UP, dir);
    b.add(new CylinderGeometry(CABLE_R - 0.5, CABLE_R - 0.5, 0.1, 16), inner, new Matrix4().compose(new Vector3(...end).addScaledVector(dir, 0.6), q, new Vector3(1, 1, 1)));
  }
  return b.finish();
}

// ---------------------------------------------------------------- plugs and boot

/** Clear 8P8C plug: front face at the origin, body back along -y, gold contacts on top, clip underneath. */
function addPlugBody(b, clear, matrix = null) {
  const m = (geo, p, q) => (matrix ? new Matrix4().multiplyMatrices(matrix, pose(p, q)) : pose(p, q));
  const [w, len, h] = PLUG.size;
  b.add(new RoundedBoxGeometry(w, len, h, 2, 0.7), clear, m(null, [0, -len / 2, PLUG.centreZ]));
  // The clip: a tab from the front underside, rising away from the body towards the back.
  const tilt = new Quaternion().setFromAxisAngle(new Vector3(1, 0, 0), 0.24);
  b.add(new BoxGeometry(5.6, 13, 1.1), clear, m(null, [0, -9.6, PLUG.centreZ - h / 2 - 1.5], tilt));
  // The ridges between the contact slots on top.
  for (let i = 0; i <= 8; i++) b.add(new BoxGeometry(0.42, 6, 0.5), clear, m(null, [(i - 4) * PIN_PITCH, -3.6, PLUG.centreZ + h / 2 + 0.2]));
}

function addPins(b, gold, matrix = null, lift = 0) {
  for (let i = 0; i < 8; i++) {
    const p = [(i - 3.5) * PIN_PITCH, -3.6, PLUG.pinTop - 1.2 + lift];
    b.add(new BoxGeometry(0.55, 3.2, 2.4), gold, matrix ? new Matrix4().multiplyMatrices(matrix, pose(p)) : pose(p));
  }
}

export function buildPlug() {
  const b = new Builder();
  addPlugBody(b, b.paint(0xe6f0f6, { roughness: 0.12, opacity: 0.34 }));
  return b.finish();
}

export function buildPins() {
  const b = new Builder();
  addPins(b, b.paint(0xe2b24c, { metalness: 0.85, roughness: 0.28 }));
  return b.finish();
}

/** Metal-shell plug for shielded cable: a steel shell over the body with a ground tab at the back. */
export function buildShieldedPlug() {
  const b = new Builder();
  const clear = b.paint(0xe6f0f6, { roughness: 0.12, opacity: 0.34 });
  const steel = b.paint(0xc9ced3, { metalness: 0.9, roughness: 0.3 });
  addPlugBody(b, clear);
  const [w, len, h] = PLUG.size;
  b.box([w + 0.5, len - 6, h + 0.4], [0, -(len + 6) / 2, PLUG.centreZ], steel, { round: 0.5 });
  b.box([4.2, 7, 0.5], [0, -len - 3.2, PLUG.centreZ + h / 2 - 0.4], steel);
  addPins(b, b.paint(0xe2b24c, { metalness: 0.85, roughness: 0.28 }));
  return b.finish();
}

/** Snagless boot: nose at the origin facing +y, tail back along -y, the hood under the nose shielding the clip. */
function addBoot(b, rubber, matrix = null) {
  // Outside from the tail to the nose, then a short way back in, so neither open end looks hollow.
  const pts = [[2.9, -BOOT.length], [3.6, -BOOT.length + 0.6], [3.7, -24]];
  for (let y = -22; y < -8; y += 3) pts.push([4.3 + (y + 22) * 0.06, y], [4.9 + (y + 22) * 0.06, y + 1.4]);
  pts.push([6.4, -6.5], [6.9, -4], [6.9, 0], [6.0, 0], [6.0, -3]);
  const lathe = new LatheGeometry(pts.map(([r, y]) => new Vector2(r, y)), 24);
  b.add(lathe, rubber, matrix);
  // The hood that covers the clip, rising a little towards its free end.
  const hood = pose([0, 2.5, -6.1], new Quaternion().setFromAxisAngle(new Vector3(1, 0, 0), 0.16));
  b.add(new RoundedBoxGeometry(7.4, 9, 1.5, 2, 0.6), rubber, matrix ? new Matrix4().multiplyMatrices(matrix, hood) : hood);
}

export function buildBoot(spec) {
  const b = new Builder();
  addBoot(b, b.paint(spec.colour, { roughness: 0.7 }));
  return b.finish();
}

// ---------------------------------------------------------------- finished lead (tester chapters)

/** A crimped lead with a plug and boot at each end, plugged in as LEAD describes. */
export function buildLead() {
  const b = new Builder();
  const clear = b.paint(0xe6f0f6, { roughness: 0.12, opacity: 0.34 });
  const gold = b.paint(0xe2b24c, { metalness: 0.85, roughness: 0.28 });
  const rubber = b.paint(BOOT.colour, { roughness: 0.7 });
  const blue = b.paint(JACKET, { roughness: 0.55 });
  const wires = b.paint(0xffffff, { vertexColors: true, roughness: 0.5 });
  for (const end of LEAD.ends) {
    const m = pose(end.front, end.q);
    addPlugBody(b, clear, m);
    addPins(b, gold, m);
    addBoot(b, rubber, new Matrix4().multiplyMatrices(m, pose([0, -PLUG.size[1] + BOOT.overlap, 0])));
    // The wires in the plug and the jacket under its back edge, in the plug's frame.
    addWires(b, wires, 'trimmed', new Matrix4().multiplyMatrices(m, pose([0, -PLUG.front, 0])));
    addTube(b, [[0, PLUG.jacketEnd - PLUG.front, 0], [0, -PLUG.size[1] - BOOT.length + BOOT.overlap - 2, 0]].map((p) => new Vector3(...p).applyMatrix4(m).toArray()), CABLE_R, blue);
  }
  addTube(b, LEAD.points, CABLE_R, blue);
  return b.finish();
}

/** Straight lengths of cable, cut to the list: each piece lies along x from its centre. */
export function buildPiece(spec) {
  const b = new Builder();
  const half = spec.length / 2;
  addTube(b, [[-half, 0, 0], [0, 0, 0], [half, 0, 0]], CABLE_R, b.paint(JACKET, { roughness: 0.55 }), { step: 6 });
  return b.finish();
}

// ---------------------------------------------------------------- yellow stripper

function ringShape(r0, r1, cx = 0, cy = 0) {
  const s = new Shape();
  s.absarc(cx, cy, r1, 0, Math.PI * 2, false);
  const hole = new Path();
  hole.absarc(cx, cy, r0, 0, Math.PI * 2, true);
  s.holes.push(hole);
  return s;
}

/** Drawn in its own xz plane round the cable hole at the origin, 9 mm thick along y. */
export function buildStripper() {
  const b = new Builder();
  const yellow = b.paint(0xf2c418, { roughness: 0.5 });
  const steel = b.paint(0xb9c0c6, { metalness: 0.85, roughness: 0.3 });
  const T = 9;
  const flat = new Matrix4().makeRotationX(Math.PI / 2).premultiply(new Matrix4().makeTranslation(0, T / 2, 0));
  const extrude = (shape) => new ExtrudeGeometry(shape, { depth: T, bevelEnabled: false, curveSegments: 18 });
  b.add(extrude(ringShape(8.5, 12.5, 0, 26)), yellow, flat);
  const body = new Shape();
  body.moveTo(-8.5, 14.2);
  body.lineTo(-8.5, -38);
  body.absarc(0, -38, 8.5, Math.PI, 0, false);
  body.lineTo(8.5, 14.2);
  body.lineTo(-8.5, 14.2);
  const hole = new Path();
  hole.absarc(0, 0, CABLE_R + 0.5, 0, Math.PI * 2, true);
  body.holes.push(hole);
  b.add(extrude(body), yellow, flat);
  // The blade just touching the jacket, and the thumb grip ribs.
  b.box([1.2, 0.6, 2.2], [CABLE_R + 0.3, 0, 0], steel);
  for (let z = -34; z < -14; z += 4) b.box([17.4, 1.2, 1.4], [0, -T / 2 - 0.4, z], yellow);
  return b.finish();
}

// ---------------------------------------------------------------- crimper

// Tool frame: the 8P die at the origin, the tool drawn in its xz plane, 13 mm thick along y. The
// jaw pivots about CRIMPER.pivot; the parts are drawn closed.
export const CRIMPER = { pivot: [-36, 0, 0], open: 0.2, blade: [40, 0, 1.5] };
const STEEL = 0x30343a;
const GRIP = 0x1f9d78;

function crimperHalf(sign) {
  const b = new Builder();
  const steel = b.paint(STEEL, { metalness: 0.65, roughness: 0.38 });
  const bright = b.paint(0xc5cbd1, { metalness: 0.9, roughness: 0.25 });
  const grip = b.paint(GRIP, { roughness: 0.62 });
  const dark = b.paint(0x0c0d0f, { roughness: 0.8 });
  if (sign < 0) {
    b.box([70, 13, 11.6], [-9, 0, -9.2], steel, { round: 1.2 });
    b.rod(6.2, 15, CRIMPER.pivot, bright, 'y', 24);
    b.bar([24, -9.4], [76, -14], 9, 11, steel, 1);
    b.bar([70, -14], [186, -22], 14, 16, grip, 4);
    b.box([20, 1.6, 13], [40, 0.8, -5.5], bright);
    // The die openings on the face: 4P, 8P and 6P from the pivot.
    for (const [x, w] of [[-20, 7], [0, 12.4], [16, 9.4]]) for (const y of [-6.6, 6.6]) b.box([w, 0.3, 3], [x, y, -2.2], dark);
  } else {
    b.box([70, 13, 11], [-9, 0, 9.9], steel, { round: 1.2 });
    b.box([8.8, 3.4, 0.6], [0, 2.8, 4.4], bright);
    b.bar([24, 9.4], [76, 13], 9, 11, steel, 1);
    b.bar([70, 13], [186, 21], 14, 16, grip, 4);
    b.box([20, 1.6, 13], [40, -0.8, 4.5], bright);
    for (const [x, w] of [[-20, 7], [0, 12.4], [16, 9.4]]) for (const y of [-6.6, 6.6]) b.box([w, 0.3, 3], [x, y, 5.4], dark);
  }
  return b.finish();
}

export const buildCrimperLower = () => crimperHalf(-1);
export const buildCrimperUpper = () => crimperHalf(1);

// ---------------------------------------------------------------- 468 tester

const PX = 8;

function labelTexture(w, h, draw, anisotropy) {
  const c = document.createElement('canvas');
  c.width = Math.round(w * PX);
  c.height = Math.round(h * PX);
  const g = c.getContext('2d');
  g.scale(PX, PX);
  draw(g);
  const t = new CanvasTexture(c);
  t.colorSpace = SRGBColorSpace;
  t.anisotropy = anisotropy;
  return t;
}

/** Label: the green face with the lamp row, its numbers and the unit's printing. `x0` is the label's left edge in bench x. */
function drawLabel(g, w, h, unit) {
  g.fillStyle = '#41b04a';
  g.fillRect(0, 0, w, h);
  g.fillStyle = '#f5f7f2';
  g.fillRect(0.8, 0.8, w - 1.6, h - 1.6);
  g.fillStyle = '#41b04a';
  g.fillRect(1.6, 1.6, w - 3.2, h - 3.2);
  const ledY = unit.ledRow;
  g.fillStyle = '#1b2a1c';
  g.fillRect(LED_X[0] - unit.x0 - 4, ledY - 3.2, LED_X[8] - LED_X[0] + 8, 6.4);
  g.fillStyle = '#4a1f1a';
  for (const x of LED_X) {
    g.beginPath();
    g.arc(x - unit.x0, ledY, 1.6, 0, Math.PI * 2);
    g.fill();
  }
  g.fillStyle = '#ffffff';
  g.textAlign = 'center';
  g.textBaseline = 'middle';
  g.font = '600 3.4px sans-serif';
  ['1', '2', '3', '4', '5', '6', '7', '8', 'G'].forEach((t, i) => g.fillText(t, LED_X[i] - unit.x0, ledY + 6));
  g.font = '600 3.1px sans-serif';
  g.fillText(unit.heading, (LED_X[0] + LED_X[8]) / 2 - unit.x0, ledY - 6.2);
  unit.extra?.(g);
}

function buildTester(spec, anisotropy) {
  const b = new Builder();
  const shell = b.paint(0xebe7da, { roughness: 0.55 });
  const dark = b.paint(0x111214, { roughness: 0.7 });
  const unit = spec.unit;
  const [w, d, h] = unit.size;
  b.box(unit.size, [0, 0, 0], shell, { round: 4 });
  // The RJ45 socket on the +x end.
  b.box([1, 12, 10], [w / 2, 0, 1], dark);
  const out = b.finish();
  const [lw, ld] = unit.label;
  const map = labelTexture(lw, ld, (g) => drawLabel(g, lw, ld, unit), anisotropy);
  const label = new Mesh(new PlaneGeometry(lw, ld), new MeshStandardMaterial({ map, roughness: 0.6, metalness: 0 }));
  // Texture top is the rear edge (+y), seen from the front.
  label.position.set(unit.labelAt[0], unit.labelAt[1], h / 2 + 0.05);
  label.receiveShadow = true;
  out.object.add(label);
  out.materials.push(label.material);
  return out;
}

export const buildMain = (spec, anisotropy) => buildTester({ ...spec, unit: MAIN }, anisotropy);
export const buildRemote = (spec, anisotropy) => buildTester({ ...spec, unit: REMOTE }, anisotropy);

/** The OFF / ON / S slider knob. */
export function buildSwitch() {
  const b = new Builder();
  b.box([3.4, 5, 1.6], [0, 0, 0], b.paint(0x2b2d31, { roughness: 0.6 }), { round: 0.5 });
  return b.finish();
}

/** One lamp lit: the viewer fades it in and out. */
export function buildLamp() {
  const b = new Builder();
  b.rod(1.7, 0.6, [0, 0, 0], b.paint(0x7dff8a, { emissive: 0x39ff5a, emissiveIntensity: 2.6, roughness: 0.3 }), 'z', 16);
  return b.finish();
}

// ---------------------------------------------------------------- work mat

/** A self-healing cutting mat with a 10 mm grid and a centimetre ruler along the front edge. */
export function buildMat(spec, anisotropy) {
  const [w, d, t] = spec.size;
  const S = 3;
  const c = document.createElement('canvas');
  c.width = w * S;
  c.height = d * S;
  const g = c.getContext('2d');
  g.scale(S, S);
  g.fillStyle = '#1d2b27';
  g.fillRect(0, 0, w, d);
  for (let x = 10; x < w; x += 10) {
    g.fillStyle = x % 50 === 0 ? '#3a5a4f' : '#2a3e37';
    g.fillRect(x - 0.2, 0, x % 50 === 0 ? 0.6 : 0.4, d);
  }
  for (let y = 10; y < d; y += 10) {
    g.fillStyle = y % 50 === 0 ? '#3a5a4f' : '#2a3e37';
    g.fillRect(0, y - 0.2, w, y % 50 === 0 ? 0.6 : 0.4);
  }
  // Ruler: 0 at the left edge of the pieces (x = spec.zero from the mat's left edge), in cm.
  g.fillStyle = '#c9d8cf';
  g.font = '600 5px sans-serif';
  g.textAlign = 'center';
  g.textBaseline = 'alphabetic';
  for (let cm = 0; spec.zero + cm * 10 <= w - 4; cm++) {
    const x = spec.zero + cm * 10;
    g.fillRect(x - 0.25, d - (cm % 5 === 0 ? 7 : 4), 0.5, cm % 5 === 0 ? 7 : 4);
    if (cm % 5 === 0) g.fillText(String(cm), x, d - 9);
  }
  const map = new CanvasTexture(c);
  map.colorSpace = SRGBColorSpace;
  map.anisotropy = anisotropy;
  const material = new MeshStandardMaterial({ map, roughness: 0.92, metalness: 0 });
  const mesh = new Mesh(new BoxGeometry(w, d, t), material);
  mesh.receiveShadow = true;
  const object = new Group();
  object.add(mesh);
  return { object, materials: [material] };
}

export { T568B };
