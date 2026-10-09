import { test } from 'node:test';
import assert from 'node:assert/strict';
import { Player, formatTime, SPEEDS } from '../src/player.js';
import { buildTimeline } from '../src/timeline.js';
import { placements } from './helpers.mjs';

const tl = buildTimeline(placements);
const make = () => new Player(tl);

test('play, pause and tick advance at the chosen speed', () => {
  const p = make();
  assert.equal(p.playing, false);
  p.play();
  assert.equal(p.direction, 1);
  for (let i = 0; i < 60; i++) p.tick(1 / 60);
  assert.ok(Math.abs(p.time - 1) < 1e-9);
  p.pause();
  p.tick(0.5);
  assert.ok(Math.abs(p.time - 1) < 1e-9, 'paused time does not move');
  p.setSpeed(2);
  p.play();
  p.tick(0.05);
  assert.ok(Math.abs(p.time - 1.1) < 1e-9);
  p.tick(5); // long frame is clamped to 0.1 s
  assert.ok(Math.abs(p.time - 1.3) < 1e-9);
});

test('playback stops at the end, and play restarts from the beginning', () => {
  const p = make();
  const events = [];
  p.on((r) => events.push(r));
  p.seek(tl.duration - 0.05);
  p.play();
  p.tick(0.1);
  assert.equal(p.time, tl.duration);
  assert.equal(p.playing, false);
  assert.ok(events.includes('ended'));
  p.play();
  assert.equal(p.time, 0);
  assert.equal(p.direction, 1);
});

test('rewind plays backwards and stops at zero', () => {
  const p = make();
  p.seek(10);
  p.toggleReverse();
  assert.equal(p.direction, -1);
  for (let i = 0; i < 30; i++) p.tick(1 / 60);
  assert.ok(Math.abs(p.time - 9.5) < 1e-9);
  p.toggleReverse();
  assert.equal(p.playing, false);
  p.reverse();
  for (let i = 0; i < 200; i++) p.tick(0.1);
  assert.equal(p.time, 0);
  assert.equal(p.playing, false);
  p.reverse(); // nothing to rewind at zero
  assert.equal(p.playing, false);
  p.seek(5);
  p.reverse();
  p.play(); // play switches straight back to forward
  assert.equal(p.direction, 1);
});

test('seeking keeps the play state; scrubbing pauses and resumes', () => {
  const p = make();
  p.play();
  p.seek(40);
  assert.equal(p.direction, 1);
  assert.equal(p.time, 40);
  p.beginScrub();
  assert.equal(p.playing, false);
  p.tick(1);
  assert.equal(p.time, 40, 'no ticking while scrubbing');
  p.seek(20, 'scrub');
  p.seek(25, 'scrub');
  p.endScrub();
  assert.equal(p.direction, 1, 'resumes forward');
  assert.equal(p.time, 25);
  p.pause();
  p.beginScrub();
  p.seek(30, 'scrub');
  p.endScrub();
  assert.equal(p.playing, false, 'stays paused when scrubbing from pause');
  p.toggleReverse();
  p.beginScrub();
  p.endScrub();
  assert.equal(p.direction, -1, 'resumes rewinding');
  p.seek(-5);
  assert.equal(p.time, 0);
  p.seek(tl.duration + 50);
  assert.equal(p.time, tl.duration);
});

test('chapter stepping follows video-player rules', () => {
  const p = make();
  const cs = tl.chapters;
  p.nextChapter();
  assert.equal(p.time, cs[1].start);
  p.nextChapter();
  assert.equal(p.time, cs[2].start);
  p.seek(cs[2].start + 3);
  p.prevChapter();
  assert.equal(p.time, cs[2].start, 'restart current chapter when well into it');
  p.prevChapter();
  assert.equal(p.time, cs[1].start, 'go to the previous chapter at its start');
  p.goToChapter(cs.length - 1);
  p.nextChapter();
  assert.equal(p.time, tl.duration);
  p.goToChapter(0);
  p.prevChapter();
  assert.equal(p.time, 0);
  for (const c of cs) {
    p.seek(c.start);
    assert.equal(p.chapterIndex, c.index);
  }
});

test('speed cycles through the menu and time formats like a video player', () => {
  const p = make();
  const seen = [];
  for (let i = 0; i < SPEEDS.length; i++) {
    p.cycleSpeed();
    seen.push(p.speed);
  }
  assert.deepEqual([...seen].sort(), [...SPEEDS].sort());
  assert.equal(formatTime(0), '0:00');
  assert.equal(formatTime(59.99), '0:59');
  assert.equal(formatTime(61), '1:01');
  assert.equal(formatTime(tl.duration), `${Math.floor(tl.duration / 60)}:${String(Math.floor(tl.duration % 60)).padStart(2, '0')}`);
});
