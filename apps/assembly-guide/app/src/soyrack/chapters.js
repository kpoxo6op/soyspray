// Soyrack build order: test prints first, then the rack. Every pose is a function of time.

import { add3 } from '../math.js';
import { HOLD_IN, tier } from '../timeline.js';
import { TEST_CHAPTERS } from './testprints.js';
import { trayNutIds } from './rack.js';
import { CRIMP_CHAPTERS } from './crimp.js';

const CORNERS = ['FL', 'FR', 'RL', 'RR'];
const each = (prefix) => CORNERS.map((k) => `${prefix}.${k}`);
const TRAY_NUTS = trayNutIds();
const LEFT = /\.(FL|RL)(\.|$)/;
const FRONT = /\.(FL|FR)(\.|$)/;
// Where each nut comes from: into a side slot from inside the rack, into a top slot of an upper
// post from behind it (towards the middle of the rack side), or down into the hex on a foot.
const inward = (id) => [LEFT.test(id) ? 22 : -22, 0, 0];
const fromBehind = (id) => [0, FRONT.test(id) ? 22 : -22, 0];
const fromAbove = () => [0, 0, 24];

/** A chapter in which no part moves, `seconds` long; the stage lays its cords meanwhile. */
const hold = (seconds) => (c) => { c.end = c.start + seconds; };

/** Nuts pushed home one after another, each travelling in from `from(id)` mm away. */
function slide(c, ids, at, from, { dur = 0.7, stagger = 0.1 } = {}) {
  let end = at;
  ids.forEach((id, i) => {
    const n = c.get(id);
    const t = at + i * stagger;
    c.showAt([id], t);
    c.path(id, [
      { at: t, p: add3(n.final.p, from(id)), q: n.final.q },
      { at: t + dur, p: n.final.p, q: n.final.q, e: 'out' },
    ], { highlight: false });
    end = t + dur;
  });
  return end;
}

/** Lower parts one after another from `rise` mm above, slowing for the last `settle` mm. */
function lower(c, ids, at, { rise, settle = 14, dur = 2.2, stagger = 0.3 } = {}) {
  let end = at;
  ids.forEach((id, i) => {
    end = c.move(id, at + i * stagger, dur, { from: [0, 0, rise], via: [0, 0, settle], viaAt: 0.7 });
  });
  return end;
}

