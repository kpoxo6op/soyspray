import { test } from 'node:test';
import assert from 'node:assert/strict';
import { installDomStubs, fakeRenderer, placements, meshBytes } from './helpers.mjs';

const makeElement = installDomStubs();
const { Viewer } = await import('../src/scene.js');
const { buildTimeline } = await import('../src/timeline.js');
const { decodeMeshes } = await import('../src/meshes.js');
const { Matrix4, Vector3 } = await import('three');

const timeline = buildTimeline(placements);
const container = makeElement();
const renderer = fakeRenderer(makeElement);
const viewer = new Viewer({ container, timeline, meshes: decodeMeshes(meshBytes), renderer });

function finiteMatrix(m) {
  return m.elements.every(Number.isFinite);
}

test('every timeline node has a scene object; parts use the real meshes', () => {
  let parts = 0;
  for (const [id, rec] of viewer.objects) {
    assert.ok(timeline.nodes.has(id));
    if (rec.node.kind === 'part') {
      parts++;
      assert.equal(rec.obj.geometry, viewer.partGeometries[rec.node.mesh]);
      assert.ok(rec.obj.geometry.attributes.normal, 'creased normals');
    }
  }
  assert.equal(parts, 40);
  const screws = viewer.screwSets.reduce((a, s) => a + s.ids.length, 0);
  assert.equal(screws, 84);
});

test('setTime produces finite transforms across the whole timeline and hides future parts', () => {
  for (let t = 0; t <= timeline.duration; t += 0.25) {
    viewer.setTime(t);
    for (const rec of viewer.objects.values()) assert.ok(finiteMatrix(rec.obj.matrixWorld), `${rec.node.id} at ${t}`);
  }
  viewer.setTime(0);
  const shown = [...viewer.objects.values()].filter((r) => r.node.kind === 'part' && r.obj.visible).map((r) => r.node.id);
  assert.deepEqual(shown.sort(), ['new.rectB.xF', 'new.rectB.xR', 'new.rectB.yL', 'new.rectB.yR']);
  const m = new Matrix4();
  for (const { im } of viewer.screwSets) {
    for (let i = 0; i < im.count; i++) {
      im.getMatrixAt(i, m);
      assert.equal(m.determinant(), 0, 'no screw shown at t=0');
    }
  }
});

test('assembled rack matches the derived placements in three.js world space', () => {
  viewer.setTime(timeline.duration);
  // rack (x, y, z) -> three (x, z, -y)
  for (const it of placements.instances) {
    const rec = viewer.objects.get(it.id);
    // exact bounds of the transformed vertices (a rotated local box would overestimate)
    const pos = rec.obj.geometry.attributes.position;
    const v = new Vector3();
    const lo = [Infinity, Infinity, Infinity];
    const hi = [-Infinity, -Infinity, -Infinity];
    for (let i = 0; i < pos.count; i++) {
      v.fromBufferAttribute(pos, i).applyMatrix4(rec.obj.matrixWorld);
      const r = [v.x, -v.z, v.y];
      for (let k = 0; k < 3; k++) {
        lo[k] = Math.min(lo[k], r[k]);
        hi[k] = Math.max(hi[k], r[k]);
      }
    }
    for (let k = 0; k < 3; k++) {
      assert.ok(Math.abs(lo[k] - it.worldMin[k]) < 0.05, `${it.id} min axis ${k}: ${lo[k]} vs ${it.worldMin[k]}`);
      assert.ok(Math.abs(hi[k] - it.worldMax[k]) < 0.05, `${it.id} max axis ${k}: ${hi[k]} vs ${it.worldMax[k]}`);
    }
  }
  const m = new Matrix4();
  for (const { im } of viewer.screwSets) {
    for (let i = 0; i < im.count; i++) {
      im.getMatrixAt(i, m);
      assert.ok(Math.abs(m.determinant() - 1) < 1e-6, 'all screws shown, unscaled');
    }
  }
});

test('home view frames all content above the transport bar', () => {
  const box = viewer.contentBox;
  assert.ok(box.min.y < -17 && box.max.y > 400, 'includes floor-level feet and the top of the rack');
  viewer.setBottomInset(220);
  const home = viewer.homeView();
  const dist = home.position.distanceTo(home.target);
  assert.ok(dist > 600 && dist < 6000, `distance ${dist}`);
  // Every corner of the content box projects inside the frustum.
  viewer.camera.position.copy(home.position);
  viewer.camera.lookAt(home.target);
  viewer.camera.updateMatrixWorld(true);
  viewer.camera.updateProjectionMatrix();
  const v = new Vector3();
  for (let i = 0; i < 8; i++) {
    v.set(i & 1 ? box.max.x : box.min.x, i & 2 ? box.max.y : box.min.y, i & 4 ? box.max.z : box.min.z).project(viewer.camera);
    assert.ok(Math.abs(v.x) <= 1.001 && Math.abs(v.y) <= 1.001, `corner ${i} in view (${v.x.toFixed(2)}, ${v.y.toFixed(2)})`);
    // the transport bar covers the bottom 220 px of 800: keep content above it
    assert.ok(v.y >= -1 + (2 * 220) / 800 - 0.02, `corner ${i} above the bar (${v.y.toFixed(3)})`);
  }
});

test('render is on demand and shadows refresh only when the state changes', () => {
  const before = renderer.calls.render;
  viewer.setTime(12);
  assert.equal(viewer.dirty, true);
  viewer.render();
  assert.equal(renderer.calls.render, before + 1);
  assert.equal(renderer.shadowMap.needsUpdate, true);
  renderer.shadowMap.needsUpdate = false;
  viewer.dirty = true; // camera-only change
  viewer.render();
  assert.equal(renderer.shadowMap.needsUpdate, false);
});
