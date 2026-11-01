// Boris's Bambu Lab P1S, drawn in code at its real size (389 × 389 × 457 mm), and the leftover PETG that the
// loading chapter feeds into it. Layout follows Bambu's P1S photos: the screen and logo on the front beam, the
// door hinged on the left, and on the back, on the printer's left, the PTFE inlet near the top, the spool holder
// and the purge chute. The printer has no AMS, so one PTFE tube runs from that inlet to the toolhead.
// Printer coordinates: origin at the centre of its footprint on the bench, +z is the front, y is up, metres.

import {
  BoxGeometry,
  BufferAttribute,
  BufferGeometry,
  CanvasTexture,
  CatmullRomCurve3,
  CylinderGeometry,
  Group,
  Mesh,
  MeshBasicMaterial,
  MeshStandardMaterial,
  Object3D,
  PlaneGeometry,
  Quaternion,
  SphereGeometry,
  SRGBColorSpace,
  TorusGeometry,
  Vector3,
} from 'three';
import { RoundedBoxGeometry } from 'three/examples/jsm/geometries/RoundedBoxGeometry.js';
import { mergeGeometries } from 'three/examples/jsm/utils/BufferGeometryUtils.js';

const MM = 0.001;
const v3 = (x, y, z) => new Vector3(x * MM, y * MM, z * MM);
const std = (color, roughness = 0.5, metalness = 0, extra = {}) => new MeshStandardMaterial({ color, roughness, metalness, ...extra });

export const SIZE = { w: 389, d: 389, h: 457 }; // mm, from Bambu's P1S specification
const W2 = SIZE.w / 2;
const D2 = SIZE.d / 2;
const R = 24; // rounded vertical corners
const GY = 345; // X rods' centre height
const NOZZLE = GY - 63; // nozzle tip height with the head on its rods
export const PURGE_AT = [-140, -150]; // toolhead x, z over the purge chute (back left), mm
export const PARK_AT = [0, -40]; // toolhead x, z at rest, mm
export const PETG_COLOR = 0x7ea6bf;

export const MATS = {
  shell: std(0x1b1c1e, 0.5, 0.15),
  inner: std(0x0f1011, 0.75, 0.05),
  plastic: std(0x1d1f22, 0.42),
  key: std(0x3a3d42, 0.36, 0.2),
  steel: std(0x9ea3a8, 0.3, 0.85),
  cover: std(0xd3d5d7, 0.42, 0.25),
  brass: std(0xc8a24a, 0.3, 1),
  glass: std(0x1b2127, 0.07, 0.92, { transparent: true, opacity: 0.5, depthWrite: false }),
  ptfe: std(0xf1f0ec, 0.32, 0, { transparent: true, opacity: 0.5, depthWrite: false }),
  petg: std(PETG_COLOR, 0.24, 0.02),
  red: std(0xb7322a, 0.45),
};

function box(w, h, d, x, y, z) {
  const g = new BoxGeometry(w * MM, h * MM, d * MM);
  g.translate(x * MM, y * MM, z * MM);
  return g;
}
function rbox(w, h, d, r, x, y, z) {
  const g = new RoundedBoxGeometry(w * MM, h * MM, d * MM, 3, r * MM);
  g.translate(x * MM, y * MM, z * MM);
  return g;
}
function cyl(rt, rb, h, x, y, z, axis = 'y', seg = 28) {
  const g = new CylinderGeometry(rt * MM, rb * MM, h * MM, seg);
  if (axis === 'x') g.rotateZ(Math.PI / 2);
  if (axis === 'z') g.rotateX(Math.PI / 2);
  g.translate(x * MM, y * MM, z * MM);
  return g;
}
function merged(geoms, material) {
  const m = new Mesh(mergeGeometries(geoms.map((g) => (g.index ? g.toNonIndexed() : g)), false), material);
  m.castShadow = true;
  m.receiveShadow = true;
  return m;
}
function mesh(geo, material, cast = true) {
  const m = new Mesh(geo, material);
  m.castShadow = cast;
  m.receiveShadow = true;
  return m;
}

