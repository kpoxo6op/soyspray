// Small objects drawn in code: things the Blender model does not have (scale, cup, spool, print bed) and the
// pieces the soldering lessons animate (solder wire, joints, wires, heatshrink). Sizes are real, in metres.

import {
  AdditiveBlending,
  BoxGeometry,
  CanvasTexture,
  CatmullRomCurve3,
  CylinderGeometry,
  DoubleSide,
  Group,
  LatheGeometry,
  Mesh,
  MeshBasicMaterial,
  MeshStandardMaterial,
  PlaneGeometry,
  SphereGeometry,
  SRGBColorSpace,
  TorusGeometry,
  TubeGeometry,
  Vector2,
  Vector3,
} from 'three';
import { RoundedBoxGeometry } from 'three/examples/jsm/geometries/RoundedBoxGeometry.js';

const MM = 0.001;
const std = (color, roughness = 0.5, metalness = 0, extra = {}) => new MeshStandardMaterial({ color, roughness, metalness, ...extra });

export const MAT = {
  tin: std(0xe6e9ec, 0.14, 0.9),
  tinDull: std(0x9a9c9e, 0.6, 0.85),
  copper: std(0xc9773f, 0.28, 1),
  paper: std(0xf6f4ef, 0.85, 0, { side: DoubleSide }),
  steel: std(0xc4c8cc, 0.25, 1),
  dark: std(0x1d1f22, 0.55),
  plastic: std(0x2a2c30, 0.45),
  brass: std(0xc8a24a, 0.3, 1),
  red: std(0xc3261f, 0.42),
  blue: std(0x2c62c9, 0.42),
  black: std(0x18191b, 0.45),
  white: std(0xf3f1ec, 0.5),
  foam: std(0x5a5f66, 0.92),
  tape: std(0xe8dcb8, 0.8),
  pcb: std(0x1e7a3a, 0.32),
  gold: std(0xe2b860, 0.22, 1),
};

function mesh(geo, mat, cast = true) {
  const m = new Mesh(geo, mat);
  m.castShadow = cast;
  m.receiveShadow = true;
  return m;
}

function textCanvas(w, h) {
  const c = document.createElement('canvas');
  c.width = w;
  c.height = h;
  const t = new CanvasTexture(c);
  t.colorSpace = SRGBColorSpace;
  return { c, g: c.getContext('2d'), t };
}

/** A 200 g x 0.01 g pocket scale with a working display: setReading('52.40'). */
export function pocketScale() {
  const g = new Group();
  const body = mesh(new RoundedBoxGeometry(64 * MM, 16 * MM, 100 * MM, 3, 3 * MM), std(0x2b2d31, 0.4, 0.2));
  body.position.y = 8 * MM;
  const pan = mesh(new RoundedBoxGeometry(58 * MM, 2 * MM, 58 * MM, 2, 1 * MM), MAT.steel);
  pan.position.set(0, 17 * MM, -16 * MM);
  const lcdTex = textCanvas(256, 96);
  const lcd = mesh(new PlaneGeometry(44 * MM, 16 * MM), new MeshBasicMaterial({ map: lcdTex.t, toneMapped: false }), false);
  lcd.rotation.x = -Math.PI / 2;
  lcd.position.set(0, 16.2 * MM, 30 * MM);
  for (const x of [-18, 0, 18]) {
    const b = mesh(new CylinderGeometry(3.4 * MM, 3.4 * MM, 1.2 * MM, 20), std(0x6b6f76, 0.5));
    b.position.set(x * MM, 16.2 * MM, 43 * MM);
    g.add(b);
  }
  g.add(body, pan, lcd);
  let shown = null;
  g.userData.setReading = (text) => {
    if (text === shown) return;
    shown = text;
    const { g: c, t } = lcdTex;
    c.fillStyle = '#a9b59a';
    c.fillRect(0, 0, 256, 96);
    c.fillStyle = '#1b1f1a';
    c.font = '600 58px ui-monospace, SFMono-Regular, Menlo, Consolas, monospace';
    c.textAlign = 'right';
    c.textBaseline = 'middle';
    c.fillText(text, 214, 52);
    c.font = '600 26px ui-monospace, SFMono-Regular, Menlo, Consolas, monospace';
    c.fillText('g', 246, 60);
    t.needsUpdate = true;
  };
  g.userData.setReading('0.00');
  g.userData.panTop = 18 * MM;
  g.userData.panZ = -16 * MM;
  return g;
}

