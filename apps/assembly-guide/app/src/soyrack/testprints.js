// The four test prints and how each fit is checked before the big parts print: what goes where,
// how and with what. Each piece is cut from the part it tests, so its holes keep their rack
// positions from cad/soyrack.scad; a pose places a piece's mesh centre on the table under the rack.

import { add3, sub3, qaxis, qrotate, basisQuat } from '../math.js';
import { HOLD_IN } from '../timeline.js';
import { FLOOR_Z } from './rack.js';
import { buildCoupler, buildInsert, buildIron } from './models.js';

const ID_Q = [0, 0, 0, 1];

// Mesh bounding boxes of the four pieces (centre and size), from their cuts in soyrack.scad.
export const PIECES = {
  post: { id: 'coupon.post', part: 'coupon_post', centre: [14, 14.5, 35], size: [20, 23, 76] },
  corner: { id: 'coupon.corner', part: 'coupon_corner', centre: [26.5, 22.5, -4], size: [45, 45, 8] },
  nut: { id: 'coupon.nut', part: 'coupon_nut', centre: [20.5, 19.5, -82.2], size: [33, 39, 22.4] },
  keystone: { id: 'coupon.keystone', part: 'coupon_keystone', centre: [36, 1.2, 17], size: [72, 2.4, 34] },
};

// Features in rack millimetres: the tie rod axis (post end, corner and nut corner), the post end's
// insert holes 1 and 2 on its front face, the top of the nut corner's hex hole, and the strip's
// windows on its plain face (2.4 mm plate, then 2.0 mm).
export const ROD = [12, 19];
export const HOLES = [[18.97, 3, 25], [18.97, 3, 35]];
export const HEX_TOP = -77;
export const WINDOWS = [[18, 0, 17], [54, 0, 17]];

/** World position of rack point `r` of a piece placed at `pose`. */
export const onPiece = (piece, pose, r) => add3(pose.p, qrotate(pose.q, sub3(r, PIECES[piece].centre)));

const standing = (piece, x, y) => ({ p: [x, y, FLOOR_Z + PIECES[piece].size[2] / 2], q: ID_Q });
export const POSES = {
  post: standing('post', 24, 88),
  corner: standing('corner', 78, 88),
  nut: standing('nut', 138, 88),
  keystone: standing('keystone', 206, 88),
};
// The post end pressed into the corner's pocket: the two keep their rack offset.
POSES.seated = { p: add3(POSES.corner.p, sub3(PIECES.post.centre, PIECES.corner.centre)), q: ID_Q };
// On its back for the inserts: holes up, the pocket end to the left.
POSES.lying = { p: [68, 46, FLOOR_Z + PIECES.post.size[1] / 2], q: basisQuat([0, 0, -1], [1, 0, 0]) };
// The nut corner turned over, hex hole up.
POSES.turned = { p: POSES.nut.p, q: [1, 0, 0, 0] };

const rodAxis = onPiece('post', POSES.seated, [...ROD, 0]);
const holeTops = HOLES.map((h) => onPiece('post', POSES.lying, h));
const hexFloor = onPiece('nut', POSES.turned, [...ROD, HEX_TOP]); // the top of the hole, now at the bottom
const windows = WINDOWS.map((w) => onPiece('keystone', POSES.keystone, w));
const DOWN = [0, 0, -1];

/** The pieces and the fasteners the checks use, in the shape of soyrackPlacements. */
export function testPlacements() {
  const instances = Object.entries(PIECES).map(([key, { id, part }]) => ({ id, group: 'world', part, p: POSES[key].p, q: ID_Q }));
  const screw = (id, type, head, out) => ({ id, group: 'world', type, head, dir: DOWN, out });
  const screws = [
    // A tie rod slid down through the post end and the corner to the table.
    screw('coupon.rod', 'm5rod', [rodAxis[0], rodAxis[1], FLOOR_Z + 300], 120),
    // An M4 x 12 screw threaded into the first insert, its head on the insert.
    screw('coupon.m4', 'm4x12', add3(holeTops[0], [0, 0, 2]), 26),
    // The M5 nut at the bottom of the turned hex hole, and an M5 x 50 screw caught in it.
    screw('coupon.nut5', 'm5nut', add3(hexFloor, [0, 0, 4]), 40),
    screw('coupon.bolt', 'm5x50', add3(hexFloor, [0, 0, 53]), 30),
  ];
  return { groups: {}, instances, screws };
}

const INSERTS = ['coupon.insert1', 'coupon.insert2'];
const KEYS = ['coupon.key24', 'coupon.key20'];
const IRON = 'coupon.iron';

