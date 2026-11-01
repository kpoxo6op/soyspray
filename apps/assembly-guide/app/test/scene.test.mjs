import { test } from 'node:test';
import assert from 'node:assert/strict';
import { installDomStubs, fakeRenderer, meshes } from './helpers.mjs';

const makeElement = installDomStubs();
const { Viewer } = await import('../src/scene.js');
const { buildSoyrackTimeline, SoyrackStage, FLOOR_Z } = await import('../src/soyrack/index.js');
const { soyrackPlacements, CAP_TOP } = await import('../src/soyrack/rack.js');
const { Matrix4, Vector3, Raycaster, DoubleSide } = await import('three');

const timeline = buildSoyrackTimeline(meshes);
const container = makeElement();
const renderer = fakeRenderer(makeElement);
const viewer = new Viewer({ container, timeline, meshes, Stage: SoyrackStage, floorZ: FLOOR_Z, renderer });
const nodes = [...timeline.nodes.values()];

function finiteMatrix(m) {
  return m.elements.every(Number.isFinite);
}

test('every timeline node has a scene object; parts use the real meshes', () => {
  let parts = 0;
  for (const [id, rec] of viewer.objects) {
    assert.ok(timeline.nodes.has(id));
    if (rec.node.kind === 'part') {
      parts++;
      if (!id.startsWith('tray.L')) assert.ok(rec.obj.geometry === viewer.partGeometries[rec.node.mesh], `${id} keeps the original geometry`);
      assert.ok(rec.obj.geometry.attributes.normal, 'creased normals');
    }
  }
  assert.equal(parts, nodes.filter((n) => n.kind === 'part').length);
  const screws = viewer.screwSets.reduce((a, s) => a + s.ids.length, 0);
  assert.equal(screws, nodes.filter((n) => n.kind === 'screw').length);
});

test('setTime produces finite transforms across the whole timeline and hides future parts', () => {
  for (let t = 0; t <= timeline.duration; t += 0.25) {
    viewer.setTime(t);
    for (const rec of viewer.objects.values()) assert.ok(finiteMatrix(rec.obj.matrixWorld), `${rec.node.id} at ${t}`);
  }
  viewer.setTime(0);
  const shown = [...viewer.objects.values()].filter((r) => r.node.kind === 'part' && r.obj.visible).map((r) => r.node.id);
  assert.deepEqual(shown.sort(), ['coupon.base', 'coupon.corner', 'coupon.keystone', 'coupon.post']);
  const m = new Matrix4();
  for (const { im } of viewer.screwSets) {
    for (let i = 0; i < im.count; i++) {
      im.getMatrixAt(i, m);
      assert.equal(m.determinant(), 0, 'no screw shown at t=0');
    }
  }
});

// Contract: the rack frame (x right, y rear, z up) maps onto the three.js world exactly, so every
// finished part fills the box its placement names.
test('the finished rack sits where its placements say in three.js world space', () => {
  viewer.setTime(timeline.duration);
  for (const it of soyrackPlacements(meshes).instances) {
    const rec = viewer.objects.get(it.id);
    const pos = rec.obj.geometry.attributes.position;
    const v = new Vector3();
    const lo = [Infinity, Infinity, Infinity];
    const hi = [-Infinity, -Infinity, -Infinity];
    for (let i = 0; i < pos.count; i++) {
      v.fromBufferAttribute(pos, i).applyMatrix4(rec.obj.matrixWorld);
      const r = [v.x, -v.z, v.y]; // three (x, y, z) -> rack (x, -z, y)
      for (let k = 0; k < 3; k++) {
        lo[k] = Math.min(lo[k], r[k]);
        hi[k] = Math.max(hi[k], r[k]);
      }
    }
    const size = meshes[it.part].size;
    for (let k = 0; k < 3; k++) {
      assert.ok(Math.abs(lo[k] - (it.p[k] - size[k] / 2)) < 0.05, `${it.id} min axis ${k}`);
      assert.ok(Math.abs(hi[k] - (it.p[k] + size[k] / 2)) < 0.05, `${it.id} max axis ${k}`);
    }
  }
  const m = new Matrix4();
  const rackScrews = new Set(nodes.filter((n) => n.kind === 'screw' && !n.id.startsWith('coupon.')).map((n) => n.id));
  for (const { im, ids } of viewer.screwSets) {
    ids.forEach((id, i) => {
      if (!rackScrews.has(id)) return;
      im.getMatrixAt(i, m);
      assert.ok(Math.abs(m.determinant() - 1) < 1e-6, `${id} shown, unscaled`);
    });
  }
});

// Contract: the prepared node trays have a real connector opening, with floor and ribs intact.
test('node-tray rear openings clear the ports while retaining support', () => {
  viewer.setTime(timeline.duration);
  for (let i = 0; i < 3; i++) {
    const mesh = viewer.objects.get(`tray.L${i}`).obj;
    mesh.material.side = DoubleSide;
    const ray = new Raycaster(new Vector3(59.5, 33.9 + i * 50, -220), new Vector3(0, 0, 1), 0, 40);
    assert.equal(ray.intersectObject(mesh).length, 0, 'rear Ethernet opening');
    ray.set(new Vector3(34.5, 29 + i * 50, -220), new Vector3(0, 0, 1));
    assert.ok(ray.intersectObject(mesh).length > 0, 'corner rib remains');
    ray.set(new Vector3(37, 40 + i * 50, -185), new Vector3(0, -1, 0));
    assert.ok(ray.intersectObject(mesh).length > 0, 'tray floor remains');
  }
});

// Contract: each chapter's framing fits on screen above the caption and transport bar.
test('every chapter frames its view above the transport bar', () => {
  viewer.setBottomInset(220);
  for (const c of timeline.chapters) {
    viewer.setTime((c.start + c.end) / 2);
    const box = viewer.stage.camera().box.clone().applyMatrix4(viewer.root.matrixWorld);
    const home = viewer.homeView();
    const dist = home.position.distanceTo(home.target);
    assert.ok(dist > 100 && dist < 6000, `${c.id} distance ${dist}`);
    viewer.camera.position.copy(home.position);
    viewer.camera.lookAt(home.target);
    viewer.camera.updateMatrixWorld(true);
    viewer.camera.updateProjectionMatrix();
    const v = new Vector3();
    for (let i = 0; i < 8; i++) {
      v.set(i & 1 ? box.max.x : box.min.x, i & 2 ? box.max.y : box.min.y, i & 4 ? box.max.z : box.min.z).project(viewer.camera);
      assert.ok(Math.abs(v.x) <= 1.001 && Math.abs(v.y) <= 1.001, `${c.id} corner ${i} in view (${v.x.toFixed(2)}, ${v.y.toFixed(2)})`);
      // the transport bar covers the bottom 220 px of 800: keep content above it
      assert.ok(v.y >= -1 + (2 * 220) / 800 - 0.02, `${c.id} corner ${i} above the bar (${v.y.toFixed(3)})`);
    }
  }
  const all = viewer.frameBox;
  assert.ok(all.min.y < FLOOR_Z + 1 && all.max.y > CAP_TOP - 1, 'content runs from the pads to the top cap');
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