/** A paper cup, 80 mm tall, open at the top. */
export function paperCup() {
  const pts = [
    [0, 0], [26, 0], [26.4, 1.5], [36, 80], [37.2, 80.5], [37, 81.5], [35.6, 80.6], [26, 2], [0, 2],
  ].map(([r, y]) => new Vector2(r * MM, y * MM));
  const g = new Group();
  g.add(mesh(new LatheGeometry(pts, 48), MAT.paper));
  return g;
}

/** A 1 kg filament spool, 200 mm across and 67 mm wide, lying on one flange. */
export function filamentSpool() {
  const g = new Group();
  const flange = std(0x1c1d20, 0.35, 0, { transparent: true, opacity: 0.92 });
  for (const y of [0, 64]) {
    const f = mesh(new CylinderGeometry(100 * MM, 100 * MM, 3 * MM, 72), flange);
    f.position.y = (y + 1.5) * MM;
    g.add(f);
  }
  const wind = mesh(new CylinderGeometry(84 * MM, 84 * MM, 61 * MM, 72, 1, true), std(0xf2efe7, 0.7));
  wind.position.y = 33.5 * MM;
  const top = mesh(new TorusGeometry(64 * MM, 20 * MM, 2, 72), std(0xf2efe7, 0.7));
  top.rotation.x = Math.PI / 2;
  top.scale.z = 0.05;
  top.position.y = 64 * MM;
  const hub = mesh(new CylinderGeometry(27 * MM, 27 * MM, 67 * MM, 48, 1, true), flange);
  hub.position.y = 33.5 * MM;
  g.add(wind, top, hub);
  return g;
}

/** The P1S textured PEI plate (256 mm square) with a speckled bronze finish. */
export function buildPlate() {
  const g = new Group();
  const tex = textCanvas(512, 512);
  const c = tex.g;
  c.fillStyle = '#3b3328';
  c.fillRect(0, 0, 512, 512);
  let seed = 11;
  const rnd = () => ((seed = (seed * 48271) % 2147483647) / 2147483647);
  for (let i = 0; i < 26000; i++) {
    const v = 40 + rnd() * 70;
    c.fillStyle = `rgba(${v + 40},${v + 24},${v},${0.35 + rnd() * 0.4})`;
    c.fillRect(rnd() * 512, rnd() * 512, 1.4, 1.4);
  }
  c.strokeStyle = 'rgba(210,190,150,0.35)';
  c.lineWidth = 3;
  c.strokeRect(8, 8, 496, 496);
  tex.t.anisotropy = 4;
  const plate = mesh(new BoxGeometry(257 * MM, 1.2 * MM, 257 * MM), [
    std(0x2a2620, 0.6), std(0x2a2620, 0.6), new MeshStandardMaterial({ map: tex.t, roughness: 0.82, metalness: 0.25 }),
    std(0x2a2620, 0.6), std(0x2a2620, 0.6), std(0x2a2620, 0.6),
  ]);
  plate.position.y = 0.6 * MM;
  g.add(plate);
  g.userData.top = 1.2 * MM;
  return g;
}

/** The printer's hot end, cut down to what matters here: heater block, heat break and a glowing brass nozzle. */
export function toolhead() {
  const g = new Group();
  const brk = mesh(new CylinderGeometry(2.2 * MM, 2.2 * MM, 60 * MM, 16), std(0x8d9196, 0.3, 0.9));
  brk.position.y = 41 * MM;
  const block = mesh(new BoxGeometry(14 * MM, 7 * MM, 12 * MM), std(0x8d9196, 0.35, 0.8));
  block.position.y = 7.5 * MM;
  const nozzle = mesh(new CylinderGeometry(0.9 * MM, 3 * MM, 4 * MM, 20), MAT.brass);
  nozzle.position.y = 2 * MM;
  const glow = new Mesh(new SphereGeometry(0.9 * MM, 12, 8), new MeshBasicMaterial({ color: 0xffb066, toneMapped: false }));
  g.add(brk, block, nozzle, glow);
  return g;
}

