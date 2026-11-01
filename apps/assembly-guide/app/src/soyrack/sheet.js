// v3 parts sheet: what to print (with STL links and PETG estimates), what to buy, what carries over.
import printList from '../../data/v3/parts.json' with { type: 'json' };
import { TIES } from './cables.js';

const STL = 'https://github.com/kpoxo6op/soyspray/raw/main/apps/assembly-guide/cad/stl/';
export const CAD_FOLDER = 'https://github.com/kpoxo6op/soyspray/tree/main/apps/assembly-guide/cad';
const ali = (terms) => `https://www.aliexpress.com/w/wholesale-${terms}.html`;
export const BOARD_LINK = 'https://www.legrand.co.nz/en/catalog/products/hpm-general-purpose-4-outlet-powerboard-white-d1051';
export const CHECKED = '2026-10-29';

export const TEST_PRINTS = [
  { part: 'coupon_post', name: 'Post end', detail: 'M4 nuts push into the side slots of holes 1 and 2; an M4 × 12 screw from the front should thread into each and pull tight without the nut turning.' },
  { part: 'coupon_corner', name: 'Deck corner', detail: 'The post end and its foot should press into the pocket by hand and not rock.' },
  { part: 'coupon_base', name: 'Base corner', detail: 'An M4 nut pushes into its slot. With the deck corner and the post end stacked on it, an M4 × 25 screw down through the foot should pull all three tight.' },
  { part: 'coupon_keystone', name: 'Keystone strip', detail: 'Push a keystone coupler into each window. Keep the plate, 2.4 or 2.0 mm, where it clicks in and holds firm.' },
];

export const PRINTED = [
  { part: 'base_tub', quantity: 1, name: 'Power base', detail: 'Bricks, board, switch adapter and the cord loops; a nut slot inside each corner. Prints as it stands.' },
  { part: 'base_deck', quantity: 1, name: 'Base deck', detail: 'Lower bay floor with three rear lead slots.' },
  { part: 'post_lower_a', quantity: 2, name: 'Lower post A', detail: 'Front left and rear right; a foot at each end. Lies on its numbered face.' },
  { part: 'post_lower_b', quantity: 2, name: 'Lower post B', detail: 'Front right and rear left. Lies on its numbered face.' },
  { part: 'mid_deck', quantity: 1, name: 'Mid deck', detail: 'Between the bays; the post feet screw together through its corners.' },
  { part: 'post_upper_a', quantity: 2, name: 'Upper post A', detail: 'Front left and rear right; the top cap screws into it.' },
  { part: 'post_upper_b', quantity: 2, name: 'Upper post B', detail: 'Front right and rear left.' },
  { part: 'top_cap', quantity: 1, name: 'Top cap', detail: 'Grips; the four screw heads sit flush. Prints upside down.' },
  { part: 'drive_tray', quantity: 1, name: 'Drive tray', detail: 'Seagate and Touro side by side, lower holes 16 and 18.' },
  { part: 'switch_shelf', quantity: 1, name: 'Switch shelf', detail: 'Upper holes 1 and 3.' },
  { part: 'keystone_panel', quantity: 1, name: 'Keystone panel', detail: 'Four slots on the rear upper posts. Lies on its outer face.' },
  { part: 'zigbee_mast', quantity: 1, name: 'Zigbee mast', detail: 'Stands 1 m or more from the USB 3 ports. Ballast: three M10 washers in each of six pockets.' },
];

export const BUY = [
  { key: 'nut4', quantity: 50, name: 'M4 hex nuts', detail: 'DIN 934, 7 mm across flats. 36 used: each pushes into a slot or drops into a hex in the print.', url: ali('m4-hex-nut-din934') },
  { key: 'bolt', quantity: 20, name: 'M4 × 25 socket head screws', detail: 'DIN 912. 12 used: one through each corner of the base, the mid deck and the top cap.', url: ali('m4-x-25-socket-head-cap-screw') },
  { key: 'm4', quantity: 20, name: 'M4 × 12 countersunk socket screws', detail: 'DIN 7991. 12 new; the node trays keep their own 12.', url: ali('m4-x-12-countersunk-socket-screw') },
  { key: 'pad', quantity: 4, name: '20 mm silicone pads', detail: 'Round, self-adhesive, 2 mm thick; one under each corner of the base.', url: ali('20mm-silicone-feet-self-adhesive') },
  { key: 'keystone', quantity: 2, name: 'Cat6 RJ45 keystone couplers', detail: 'UTP, straight through, plus 2 keystone blanks.', url: ali('cat6-rj45-keystone-coupler') },
  { key: 'extension', quantity: 1, length: 1500, name: 'USB 2.0 extension, 1.5 m', detail: 'A male to A female, for the Zigbee mast.', url: ali('usb-2.0-extension-cable-1.5m') },
  { key: 'ballast', quantity: 18, name: 'M10 washers', detail: '20 mm outside, 2 mm thick: ballast for the Zigbee mast. Any hardware store.', url: ali('m10-flat-washer-din125') },
  { key: 'strap', quantity: 20, name: 'Hook-and-loop straps', detail: `12 × 300 mm, cut to length. ${TIES.length} used: two hold the board and the switch cord coil down, two hold each of the six cord loops.`, url: ali('hook-and-loop-cable-straps-12mm-300mm') },
  { key: 'board', quantity: 1, name: 'HPM D105/1 four-outlet board', detail: '230 × 50 × 25 mm with a 1.8 m lead; buy locally. Any board up to 238 × 32 mm on its side fits.', url: BOARD_LINK, shop: 'Legrand NZ' },
];