function canvasTex(w, h) {
  const c = document.createElement('canvas');
  c.width = w;
  c.height = h;
  const t = new CanvasTexture(c);
  t.colorSpace = SRGBColorSpace;
  t.anisotropy = 4;
  return { c, g: c.getContext('2d'), t };
}

/**
 * A round strand through a list of points: the filament, the PTFE tube, a purge. setPath(points) moves its vertices
 * along evenly spaced samples; show(a, b) draws the stretch between fractions a and b of its length.
 */
export class Strand {
  constructor(radius, segments, radial, material, cast = true) {
    this.r = radius;
    this.n = segments;
    this.m = radial;
    const verts = (segments + 1) * radial;
    this.pos = new Float32Array(verts * 3);
    this.nor = new Float32Array(verts * 3);
    const g = new BufferGeometry();
    g.setAttribute('position', new BufferAttribute(this.pos, 3));
    g.setAttribute('normal', new BufferAttribute(this.nor, 3));
    const idx = [];
    for (let i = 0; i < segments; i++) {
      for (let j = 0; j < radial; j++) {
        const a = i * radial + j;
        const b = i * radial + ((j + 1) % radial);
        idx.push(a, a + radial, b, b, a + radial, b + radial);
      }
    }
    g.setIndex(idx);
    this.geo = g;
    this.mesh = mesh(g, material, cast);
    this.mesh.frustumCulled = false;
    this.points = [];
    this.length = 0;
    this.key = '';
    this._t = [new Vector3(), new Vector3()];
    this._q = new Quaternion();
    this._n = new Vector3();
    this._b = new Vector3();
  }

  /** Lay the strand along a smooth curve through `ctrl` (Vector3s). Skipped when `key` matches the last call. */
  setPath(ctrl, key = null) {
    if (key !== null && key === this.key) return;
    this.key = key;
    const curve = new CatmullRomCurve3(ctrl, false, 'centripetal');
    curve.arcLengthDivisions = Math.max(200, ctrl.length * 24);
    const pts = curve.getSpacedPoints(this.n);
    this.points = pts;
    this.length = curve.getLength();
    const { pos, nor, m, r } = this;
    const [tPrev, t] = this._t;
    const n = this._n.set(0, 0, 0);
    const b = this._b;
    for (let i = 0; i <= this.n; i++) {
      const a = pts[Math.max(0, i - 1)];
      const c = pts[Math.min(this.n, i + 1)];
      t.subVectors(c, a).normalize();
      if (i === 0) {
        n.set(0, 1, 0);
        if (Math.abs(t.y) > 0.9) n.set(1, 0, 0);
        n.addScaledVector(t, -n.dot(t)).normalize();
      } else {
        n.applyQuaternion(this._q.setFromUnitVectors(tPrev, t)).normalize(); // parallel transport: no twisting
      }
      tPrev.copy(t);
      b.crossVectors(t, n);
      const p = pts[i];
      for (let j = 0; j < m; j++) {
        const ang = (j / m) * Math.PI * 2;
        const cx = Math.cos(ang);
        const sx = Math.sin(ang);
        const k = (i * m + j) * 3;
        const nx = n.x * cx + b.x * sx;
        const ny = n.y * cx + b.y * sx;
        const nz = n.z * cx + b.z * sx;
        nor[k] = nx;
        nor[k + 1] = ny;
        nor[k + 2] = nz;
        pos[k] = p.x + nx * r;
        pos[k + 1] = p.y + ny * r;
        pos[k + 2] = p.z + nz * r;
      }
    }
    this.geo.attributes.position.needsUpdate = true;
    this.geo.attributes.normal.needsUpdate = true;
  }

  /** Draw the stretch from fraction a to b of the length (0..1). */
  show(a = 0, b = 1) {
    const i0 = Math.max(0, Math.min(this.n, Math.floor(a * this.n)));
    const i1 = Math.max(i0, Math.min(this.n, Math.ceil(b * this.n)));
    this.mesh.visible = i1 > i0;
    this.geo.setDrawRange(i0 * this.m * 6, (i1 - i0) * this.m * 6);
  }