export const TEST_DEVICES = [
  ...holeTops.map((p, i) => ({ id: INSERTS[i], model: 'insert', size: [6.3, 6.3, 8.1], centre: p, build: buildInsert })),
  { id: IRON, model: 'iron', size: [13.5, 13.5, 152], centre: add3(holeTops[0], [0, 0, 40]), build: buildIron },
  ...windows.map((p, i) => ({ id: KEYS[i], model: 'coupler', size: [16.6, 30, 18.4], centre: p, build: buildCoupler })),
];

// ---------------------------------------------------------------- chapters

const POST = PIECES.post.id;
const CORNER = PIECES.corner.id;
const NUT = PIECES.nut.id;
const STRIP = PIECES.keystone.id;
const ALL = [POST, CORNER, NUT, STRIP];

/** Opacity of `ids` from `a` to `b`, starting `at` seconds into the chapter. */
function fade(c, ids, at, [a, b], dur = 0.5) {
  const t = c.start + at;
  for (const id of ids) c.get(id).alpha.push({ t, v: a }, { t: t + dur, v: b });
  c.end = Math.max(c.end, t + dur);
}

const SEE_THROUGH = 0.3;

export const TEST_CHAPTERS = [
  {
    id: 'test-prints', title: 'Test prints first', view: 'prints',
    text: 'Print these four small pieces before the big parts. Each checks one fit the rack depends on, and the next chapters show what goes where and with what. The post end and the corner need nothing else; the rest wait for the ordered parts.',
    tags: [
      { text: 'Post end', node: POST, at: [0, 0, 38], side: 'n', from: 1.5 },
      { text: 'Deck corner', node: CORNER, at: [8, -18, 4], side: 'sw', from: 1.9 },
      { text: 'Nut corner', node: NUT, at: [0, -12, 11.2], side: 'se', from: 2.4 },
      { text: 'Keystone strip', node: STRIP, at: [0, 0, 17], side: 'n', from: 2.8 },
    ],
    script(c) {
      c.show(ALL);
      ALL.forEach((id, i) => c.move(id, HOLD_IN + i * 0.45, 1.5, { from: [0, 0, 30], via: [0, 0, 6] }));
      c.end = Math.max(c.end, c.start + 7);
    },
  },
  {
    id: 'test-corner', title: 'Post end into the deck corner', view: 'test-corner',
    text: 'Press the post end into the square pocket by hand. Good: it goes all the way down without forcing and does not rock. When the rods arrive, one should slide down through both pieces.',
    tags: [
      { text: 'Square pocket, 3 mm deep', node: CORNER, at: [-12.5, -8, 4], side: 'sw', until: 3.6 },
      { text: 'All the way in by hand, no rocking', node: POST, at: [0, -11.5, -26], side: 'w', from: 4.9, until: 7.0 },
      { text: 'M5 × 300 rod slides through', node: 'coupon.rod', at: [0, 290, 0], side: 'e', from: 7.6 },
    ],
    script(c) {
      const { post: rest, seated } = POSES;
      const t = HOLD_IN;
      c.path(POST, [
        { at: t, p: rest.p, q: ID_Q },
        { at: t + 0.9, p: add3(rest.p, [0, 0, 32]), q: ID_Q },
        { at: t + 2.1, p: add3(seated.p, [0, 0, 24]), q: ID_Q },
        { at: t + 2.8, p: add3(seated.p, [0, 0, 3.5]), q: ID_Q },
        { at: t + 3.9, p: seated.p, q: ID_Q, e: 'settle' },
      ]);
      const r = t + 6.4;
      fade(c, [POST, CORNER], r - 0.4, [1, SEE_THROUGH]);
      const end = c.screws(['coupon.rod'], r, { dur: 2.6 });
      fade(c, [POST, CORNER], end + 0.8, [SEE_THROUGH, 1]);
    },
  },
  {
    id: 'test-inserts', title: 'Brass inserts in the post end', view: 'test-inserts',
    text: 'Lay the post end holes up. Set an M4 insert on hole 1, rest the soldering iron in it at about 230 °C and let it sink straight in until flush, then do hole 2. Once cool, an M4 × 12 screw should thread in and hold firm.',
    tags: [
      { text: 'M4 brass insert', node: INSERTS[0], at: [0, 0, 0], side: 'w', from: 4.6, until: 7.4 },
      { text: 'Soldering iron, about 230 °C', node: IRON, at: [0, 0, 34], side: 'e', from: 5.0, until: 10.9 },
      { text: 'Flush with the face', node: INSERTS[0], at: [0, 0, 0], side: 'w', from: 7.6, until: 11.2 },
      { text: 'M4 × 12 screw threads in and holds', node: 'coupon.m4', at: [0, 0, 0], side: 'w', from: 12.4 },
    ],
    script(c) {
      // The rod comes out, and the post end lifts out of the corner and lies on its back.
      const rod = c.get('coupon.rod').final;
      c.path('coupon.rod', [
        { at: 0.2, p: rod.p, q: rod.q },
        { at: 1.4, p: add3(rod.p, [0, 0, 170]), q: rod.q, e: 'in' },
      ], { highlight: false });
      fade(c, ['coupon.rod'], 1.2, [1, 0], 0.2);
      const { seated, lying } = POSES;
      c.path(POST, [
        { at: 1.0, p: seated.p, q: ID_Q },
        { at: 1.8, p: add3(seated.p, [0, 0, 28]), q: ID_Q },
        { at: 3.2, p: add3(lying.p, [0, 0, 26]), q: lying.q },
        { at: 4.0, p: lying.p, q: lying.q, e: 'settle' },
      ]);
      // Each insert stands on its hole; the iron's tip rests in it and both sink until it is flush.
      const SIT = 7.8;
      const TIP_IN = 1.5;
      const iron = [];
      let t = 4.4;
      holeTops.forEach((flush, i) => {
        const sit = add3(flush, [0, 0, SIT]);
        c.showAt([INSERTS[i]], t);
        c.path(INSERTS[i], [
          { at: t, p: sit, q: ID_Q },
          { at: t + 1.0, p: sit, q: ID_Q },
          { at: t + 2.6, p: flush, q: ID_Q, e: 'settle' },
        ]);
        if (i === 0) c.showAt([IRON], t + 0.3);
        iron.push(
          { at: t + 0.3, p: add3(sit, [0, 0, i ? 30 : 64]), q: ID_Q },
          { at: t + 1.0, p: add3(sit, [0, 0, -TIP_IN]), q: ID_Q },
          { at: t + 2.6, p: add3(flush, [0, 0, -TIP_IN]), q: ID_Q, e: 'settle' },
          { at: t + 3.2, p: add3(flush, [0, 0, 36]), q: ID_Q },
        );
        t += 3.4;
      });
      c.path(IRON, iron, { highlight: false });
      fade(c, [IRON], t - 0.3, [1, 0]);
      c.screws(['coupon.m4'], t + 0.4, { dur: 1.4 });
    },
  },
  {
    id: 'test-nut', title: 'M5 nut in the nut corner', view: 'test-nut',
    text: 'Turn the nut corner over. An M5 nut should drop down the hex hole by itself and sit flat at the bottom. Thread an M5 screw in from above: the nut must not turn with it.',
    tags: [
      { text: 'Hex hole up', node: NUT, at: [-8.5, -0.5, -11.2], side: 'nw', from: 4.0, until: 5.0 },
      { text: 'M5 nut drops in and sits flat', node: 'coupon.nut5', at: [0, 2, 0], side: 'w', from: 5.2, until: 7.6 },
      { text: 'M5 × 50 screw: the nut must not turn', node: 'coupon.bolt', at: [0, 30, 0], side: 'e', from: 7.2 },
    ],
    script(c) {
      const { nut: rest, turned } = POSES;
      const t = HOLD_IN;
      c.path(NUT, [
        { at: t, p: rest.p, q: ID_Q },
        { at: t + 0.8, p: add3(rest.p, [0, 0, 22]), q: ID_Q },
        { at: t + 1.5, p: add3(rest.p, [0, 0, 26]), q: qaxis([1, 0, 0], Math.PI / 2), e: 'in' },
        { at: t + 2.2, p: add3(rest.p, [0, 0, 22]), q: turned.q, e: 'out' },
        { at: t + 3.0, p: turned.p, q: turned.q, e: 'settle' },
      ]);
      const n = t + 3.5;
      fade(c, [NUT], n, [1, SEE_THROUGH]);
      const nutEnd = c.screws(['coupon.nut5'], n + 0.3, { dur: 1.6 });
      const boltEnd = c.screws(['coupon.bolt'], nutEnd + 0.5, { dur: 1.8 });
      fade(c, [NUT], boltEnd + 1.0, [SEE_THROUGH, 1]);
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
    text: 'Send one word per check: good, tight or loose, and which plate held the coupler firmly. I adjust the files and send new pieces to print. When all four are good, print the rack.',
    tags: [
      { text: 'In by hand, no rocking?', node: CORNER, at: [-12.5, -8, 4], side: 'nw', until: 5.6 },
      { text: 'Inserts flush, screw holds?', node: INSERTS[1], at: [0, 0, 0], side: 's', until: 5.6 },
      { text: 'Nut drops in, does not turn?', node: NUT, at: [0, 0, -11.2], side: 'n', until: 5.6 }, // turned over: local -z is up
      { text: '2.4 or 2.0: which holds firm?', node: STRIP, at: [0, 0, 17], side: 'ne', until: 5.6 },
    ],
    script(c) {
      fade(c, [...ALL, ...INSERTS, 'coupon.m4', 'coupon.nut5', 'coupon.bolt', ...KEYS], HOLD_IN + 5.0, [1, 0], 0.8);
    },
  },
];