/** Solder wire held in the hand: a gentle curve ending at the origin, pointing along -x. */
export function solderWire(length = 60) {
  const pts = [];
  for (let i = 0; i <= 12; i++) {
    const s = i / 12;
    pts.push(new Vector3(s * length * MM, s * s * 12 * MM, -s * s * 6 * MM));
  }
  const g = new Group();
  g.add(mesh(new TubeGeometry(new CatmullRomCurve3(pts), 40, 0.36 * MM, 8), std(0xd9dde0, 0.3, 0.6)));
  return g;
}

// Joint profiles from parts_v3.solder_joint (radius, height in mm), seen from the solder side.
const JOINTS = {
  good: [[0.9, 0], [0.83, 0.15], [0.56, 0.45], [0.5, 0.9], [0.38, 1.4], [0, 1.55]],
  cold: [[0.5, 0], [0.77, 0.25], [0.86, 0.7], [0.72, 1.2], [0.36, 1.6], [0, 1.75]],
  blob: [[0.81, 0], [1.22, 0.4], [1.35, 1.1], [1.13, 1.8], [0.54, 2.3], [0, 2.45]],
};

/** A solder joint. Its scale.y and scale.x grow from 0 to 1 while it forms. */
export function joint(kind = 'good', size = 1.3) {
  const pts = JOINTS[kind].map(([r, y]) => new Vector2(r * size * MM, y * size * MM));
  pts.unshift(new Vector2(0, 0));
  return mesh(new LatheGeometry(pts, 32), kind === 'cold' ? MAT.tinDull : MAT.tin);
}

/** Two pads joined by a smear of solder: the bridge to soak up with braid. */
export function bridge(pitch = 2.54, size = 1.3) {
  const g = new Group();
  for (const s of [-0.5, 0.5]) {
    const j = joint('blob', size * 0.9);
    j.position.x = s * pitch * MM;
    g.add(j);
  }
  const web = mesh(new CylinderGeometry(1.1 * MM, 1.1 * MM, pitch * MM, 16), MAT.tin);
  web.rotation.z = Math.PI / 2;
  web.position.y = 1.1 * MM;
  web.scale.z = 0.6;
  g.add(web);
  return g;
}

/** A 1/4 W resistor standing over two holes 10.16 mm apart, leads through the board. */
export function resistor() {
  const g = new Group();
  const body = mesh(new CylinderGeometry(1.25 * MM, 1.25 * MM, 6.2 * MM, 20), std(0xc9b18a, 0.55));
  body.rotation.z = Math.PI / 2;
  body.position.y = 3.2 * MM;
  g.add(body);
  [0x6b3f1f, 0x111111, 0xc3261f, 0xd4af37].forEach((c, i) => {
    const band = mesh(new CylinderGeometry(1.28 * MM, 1.28 * MM, 0.55 * MM, 20), std(c, 0.5));
    band.rotation.z = Math.PI / 2;
    band.position.set((-2.1 + i * 1.25 + (i === 3 ? 0.5 : 0)) * MM, 3.2 * MM, 0);
    g.add(band);
  });
  for (const s of [-1, 1]) {
    const pts = [new Vector3(s * 3.1 * MM, 3.2 * MM, 0), new Vector3(s * 4.6 * MM, 3.1 * MM, 0), new Vector3(s * 5.08 * MM, 2 * MM, 0), new Vector3(s * 5.08 * MM, -3.5 * MM, 0)];
    g.add(mesh(new TubeGeometry(new CatmullRomCurve3(pts), 16, 0.3 * MM, 8), MAT.steel));
  }
  return g;
}

