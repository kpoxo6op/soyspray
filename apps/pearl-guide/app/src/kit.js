// Stage 0 shopping list. Everything in "Arrived by post" came from AliExpress (orders of 1 November 2026, all arrived
// by 20 November); it carries no price, and its links are searches for buying another. In "Still to buy", the Jaycar
// and PB Tech prices were read on their NZ sites on 20 November 2026 (the switch moved from AliExpress to Jaycar that
// day so it does not take two more weeks), the Spotlight helium price on 31 October 2026.
// Item ids are the keys of the Kit ticks (pearl.stage0.kit), shared with the soldering page: keep an id when the role
// stays the same. `station` is the soldering iron, now the CXG pen iron, so a tick made for the iron still counts.

export const CHECKED = '20 Nov 2026';

const ali = (q) => `https://www.aliexpress.com/w/wholesale-${q.trim().replace(/\s+/g, '-')}.html`;
const jaycar = (code) => `https://www.jaycar.co.nz/p/${code}`;
const byPost = ([id, name, why, search]) => ({ id, name, why, shop: 'AliExpress', url: ali(search) });

export const GROUPS = [
  {
    id: 'post',
    title: 'Arrived by post',
    when: 'Already on your bench. Tick each one as you unpack it.',
    items: [
      ['station', 'CXG E60WT pen-style soldering iron, 60 W', 'Set 330 °C with the buttons on the handle. Put it down only in its stand.', 'cxg e60wt soldering iron'],
      ['solder', 'JCD 60/40 rosin-core solder, 0.8 mm, 50 g', 'The rosin core is the flux. It contains lead, so wash your hands after.', 'jcd 60 40 rosin core solder 0.8mm 50g'],
      ['flux', 'Flux pen', 'A dab makes a dull joint flow again.', 'solder flux pen'],
      ['braid', 'Desolder braid, 1.5 mm', 'Soaks up bridges and extra solder.', 'desolder braid 1.5mm'],
      ['multimeter', 'ANENG M126 multimeter', 'Its beep checks joints and bridges. Volts check the battery lead.', 'aneng m126 multimeter'],
      ['cutters', 'PLATO 170 flush cutters', 'Cuts legs level with the joint, flat side down.', 'plato 170 flush cutter'],
      ['tweezers', 'ESD tweezers, set of 6', 'Hold a small wire on a pad. Use the fine straight pair.', 'esd tweezers set 6'],
      ['third_hand', '4-arm magnetic helping hands', 'Hold the board and wires so both hands are free.', 'magnetic helping hands 4 arm soldering'],
      ['practice', 'Traffic-light learn-to-solder kit', 'Your first through-hole joints, and it lights up when they are right.', 'traffic light diy soldering practice kit'],
      ['heatshrink', 'Heatshrink assortment, 127 pieces', 'Covers a splice. Use the thinnest size.', 'heat shrink tubing assortment 127 pcs'],
      ['mat', 'Silicone bench mat', 'A heatproof surface that grips parts.', 'silicone soldering mat'],
      ['stripper', 'Pro’sKit 8PK-3001D precision wire stripper', 'Strips 28 AWG without cutting the strands.', 'proskit 8pk-3001d wire stripper'],
      ['wire', '28 AWG silicone wire, five colours, 5 m each', 'Pearl’s wire. Soft, and the insulation does not melt back.', '28awg silicone wire 5 colors'],
      ['jst', 'JST-PH 2.0 two-pin leads, plugs and sockets, 10 pairs', 'The battery lead you solder to the motor.', 'jst ph 2.0 2 pin male female cable 10 pairs'],
      ['drivers', 'DRV8833 motor driver boards, 5', 'One to practise small joints on, two spare, two kept clean for Pearl.', 'drv8833 motor driver module'],
      ['battery', '502030 1S LiPo, 300 mAh, JST-PH 2.0 plug', 'Powers the thrust test. It arrives part-charged, which is enough.', '502030 3.7v 300mah lipo protection jst ph 2.0'],
      ['scale', 'Pocket scale, 200 g × 0.01 g', 'Weighs prints, lift and thrust. Calibrate it with its weight first.', '0.01g pocket scale 200g calibration weight'],
      ['balloons', '32-inch 4D round foil balloons, white, 5', 'Pearl’s orb. About 56 to 60 cm across when full.', '32 inch 4d round foil balloon white'],
      ['motors', '0610 coreless motors (6 × 10 mm, 3.7 V), 4', 'The same size as Pearl’s fans, for the thrust test.', '0610 coreless motor 6x10mm 3.7v'],
      ['props', 'Gemfan 1219 props, 31 mm 3-blade, 0.8 mm hole', 'Press onto the motor shaft.', 'gemfan 1219 31mm 3 blade propeller 0.8mm'],
    ].map(byPost),
  },
  {
    id: 'buy',
    title: 'Still to buy',
    when: 'One Jaycar trip: glasses before your first joint, switches and resistors before Pearl’s switched lead. Helium is click and collect only.',
    items: [
      { id: 'glasses', name: 'Wrap-around clear safety glasses', code: 'TH3002', why: 'Clipped leads and solder can flick. Wear them from the first cut leg.', shop: 'Jaycar', url: jaycar('TH3002'), price: 5.9 },
      { id: 'switch', name: 'SPDT micro slide switches, 2', code: 'SS0834', why: 'One for the practice lead and one for Pearl. Check it fits the hatch’s switch cradle, drawn for an SS-12D00.', shop: 'Jaycar', url: jaycar('SS0834'), price: 6 },
      { id: 'resistors', name: '10 kΩ resistors, pack of 8', code: 'RR0596', why: 'Two make the battery divider you check with the meter.', shop: 'Jaycar', url: jaycar('RR0596'), price: 1 },
      { id: 'sleeve', name: '1.5 mm white heatshrink', code: 'WH5570', why: 'Sleeves Pearl’s red and blue motor leads so they disappear on the white pod.', shop: 'Jaycar', url: jaycar('WH5570'), price: 2.1 },
      { id: 'helium', name: 'Alpen Jumbo helium balloon tank', why: '90% helium, 10% oxygen. Enough for the first fill and several top-ups.', shop: 'Spotlight', url: 'https://www.spotlightstores.com/en-nz/p/alpen-jumbo-helium-balloon-tank/BP80530768-blue', price: 85 },
      { id: 'filament', name: 'Bambu Lab PLA Matte, Ivory White, 1 kg', code: 'INKBAM0052', why: 'Matte white hides layer lines and lets less light through.', shop: 'PB Tech', url: 'https://www.pbtech.co.nz/product/INKBAM0052/Bambu-Lab-PLA-Matte-Filament---Ivory-White-1kg---1', price: 40 },
    ],
  },
  {
    id: 'home',
    title: 'From home',
    when: 'Nothing to buy.',
    items: [
      { id: 'coins', name: 'Coins: six $2 and four 10c', why: '$2 weighs 10 g and 10c weighs 3.3 g: handy test weights.' },
      { id: 'cup', name: 'A paper cup and sewing thread', why: 'For the lift test.' },
      { id: 'tape', name: 'Tape measure, masking tape, a small block of foam or wood', why: 'For measuring the orb and the thrust test.' },
      { id: 'sponge', name: 'A piece of cellulose kitchen sponge, or brass wool', why: 'Only if the iron’s stand came with neither. Synthetic foam melts.' },
    ],
  },
];

export function totals() {
  const by = {};
  let all = 0;
  let est = false;
  for (const g of GROUPS) {
    by[g.id] = g.items.reduce((s, i) => s + (i.price || 0), 0);
    all += by[g.id];
    est ||= g.items.some((i) => i.est);
  }
  return { by, all, est };
}

export const money = (n) => `$${n.toFixed(2).replace(/\.00$/, '')}`;

export const KIT = {
  title: 'Kit for Stage 0',
  lede: `The tools and parts came by post. What is still to buy adds up to the total under its heading. List checked ${CHECKED}.`,
  checked: CHECKED,
  groups: GROUPS,
};
