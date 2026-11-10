import { test } from 'node:test';
import assert from 'node:assert/strict';
import { Vector3 } from 'three';
import { installDomStubs, fakeRenderer, meshes } from './helpers.mjs';

const makeElement = installDomStubs();
const { Viewer } = await import('../src/scene.js');
const { createTags } = await import('../src/tags.js');
const { buildSoyrackTimeline, SoyrackStage, FLOOR_Z } = await import('../src/soyrack/index.js');

const timeline = buildSoyrackTimeline(meshes);

function makeViewer() {
  const renderer = fakeRenderer(makeElement);
  let measured = 0;
  renderer.domElement.getBoundingClientRect = () => {
    measured++;
    return { left: 0, top: 0, width: 1280, height: 800 };
  };
  const viewer = new Viewer({ container: makeElement(), timeline, meshes, Stage: SoyrackStage, floorZ: FLOOR_Z, renderer });
  viewer.camera.updateMatrixWorld(); // the real renderer does this on every draw
  return { viewer, measured: () => measured };
}

test('projectRackPoint maps the point the camera looks at to the middle of the canvas, measuring nothing', () => {
  const { viewer, measured } = makeViewer();
  const before = measured();
  const centre = viewer.root.worldToLocal(viewer.controls.target.clone());
  const a = viewer.projectRackPoint(centre, 1280, 800);
  assert.ok(Math.abs(a.x - 640) < 0.5 && Math.abs(a.y - 400) < 0.5, `centre lands at ${a.x}, ${a.y}`);
  assert.equal(a.visible, true);
  const half = viewer.projectRackPoint(centre, 640, 400);
  assert.ok(Math.abs(half.x - 320) < 0.5 && Math.abs(half.y - 200) < 0.5, 'the result scales with the size it is given');
  const behind = viewer.root.worldToLocal(viewer.camera.position.clone().multiplyScalar(2).sub(viewer.controls.target));
  assert.equal(viewer.projectRackPoint(behind, 1280, 800).visible, false, 'a point behind the camera is not visible');
  const far = viewer.root.worldToLocal(viewer.controls.target.clone().add(new Vector3(1e5, 0, 0)));
  assert.equal(viewer.projectRackPoint(far, 1280, 800).visible, false, 'a point off to the side is not visible');
  assert.equal(measured(), before, 'no layout was read');
});

/** Just enough DOM for createTags: elements that count how often their box is measured. */
function fakeDom() {
  const counts = { measured: 0 };
  const observers = [];
  const element = () => ({
    style: {},
    className: '',
    textContent: '',
    offsetWidth: 80,
    offsetHeight: 20,
    classList: { add() {}, toggle() {} },
    setAttribute() {},
    appendChild() {},
    append() {},
    insertBefore() {},
    getBoundingClientRect() {
      counts.measured++;
      return { left: 0, top: 0, width: 1280, height: 800 };
    },
  });
  globalThis.document = { createElement: element, createElementNS: element };
  globalThis.ResizeObserver = class {
    constructor(cb) {
      this.cb = cb;
      observers.push(this);
    }
    observe() {}
  };
  return { counts, element, resize: () => observers.forEach((o) => o.cb([])) };
}

test('name tags measure the page once, not on every frame, and again after a resize', () => {
  const { viewer, measured } = makeViewer();
  const saved = { document: globalThis.document, ResizeObserver: globalThis.ResizeObserver };
  const dom = fakeDom();
  try {
    const chapter = timeline.chapters.find((c) => c.tags.length);
    const player = { time: chapter.start + (chapter.end - chapter.start) * 0.5 };
    viewer.setTime(player.time);
    const tags = createTags({ root: dom.element(), before: dom.element(), player, timeline, viewer });
    const total = () => dom.counts.measured + measured();

    tags.update();
    const first = total();
    assert.ok(first >= 1 && first <= 2, `the first frame measures the layer and the canvas (${first})`);
    for (let i = 0; i < 50; i++) {
      player.time += 1 / 60;
      viewer.setTime(player.time);
      tags.update();
    }
    assert.equal(total(), first, '50 more frames measure nothing');

    dom.resize();
    tags.update();
    tags.update();
    assert.equal(total(), first * 2, 'a resize costs one more measurement');
  } finally {
    globalThis.document = saved.document;
    globalThis.ResizeObserver = saved.ResizeObserver;
  }
});
