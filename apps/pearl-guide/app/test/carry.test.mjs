import { test } from 'node:test';
import assert from 'node:assert/strict';
import { adoptCarried } from '../src/sheets.js';

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
