import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { SOURCE, meshes, trayMeshes } from './helpers.mjs';
import { soyrackPlacements } from '../src/soyrack/rack.js';
import { testPlacements } from '../src/soyrack/testprints.js';

const printList = JSON.parse(readFileSync(resolve(SOURCE, 'data/v3/parts.json'), 'utf8'));

test('the rack parts and the node tray decode with sane topology', () => {
  assert.deepEqual(Object.keys(trayMeshes), ['trayVent']);
  assert.equal(trayMeshes.trayVent.sourceTriangles, 300);
  for (const part of Object.keys(printList)) assert.ok(meshes[part], `${part} has a browser mesh`);
  for (const [name, m] of Object.entries(meshes)) {
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

// Contract: every placement names a real mesh with a unit rotation, and every mesh shipped in
// the bundle is placed: nothing is carried that the guide never shows.
test('placements and meshes match one to one', () => {
  const instances = [...soyrackPlacements(meshes).instances, ...testPlacements().instances];
  for (const it of instances) {
    assert.ok(meshes[it.part], `${it.id} names mesh ${it.part}`);
    assert.ok(Math.abs(Math.hypot(...it.q) - 1) < 1e-6, `${it.id} quaternion`);
  }
  assert.deepEqual([...new Set(instances.map((it) => it.part))].sort(), Object.keys(meshes).sort());
  assert.equal(instances.filter((it) => it.part === 'trayVent').length, 3);
});
