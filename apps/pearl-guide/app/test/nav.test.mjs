import { test } from 'node:test';
import assert from 'node:assert/strict';
import { parseHash, loopWanted } from '../src/nav.js';
import { autoLoop } from '../src/loop.js';
import { Player } from '../src/player.js';

const chapters = [{ id: 'bench', start: 0, end: 191 }, { id: 'light', start: 191, end: 200 }];

// External chapter links must resolve like time links; existing content tests do not navigate addresses.
test('hashes resolve chapter ids, times and panels without treating unknown text as a seek', () => {
  for (const [hash, time, panel] of [
    ['#light', 191, null], ['#t=191', 191, null], ['#kit', null, 'kit'],
    ['#t=191&kit', 191, 'kit'], ['#chapters', null, 'chapters'], ['#files', null, 'files'],
    ['#unknown', null, null], ['', null, null], ['#bench', 0, null],
    ['#t=1.5', 1.5, null], ['#t=-1', null, null], ['#t=191junk', null, null],
  ]) assert.deepEqual(parseHash(hash, chapters), { time, panel }, hash);
});

test('loop query overrides each page default', () => {
  for (const byDefault of [false, true]) {
    assert.equal(loopWanted('', byDefault), byDefault);
    assert.equal(loopWanted('?loop', byDefault), true);
    assert.equal(loopWanted('?loop=0', byDefault), false);
    assert.equal(loopWanted('?other=1&loop=1', byDefault), true);
  }
});

function setup(t, { enabled = true, reduced = false } = {}) {
  t.mock.timers.enable({ apis: ['setTimeout'] });
  const player = new Player({ duration: 200, chapters });
  const motion = { matches: reduced };
  autoLoop(player, enabled, motion);
  const events = [];
  player.on((reason) => events.push(reason));
  player.seek(199.95);
  player.play();
  player.tick(0.1);
  assert.equal(player.time, 200);
  assert.equal(player.playing, false);
  return { player, events, motion };
}

// Frame-queue tests own rendering, but not the end-of-playback delay or cancellation of a pending restart.
test('a forward completion restarts once, after 2.5 seconds', (t) => {
  const { player, events } = setup(t);
  t.mock.timers.tick(2499);
  assert.equal(player.time, 200);
  assert.equal(player.playing, false);
  t.mock.timers.tick(1);
  assert.equal(player.time, 0);
  assert.equal(player.playing, true);
  assert.deepEqual(events.slice(-2), ['loop', 'play']);
  t.mock.timers.tick(5000);
  assert.equal(events.filter((e) => e === 'loop').length, 1);
});

for (const [name, action] of [
  ['seek', (p) => p.seek(50)], ['speed', (p) => p.setSpeed(0.5)],
  ['scrub', (p) => p.beginScrub()], ['play', (p) => p.play()],
]) test(`${name} cancels a pending restart`, (t) => {
  const { player, events } = setup(t);
  action(player);
  t.mock.timers.tick(3000);
  assert.ok(!events.includes('loop'));
});

for (const options of [{ enabled: false }, { reduced: true }]) {
  test(`no restart with ${JSON.stringify(options)}`, (t) => {
    const { player, events } = setup(t, options);
    t.mock.timers.tick(3000);
    assert.equal(player.playing, false);
    assert.ok(!events.includes('loop'));
  });
}

test('a new reduced-motion preference suppresses a pending restart', (t) => {
  const { player, motion } = setup(t);
  motion.matches = true;
  t.mock.timers.tick(3000);
  assert.equal(player.playing, false);
});

test('rewinding to the start does not loop', (t) => {
  t.mock.timers.enable({ apis: ['setTimeout'] });
  const player = new Player({ duration: 200, chapters });
  autoLoop(player, true, { matches: false });
  player.seek(0.05);
  player.reverse();
  player.tick(0.1);
  t.mock.timers.tick(3000);
  assert.equal(player.time, 0);
  assert.equal(player.playing, false);
});
