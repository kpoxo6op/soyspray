// Every shopping line must be true and buyable: what arrived says what it is, and what is still to buy has a shop, a
// working kind of link, a price with its date and a reason.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { CHECKED, GROUPS, KIT, totals } from '../src/kit.js';
import { KIT as SOLDERING_KIT, KIT_IDS } from '../src/soldering/kit.js';
import { checkCopy, checkTitles, kitStrings } from './rules.mjs';

const SHOP_URL = /^https:\/\/www\.(jaycar\.co\.nz|aliexpress\.com|spotlightstores\.com|pbtech\.co\.nz)\//;
const group = (id) => GROUPS.find((g) => g.id === id);

test('the list is what is on the bench, what is still to buy and what is at home', () => {
  assert.match(CHECKED, /^\d{1,2} [A-Z][a-z]{2} 20\d\d$/);
  assert.deepEqual(GROUPS.map((g) => g.title), ['On your bench', 'Still to buy', 'From home']);
  const ids = new Set();
  for (const g of GROUPS) {
    for (const i of g.items) {
      assert.ok(!ids.has(i.id), `${i.id} appears once, so one tick covers it`);
      ids.add(i.id);
      assert.ok(i.name && i.why, `${i.id} needs a name and a reason`);
      if (i.url) assert.match(i.url, SHOP_URL, `${i.id} link`);
      if (i.shop === 'Jaycar') assert.ok(i.url.endsWith(`/p/${i.code}`), `${i.id} links its Jaycar code`);
      if (i.shop === 'AliExpress' && i.price) assert.ok(i.est, `${i.id}: AliExpress prices are typical, not quotes`);
    }
  }
});

test('what is on the bench came from AliExpress or Jaycar and has no price to pay', () => {
  for (const i of group('post').items) {
    assert.ok(['AliExpress', 'Jaycar'].includes(i.shop), i.id);
    assert.ok(!i.price, `${i.id} is paid for`);
  }
  const drivers = group('post').items.find((i) => i.id === 'drivers');
  assert.match(drivers.name, /, 5$/, 'five driver boards arrived');
});

test('still to buy: a shop, a link and a price for each', () => {
  for (const i of group('buy').items) {
    assert.ok(i.shop && i.url && i.price > 0, `${i.id} needs a shop, a link and a price`);
  }
  const names = new Set(group('post').items.map((i) => i.name));
  for (const i of group('buy').items) assert.ok(!names.has(i.name), `${i.name} arrived already`);
});

test('ticks carry over: ids keep their roles', () => {
  // ids Boris may already have ticked, for items he still has in the same role
  const ids = GROUPS.flatMap((g) => g.items.map((i) => i.id));
  for (const id of ['station', 'solder', 'flux', 'braid', 'multimeter', 'cutters', 'tweezers', 'third_hand', 'practice', 'heatshrink', 'mat', 'stripper', 'wire', 'jst', 'drivers', 'battery', 'scale', 'balloons', 'motors', 'props', 'switch', 'resistors', 'sleeve', 'glasses', 'helium', 'filament']) {
    assert.ok(ids.includes(id), `kit keeps ${id}`);
  }
});

test('the Kit panel shows one total for what is still to buy, under its heading', () => {
  const t = totals();
  const sum = GROUPS.flatMap((g) => g.items).reduce((s, i) => s + (i.price || 0), 0);
  assert.equal(Math.round(t.all * 100), Math.round(sum * 100));
  // the panel adds each group up under its heading; a second, rounded figure in the lede would disagree with it
  assert.ok(!/\$\d/.test(KIT.lede), KIT.lede);
  assert.ok(KIT.lede.includes(CHECKED));
  checkCopy([KIT.title, KIT.lede, ...kitStrings(GROUPS)]);
  checkTitles([KIT.title, ...GROUPS.map((g) => g.title)]);
});

test('the soldering page shows the soldering subset of this one list', () => {
  const ids = GROUPS.flatMap((g) => g.items.map((i) => i.id));
  for (const id of KIT_IDS) assert.ok(ids.includes(id), `soldering kit asks for ${id}, which the list lacks`);
  const shown = SOLDERING_KIT.groups.flatMap((g) => g.items.map((i) => i.id));
  assert.deepEqual([...shown].sort(), [...KIT_IDS].sort());
  assert.equal(SOLDERING_KIT.checked, CHECKED);
});
