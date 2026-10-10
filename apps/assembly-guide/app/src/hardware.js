import { BoxGeometry, CylinderGeometry, ExtrudeGeometry, Group, Mesh, MeshStandardMaterial, Shape } from 'three';
import { RoundedBoxGeometry } from 'three/examples/jsm/geometries/RoundedBoxGeometry.js';
import { CONNECTORS, PORTS } from './ports.js';
import { basisQuat } from './math.js';

const DARK = 0x101317;
const paint = (color, metalness = 0.05) => new MeshStandardMaterial({ color, roughness: 0.43, metalness });
function block(group, size, p, material, round = 0) {
  const m = new Mesh(round ? new RoundedBoxGeometry(...size, 2, round) : new BoxGeometry(...size), material);
  m.position.set(...p); m.castShadow = true; m.receiveShadow = true; group.add(m); return m;
}
function slots(g) {
  const dark = paint(DARK);
  for (const sign of [-1, 1]) {
    const m = block(g, [1.8, 0.8, 7], [sign * 6.5, 0.5, 3.5], dark); m.rotation.y = sign * 0.52;
  }
  block(g, [1.8, 0.8, 7], [0, 0.5, -7], dark);
}
export function addPorts(object, model, materials) {
  for (const [id, p] of Object.entries(PORTS[model] || {})) {
    if (p.type === 'fixed') continue;
    const g = new Group(); g.position.set(...p.pos); g.quaternion.set(...basisQuat(p.n, p.u));
    if (p.type === 'nz') {
      const disk = new Mesh(new CylinderGeometry(17, 17, 0.9, 32), paint(0xe3e2de)); disk.position.y = 0.2; g.add(disk); slots(g);
    } else {
      const dims = CONNECTORS[p.type] || { w: 14, h: 8 };
      block(g, [dims.w + 1.5, 0.6, dims.h + 1], [0, 0.2, 0], paint(0x777b80, 0.7));
      block(g, [dims.w - 0.8, 0.8, dims.h - 0.8], [0, 0.65, 0], paint(DARK));
      if (p.type === 'usbA') block(g, [10, 0.8, 1.7], [0, 1.1, -0.8], paint(id.includes('G2') ? 0x252627 : 0x2674bc));
      if (p.type === 'slim') block(g, [9, 0.8, 3.4], [0, 1.1, 0], paint(0xf0c037));
      if (p.type === 'rj45') for (let i = 0; i < 8; i++) block(g, [0.55, 0.8, 2.5], [-4.1 + i * 1.15, 1.1, 2], paint(0xc8a153, 0.8));
    }
    object.add(g); g.traverse((m) => { if (m.isMesh) materials.push(m.material); });
  }
}
export function buildConnector(type, colour = DARK) {
  const g = new Group(), c = CONNECTORS[type], rubber = paint(colour), metal = paint(0xb9c0c6, 0.85);
  block(g, [c.w, c.len - c.depth, c.h], [0, c.depth + (c.len - c.depth) / 2, 0], rubber, 1.2);
  if (type === 'nz') {
    for (const sign of [-1, 1]) { const pin = block(g, [1.8, c.depth, 7], [sign * 6.5, c.depth / 2, 3.5], metal); pin.rotation.y = sign * 0.52; }
    block(g, [1.8, c.depth, 7], [0, c.depth / 2, -7], metal);
  } else if (type === 'rj45') {
    block(g, [11.5, c.depth, 8], [0, c.depth / 2, 0], paint(0x909c9c, 0.35), 0.5);
    for (let i = 0; i < 8; i++) block(g, [0.5, 7, 0.5], [-4.1 + i * 1.15, 4, 4.2], paint(0xd9b553, 0.8));
    block(g, [3, 12, 0.7], [0, 17, 5.8], rubber);
  } else block(g, [c.w * 0.78, Math.max(1, c.depth), c.h * 0.58], [0, c.depth / 2, 0], type === 'slim' ? paint(0xe5b926, 0.4) : type === 'c5' ? rubber : metal, 0.5);
  return g;
}
export function buildExtraDevice(spec) {
  const g = new Group(), materials = [];
  const mat = paint(['powerline', 'wallSocket', 'psuSwitch'].includes(spec.model) ? 0xefeee9 : 0x191c20); materials.push(mat);
  if (spec.model === 'board') {
    const s = new Shape(); s.moveTo(-45, -27.5); s.lineTo(45, -27.5); s.lineTo(15, 27.5); s.lineTo(-15, 27.5); s.closePath();
    const geo = new ExtrudeGeometry(s, { depth: 250, bevelEnabled: false, steps: 1 }); geo.rotateX(Math.PI / 2); geo.translate(0, 125, 0);
    const m = new Mesh(geo, paint(0xefeee9)); g.add(m); materials.push(m.material);
    block(g, [18, 22, 2], [0, -105, 28], paint(0xc13c31), 1);
    const stub = new Mesh(new CylinderGeometry(4, 4, 11, 16), paint(0xefeee9)); stub.position.set(0, 130.5, -14); g.add(stub);
  } else if (spec.model === 'deck') {
    block(g, [253, 209, 6], [0, 0, 0], paint(0x7c654b), 1);
    for (const x of [-111.5, 111.5]) for (const y of [-88.5, 88.5]) {
      const m = new Mesh(new CylinderGeometry(7, 7, 10, 20), paint(0x353536)); m.rotation.x = Math.PI / 2; m.position.set(x, y, -8); g.add(m);
    }
  } else {
    block(g, spec.size, [0, 0, 0], mat, 2);
    if (spec.model === 'wallSocket') for (const x of [-28, 28]) block(g, [11, 1, 6], [x, -6.6, 24], paint(0xe4e3df), 0.5);
    if (spec.model === 'powerline') {
      block(g, [13, 1, 2], [0, 21.2, 28], paint(0x61bd74));
      for (const x of [-6.5, 6.5]) block(g, [1.8, 17, 7], [x, -29.5, 32], paint(0xc9ced1, 0.8));
    }
    if (spec.model === 'zigbee') {
      block(g, [12, 12, 4.8], [0, -30, 0], paint(0xb9bec4, 0.8));
      const rod = new Mesh(new CylinderGeometry(2.8, 3.3, 98, 20), mat); rod.rotation.x = Math.PI / 2; rod.position.set(0, 25, 53); g.add(rod);
    }
    if (spec.model === 'zigbeeEnd') block(g, [13, 1, 5], [0, 20.3, 0], paint(DARK));
    if (spec.model === 'psuRouter' || spec.model === 'psuSwitch') {
      const depth = spec.size[1];
      for (const x of [-6.5, 6.5]) block(g, [1.8, 17, 7], [x, -depth / 2 - 8.5, 3.5], paint(0xc9ced1, 0.8));
      block(g, [1.8, 17, 7], [0, -depth / 2 - 8.5, -7], paint(0xc9ced1, 0.8));
    }
  }
  addPorts(g, spec.model, materials);
  g.traverse((m) => { if (m.isMesh) { m.castShadow = true; m.receiveShadow = true; if (!materials.includes(m.material)) materials.push(m.material); } });
  return { object: g, materials };
}
