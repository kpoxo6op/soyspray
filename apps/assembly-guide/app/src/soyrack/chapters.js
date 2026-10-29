// Soyrack (v3) build order. Same chapter API as the v1/v2 guide: every pose is a function of time.

import { HOLD_IN, tier } from '../timeline.js';

const CORNERS = ['FL', 'FR', 'RL', 'RR'];
const each = (prefix) => CORNERS.map((k) => `${prefix}.${k}`);

/** Fade parts out `at` seconds into the chapter. */
function hide(c, ids, at, dur = 0.8) {
  const t = c.start + at;
  for (const id of ids) c.get(id).alpha.push({ t, v: 1 }, { t: t + dur, v: 0 });
  c.end = Math.max(c.end, t + dur);
}

/** A chapter in which no part moves, `seconds` long; the stage lays its cords meanwhile. */
const hold = (seconds) => (c) => { c.end = c.start + seconds; };

/** Lower parts one after another from `rise` mm above, slowing for the last `settle` mm. */
function lower(c, ids, at, { rise, settle = 14, dur = 2.2, stagger = 0.3 } = {}) {
  let end = at;
  ids.forEach((id, i) => {
    end = c.move(id, at + i * stagger, dur, { from: [0, 0, rise], via: [0, 0, settle], viaAt: 0.7 });
  });
  return end;
}

export const SOYRACK_CHAPTERS = [
  {
    id: 'test-prints', title: 'Test prints first', view: 'prints',
    text: 'Print these four small pieces before the big parts: a post end, a deck corner, a nut corner and a keystone strip. Press two M4 inserts into the post end, push it into the corner, seat a nut, and snap a coupler into each keystone slot.',
    script(c) {
      const ids = ['coupon.post', 'coupon.corner', 'coupon.nut', 'coupon.keystone'];
      c.show(ids);
      ids.forEach((id, i) => c.move(id, HOLD_IN + i * 0.45, 1.5, { from: [0, 0, 30], via: [0, 0, 6] }));
      hide(c, ids, HOLD_IN + 6.4);
    },
  },
  {
    id: 'power-base', title: 'Power base', view: 'base',
    text: 'Push an M5 nut up the hex hole under each corner of the base, then a printed foot: its peg holds the nut at the top of the hole. Stick a 20 mm silicone pad under each foot.',
    script(c) {
      c.show(['base_tub']);
      const end = c.move('base_tub', HOLD_IN, 2.0, { from: [0, 0, 60], via: [0, 0, 10] });
      const nuts = c.screws(each('nut'), end + 0.3, { dur: 1.0, stagger: 0.2 });
      c.showAt(each('foot'), nuts + 0.2);
      CORNERS.forEach((k, i) => c.move(`foot.${k}`, nuts + 0.4 + i * 0.2, 1.4, { from: [0, 0, -28] }));
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
    id: 'tie-rods', title: 'Tie rods', view: 'frame',
    text: 'Screw an M5 × 300 mm rod down through each corner until it fills its nut. The rods tie the stack together from the feet to the top cap.',
    script(c) {
      c.screws(each('rod'), HOLD_IN, { dur: 2.4, stagger: 0.3 });
    },
  },
  {
    id: 'base-deck', title: 'Base deck', view: 'frame',
    text: 'Lower the base deck over the rods onto the base, threading the switch cord up through its right rear slot. The Lenovo cords stand behind it.',
    script(c) {
      c.show(['base_deck']);
      lower(c, ['base_deck'], HOLD_IN, { rise: 240, dur: 2.6 });
    },
  },
  {
    id: 'lower-posts', title: 'Lower posts', view: 'frame',
    text: 'With a soldering iron, press M4 inserts into holes 1, 5, 6, 10, 11, 15, 16 and 18 of both front posts. Slide the four posts down the rods into the deck pockets, numbers facing out.',
    script(c) {
      c.show(each('post.lower'));
      lower(c, each('post.lower'), HOLD_IN, { rise: 232, dur: 2.4 });
    },
  },
  {
    id: 'mid-deck', title: 'Mid deck', view: 'frame',
    text: 'Lower the mid deck onto the posts. Add an M5 washer and an M5 × 30 coupling nut to each rod, hand tight plus a quarter turn. The lower bay is now one firm frame.',
    script(c) {
      c.show(['mid_deck']);
      const end = lower(c, ['mid_deck'], HOLD_IN, { rise: 60, dur: 2.0 });
      const w = c.screws(each('washer'), end + 0.3, { dur: 0.9, stagger: 0.15 });
      c.screws(each('coupler'), w + 0.2, { dur: 1.3, stagger: 0.2 });
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
    id: 'upper-posts', title: 'Upper posts', view: 'tall',
    text: 'Press inserts into holes 1 and 3 of all four upper posts. Slide them over the coupling nuts into the mid deck.',
    script(c) {
      c.show(each('post.upper'));
      lower(c, each('post.upper'), HOLD_IN, { rise: 120, dur: 2.2 });
    },
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
    text: 'Lower the top cap onto the posts. Four M5 × 50 socket screws go down into the coupling nuts and lock the stack. Lift the rack by its two grips.',
    script(c) {
      c.show(['top_cap']);
      const end = lower(c, ['top_cap'], HOLD_IN, { rise: 150, settle: 18, dur: 2.6 });
      c.screws(each('capscrew'), end + 0.3, { dur: 1.6, stagger: 0.25 });
    },
  },
  {
    id: 'power-leads', title: 'Power leads', view: 'rear',
    text: 'Bring each Lenovo cord straight up behind the nodes and plug it in: node-0 takes the front one. The switch cord rises at the rear right, through the mid deck slot, to the switch.',
    script: hold(6.4),
  },
  {
    id: 'ethernet', title: 'Ethernet', view: 'rear',
    text: 'Crimp Cat6 leads to length: the nodes up the rear left to switch ports 7, 6 and 5, port 1 to keystone 1 and port 4 to keystone 2. Keystone 1 goes out to the router on the wall.',
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
    text: 'Done: 245 × 240 mm, 392 mm tall, feet under the tie rods. Pick v2 in the menu to compare, rotate the view, or rewind to any chapter.',
    script: hold(4.8),
  },
];
