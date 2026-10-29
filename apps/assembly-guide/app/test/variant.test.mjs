import { test } from 'node:test';
import assert from 'node:assert/strict';
import { parseLayout, VARIANT, DRILLED } from '../src/variant.js';
import { buildTimeline, evaluate } from '../src/timeline.js';
import { placements } from './helpers.mjs';
// Contract: a missing/unknown URL selects no holes, while explicit v1 selects the
// optional modification. Physical tests cannot detect a wrong public default.
test('URL selects the complete installation; default and invalid layouts are v2',()=>{
  assert.equal(parseLayout(''),'v2');assert.equal(parseLayout('?layout=unknown'),'v2');
  assert.equal(parseLayout('?layout=v1'),'v1');assert.equal(parseLayout('?layout=v2'),'v2');assert.equal(parseLayout('?layout=v3'),'v3');
  assert.equal(VARIANT,DRILLED?'v1':'v2');
});
// Contract: rebuilding or seeking backwards produces the same chapter times and
// device poses in the selected variant. Player controls alone cannot own its assembly data.
test('selected installation builds deterministically and retraces arbitrary seeks',()=>{
  const a=buildTimeline(placements),b=buildTimeline(placements);
  assert.deepEqual(a.chapters,b.chapters);
  const times=[0,51,140,185,220,280,a.duration];
  const states=times.map(t=>evaluate(a,t));
  for(let i=times.length-1;i>=0;i--)assert.deepEqual(evaluate(b,times[i]),states[i]);
});
