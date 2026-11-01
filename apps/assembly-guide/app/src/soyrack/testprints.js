// The four test prints and how each fit is checked before the big parts print: what goes where,
// how and with what. Each piece is cut from the part it tests, so its holes keep their rack
// positions from cad/soyrack.scad; a pose places a piece's mesh centre on the table under the rack.

import { add3, sub3, qaxis, qfromTo, qmul, qrotate } from '../math.js';
import { HOLD_IN } from '../timeline.js';
import { FLOOR_Z } from './rack.js';
import { buildCoupler } from './models.js';

const ID_Q = [0, 0, 0, 1];

// Mesh bounding boxes of the four pieces (centre and size), from their cuts in soyrack.scad.
export const PIECES = {
  post: { id: 'coupon.post', part: 'coupon_post', centre: [14, 20.5, 19], size: [20, 35, 44] },
  corner: { id: 'coupon.corner', part: 'coupon_corner', centre: [26.5, 25.5, -4], size: [45, 51, 8] },
  base: { id: 'coupon.base', part: 'coupon_base', centre: [14, 20, -17.5], size: [20, 40, 19] },
  keystone: { id: 'coupon.keystone', part: 'coupon_keystone', centre: [36, 1.2, 17], size: [72, 2.4, 34] },
};

// Features in rack millimetres: the corner screw axis through the post end's foot, the deck
// corner and the base corner, the top of the foot and the underside of the nut in the base
// corner's slot; tray holes 1 and 2 on the post end's front face and the depth of their nuts
// behind it; the strip's windows on its plain face (2.4 mm plate, then 2.0 mm).
export const JOINT = [14, 32];
export const FOOT_TOP = 5;
export const BASE_NUT = -17.2;
export const HOLES = [[18.97, 3, 25], [18.97, 3, 35]];
export const NUT_Y = 6;
export const WINDOWS = [[18, 0, 17], [54, 0, 17]];

/** World position of rack point `r` of a piece placed at `pose`. */
export const onPiece = (piece, pose, r) => add3(pose.p, qrotate(pose.q, sub3(r, PIECES[piece].centre)));

const standing = (piece, x, y) => ({ p: [x, y, FLOOR_Z + PIECES[piece].size[2] / 2], q: ID_Q });
export const POSES = {
  post: standing('post', 24, 88),
  corner: standing('corner', 78, 88),
  base: standing('base', 130, 88),
  keystone: standing('keystone', 212, 88),
};
// The deck corner set on the base corner, and the post end pressed into its pocket: all three
// keep their rack offsets.
POSES.deckOn = { p: add3(POSES.base.p, sub3(PIECES.corner.centre, PIECES.base.centre)), q: ID_Q };
POSES.seated = { p: add3(POSES.deckOn.p, sub3(PIECES.post.centre, PIECES.corner.centre)), q: ID_Q };

const UP = [0, 0, 1];
const DOWN = [0, 0, -1];
const BACK = [0, 1, 0];
// A nut turned so its flats meet the walls of the slot it pushes into sideways.
const inSlot = (dir) => qmul(qfromTo([0, 1, 0], dir), qaxis([0, 1, 0], Math.PI / 6));

const NUT = 'coupon.nut';
const BOLT = 'coupon.bolt';
const TRAY_NUTS = ['coupon.tnut1', 'coupon.tnut2'];
const TRAY_SCREWS = ['coupon.m4a', 'coupon.m4b'];
const KEYS = ['coupon.key24', 'coupon.key20'];

/** The pieces and the fasteners the checks use, in the shape of soyrackPlacements. */
export function testPlacements() {
  const instances = Object.entries(PIECES).map(([key, { id, part }]) => ({ id, group: 'world', part, p: POSES[key].p, q: ID_Q }));
  const fastener = (id, type, head, dir, out, q) => ({ id, group: 'world', type, head, dir, out, ...(q && { q }) });
  const screws = [
    // The nut in the base corner's slot, and the M4 x 25 screw down through the foot and the deck corner into it.
    fastener(NUT, 'm4nut', onPiece('base', POSES.base, [...JOINT, BASE_NUT]), UP, 0, inSlot(UP)),
    fastener(BOLT, 'm4x25', onPiece('post', POSES.seated, [...JOINT, FOOT_TOP]), DOWN, 40),
    // A nut in the side slot of tray holes 1 and 2, and an M4 x 12 screw from the front into each:
    // with no shelf in front, its head stands on the face.
    ...HOLES.map(([x, , z], i) => fastener(TRAY_NUTS[i], 'm4nut', onPiece('post', POSES.seated, [x, NUT_Y, z]), BACK, 0, inSlot(BACK))),
    ...HOLES.map(([x, y, z], i) => fastener(TRAY_SCREWS[i], 'm4x12', onPiece('post', POSES.seated, [x, y - 2, z]), BACK, 26)),
  ];
  return { groups: {}, instances, screws };
}

