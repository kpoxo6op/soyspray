// Every shopping line must be buyable: a shop, a working kind of link, a price with its date, a reason.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { CHECKED, GROUPS, totals } from '../src/kit.js';

test('each item says what, why, where and how much', () => {
  assert.match(CHECKED, /^\d{1,2} [A-Z][a-z]{2} 20\d\d$/);
  const ids = new Set();
  for (const g of GROUPS) {
    for (const i of g.items) {
      assert.ok(!ids.has(i.id), `duplicate ${i.id}`);
      ids.add(i.id);
      assert.ok(i.name && i.why, `${i.id} needs a name and a reason`);
      if (g.id === 'home') continue;
      assert.ok(i.price > 0 && i.shop, `${i.id} needs a price and a shop`);
      assert.match(i.url, /^https:\/\/www\.(jaycar\.co\.nz|aliexpress\.com|spotlightstores\.com|pbtech\.co\.nz)\//, `${i.id} link`);
      if (i.shop === 'Jaycar') assert.ok(i.url.endsWith(`/p/${i.code}`), `${i.id} links its Jaycar code`);
      if (i.shop === 'AliExpress') assert.ok(i.est, `${i.id}: AliExpress prices are typical, not quotes`);
    }
  }
});

test('the total the guide quotes matches the list', () => {
  const t = totals();
  const sum = GROUPS.flatMap((g) => g.items).reduce((s, i) => s + (i.price || 0), 0);
  assert.equal(Math.round(t.all * 100), Math.round(sum * 100));
  assert.ok(Math.abs(Math.round(t.all / 10) * 10 - 530) <= 10, `the Buy chapter says about $530, the list adds to ${t.all}`);
});
