import { test } from 'node:test';
import assert from 'node:assert/strict';
import { installDomStubs, fakeRenderer, meshes } from './helpers.mjs';

const makeElement = installDomStubs();
const { Viewer } = await import('../src/scene.js');
const { buildSoyrackTimeline, SoyrackStage, FLOOR_Z } = await import('../src/soyrack/index.js');

const timeline = buildSoyrackTimeline(meshes);

function sceneState(viewer) {
  const rows = [];
  viewer.scene.traverse((o) => {
    const mats = o.material ? (Array.isArray(o.material) ? o.material : [o.material]) : [];
    rows.push([o.visible, ...mats.map((m) => m.transparent)]);
  });
  return JSON.stringify(rows);
}

test('warmUp shows the renderer every material opaque and see-through, then puts the scene back', async () => {
  const renderer = fakeRenderer(makeElement);
  const viewer = new Viewer({ container: makeElement(), timeline, meshes, Stage: SoyrackStage, floorZ: FLOOR_Z, renderer });
  viewer.setTime(timeline.duration * 0.4); // mid-assembly: some parts shown, some hidden, some fading
  const before = sceneState(viewer);
  const passes = [];
  const look = () => {
    const seen = { hidden: 0, opaque: 0, clear: 0 };
    viewer.scene.traverse((o) => {
      if (!o.visible) seen.hidden++;
      if (!o.material) return;
      for (const m of Array.isArray(o.material) ? o.material : [o.material]) seen[m.transparent ? 'clear' : 'opaque']++;
    });
    return seen;
  };
  renderer.compileAsync = async () => {
    passes.push(look());
  };
  const rendersBefore = renderer.calls.render;
  viewer.dirty = false;
  viewer.shadowDirty = false;

  await viewer.warmUp();

  assert.equal(passes.length, 2, 'two compile passes');
  assert.ok(passes[0].opaque > 100 && passes[0].clear === 0, 'first pass: every material opaque');
  assert.ok(passes[1].clear > 100 && passes[1].opaque === 0, 'second pass: every material see-through');
  assert.equal(passes[0].hidden + passes[1].hidden, 0, 'nothing is hidden from the compile passes');
  assert.equal(renderer.calls.render - rendersBefore, 2, 'each pass also draws once, shadows included');
  assert.equal(sceneState(viewer), before, 'visibility and transparency are restored');
  assert.ok(viewer.dirty && viewer.shadowDirty, 'the next frame redraws');
});

test('warmUp still restores the scene when the renderer cannot compile ahead of time', async () => {
  const renderer = fakeRenderer(makeElement); // no compileAsync at all, like an old browser
  const viewer = new Viewer({ container: makeElement(), timeline, meshes, Stage: SoyrackStage, floorZ: FLOOR_Z, renderer });
  viewer.setTime(12);
  const before = sceneState(viewer);
  const rendersBefore = renderer.calls.render;
  await viewer.warmUp();
  assert.equal(renderer.calls.render - rendersBefore, 2, 'the draws compile the shaders instead');
  assert.equal(sceneState(viewer), before);
});
