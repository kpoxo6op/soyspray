// Procedural equipment models. Local frame matches the rack: x right, y rear (front face at -y), z up.
// Sizes come from src/layout.js; detail is drawn into canvas textures so nothing is fetched at runtime.

import {
  CanvasTexture,
  CylinderGeometry,
  Group,
  Mesh,
  MeshStandardMaterial,
  PlaneGeometry,
  SRGBColorSpace,
} from 'three';
import { RoundedBoxGeometry } from 'three/examples/jsm/geometries/RoundedBoxGeometry.js';
import { addPorts, buildExtraDevice } from './hardware.js';

const PX_PER_MM = 6;

function canvasFor(wMm, hMm, scale = PX_PER_MM) {
  const c = document.createElement('canvas');
  c.width = Math.round(wMm * scale);
  c.height = Math.round(hMm * scale);
  const g = c.getContext('2d');
  g.scale(scale, scale); // draw in millimetres
  return { c, g };
}

function texture(c, anisotropy) {
  const t = new CanvasTexture(c);
  t.colorSpace = SRGBColorSpace;
  t.anisotropy = anisotropy;
  return t;
}

function roundRect(g, x, y, w, h, r) {
  g.beginPath();
  g.moveTo(x + r, y);
  g.arcTo(x + w, y, x + w, y + h, r);
  g.arcTo(x + w, y + h, x, y + h, r);
  g.arcTo(x, y + h, x, y, r);
  g.arcTo(x, y, x + w, y, r);
  g.closePath();
}

function rj45(g, x, y, w = 11.5, h = 9.5, body = '#1a1a1a') {
  roundRect(g, x, y, w, h, 0.8);
  g.fillStyle = body;
  g.fill();
  g.fillStyle = '#0b0b0b';
  g.fillRect(x + 1.2, y + 1.2, w - 2.4, h - 3.2);
  g.fillRect(x + w / 2 - 2.2, y + h - 2.4, 4.4, 1.6);
  g.fillStyle = '#b8964a';
  for (let i = 0; i < 8; i++) g.fillRect(x + 2 + i * ((w - 4) / 8), y + 1.4, 0.55, 2.2);
}

function usbA(g, x, y) {
  roundRect(g, x, y, 13, 5.6, 0.6);
  g.fillStyle = '#2a2b2e';
  g.fill();
  g.fillStyle = '#0c0c0d';
  g.fillRect(x + 1, y + 1, 11, 3.6);
  g.fillStyle = '#3f6fd1';
  g.fillRect(x + 1.6, y + 1.4, 9.8, 1.3);
}

// ---------------------------------------------------------------- panels

function m920qFront(label) {
  const W = 179, H = 37;
  const { c, g } = canvasFor(W, H, 7);
  const bg = g.createLinearGradient(0, 0, 0, H);
  bg.addColorStop(0, '#1d1e21');
  bg.addColorStop(1, '#141517');
  g.fillStyle = bg;
  g.fillRect(0, 0, W, H);
  // perforated intake grille on the right half
  g.fillStyle = '#060607';
  for (let x = 92; x < W - 5; x += 2.6) {
    for (let y = 5; y < H - 4; y += 2.6) {
      g.beginPath();
      g.arc(x + ((Math.round(y / 2.6) % 2) * 1.3), y, 0.75, 0, Math.PI * 2);
      g.fill();
    }
  }
  // red Lenovo badge (front left, as in the fit-study model)
  g.fillStyle = '#d0281f';
  g.fillRect(5, 22, 31, 7);
  g.fillStyle = '#ffffff';
  g.font = '600 4.6px system-ui, sans-serif';
  g.textBaseline = 'middle';
  g.fillText('Lenovo', 11.5, 25.6);
  // power button, audio jacks, USB ports
  g.strokeStyle = '#5b5d62';
  g.lineWidth = 0.6;
  g.beginPath();
  g.arc(10, 11, 3.2, 0, Math.PI * 2);
  g.stroke();
  g.beginPath();
  g.arc(10, 11, 1.4, -Math.PI * 0.35, Math.PI * 1.35);
  g.stroke();
  g.fillStyle = '#060607';
  for (const x of [20, 27]) {
    g.beginPath();
    g.arc(x, 11, 1.6, 0, Math.PI * 2);
    g.fill();
  }
  usbA(g, 36, 8.2);
  usbA(g, 52, 8.2);
  g.fillStyle = '#8c8f95';
  g.font = '500 3.2px system-ui, sans-serif';
  g.fillText('ThinkCentre', 40, 25.6);
  // node label sticker
  roundRect(g, 66, 20.5, 20, 8.5, 1);
  g.fillStyle = '#f2f1ec';
  g.fill();
  g.fillStyle = '#111';
  g.font = '700 4.4px ui-monospace, Menlo, monospace';
  g.textAlign = 'center';
  g.fillText(label, 76, 25);
  return c;
}