export const SOYRACK_CHAPTERS = [
  ...TEST_CHAPTERS,
  {
    id: 'power-base', section: 'Build the rack', title: 'Power base', view: 'base',
    text: 'Push an M4 nut into the slot inside each corner of the base until it stops. Stick a 20 mm silicone pad under each corner.',
    script(c) {
      c.show(['base_tub']);
      const end = c.move('base_tub', HOLD_IN, 2.0, { from: [0, 0, 60], via: [0, 0, 10] });
      const nuts = slide(c, each('nut.base'), end + 0.3, inward, { dur: 1.0, stagger: 0.25 });
      c.showAt(each('pad'), nuts + 0.3);
      CORNERS.forEach((k, i) => c.move(`pad.${k}`, nuts + 0.5 + i * 0.2, 1.2, { from: [0, k[0] === 'F' ? -40 : 40, 0] }));
    },
  },
  {
    id: 'bricks-board', title: 'Bricks and board', view: 'base-rear',
    text: 'Stand the three Lenovo bricks on edge between the fins, inlets to the rear. Lay the four-outlet board on its side on the rails in the rear trough, outlets facing in, and plug the switch adapter into the right-hand outlet.',
    script(c) {
      ['brick0', 'brick1', 'brick2'].forEach((id, i) => {
        c.showAt([id], HOLD_IN + i * 0.5);
        c.move(id, HOLD_IN + 0.2 + i * 0.5, 1.9, { from: [0, 0, 90], via: [0, 0, 8] });
      });
      c.showAt(['board'], HOLD_IN + 2.4);
      const b = c.move('board', HOLD_IN + 2.6, 2.0, { from: [0, 30, 80], via: [0, 0, 8] });
      c.showAt(['psuSwitch'], b + 0.3);
      c.move('psuSwitch', b + 0.5, 1.4, { from: [0, -40, 0] });
      c.end = Math.max(c.end, c.start + b + 4.2);
    },
  },
  {
    id: 'mains-cords', title: 'Mains cords', view: 'cords',
    text: 'Plug each brick’s own 1 m mains cord into the outlet behind it, loop the spare over the brick and strap it twice. Coil the switch adapter’s 1.5 m cord flat on the board, stand its end up at the rear right, and strap the board down over the coil.',
    script: hold(7.2),
  },
  {
    id: 'dc-cords', title: 'Lenovo cords', view: 'cords',
    text: 'Run each 1.8 m Lenovo cord up the front of its brick and along to the right half, loop the spare on edge and strap it twice. Leave the plug ends standing up out of the rear trough: node-0’s at the front, node-2’s at the back.',
    script: hold(7.2),
  },
  {
    id: 'base-deck', title: 'Base deck', view: 'frame',
    text: 'Lower the base deck onto the base, threading the switch cord up through its right rear slot. The Lenovo cords stand behind it.',
    script(c) {
      c.show(['base_deck']);
      lower(c, ['base_deck'], HOLD_IN, { rise: 240, dur: 2.6 });
    },
  },
  {
    id: 'lower-posts', title: 'Lower posts', view: 'frame',
    text: 'Stand the four posts in the deck pockets, numbers facing out, feet towards the middle. Fix each foot with an M4 × 25 screw down into the nut in the base. Push M4 nuts into the side slots of holes 1, 5, 6, 10, 11, 15, 16 and 18 of both front posts.',
    script(c) {
      c.show(each('post.lower'));
      const end = lower(c, each('post.lower'), HOLD_IN, { rise: 232, dur: 2.4 });
      const bolts = c.screws(each('bolt.base'), end + 0.3, { dur: 1.2, stagger: 0.2 });
      slide(c, TRAY_NUTS.filter((id) => id.startsWith('nut.lower.')), bolts + 0.3, inward);
    },
  },
  {
    id: 'mid-deck', title: 'Mid deck', view: 'frame',
    text: 'Take the four plugs out first: lift the deck off the plate, then push an M4 screw by hand through each corner hole, from the top, against its plug. Release is untested: if one stays, stop; never cut or push harder. Lower the deck over the post feet by hand; never force it.',
    script(c) {
      c.show(['mid_deck']);
      lower(c, ['mid_deck'], HOLD_IN, { rise: 60, dur: 2.0 });
      c.end = Math.max(c.end, c.start + 3.6);
    },
  },
  {
    id: 'upper-posts', title: 'Upper posts', view: 'tall',
    text: 'Stand the four upper posts on the mid deck, each foot over the one below. Drop an M4 nut into the hex on each upper foot and fix the corner with an M4 × 25 up through both feet and the deck. Push nuts into the side slots of holes 1 and 3 of all four. The frame is now firm.',
    script(c) {
      c.show(each('post.upper'));
      const end = lower(c, each('post.upper'), HOLD_IN, { rise: 120, dur: 2.2 });
      const hex = slide(c, each('nut.mid'), end + 0.3, fromAbove, { dur: 0.8, stagger: 0.15 });
      const bolts = c.screws(each('bolt.mid'), hex + 0.3, { dur: 1.2, stagger: 0.2 });
      slide(c, TRAY_NUTS.filter((id) => id.startsWith('nut.upper.')), bolts + 0.3, inward);
    },
  },
  {
    id: 'node-0', title: 'node-0', view: 'lower',
    text: 'Open each node tray’s rear lip between the corner ribs for the plugs. Fit the ventilated tray on holes 1 and 5 with four M4 × 12, then slide node-0 in.',
    script: (c) => tier(c, 'tray.L0', [{ id: 'node0' }]),
  },
  {
    id: 'node-1', title: 'node-1', view: 'lower',
    text: 'Fit the second ventilated tray on holes 6 and 10 with four M4 × 12, then slide node-1 in.',
    script: (c) => tier(c, 'tray.L1', [{ id: 'node1' }]),
  },
  {
    id: 'node-2', title: 'node-2', view: 'lower',
    text: 'Fit the third ventilated tray on holes 11 and 15 with four M4 × 12, then slide node-2 in.',
    script: (c) => tier(c, 'tray.L2', [{ id: 'node2' }]),
  },
  {
    id: 'drive-tray', title: 'USB drives', view: 'lower',
    text: 'Hang the drive tray on holes 16 and 18 with four M4 × 12. Set the Seagate and the Touro in their rims, sockets to the rear.',
    script: (c) => tier(c, 'drive_tray', [{ id: 'usbA', via: [0, 0, 10] }, { id: 'usbB', via: [0, 0, 10] }]),
  },
  {
    id: 'switch', title: 'Eight-port switch', view: 'upper',
    text: 'Hang the switch shelf on upper holes 1 and 3 with four M4 × 12. Set the switch in its rim with the ports at the back.',
    script: (c) => tier(c, 'switch_shelf', [{ id: 'switch', via: [0, 0, 10] }]),
  },
  {
    id: 'keystone-panel', title: 'Keystone panel', view: 'rear-upper',
    text: 'Snap RJ45 couplers into slots 1 and 2 and blanks into 3 and 4. Fix the panel across the rear upper posts with four M4 × 12.',
    script(c) {
      c.show(['keystone_panel']);
      const p = c.move('keystone_panel', HOLD_IN, 2.0, { from: [0, 90, 0], via: [0, 12, 0] });
      const s = c.screws(['sLlo', 'sLhi', 'sRlo', 'sRhi'].map((k) => `keystone_panel.${k}`), p + 0.2);
      ['key1', 'key2', 'key3', 'key4'].forEach((id, i) => {
        c.showAt([id], s + 0.3 + i * 0.35);
        c.move(id, s + 0.5 + i * 0.35, 1.2, { from: [0, 40, 0] });
      });
    },
  },
  {
    id: 'top-cap', title: 'Top cap', view: 'tall',
    text: 'Push an M4 nut into the slot near the top of each upper post, from behind. Lower the top cap onto the posts and fix it with four M4 × 25 socket screws down into those nuts. Lift the rack by its two grips.',
    script(c) {
      c.show(['top_cap']);
      const nuts = slide(c, each('nut.cap'), HOLD_IN, fromBehind, { dur: 0.9, stagger: 0.2 });
      const end = lower(c, ['top_cap'], nuts + 0.3, { rise: 150, settle: 18, dur: 2.6 });
      c.screws(each('bolt.cap'), end + 0.3, { dur: 1.4, stagger: 0.25 });
    },
  },
  {
    id: 'power-leads', title: 'Power leads', view: 'rear',
    text: 'Bring each Lenovo cord straight up behind the nodes and plug it in: node-0 takes the front one. The switch cord rises at the rear right, through the mid deck slot, to the switch.',
    script: hold(6.4),
  },
  ...CRIMP_CHAPTERS,
  {
    id: 'ethernet', section: 'Leads in and done', title: 'Ethernet', view: 'rear',
    text: 'Plug in the leads you crimped: the blue ones from the nodes up the rear left to switch ports 7, 6 and 5, yellow from port 1 to keystone 1 and green from port 4 to keystone 2. Keystone 1 goes out to the router on the wall.',
    script: hold(6.4),
  },
  {
    id: 'usb-zigbee', title: 'USB and Zigbee', view: 'zigbee',
    text: 'Plug both drives into node-0 and hang each lead’s spare in one loop behind the nodes. A 1.5 m USB 2 extension takes the Zigbee dongle to its printed mast, 1 m or more from every USB 3 port.',
    script(c) {
      c.show(['zigbee_mast', 'dongle']);
      const m = c.move('zigbee_mast', HOLD_IN, 1.6, { from: [0, 0, 40], via: [0, 0, 6] });
      c.move('dongle', m + 0.2, 1.2, { from: [0, 0, 36] });
      c.end = Math.max(c.end, c.start + 6.4);
    },
  },
  {
    id: 'soyrack', title: 'Soyrack', view: 'tall',
    text: 'Done: 245 × 240 mm and 388 mm tall, held together by M4 screws and nuts. It stands on the TV unit on its four pads: no holes, screws or glue in the unit. Rotate the view or rewind to any chapter.',
    script: hold(4.8),
  },
];