  /** The point at fraction f of the length. */
  at(f, out = new Vector3()) {
    const x = Math.max(0, Math.min(1, f)) * this.n;
    const i = Math.min(this.n - 1, Math.floor(x));
    return out.lerpVectors(this.points[i], this.points[i + 1], x - i);
  }
}

// ---------------------------------------------------------------- the screen: 192 × 64 pixels, white on black

const SCREEN = { w: 66, h: 22 }; // mm, a 2.7-inch 3:1 panel
function drawScreen(g, w, h, s) {
  g.fillStyle = '#07090b';
  g.fillRect(0, 0, w, h);
  g.fillStyle = '#e9eef0';
  g.textBaseline = 'middle';
  const small = `600 ${Math.round(h * 0.15)}px ui-monospace, Menlo, Consolas, monospace`;
  const big = `600 ${Math.round(h * 0.2)}px ui-monospace, Menlo, Consolas, monospace`;
  // left column: nozzle and bed temperatures, as the P1S shows them
  g.font = small;
  g.textAlign = 'left';
  g.fillText(`${String(Math.round(s.nozzle ?? 25)).padStart(3)}/${String(s.target ?? 0).padStart(3)}°C`, w * 0.04, h * 0.22);
  g.fillText(`${String(Math.round(s.bed ?? 23)).padStart(3)}/${String(s.bedTarget ?? 0).padStart(3)}°C`, w * 0.04, h * 0.45);
  g.fillStyle = 'rgba(233,238,240,0.35)';
  g.fillRect(w * 0.37, h * 0.12, 2, h * 0.76);
  g.fillStyle = '#e9eef0';
  g.font = big;
  g.fillText(s.title || '', w * 0.41, h * 0.24);
  if (s.line) {
    g.font = small;
    g.fillText(s.line, w * 0.41, h * 0.48);
  }
  if (s.bar != null) {
    g.fillStyle = 'rgba(233,238,240,0.3)';
    g.fillRect(w * 0.41, h * 0.62, w * 0.53, h * 0.07);
    g.fillStyle = '#e9eef0';
    g.fillRect(w * 0.41, h * 0.62, w * 0.53 * s.bar, h * 0.07);
  }
  (s.buttons || []).forEach((label, i) => {
    const x = w * (0.41 + i * 0.28);
    const y = h * 0.72;
    const bw = w * 0.25;
    const bh = h * 0.2;
    const on = label === s.sel;
    g.fillStyle = on ? '#cfe3ea' : 'rgba(233,238,240,0.0)';
    g.fillRect(x, y, bw, bh);
    g.strokeStyle = '#cfe3ea';
    g.lineWidth = 2;
    g.strokeRect(x + 1, y + 1, bw - 2, bh - 2);
    g.fillStyle = on ? '#07090b' : '#e9eef0';
    g.font = small;
    g.textAlign = 'center';
    g.fillText(label, x + bw / 2, y + bh / 2 + 1);
    g.textAlign = 'left';
  });
}

function logo(text, sub) {
  const { c, g, t } = canvasTex(512, 128);
  g.clearRect(0, 0, c.width, c.height);
  g.fillStyle = '#a3a7ab';
  g.fillRect(8, 30, 26, 68);
  g.fillStyle = '#2a2c2f';
  g.fillRect(19, 30, 4, 68);
  g.fillRect(8, 62, 26, 4);
  g.fillStyle = '#a3a7ab';
  g.font = '500 46px system-ui, sans-serif';
  g.textBaseline = 'alphabetic';
  g.fillText(text, 48, 60);
  if (sub) {
    g.font = '400 40px system-ui, sans-serif';
    g.fillText(sub, 48, 104);
  }
  return new MeshBasicMaterial({ map: t, transparent: true, toneMapped: false, depthWrite: false });
}

// ---------------------------------------------------------------- the printer

