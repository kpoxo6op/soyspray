import { test } from 'node:test';
import assert from 'node:assert/strict';
import { adoptCarried, updateTick } from '../src/sheets.js';

// The old pearl.soyspray.vip hands its ticks to explain.soyspray.vip/pearl/ once (public/moved.html).
function browser(store = {}) {
  const data = { ...store };
  globalThis.localStorage = { getItem: (k) => (k in data ? data[k] : null), setItem: (k, v) => (data[k] = String(v)) };
  const calls = [];
  return { data, hist: { replaceState: (...a) => calls.push(a[2]) }, calls };
}

test('carried ticks merge with ticks already saved here, and the address loses ?carry', () => {
  const b = browser({ 'pearl.stage0.done': '["buy"]' });
  const carry = encodeURIComponent(JSON.stringify({ 'pearl.stage0.done': ['print', 'buy'], 'pearl.stage0.kit': ['iron'] }));
  assert.equal(adoptCarried({ search: `?carry=${carry}`, pathname: '/pearl/', hash: '#t=191' }, b.hist), true);
  assert.deepEqual(JSON.parse(b.data['pearl.stage0.done']).sort(), ['buy', 'print']);
  assert.deepEqual(JSON.parse(b.data['pearl.stage0.kit']), ['iron']);
  assert.deepEqual(b.calls, ['/pearl/#t=191']);
});

test('a damaged or foreign carry changes nothing but the address', () => {
  const b = browser({ 'pearl.stage0.done': '["buy"]' });
  adoptCarried({ search: '?carry=%7Bnot-json', pathname: '/pearl/', hash: '' }, b.hist);
  adoptCarried({ search: `?carry=${encodeURIComponent('{"other.key":["x"],"pearl.stage0.done":[1,{}]}')}`, pathname: '/pearl/', hash: '' }, b.hist);
  assert.deepEqual(b.data, { 'pearl.stage0.done': '["buy"]' });
  assert.equal(b.calls.length, 2);
  assert.equal(adoptCarried({ search: '', pathname: '/pearl/', hash: '' }, b.hist), false);
});

// A carry is untrusted input: adding a page must not let old-host links write that page's progress.
test('carried progress cannot write soldering Done ticks', () => {
  const b = browser({ 'explain.soldering.done': '["bench"]' });
  const payload = { 'explain.soldering.done': ['light'], 'pearl.stage0.done': ['buy'] };
  adoptCarried({ search: `?carry=${encodeURIComponent(JSON.stringify(payload))}`, pathname: '/pearl/', hash: '' }, b.hist);
  assert.deepEqual(JSON.parse(b.data['explain.soldering.done']), ['bench']);
  assert.deepEqual(JSON.parse(b.data['pearl.stage0.done']), ['buy']);
});

// Carry tests cover migration, not two live pages saving changes from stale snapshots.
test('sequential tab changes preserve other ticks and respect removals', () => {
  const b = browser();
  const stale = new Set();
  updateTick('pearl.stage0.kit', 'iron', true, stale);
  updateTick('pearl.stage0.kit', 'solder', true, stale);
  assert.deepEqual(JSON.parse(b.data['pearl.stage0.kit']), ['iron', 'solder']);
  updateTick('pearl.stage0.kit', 'iron', false, stale);
  updateTick('pearl.stage0.kit', 'meter', true, new Set(['iron', 'solder']));
  assert.deepEqual(JSON.parse(b.data['pearl.stage0.kit']), ['solder', 'meter']);
  updateTick('explain.soldering.done', 'bench', true, stale);
  updateTick('explain.soldering.done', 'light', true, stale);
  assert.deepEqual(JSON.parse(b.data['explain.soldering.done']), ['bench', 'light']);
  assert.equal(b.data['pearl.stage0.done'], undefined);
});

test('blocked storage preserves ticks for this visit', () => {
  globalThis.localStorage = {
    getItem() { throw new Error('blocked'); },
    setItem() { throw new Error('blocked'); },
  };
  let ticks = updateTick('kit', 'iron', true, new Set());
  ticks = updateTick('kit', 'solder', true, ticks);
  assert.deepEqual([...ticks], ['iron', 'solder']);
  ticks = updateTick('kit', 'iron', false, ticks);
  assert.deepEqual([...ticks], ['solder']);
});