function switchFront() {
  const W = 112, H = 25;
  const { c, g } = canvasFor(W, H, 8);
  g.fillStyle = '#ecebe7';
  g.fillRect(0, 0, W, H);
  for (let i = 0; i < 5; i++) {
    const x = 12 + i * 17;
    rj45(g, x, 9.5, 12.5, 10, '#d9d8d3');
    g.fillStyle = i < 4 ? '#3ad36b' : '#9aa09c';
    g.beginPath();
    g.arc(x + 6.2, 5.6, 0.9, 0, Math.PI * 2);
    g.fill();
  }
  g.fillStyle = '#c73a2f';
  g.fillRect(W - 6, 0, 6, H);
  return c;
}

function routerFront() {
  const W = 148, H = 30;
  const { c, g } = canvasFor(W, H, 7);
  const bg = g.createLinearGradient(0, 0, 0, H);
  bg.addColorStop(0, '#2d64b0');
  bg.addColorStop(1, '#214e8f');
  g.fillStyle = bg;
  g.fillRect(0, 0, W, H);
  g.fillStyle = 'rgba(0,0,0,0.25)';
  g.fillRect(0, H - 2, W, 2);
  rj45(g, 14, 10, 14, 11.5);
  rj45(g, 32, 10, 14, 11.5);
  usbA(g, 52, 13);
  roundRect(g, 70, 14, 9, 3.4, 1.6);
  g.fillStyle = '#0d0d0e';
  g.fill();
  for (let i = 0; i < 3; i++) {
    g.fillStyle = ['#4fe37e', '#f2c14e', '#e8eef7'][i];
    g.beginPath();
    g.arc(90 + i * 6, 15.7, 1, 0, Math.PI * 2);
    g.fill();
  }
  g.fillStyle = 'rgba(255,255,255,0.78)';
  g.font = '700 5px system-ui, sans-serif';
  g.textBaseline = 'middle';
  g.fillText('OpenWrt', 112, 16);
  return c;
}

function boardTop() {
  const W = 55, H = 205;
  const { c, g } = canvasFor(W, H, 6);
  g.fillStyle = '#f1f0eb';
  g.fillRect(0, 0, W, H);
  for (let i = 0; i < 4; i++) {
    const y = 26 + i * 44;
    roundRect(g, 10, y, 31, 31, 6);
    g.fillStyle = '#e4e2dc';
    g.fill();
    g.strokeStyle = 'rgba(0,0,0,0.08)';
    g.lineWidth = 0.6;
    g.stroke();
    g.fillStyle = '#26262a';
    const cx = 25.5, cy = y + 14;
    for (const s of [-1, 1]) {
      g.save();
      g.translate(cx + s * 5.5, cy - 2);
      g.rotate(s * 0.52);
      g.fillRect(-0.9, -3.4, 1.8, 6.8);
      g.restore();
    }
    g.fillRect(cx - 0.9, cy + 5, 1.8, 6);
    roundRect(g, 44, y + 10, 7, 11, 1.2);
    g.fillStyle = '#d9d6cf';
    g.fill();
  }
  return c;
}

function touroTop() {
  const W = 78, H = 112;
  const { c, g } = canvasFor(W, H, 5);
  g.fillStyle = '#1e1f22';
  g.fillRect(0, 0, W, H);
  g.fillStyle = 'rgba(210,214,220,0.75)';
  g.font = '600 7px system-ui, sans-serif';
  g.textAlign = 'center';
  g.textBaseline = 'middle';
  g.fillText('TOURO', W / 2, H * 0.32);
  return c;
}

function brickTop() {
  const W = 46, H = 112;
  const { c, g } = canvasFor(W, H, 5);
  g.fillStyle = '#121315';
  g.fillRect(0, 0, W, H);
  roundRect(g, 8, 34, 30, 44, 2);
  g.fillStyle = '#18191c';
  g.fill();
  g.fillStyle = 'rgba(150,152,158,0.55)';
  g.font = '600 4.2px system-ui, sans-serif';
  g.textAlign = 'center';
  g.textBaseline = 'middle';
  g.save();
  g.translate(W / 2, 56);
  g.rotate(-Math.PI / 2);
  g.fillText('Lenovo', 0, 0);
  g.restore();
  return c;
}

// ---------------------------------------------------------------- builders