export function buildP1S() {
  const root = new Group();
  root.name = 'P1S';

  // enclosure: four rounded corner posts, side and back panels, the front beam and sill, the top rim
  const shell = [];
  for (const sx of [-1, 1]) for (const sz of [-1, 1]) shell.push(cyl(R, R, SIZE.h, sx * (W2 - R), SIZE.h / 2, sz * (D2 - R), 'y', 32));
  for (const sx of [-1, 1]) shell.push(box(5, SIZE.h, SIZE.d - 2 * R, sx * (W2 - 2.5), SIZE.h / 2, 0));
  shell.push(box(SIZE.w - 2 * R, SIZE.h, 5, 0, SIZE.h / 2, -(D2 - 2.5)));
  shell.push(box(SIZE.w - 2 * R, 76, 9, 0, SIZE.h - 38, D2 - 4.5));
  shell.push(box(SIZE.w - 2 * R, 26, 9, 0, 13, D2 - 4.5));
  shell.push(box(SIZE.w - 2 * R, 8, 22, 0, SIZE.h - 4, D2 - 11), box(SIZE.w - 2 * R, 8, 22, 0, SIZE.h - 4, -(D2 - 11)));
  shell.push(box(22, 8, SIZE.d - 2 * R, -(W2 - 11), SIZE.h - 4, 0), box(22, 8, SIZE.d - 2 * R, W2 - 11, SIZE.h - 4, 0));
  root.add(merged(shell, MATS.shell));

  // inside: black lining, the floor, two Z lead screws at the back, the gantry's side rails and the purge chute
  const inner = [
    box(2, SIZE.h - 40, SIZE.d - 2 * R, -(W2 - 6), SIZE.h / 2, 0),
    box(2, SIZE.h - 40, SIZE.d - 2 * R, W2 - 6, SIZE.h / 2, 0),
    box(SIZE.w - 2 * R, SIZE.h - 40, 2, 0, SIZE.h / 2, -(D2 - 6)),
    box(SIZE.w - 12, 6, SIZE.d - 12, 0, 29, 0),
    box(12, 16, SIZE.d - 70, -(W2 - 14), GY + 28, 0),
    box(12, 16, SIZE.d - 70, W2 - 14, GY + 28, 0),
    box(54, 36, 44, PURGE_AT[0], 236, PURGE_AT[1] - 4),
  ];
  root.add(merged(inner, MATS.inner));
  root.add(merged([cyl(4, 4, 330, -150, 200, -172), cyl(4, 4, 330, 150, 200, -172)], MATS.steel));
  root.add(mesh(box(30, 3, 8, PURGE_AT[0] + 36, 258, PURGE_AT[1] - 16), MATS.cover)); // nozzle wiper

  // glass: the lid and, on the door, the front
  const lid = mesh(box(SIZE.w - 40, 4, SIZE.d - 40, 0, SIZE.h - 2, 0), MATS.glass, false);
  root.add(lid);
  root.add(mesh(cyl(10, 10, 7, 40, SIZE.h + 3.5, 150), MATS.steel)); // lid knob

  const door = new Group();
  door.position.set(-(W2 - R) * MM, 0, (D2 + 1.5) * MM);
  const dw = SIZE.w - 2 * R + 2;
  const dh = SIZE.h - 76 - 26;
  door.add(mesh(box(dw, dh, 4, dw / 2, 26 + dh / 2, 0), MATS.glass, false));
  door.add(merged([box(dw, 9, 6, dw / 2, 26 + 4.5, 0), box(dw, 9, 6, dw / 2, 26 + dh - 4.5, 0), box(9, dh, 6, 4.5, 26 + dh / 2, 0), box(9, dh, 6, dw - 4.5, 26 + dh / 2, 0)], MATS.plastic));
  door.add(mesh(rbox(12, 48, 12, 3, dw - 3, 26 + dh / 2, 6), MATS.cover));
  root.add(door);

  // front beam: the screen module on the left, the logo on the right
  const screenTex = canvasTex(384, 128);
  const screenMat = new MeshBasicMaterial({ map: screenTex.t, toneMapped: false });
  const beamY = SIZE.h - 38;
  root.add(mesh(rbox(150, 42, 10, 5, -84, beamY, D2 + 4), MATS.plastic));
  const screen = mesh(new PlaneGeometry(SCREEN.w * MM, SCREEN.h * MM), screenMat, false);
  screen.position.set(-118 * MM, beamY * MM, (D2 + 9.2) * MM);
  root.add(screen);
  root.add(merged([cyl(15, 15, 4, -56, beamY, D2 + 9, 'z', 32), cyl(4.5, 4.5, 4, -27, beamY + 9, D2 + 9, 'z', 20), cyl(4.5, 4.5, 4, -27, beamY - 9, D2 + 9, 'z', 20)], MATS.key));
  root.add(mesh(cyl(6.5, 6.5, 5, -56, beamY, D2 + 10, 'z', 24), MATS.plastic));
  const ring = mesh(new TorusGeometry(15 * MM, 0.9 * MM, 8, 40), MATS.steel, false);
  ring.position.set(-56 * MM, beamY * MM, (D2 + 11) * MM);
  root.add(ring);
  const brand = mesh(new PlaneGeometry(56 * MM, 14 * MM), logo('Bambu Lab', 'P1S'), false);
  brand.position.set(128 * MM, (beamY + 12) * MM, (D2 + 0.2) * MM);
  root.add(brand);

  // back, on the printer's left: the PTFE inlet bracket near the top, the spool holder, the purge chute, the vents
  const back = -(D2 + 0.4);
  root.add(merged([rbox(60, 16, 14, 3, -58, 432, -(D2 + 7)), rbox(56, 78, 10, 5, -62, 258, -(D2 + 5)), cyl(24, 24, 70, -62, 272, -(D2 + 45), 'z', 32), cyl(30, 30, 5, -62, 272, -(D2 + 80), 'z', 32)], MATS.plastic));
  root.add(merged([box(74, 94, 3, -136, 104, back - 1), box(98, 120, 2, -36, 112, back - 0.6)], MATS.inner));
  root.add(mesh(box(60, 4, 40, -136, 70, back - 10), MATS.cover)); // the chute's ramp, seen through its opening
  root.add(merged([box(15, 10, 4, 146, 70, back - 2), box(30, 22, 3, 146, 46, back - 1.5)], MATS.red));
  root.add(mesh(cyl(3.4, 3.4, 12, -96, 432, -(D2 + 12), 'x', 16), MATS.cover)); // tube coupler at the inlet

  // the gantry: X rods that move front to back, carrying the toolhead left to right
  const gantry = new Group();
  root.add(gantry);
  gantry.add(merged([cyl(4, 4, SIZE.w - 40, 0, GY + 18, 0, 'x', 16), cyl(4, 4, SIZE.w - 40, 0, GY - 18, 0, 'x', 16)], MATS.steel));
  gantry.add(merged([box(24, 50, 34, -(W2 - 20), GY, 0), box(24, 50, 34, W2 - 20, GY, 0)], MATS.plastic));
  const head = new Group();
  gantry.add(head);
  head.add(mesh(rbox(60, 74, 44, 4, 0, GY, -6), MATS.key));
  head.add(mesh(rbox(64, 76, 12, 5, 0, GY, 20), MATS.cover));
  head.add(mesh(box(7, 62, 10, -35, GY + 2, 14), MATS.cover)); // cutter lever
  head.add(mesh(cyl(19, 19, 2, 0, GY - 4, 26.4, 'z', 32), MATS.plastic));
  const fanRing = mesh(new TorusGeometry(19.5 * MM, 1.6 * MM, 8, 40), MATS.steel, false);
  fanRing.position.set(0, (GY - 4) * MM, 26.6 * MM);
  head.add(fanRing);
  const headLogo = mesh(new PlaneGeometry(30 * MM, 7.5 * MM), logo('Bambu Lab'), false);
  headLogo.position.set(2 * MM, (GY + 28) * MM, 26.2 * MM);
  head.add(headLogo);
  head.add(mesh(box(42, 20, 36, 0, GY - 47, 0), MATS.plastic));
  head.add(mesh(cyl(1.0, 2.8, 6, 0, NOZZLE + 3, 0, 'y', 20), MATS.brass));
  head.add(mesh(cyl(4.5, 4.5, 8, 0, GY + 41, -4, 'y', 20), MATS.cover)); // PTFE connector

  // the bed: a heated plate the build plate sits on; it drops as a print grows
  const bed = new Group();
  root.add(bed);
  bed.add(merged([box(262, 8, 262, 0, -4, 0), box(22, 14, 150, -105, -15, -110), box(22, 14, 150, 105, -15, -110)], MATS.key));

  // PTFE tube from the inlet to the toolhead, and the filament inside it
  const ptfe = new Strand(2.0 * MM, 170, 10, MATS.ptfe, false);
  const feed = new Strand(0.875 * MM, 260, 8, MATS.petg);
  const tip = mesh(new SphereGeometry(0.875 * MM, 12, 8), MATS.petg);
  const purge = new Strand(0.95 * MM, 48, 8, MATS.petg);
  root.add(ptfe.mesh, feed.mesh, tip, purge.mesh);

  // label anchors
  const anchors = {};
  const anchor = (name, parent, x, y, z) => {
    const o = new Object3D();
    o.position.set(x * MM, y * MM, z * MM);
    parent.add(o);
    anchors[name] = o;
  };
  anchor('inlet', root, -104, 432, -(D2 + 12));
  anchor('holder', root, -62, 300, -(D2 + 60));
  anchor('chute', root, -136, 104, back);
  anchor('screen', root, -118, beamY, D2 + 10);
  anchor('head', head, 0, GY + 38, 0);
  anchor('nozzle', head, 0, NOZZLE, 0);
  anchor('door', door, dw - 3, 26 + dh / 2, 8);

  // ------------------------------------------------------------ state, reset by rest() every frame
  const state = {};
  const ctrl = (hx, hz) => {
    const top = GY + 45;
    return [
      v3(-104, 432, -(D2 + 12)), // tube end at the inlet, open towards the printer's left
      v3(-72, 432, -(D2 + 12)),
      v3(-50, 432, -(D2 - 4)),
      v3(-40, 434, -(D2 - 34)),
      v3(-30, 440, -110),
      v3((hx - 30) / 2, 446, (hz - 110) / 2 + 6),
      v3(hx, 432, hz - 14),
      v3(hx, top + 6, hz - 5),
      v3(hx, top, hz - 4),
    ];
  };
  const api = {
    anchors,
    size: SIZE,
    nozzleY: NOZZLE * MM,
    /** Closed door, toolhead parked, bed low, no filament in the tube, screen at rest. */
    rest() {
      api.door(0);
      api.head(PARK_AT[0], PARK_AT[1]);
      api.bed(150);
      api.feed(0);
      api.purge(0);
      api.screen({ title: 'Ready', line: 'External spool', buttons: ['Load', 'Unload'], sel: null });
    },
    /** Door open by a, 0..1 (110 degrees at 1). */
    door(a) {
      door.rotation.y = -1.92 * a;
    },
    /** Toolhead over printer x, z in mm (the nozzle's position). */
    head(x, z) {
      gantry.position.z = z * MM;
      head.position.x = x * MM;
      state.hx = x;
      state.hz = z;
      ptfe.setPath(ctrl(x, z), `${x.toFixed(1)},${z.toFixed(1)}`);
      ptfe.show(0, 1);
      api.feed(state.feed ?? 0);
    },
    /** Bed top at height y mm. */
    bed(y) {
      bed.position.y = y * MM;
      state.bed = y;
    },
    /**
     * Filament in the printer: 0 none, 0..1 along the PTFE tube to the toolhead, 1..2 down through the extruder to
     * the nozzle tip.
     */
    feed(f) {
      state.feed = f;
      const hx = state.hx;
      const hz = state.hz;
      const path = [...ctrl(hx, hz), v3(hx, GY - 10, hz - 1), v3(hx, NOZZLE + 6, hz), v3(hx, NOZZLE, hz)];
      feed.setPath(path, `${hx.toFixed(1)},${hz.toFixed(1)}`);
      // fraction of the strand where the tube part ends
      const tubeLen = ptfe.length;
      const all = feed.length;
      const g = f <= 1 ? (f * tubeLen) / all : (tubeLen + (f - 1) * (all - tubeLen)) / all;
      feed.show(0, g);
      tip.visible = f > 0.001;
      if (tip.visible) feed.at(g, tip.position);
    },
    /** Purged PETG hanging from the nozzle, 0..1 (about 45 mm at 1). */
    purge(p) {
      if (p <= 0.001) {
        purge.mesh.visible = false;
        return;
      }
      const x = state.hx;
      const z = state.hz;
      const pts = [];
      for (let i = 0; i <= 8; i++) {
        const s = i / 8;
        pts.push(v3(x + 3.5 * Math.sin(s * 5.2) * s, NOZZLE - s * 45, z + 3 * Math.cos(s * 4.1) * s - 1.5 * s));
      }
      purge.setPath(pts, 'purge');
      purge.show(0, p);
    },
    screen(s) {
      const key = JSON.stringify(s);
      if (key === state.screenKey) return;
      state.screenKey = key;
      drawScreen(screenTex.g, screenTex.c.width, screenTex.c.height, s);
      screenTex.t.needsUpdate = true;
    },
    /** World position of the filament tip, for a label. */
    tip: () => tip,
  };
  root.userData.p1s = api;
  api.rest();
  return root;
}

