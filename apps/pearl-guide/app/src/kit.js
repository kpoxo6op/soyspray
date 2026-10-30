// Stage 0 shopping list. Jaycar, PB Tech and Spotlight prices were read on their NZ sites on 31 October 2026.
// AliExpress prices are typical asking prices on that date, not quotes: listings change daily.

export const CHECKED = '31 Oct 2026';

const ali = (q) => `https://www.aliexpress.com/w/wholesale-${q.trim().replace(/\s+/g, '-')}.html`;
const jaycar = (code) => `https://www.jaycar.co.nz/p/${code}`;

export const GROUPS = [
  {
    id: 'online',
    title: 'Order online today',
    when: 'AliExpress, 1 to 3 weeks. Order first so the post arrives while you print and practise.',
    items: [
      { id: 'scale', name: 'Pocket scale, 200 g × 0.01 g', why: 'Weighs prints, lift and thrust. Get one with a calibration weight.', shop: 'AliExpress', url: ali('0.01g pocket scale 200g calibration weight'), price: 12, est: true },
      { id: 'balloons', name: '32-inch 4D round foil balloons, white, 3 to 5', why: 'Pearl’s orb. About 56 to 60 cm across when full.', shop: 'AliExpress', url: ali('32 inch 4d round foil balloon white'), price: 25, est: true },
      { id: 'motors', name: '0610 coreless motors (6 × 10 mm, 3.7 V), 4', why: 'The same size as Pearl’s fans, for the thrust test.', shop: 'AliExpress', url: ali('0610 coreless motor 6x10mm 3.7v'), price: 18, est: true },
      { id: 'props', name: '31 mm 3-blade props, 0.8 mm hole (Gemfan 1219)', why: 'Press onto the motor shaft. White if offered.', shop: 'AliExpress', url: ali('gemfan 1219 31mm 3 blade propeller 0.8mm'), price: 6, est: true },
      { id: 'battery', name: '1S LiPo 300 mAh, protection board, JST-PH 2.0 plug', why: 'Powers the thrust test. Arrives part-charged, which is enough.', shop: 'AliExpress', url: ali('502030 3.7v 300mah lipo protection jst ph 2.0'), price: 14, est: true },
      { id: 'jst', name: 'JST-PH 2.0 two-pin leads, plugs and sockets, 10 pairs', why: 'The battery lead you solder to the motor.', shop: 'AliExpress', url: ali('jst ph 2.0 2 pin male female cable 10 pairs'), price: 5, est: true },
      { id: 'wire', name: '28 AWG silicone wire, five colours', why: 'Pearl’s wire. Soft, and the insulation does not melt back.', shop: 'AliExpress', url: ali('28awg silicone wire 5 colors'), price: 8, est: true },
      { id: 'stripper', name: 'Precision wire stripper, 30 to 20 AWG', why: 'Jaycar’s strippers stop at 24 AWG; 28 AWG needs this.', shop: 'AliExpress', url: ali('precision wire stripper 30-20 awg'), price: 12, est: true },
      { id: 'drivers', name: 'DRV8833 motor driver boards, 3', why: 'Cheap copies of Pearl’s driver to practise small joints on.', shop: 'AliExpress', url: ali('drv8833 motor driver module'), price: 6, est: true },
    ],
  },
  {
    id: 'jaycar',
    title: 'Jaycar, one trip',
    when: 'Everything for soldering and checking your work. In stock in most stores.',
    items: [
      { id: 'station', name: 'Duratech 48 W temperature-controlled soldering station', code: 'TS1620', why: 'Set it to 330 °C and it stays there.', price: 74.9 },
      { id: 'solder', name: '0.71 mm solder, hobby tube', code: 'NS3008', why: 'Leaded resin-core solder flows well while you learn.', price: 5.9 },
      { id: 'flux', name: 'Solder flux pen, 12 ml', code: 'NS3036', why: 'A dab makes a stubborn joint flow.', price: 22.9 },
      { id: 'braid', name: '1.5 mm desolder braid', code: 'NS3026', why: 'Soaks up extra solder and bridges.', price: 12.9 },
      { id: 'third_hand', name: 'Third hand with four clips and a heavy base', code: 'TH1981', why: 'Holds the board and wires so both hands are free.', price: 19.9 },
      { id: 'multimeter', name: 'Autorange multimeter', code: 'QM1529', why: 'Its continuity beep checks every joint.', price: 49.9 },
      { id: 'cutters', name: 'Stainless steel side cutters', code: 'TH1890', why: 'Trims leads flush after a joint.', price: 26.9 },
      { id: 'tweezers', name: 'Precision tweezers', code: 'TH1754', why: 'Holds a wire end on a pad.', price: 7.9 },
      { id: 'practice', name: 'Learn to Solder kit: 3D traffic light', code: 'XC3758', why: 'Your first forty joints, and it lights up when you are done.', price: 25.9 },
      { id: 'heatshrink', name: 'Heatshrink assortment, 1.5 to 10 mm', code: 'WH5525', why: 'Covers splices.', price: 11.9 },
      { id: 'sleeve', name: '1.5 mm white heatshrink', code: 'WH5570', why: 'Sleeves Pearl’s red and blue motor leads so they disappear on the white pod.', price: 2.1 },
      { id: 'glasses', name: 'Wrap-around clear safety glasses', code: 'TH3002', why: 'Solder and clipped leads can flick.', price: 5.9 },
      { id: 'mat', name: 'Silicone bench mat, 389 × 263 mm', code: 'HM8102', why: 'A heatproof surface that grips parts.', price: 33.9 },
    ].map((i) => ({ ...i, shop: 'Jaycar', url: jaycar(i.code) })),
  },
  {
    id: 'other',
    title: 'Two more shops',
    when: 'Helium is click and collect only.',
    items: [
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
