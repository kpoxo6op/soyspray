// Procedural v3 equipment: the slimline board, keystone inserts, cord ties and the Zigbee dongle
// standing in its mast. Local frame as in devices.js: x right, y rear, z up.

import { BoxGeometry, CylinderGeometry, ExtrudeGeometry, Group, Matrix4, Mesh, MeshStandardMaterial, Path, Shape, Vector3 } from 'three';
import { RoundedBoxGeometry } from 'three/examples/jsm/geometries/RoundedBoxGeometry.js';

function kit() {
  const object = new Group();
  const materials = [];
  const paint = (color, metalness = 0.05, roughness = 0.45) => {
    const m = new MeshStandardMaterial({ color, metalness, roughness });
    materials.push(m);
    return m;
  };
  const block = (size, p, material, round = 0, parent = object) => {
    const geo = round ? new RoundedBoxGeometry(...size, 2, round) : new BoxGeometry(...size);
    const m = new Mesh(geo, material);
    m.position.set(...p);
    m.castShadow = true;
    m.receiveShadow = true;
    parent.add(m);
    return m;
  };
  const rod = (r0, r1, length, p, material, axis = 'z', parent = object) => {
    const m = new Mesh(new CylinderGeometry(r1, r0, length, 20), material);
    if (axis === 'z') m.rotation.x = Math.PI / 2; // cylinder axis (y) -> z
    else if (axis === 'x') m.rotation.z = Math.PI / 2;
    m.position.set(...p);
    m.castShadow = true;
    parent.add(m);
    return m;
  };
  return { object, materials, paint, block, rod };
}

/** White four-outlet board lying on its side: outlets on the -y face, earth slots towards +x. */
export function buildSlimBoard(spec) {
  const k = kit();
  const [w, d, h] = spec.size;
  const white = k.paint(0xf0efea, 0, 0.5);
  k.block(spec.size, [0, 0, 0], white, 4);
  const face = k.paint(0xe2e0da, 0, 0.55);
  const slot = k.paint(0x141519);
  for (const x of [-72, -24, 24, 72]) {
    // outlet pattern drawn with its earth slot down, then turned earth slot up
    const outlet = new Group();
    outlet.position.set(x, -d / 2, 0);
    outlet.rotation.y = Math.PI;
    k.object.add(outlet);
    k.rod(15, 15, 0.8, [0, -0.2, 0], face, 'y', outlet);
    for (const s of [-1, 1]) k.block([1.8, 1, 7], [s * 6.5, -0.7, 3.5], slot, 0, outlet).rotation.y = s * 0.52;
    k.block([1.8, 1, 7], [0, -0.7, -7], slot, 0, outlet);
  }
  k.block([10, 8, 2], [-w / 2 + 12, 0, h / 2 + 0.6], k.paint(0xc13c31), 1); // reset button on top
  k.rod(4.5, 4.5, 16, [w / 2 + 8, 0, 0], white, 'x');
  return { object: k.object, materials: k.materials };
}

/** RJ45 keystone coupler through the panel, or a blank insert on its outer face. */
export function buildKeystone(spec) {
  const k = kit();
  const [w, d, h] = spec.size;
  if (spec.model === 'keyBlank') {
    k.block(spec.size, [0, 0, 0], k.paint(0x16181b, 0, 0.6), 1);
    return { object: k.object, materials: k.materials };
  }
  k.block(spec.size, [0, 0, 0], k.paint(0xeeede8, 0, 0.42), 1.2);
  const dark = k.paint(0x101113);
  for (const s of [-1, 1]) k.block([w - 4.5, 1, h - 7], [0, s * (d / 2 + 0.1), -1], dark);
  return { object: k.object, materials: k.materials };
}

/** Zigbee dongle standing in the mast's socket, antenna straight up. */
export function buildDongle(spec) {
  const k = kit();
  const [, , h] = spec.size;
  k.block(spec.size, [0, 0, 0], k.paint(0x202227, 0.05, 0.5), 3);
  const black = k.paint(0x111214, 0.1, 0.55);
  k.rod(4, 4, 8, [0, 0, h / 2 + 4], k.paint(0xb9bec4, 0.8, 0.3));
  k.rod(3.4, 2.6, 100, [0, 0, h / 2 + 58], black);
  return { object: k.object, materials: k.materials };
}

function roundRect(path, hw, hh, r) {
  path.moveTo(-hw + r, -hh);
  path.lineTo(hw - r, -hh);
  path.absarc(hw - r, -hh + r, r, -Math.PI / 2, 0, false);
  path.lineTo(hw, hh - r);
  path.absarc(hw - r, hh - r, r, 0, Math.PI / 2, false);
  path.lineTo(-hw + r, hh);
  path.absarc(-hw + r, hh - r, r, Math.PI / 2, Math.PI, false);
  path.lineTo(-hw, -hh + r);
  path.absarc(-hw + r, -hh + r, r, Math.PI, 1.5 * Math.PI, false);
  return path;
}

/** Hook-and-loop strap closed round a bundle `size` across (along `spread`, then across it), 12 mm wide. */
export function buildTie(tie) {
  const k = kit();
  const [w, h] = tie.size;
  const band = 1.3;
  const r = Math.min(tie.round ?? Math.min(w, h) / 2, w / 2, h / 2);
  const shape = roundRect(new Shape(), w / 2 + band, h / 2 + band, r + band);
  shape.holes.push(roundRect(new Path(), w / 2, h / 2, r));
  const geo = new ExtrudeGeometry(shape, { depth: 12, bevelEnabled: false, curveSegments: 5 });
  geo.translate(0, 0, -6);
  const strap = new Mesh(geo, k.paint(0x33465c, 0, 0.82));
  strap.castShadow = true;
  const along = new Vector3(...tie.along).normalize();
  const spread = new Vector3(...tie.spread).addScaledVector(along, -along.dot(new Vector3(...tie.spread))).normalize();
  const across = new Vector3().crossVectors(along, spread);
  strap.quaternion.setFromRotationMatrix(new Matrix4().makeBasis(spread, across, along));
  strap.position.set(...tie.centre);
  k.object.add(strap);
  return { object: k.object, materials: k.materials };
}