export const CARRY_OVER = [
  'Three ventilated node trays and their twelve M4 × 12 screws.',
  'Nodes, both drives, the switch and its plug-in adapter, three Lenovo bricks with their own mains cords, and the Zigbee dongle.',
  'Cat6 UTP cable and RJ45 plugs for five short crimped leads and the lead out to the router.',
];

export const SOYRACK_LINKS = [
  ...PRINTED.map((p) => `${STL}${p.part}.stl`),
  ...TEST_PRINTS.map((p) => `${STL}${p.part}.stl`),
  CAD_FOLDER,
  ...BUY.map((b) => b.url),
];

const grams = (part) => printList[part]?.grams ?? 0;
export const RACK_GRAMS = PRINTED.reduce((sum, p) => sum + grams(p.part) * p.quantity, 0);
export const TEST_GRAMS = TEST_PRINTS.reduce((sum, p) => sum + grams(p.part), 0);

const link = (url, label) => `<a href="${url}" target="_blank" rel="noopener noreferrer">${label} ↗</a>`;
const kg = (g) => (g / 1000).toFixed(1);

export function soyrackSheetHTML() {
  const printed = (p, q = p.quantity) => `<li><span class="part-qty">${q}×</span><div><strong>${p.name}</strong><p>${p.detail} About ${grams(p.part)} g each.</p>${link(`${STL}${p.part}.stl`, `${p.part}.stl`)}</div></li>`;
  const bought = (b) => `<li><span class="part-qty">${b.quantity}×</span><div><strong>${b.name}</strong><p>${b.detail}</p>${link(b.url, b.shop || 'AliExpress search')} · checked ${CHECKED}</div></li>`;
  return `<header><div><span class="sheet-eyebrow">ASSEMBLY KIT · v3 · Soyrack</span><h2 id="partsTitle">Parts and where to buy</h2></div><button id="closeParts" type="button" aria-label="Close parts sheet">×</button></header>
    <div class="sheet-body"><p class="sheet-intro">A new printed rack around your three node trays: a power base that holds the bricks, the board and every cord at full length, posts screwed to the decks at each corner, a drive tray, a switch shelf, a keystone panel and a Zigbee mast. It goes together with M4 screws and nuts only. Every part fits a 256 mm bed. About ${kg(RACK_GRAMS)} kg of PETG for the rack.</p>
    <h3>Print first</h3><ul class="parts-list">${TEST_PRINTS.map((p) => printed(p, 1)).join('')}</ul>
    <p class="sheet-note">About ${TEST_GRAMS} g in all. The first five chapters show each check. If a fit is loose or tight, say which one before the big prints.</p>
    <h3>Print</h3><ul class="parts-list">${PRINTED.map((p) => printed(p)).join('')}</ul>
    <p class="sheet-note">PETG, 0.4 mm nozzle, 0.2 mm layers, 4 walls, 5 top and bottom layers, 15 % gyroid, no supports. The files are already turned for the bed. Source files and render script: ${link(CAD_FOLDER, 'source folder')}.</p>
    <h3>Buy</h3><ul class="parts-list">${BUY.map(bought).join('')}</ul>
    <h3>Carries over</h3><ul class="assumptions">${CARRY_OVER.map((s) => `<li>${s}</li>`).join('')}</ul>
    <p class="sheet-note">Every joint is an M4 screw into an M4 nut held by the print. Tighten until snug; PETG needs no force. Rack footprint 245 × 240 mm, 388 mm tall.</p></div>`;
}