/** A 28 AWG wire along +x from 0 to `length` mm, with `strip` mm of bare copper at the far end. */
export function wire(color = 'red', length = 40, strip = 4) {
  const g = new Group();
  const ins = mesh(new CylinderGeometry(0.45 * MM, 0.45 * MM, (length - strip) * MM, 12), MAT[color] || MAT.red);
  ins.rotation.z = Math.PI / 2;
  ins.position.x = ((length - strip) / 2) * MM;
  const cu = mesh(new CylinderGeometry(0.2 * MM, 0.2 * MM, strip * MM, 8), MAT.copper);
  cu.rotation.z = Math.PI / 2;
  cu.position.x = (length - strip / 2) * MM;
  g.add(ins, cu);
  g.userData.copper = cu;
  return g;
}

/** Heatshrink tube along x, centred on the origin. */
export function heatshrink(length = 12, radius = 1.5, color = 'black') {
  return mesh(new CylinderGeometry(radius * MM, radius * MM, length * MM, 20, 1, false), color === 'white' ? MAT.white : MAT.black);
}

/** A straight thread between two points; call setEnds(a, b) each frame. */
export function thread() {
  const m = mesh(new CylinderGeometry(0.3 * MM, 0.3 * MM, 1, 6), std(0xf2f0ea, 0.8), false);
  const up = new Vector3(0, 1, 0);
  const d = new Vector3();
  m.userData.setEnds = (a, b) => {
    d.subVectors(b, a);
    const len = d.length();
    m.position.copy(a).addScaledVector(d, 0.5);
    m.scale.set(1, Math.max(len, 1e-5), 1);
    m.quaternion.setFromUnitVectors(up, d.normalize());
  };
  return m;
}

/** A width measurement drawn across something: a bright line with end ticks, centred on the origin along x. */
export function dimension(length) {
  const g = new Group();
  const m = new MeshBasicMaterial({ color: 0xffd28a, toneMapped: false });
  const line = new Mesh(new BoxGeometry(length, 0.0015, 0.0015), m);
  g.add(line);
  for (const s of [-1, 1]) {
    const tick = new Mesh(new BoxGeometry(0.0015, 0.05, 0.0015), m);
    tick.position.x = (s * length) / 2;
    g.add(tick);
  }
  return g;
}

/** A bare lamp bulb to hold the printed shell against. */
export function lamp() {
  const g = new Group();
  const bulb = new Mesh(new SphereGeometry(30 * MM, 32, 16), new MeshBasicMaterial({ color: 0xfff1d6, toneMapped: false }));
  const neck = mesh(new CylinderGeometry(14 * MM, 16 * MM, 26 * MM, 24), std(0xb9bdc2, 0.3, 0.9));
  neck.position.y = -36 * MM;
  g.add(bulb, neck);
  return g;
}

/** A foam block for the thrust test. */
export function block(w = 50, h = 30, d = 40) {
  const m = mesh(new RoundedBoxGeometry(w * MM, h * MM, d * MM, 2, 2 * MM), MAT.foam);
  m.position.y = (h / 2) * MM;
  const g = new Group();
  g.add(m);
  return g;
}

/** Streaks of air leaving a fan upwards. setFlow(phase, strength). */
export function airflow(radius = 15, height = 90, count = 14) {
  const g = new Group();
  const mat = new MeshBasicMaterial({ color: 0xcfe6ff, transparent: true, opacity: 0, blending: AdditiveBlending, depthWrite: false, side: DoubleSide });
  const streaks = [];
  for (let i = 0; i < count; i++) {
    const a = (i / count) * Math.PI * 2;
    const r = (0.35 + 0.6 * ((i * 7) % count) / count) * radius * MM;
    const s = new Mesh(new PlaneGeometry(0.9 * MM, 16 * MM), mat);
    s.position.set(Math.cos(a) * r, 0, Math.sin(a) * r);
    s.rotation.y = -a;
    s.userData.offset = (i * 0.37) % 1;
    streaks.push(s);
    g.add(s);
  }
  g.userData.setFlow = (phase, strength) => {
    mat.opacity = 0.85 * strength;
    for (const s of streaks) {
      const k = (phase + s.userData.offset) % 1;
      s.position.y = k * height * MM;
      s.scale.y = 0.6 + k;
    }
  };
  return g;
}