export const TEST_DEVICES = WINDOWS.map((w, i) => ({
  id: KEYS[i], model: 'coupler', size: [16.6, 30, 18.4], centre: onPiece('keystone', POSES.keystone, w), build: buildCoupler,
}));

// ---------------------------------------------------------------- chapters

const POST = PIECES.post.id;
const CORNER = PIECES.corner.id;
const BASE = PIECES.base.id;
const STRIP = PIECES.keystone.id;
const ALL = [POST, CORNER, BASE, STRIP];

/** Opacity of `ids` from `a` to `b`, starting `at` seconds into the chapter. */
function fade(c, ids, at, [a, b], dur = 0.5) {
  const t = c.start + at;
  for (const id of ids) c.get(id).alpha.push({ t, v: a }, { t: t + dur, v: b });
  c.end = Math.max(c.end, t + dur);
}

/** Nuts pushed into their slots along -x, one after another; returns the relative end time. */
function slideIn(c, ids, at, { dur = 1.2, stagger = 0.9 } = {}) {
  let end = at;
  ids.forEach((id, i) => {
    const n = c.get(id);
    const t = at + i * stagger;
    c.showAt([id], t);
    c.path(id, [
      { at: t, p: add3(n.final.p, [26, 0, 0]), q: n.final.q },
      { at: t + dur, p: n.final.p, q: n.final.q, e: 'out' },
    ], { highlight: false });
    end = t + dur;
  });
  return end;
}

/** Lift a piece from `from`, carry it over and lower it onto `to`, settling the last few mm. */
function place(c, id, at, from, to, { lift = 30, drop = 3.5 } = {}) {
  c.path(id, [
    { at, p: from.p, q: ID_Q },
    { at: at + 0.8, p: add3(from.p, [0, 0, lift]), q: ID_Q },
    { at: at + 2.0, p: add3(to.p, [0, 0, 20]), q: ID_Q },
    { at: at + 2.7, p: add3(to.p, [0, 0, drop]), q: ID_Q },
    { at: at + 3.7, p: to.p, q: ID_Q, e: 'settle' },
  ]);
  return at + 3.7;
}

const SEE_THROUGH = 0.3;