function box(size, radius, material) {
  const [w, d, h] = size;
  const geo = new RoundedBoxGeometry(w, d, h, 3, radius);
  const m = new Mesh(geo, material);
  m.castShadow = true;
  m.receiveShadow = true;
  return m;
}

function decal(w, h, map, face, offset, materialOpts = {}) {
  const geo = new PlaneGeometry(w, h);
  if (face === 'front') geo.rotateX(Math.PI / 2);
  const mat = new MeshStandardMaterial({
    map,
    roughness: 0.55,
    metalness: 0,
    polygonOffset: true,
    polygonOffsetFactor: -2,
    polygonOffsetUnits: -2,
    ...materialOpts,
  });
  const m = new Mesh(geo, mat);
  m.position.set(...offset);
  m.receiveShadow = true;
  return m;
}

/**
 * Build one device. Returns { object, materials } where materials receive the timeline's
 * opacity and highlight values.
 */
export function buildDevice(spec, anisotropy = 4) {
  if (['board', 'spareBoard', 'deck', 'psuSwitch', 'psuRouter', 'wallSocket', 'powerline', 'zigbeeEnd', 'zigbee'].includes(spec.model)) return buildExtraDevice(spec);
  const [w, d, h] = spec.size;
  const g = new Group();
  const mats = [];
  const mat = (opts) => {
    const m = new MeshStandardMaterial(opts);
    mats.push(m);
    return m;
  };
  const addDecal = (m) => {
    mats.push(m.material);
    g.add(m);
  };

  switch (spec.model) {
    case 'm920q': {
      g.add(box(spec.size, 2.2, mat({ color: 0x1b1c1f, metalness: 0.35, roughness: 0.46 })));
      addDecal(decal(w - 4, h - 3, texture(m920qFront(spec.label), anisotropy), 'front', [0, -d / 2 - 0.25, 0], { roughness: 0.5, metalness: 0.2 }));
      break;
    }
    case 'brick': {
      g.add(box(spec.size, 4, mat({ color: 0x131416, metalness: 0.05, roughness: 0.72 })));
      addDecal(decal(w - 7, d - 7, texture(brickTop(), anisotropy), 'top', [0, 0, h / 2 + 0.25], { roughness: 0.7 }));
      break;
    }
    case 'switch': {
      g.add(box(spec.size, 3, mat({ color: 0xe9e8e3, metalness: 0, roughness: 0.42 })));
      break;
    }
    case 'seagate': {
      g.add(box(spec.size, 4, mat({ color: 0x17181a, metalness: 0.15, roughness: 0.32 })));
      break;
    }
    case 'touro': {
      g.add(box(spec.size, 4, mat({ color: 0x1f2023, metalness: 0.05, roughness: 0.68 })));
      addDecal(decal(w - 8, d - 8, texture(touroTop(), anisotropy), 'top', [0, 0, h / 2 + 0.25], { roughness: 0.66 }));
      break;
    }
    case 'router': {
      g.add(box(spec.size, 4, mat({ color: 0x2457a0, metalness: 0.62, roughness: 0.36 })));
      break;
    }
    case 'board': {
      g.add(box(spec.size, 6, mat({ color: 0xf0efea, metalness: 0, roughness: 0.48 })));
      addDecal(decal(w - 6, d - 6, texture(boardTop(), anisotropy), 'top', [0, 0, h / 2 + 0.25], { roughness: 0.5 }));
      break;
    }
    case 'antenna': {
      const black = mat({ color: 0x111214, metalness: 0.1, roughness: 0.55 });
      const knuckle = new Mesh(new CylinderGeometry(5, 5, 11, 20), black);
      knuckle.rotation.z = Math.PI / 2;
      const rod = new Mesh(new CylinderGeometry(3.4, 4.6, 112, 20), black);
      rod.rotation.x = Math.PI / 2; // cylinder axis (Y) -> +Z
      rod.position.z = 62;
      const tip = new Mesh(new CylinderGeometry(0.1, 3.4, 6, 20), black);
      tip.rotation.x = Math.PI / 2;
      tip.position.z = 121;
      for (const m of [knuckle, rod, tip]) {
        m.castShadow = true;
        g.add(m);
      }
      break;
    }
    default:
      throw new Error(`unknown device model ${spec.model}`);
  }
  if (spec.model === 'brick') {
    const stub = new Mesh(new CylinderGeometry(3, 3, 12, 16), mat({ color: 0x171819, roughness: 0.6 }));
    stub.position.y = -62; g.add(stub);
  }
  addPorts(g, spec.model, mats);
  return { object: g, materials: mats };
}