/**
 * The leftover PETG: a loose coil of about 2 m lying on the bench behind the printer, its end either lying loose
 * or led up into the PTFE inlet. route(r) blends the end from loose (0) to led in (1).
 */
export function petgCoil() {
  const root = new Group();
  root.name = 'PETG coil';
  const strand = new Strand(0.875 * MM, 520, 8, MATS.petg);
  const end = mesh(new SphereGeometry(0.875 * MM, 12, 8), MATS.petg);
  root.add(strand.mesh, end);
  const C = [-138, -326]; // coil centre on the bench, behind the printer's back left
  const turns = 3.6;
  const coil = [];
  for (let i = 0; i <= turns * 28; i++) {
    const a = (i / 28) * Math.PI * 2 + 0.4;
    const r = 58 + 6 * (i / (turns * 28));
    coil.push(v3(C[0] + r * Math.cos(a), 1.1 + 1.6 * (i / (turns * 28)) + 0.4 * Math.sin(a * 3), C[1] + r * Math.sin(a)));
  }
  const last = coil[coil.length - 1];
  const lx = last.x / MM;
  const lz = last.z / MM;
  // the end: lying loose on the bench, or led up the back of the printer into the inlet (same number of points)
  const loose = [
    [lx + 30, 2.4, lz + 12],
    [lx + 70, 2.0, lz + 8],
    [lx + 110, 1.6, lz - 6],
    [lx + 150, 1.2, lz - 20],
    [lx + 182, 1.0, lz - 26],
    [lx + 205, 1.0, lz - 28],
  ];
  const led = [
    [lx + 22, 30, lz + 22],
    [-120, 160, -(D2 + 40)],
    [-128, 330, -(D2 + 24)],
    [-132, 420, -(D2 + 14)],
    [-122, 432, -(D2 + 12)],
    [-104, 432, -(D2 + 12)],
  ];
  const api = {
    route(r) {
      const pts = coil.concat(loose.map((p, i) => v3(p[0] + (led[i][0] - p[0]) * r, p[1] + (led[i][1] - p[1]) * r, p[2] + (led[i][2] - p[2]) * r)));
      strand.setPath(pts, r.toFixed(3));
      strand.show(0, 1);
      strand.at(1, end.position);
    },
    /** Where the loose end lies (for the snip close-up), in mm. */
    looseEnd: () => loose[loose.length - 1],
    end: () => end,
  };
  root.userData.coil = api;
  api.route(0);
  return root;
}

/** A 6 mm offcut of filament, along x, for the snip. */
export function offcut() {
  const m = mesh(new CylinderGeometry(0.875 * MM, 0.875 * MM, 6 * MM, 12), MATS.petg);
  m.rotation.z = Math.PI / 2;
  const g = new Group();
  g.add(m);
  return g;
}