export const TEST_CHAPTERS = [
  {
    id: 'test-prints', title: 'Test prints first', view: 'prints',
    text: 'Print these four small pieces before the big parts. Each checks a fit the rack depends on, and the next chapters show what goes where and with what: M4 nuts, M4 screws and two keystone couplers, nothing else.',
    tags: [
      { text: 'Post end', node: POST, at: [0, 0, 22], side: 'n', from: 1.5 },
      { text: 'Deck corner', node: CORNER, at: [8, -22, 4], side: 'sw', from: 1.9 },
      { text: 'Base corner', node: BASE, at: [0, -17, 9.5], side: 'se', from: 2.4 },
      { text: 'Keystone strip', node: STRIP, at: [0, 0, 17], side: 'n', from: 2.8 },
    ],
    script(c) {
      c.show(ALL);
      ALL.forEach((id, i) => c.move(id, HOLD_IN + i * 0.45, 1.5, { from: [0, 0, 30], via: [0, 0, 6] }));
      c.end = Math.max(c.end, c.start + 7);
    },
  },
  {
    id: 'test-joint', title: 'Corner joint', view: 'test-joint',
    text: 'This is how each post is held at the bottom. Push an M4 nut into the slot of the base corner until it stops. Set the deck corner on it and press the post end into the pocket by hand: all the way down, no rocking. An M4 × 25 screw down through the foot should catch the nut and pull all three tight.',
    tags: [
      { text: 'M4 nut into the slot', node: NUT, at: [0, 1.6, 0], side: 'e', from: HOLD_IN + 0.2, until: 3.4 },
      { text: 'Pocket for the post end and its foot', node: CORNER, at: [-12.5, -5, 4], side: 'w', from: 6.4, until: 9.0 },
      { text: 'In by hand, no rocking', node: POST, at: [0, -17.5, -14], side: 'w', from: 11.2, until: 12.9 },
      { text: 'M4 × 25 screw pulls it tight', node: BOLT, at: [0, 6, 0], side: 'e', from: 14.4 },
    ],
    script(c) {
      const { corner, deckOn, post, seated } = POSES;
      fade(c, [BASE], HOLD_IN - 0.4, [1, SEE_THROUGH]);
      const nut = slideIn(c, [NUT], HOLD_IN + 0.2, { dur: 1.4 });
      fade(c, [BASE], nut + 0.3, [SEE_THROUGH, 1]);
      const deck = place(c, CORNER, nut + 0.6, corner, deckOn, { drop: 0 });
      const pressed = place(c, POST, deck + 0.4, post, seated, { lift: 40 });
      const b = pressed + 2.6;
      fade(c, [POST, CORNER, BASE], b - 0.5, [1, SEE_THROUGH]);
      const end = c.screws([BOLT], b, { dur: 2.2 });
      fade(c, [POST, CORNER, BASE], end + 0.9, [SEE_THROUGH, 1]);
    },
  },
  {
    id: 'test-tray-nuts', title: 'Nuts for the shelf screws', view: 'test-tray-nuts',
    text: 'Every tray and shelf screw goes into an M4 nut behind the face of a post. Push a nut into the side slot of hole 1 and of hole 2 until it stops. An M4 × 12 screw from the front should thread into each and pull tight without the nut turning.',
    tags: [
      { text: 'M4 nut into the side slot', node: TRAY_NUTS[0], at: [0, 1.6, 0], side: 'e', from: 1.0, until: 4.4 },
      { text: 'M4 × 12 from the front: the nut must not turn', node: TRAY_SCREWS[1], at: [0, 0, 0], side: 'w', from: 5.6 },
    ],
    script(c) {
      fade(c, [POST], HOLD_IN - 0.4, [1, SEE_THROUGH]);
      const nuts = slideIn(c, TRAY_NUTS, HOLD_IN + 0.2);
      const end = c.screws(TRAY_SCREWS, nuts + 0.5, { dur: 1.6, stagger: 0.9 });
      fade(c, [POST], end + 0.9, [SEE_THROUGH, 1]);
    },
  },
  {
    id: 'test-keystone', title: 'Keystone couplers in the strip', view: 'test-keystone',
    text: 'A keystone coupler is the snap-in RJ45 socket block that sits in the rack\'s rear panel. Push one into each window from the plain side until its clip clicks. Keep the plate where it sits firm without wobbling: 2.4 mm is what the panel uses now.',
    tags: [
      { text: 'Keystone coupler: an RJ45 socket at each end', node: KEYS[0], at: [0, -15, 8], side: 'nw', from: 1.2, until: 4.9 },
      { text: '2.4 mm plate, as in the panel', node: STRIP, at: [-18, 0, 17], side: 'n', from: 3.4 },
      { text: '2.0 mm plate', node: STRIP, at: [18, 0, 17], side: 'n', from: 5.9 },
      { text: 'Clicks in and holds firm', node: KEYS[1], at: [0, -15, -8], side: 's', from: 6.3 },
    ],
    script(c) {
      const tilt = qaxis([1, 0, 0], 0.16);
      KEYS.forEach((id, i) => {
        const t = HOLD_IN + i * 2.6;
        const f = c.get(id).final.p;
        c.showAt([id], t);
        c.path(id, [
          { at: t, p: add3(f, [0, -64, 8]), q: tilt },
          { at: t + 1.1, p: add3(f, [0, -18, 2]), q: tilt },
          { at: t + 1.6, p: add3(f, [0, -6, 0]), q: ID_Q },
          { at: t + 2.3, p: f, q: ID_Q, e: 'settle' },
        ]);
      });
      c.end = Math.max(c.end, c.start + HOLD_IN + 2.6 + 2.3 + 1.2);
    },
  },
  {
    id: 'test-report', title: 'Tell me how each one fits', view: 'test-report',
    text: 'Send one word per check: good, tight or loose, and which plate held the coupler firmly. I adjust the files and send new pieces to print. When all are good, print the rack.',
    tags: [
      { text: 'In by hand, no rocking?', node: CORNER, at: [-12.5, -5, 4], side: 'nw', until: 5.6 },
      { text: 'Screw pulls the joint tight?', node: BOLT, at: [0, 0, 0], side: 'n', until: 5.6 },
      { text: 'Nuts slide in, screws hold?', node: TRAY_SCREWS[1], at: [0, 0, 0], side: 'e', until: 5.6 },
      { text: '2.4 or 2.0: which holds firm?', node: STRIP, at: [0, 0, 17], side: 'ne', until: 5.6 },
    ],
    script(c) {
      fade(c, [...ALL, NUT, BOLT, ...TRAY_NUTS, ...TRAY_SCREWS, ...KEYS], HOLD_IN + 5.0, [1, 0], 0.8);
    },
  },
];
