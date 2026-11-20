// The soldering page's Kit panel: the soldering subset of the Pearl kit (../kit.js). One list, one store: a tick
// here is the same tick in the Pearl guide (key pearl.stage0.kit), so Boris never ticks an item twice.

import { CHECKED, GROUPS } from '../kit.js';

/** Kit item ids this page uses, in ../kit.js. `station` is the pen iron's id until kit.js names it `iron`. */
export const KIT_IDS = [
  'iron', 'station', 'solder', 'flux', 'braid', 'multimeter', 'cutters', 'tweezers', 'third_hand', 'practice', 'heatshrink',
  'mat', 'stripper', 'wire', 'jst', 'drivers', 'battery', 'glasses',
];

const groups = GROUPS.map((g) => ({ ...g, items: g.items.filter((i) => KIT_IDS.includes(i.id)) })).filter((g) => g.items.length);

export const KIT = {
  title: 'Kit for soldering',
  lede: 'What this page uses. Ticks here and in the Pearl guide are the same list.',
  checked: CHECKED,
  groups,
};
