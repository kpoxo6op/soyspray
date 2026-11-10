import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createLoop } from '../src/loop.js';

/** A stand-in for the browser's frame queue: `flush()` runs the callbacks queued for the next frame. */
function fakeFrames() {
  let queue = [];
  let nextId = 1;
  const frames = {
    requests: 0,
    request(cb) {
      frames.requests++;
      queue.push({ id: nextId, cb });
      return nextId++;
    },
    cancel(id) {
      queue = queue.filter((q) => q.id !== id);
    },
    flush(now = 0) {
      const due = queue;
      queue = [];
      for (const q of due) q.cb(now);
      return due.length;
    },
  };
  return frames;
}

test('a step that asks for a frame while it runs still queues one callback per frame', () => {
  const frames = fakeFrames();
  let steps = 0;
  const loop = createLoop(() => {
    steps++;
    loop.schedule(); // what the player's tick listener does on every played frame
    loop.schedule();
    return true;
  }, frames);
  loop.schedule();
  for (let i = 0; i < 100; i++) assert.equal(frames.flush(i * 16), 1, `frame ${i} ran one callback`);
  assert.equal(steps, 100);
  assert.equal(frames.requests, 101);
});

test('schedule before a frame is idempotent and the loop rests when the step is done', () => {
  const frames = fakeFrames();
  let steps = 0;
  const loop = createLoop(() => {
    steps++;
    return false;
  }, frames);
  loop.schedule();
  loop.schedule();
  assert.equal(frames.requests, 1);
  assert.equal(loop.pending, true);
  assert.equal(frames.flush(), 1);
  assert.equal(steps, 1);
  assert.equal(loop.pending, false);
  assert.equal(frames.flush(), 0, 'nothing queued once the step returned false');
  loop.schedule();
  assert.equal(frames.flush(), 1, 'a later schedule starts it again');
  assert.equal(steps, 2);
});

test('a frame asked for during the last step is not lost', () => {
  const frames = fakeFrames();
  let steps = 0;
  const loop = createLoop(() => {
    if (steps++ === 0) loop.schedule(); // e.g. playback ended inside this step and a listener wants a redraw
    return false;
  }, frames);
  loop.schedule();
  frames.flush();
  assert.equal(loop.pending, true);
  assert.equal(frames.flush(), 1);
  assert.equal(steps, 2);
  assert.equal(frames.flush(), 0);
});

test('stop cancels the pending frame, and a step that throws does not wedge the loop', () => {
  const frames = fakeFrames();
  let steps = 0;
  let fail = false;
  const loop = createLoop(() => {
    steps++;
    if (fail) throw new Error('boom');
    return true;
  }, frames);
  loop.schedule();
  loop.stop();
  assert.equal(frames.flush(), 0);
  assert.equal(steps, 0);
  loop.schedule();
  fail = true;
  assert.throws(() => frames.flush(), /boom/);
  fail = false;
  loop.schedule();
  assert.equal(frames.flush(), 1, 'schedule works again after the failed step');
  assert.equal(steps, 2);
});
