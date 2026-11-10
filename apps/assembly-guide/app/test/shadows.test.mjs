import { test } from 'node:test';
import assert from 'node:assert/strict';
import { installDomStubs, fakeRenderer, meshes } from './helpers.mjs';

const makeElement = installDomStubs();
const { Viewer } = await import('../src/scene.js');
const { buildSoyrackTimeline, SoyrackStage, FLOOR_Z } = await import('../src/soyrack/index.js');

const timeline = buildSoyrackTimeline(meshes);
const makeViewer = (options = {}) => new Viewer({ container: makeElement(), timeline, meshes, Stage: SoyrackStage, floorZ: FLOOR_Z, renderer: fakeRenderer(makeElement), ...options });

/** Everything the shadow map depends on: which meshes cast a shadow right now, and where each one is. */
function casters(viewer) {
  viewer.scene.updateMatrixWorld(true);
  let hash = 0;
  let count = 0;
  const mix = (n) => {
    hash = (Math.imul(hash, 31) + Math.round(n * 1000)) | 0;
  };
  viewer.scene.traverse((o) => {
    if (!o.isMesh || !o.castShadow) return;
    for (let a = o; a; a = a.parent) if (!a.visible) return;
    count++;
    mix(o.id);
    o.matrixWorld.elements.forEach(mix);
    if (o.isInstancedMesh) o.instanceMatrix.array.forEach(mix);
  });
  return `${count}:${hash}`;
}

test('the shadow map is redrawn on every frame that changes a shadow caster, and on well under half of all frames', () => {
  const viewer = makeViewer();
  viewer.setTime(0);
  let before = casters(viewer);
  let frames = 0;
  let redraws = 0;
  for (let t = 1 / 30; t < timeline.duration; t += 1 / 30) {
    viewer.shadowDirty = false; // as render() leaves it
    viewer.dirty = false;
    viewer.setTime(t);
    const now = casters(viewer);
    if (now !== before) assert.equal(viewer.shadowDirty, true, `casters changed at ${t.toFixed(2)} s without a shadow redraw`);
    assert.equal(viewer.dirty, true, 'every time step still redraws the picture');
    if (viewer.shadowDirty) redraws++;
    frames++;
    before = now;
  }
  assert.ok(redraws > 0, 'moving parts do redraw the shadows');
  assert.ok(redraws < frames * 0.5, `shadows redrawn on ${redraws} of ${frames} frames`);
});

test('seeking away and back redraws the shadows both times', () => {
  const viewer = makeViewer();
  viewer.setTime(timeline.duration);
  viewer.shadowDirty = false;
  viewer.setTime(0);
  assert.equal(viewer.shadowDirty, true);
  viewer.shadowDirty = false;
  viewer.setTime(0);
  assert.equal(viewer.shadowDirty, false, 'the same moment again changes nothing');
  viewer.setTime(timeline.duration);
  assert.equal(viewer.shadowDirty, true);
});

test('phones start at 1.5x and resolution steps down only after sustained slow frames', () => {
  const saved = globalThis.window.devicePixelRatio;
  globalThis.window.devicePixelRatio = 3;
  try {
    const phone = makeViewer({ phone: true });
    const ratios = [];
    phone.renderer.setPixelRatio = (r) => ratios.push(r);
    assert.equal(phone.ratio, 1.5);
    for (let i = 0; i < 30; i++) phone.adapt(40); // a brief stutter
    for (let i = 0; i < 200; i++) phone.adapt(16.7); // steady 60 Hz
    assert.equal(phone.ratio, 1.5, 'a brief stutter and steady frames change nothing');
    phone.dirty = false;
    for (let i = 0; i < 80; i++) phone.adapt(40);
    assert.equal(phone.ratio, 1.25, 'sustained slow frames lower it one step');
    assert.deepEqual(ratios, [1.25]);
    assert.equal(phone.dirty, true, 'and the picture is redrawn at the new size');
    for (let i = 0; i < 1000; i++) phone.adapt(40);
    assert.equal(phone.ratio, 0.85, 'it never goes below the floor');
    for (let i = 0; i < 2000; i++) phone.adapt(8);
    assert.equal(phone.ratio, 1.5, 'quick frames bring it back');

    const desktop = makeViewer();
    assert.equal(desktop.ratio, 2, 'desktops start at up to 2x');
  } finally {
    globalThis.window.devicePixelRatio = saved;
  }
});
