import { test } from 'node:test';
import assert from 'node:assert/strict';
import { decodeMeshes } from '../src/meshes.js';
import { meshBytes, placements } from './helpers.mjs';

const EXPECTED = {
  yBarLeft: 3396, yBarRight: 3396, xBar: 742, mainRail: 6832, xyPlate: 838,
  rackFeet: 838, rackJoiner: 676, trayVent: 300, trayUpper: 276,
};

test('all nine print-pack meshes decode with sane topology', () => {
  const meshes = decodeMeshes(meshBytes);
  assert.deepEqual(Object.keys(meshes).sort(), Object.keys(EXPECTED).sort());
  for (const [name, m] of Object.entries(meshes)) {
    assert.equal(m.sourceTriangles, EXPECTED[name], `${name} source triangle count`);
    assert.ok(m.triangles >= m.sourceTriangles - 30, `${name} keeps its triangles`);
    assert.equal(m.indices.length, m.triangles * 3);
    assert.equal(m.positions.length, m.vertices * 3);
    let max = 0;
    for (const i of m.indices) max = Math.max(max, i);
    assert.ok(max < m.vertices, `${name} indices in range`);
    const lo = [Infinity, Infinity, Infinity];
    const hi = [-Infinity, -Infinity, -Infinity];
    for (let i = 0; i < m.positions.length; i += 3) {
      for (let k = 0; k < 3; k++) {
        const v = m.positions[i + k];
        assert.ok(Number.isFinite(v));
        lo[k] = Math.min(lo[k], v);
        hi[k] = Math.max(hi[k], v);
      }
    }
    for (let k = 0; k < 3; k++) {
      assert.ok(Math.abs(hi[k] - lo[k] - m.size[k]) < 0.01, `${name} size axis ${k}`);
      assert.ok(Math.abs(hi[k] + lo[k]) < 0.01, `${name} centred axis ${k}`);
    }
  }
});

test('placements reference real meshes and use unit quaternions', () => {
  const meshes = decodeMeshes(meshBytes);
  assert.equal(placements.instances.length, 40);
  const counts = {};
  for (const it of placements.instances) {
    assert.ok(meshes[it.part], it.part);
    counts[it.part] = (counts[it.part] || 0) + 1;
    const n = Math.hypot(...it.q);
    assert.ok(Math.abs(n - 1) < 1e-6, `${it.id} quaternion`);
  }
  // Two frames (new + 2024) use 4 xBars, 2+2 yBars, 4 rails, 2 plates each; plus feet, joiners, trays.
  assert.deepEqual(counts, {
    yBarLeft: 4, yBarRight: 4, xBar: 8, mainRail: 8, xyPlate: 4, rackFeet: 2, rackJoiner: 4, trayVent: 3, trayUpper: 3,
  });
  const newFrame = placements.instances.filter((i) => i.id.startsWith('new.'));
  const per = (p) => newFrame.filter((i) => i.part === p).length;
  assert.equal(per('yBarLeft'), 2);
  assert.equal(per('yBarRight'), 2);
  assert.equal(per('xBar'), 4);
  assert.equal(per('mainRail'), 4);
  assert.equal(per('xyPlate'), 2);
});
