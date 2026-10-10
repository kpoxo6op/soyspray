// Remove only the central rear lip of the three node trays. Original CAD stays intact.
import { BufferGeometry, Float32BufferAttribute } from 'three';

function split(poly, axis, value) {
  const low = [], high = [];
  for (let i = 0; i < poly.length; i++) {
    const a = poly[i], b = poly[(i + 1) % poly.length];
    const da = a[axis] - value, db = b[axis] - value;
    (da <= 0 ? low : high).push(a);
    if ((da < 0 && db > 0) || (da > 0 && db < 0)) {
      const f = da / (da - db), p = a.map((v, k) => v + (b[k] - v) * f);
      low.push(p); high.push(p);
    }
  }
  return [low, high];
}

export function openNodeTray(source, centre, floorZ) {
  const cutMin = [36 - centre[0], 186.9 - centre[1], floorZ + 0.4 - centre[2]];
  const cutMax = [213 - centre[0], 190.1 - centre[1], floorZ + 13 - centre[2]];
  const pos = source.attributes.position, idx = source.index;
  const vertices = [];
  function emit(poly) {
    for (let j = 1; j + 1 < poly.length; j++) vertices.push(...poly[0], ...poly[j], ...poly[j + 1]);
  }
  const count = idx ? idx.count : pos.count;
  for (let i = 0; i < count; i += 3) {
    let inside = [0, 1, 2].map(k => {
      const n = idx ? idx.getX(i + k) : i + k;
      return [pos.getX(n), pos.getY(n), pos.getZ(n)];
    });
    for (let axis = 0; axis < 3 && inside.length; axis++) {
      let halves = split(inside, axis, cutMin[axis]); emit(halves[0]); inside = halves[1];
      halves = split(inside, axis, cutMax[axis]); emit(halves[1]); inside = halves[0];
    }
  }
  // Close the shallow cut surface and its ends; leave the floor and corner ribs.
  const lo = cutMin, hi = cutMax;
  emit([[lo[0], -centre[1] + 187, lo[2]], [hi[0], -centre[1] + 187, lo[2]],
    [hi[0], -centre[1] + 190, lo[2]], [lo[0], -centre[1] + 190, lo[2]]]);
  for (const [x, reverse] of [[lo[0], false], [hi[0], true]]) {
    const p = [[x, 187 - centre[1], lo[2]], [x, 190 - centre[1], lo[2]],
      [x, 190 - centre[1], floorZ + 12 - centre[2]], [x, 187 - centre[1], floorZ + 12 - centre[2]]];
    emit(reverse ? p.reverse() : p);
  }
  const g = new BufferGeometry(); g.setAttribute('position', new Float32BufferAttribute(vertices, 3));
  g.computeVertexNormals(); g.computeBoundingBox(); g.computeBoundingSphere(); return g;
}
