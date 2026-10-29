// Soyrack (v3): a printable PETG rack for three Lenovo M920q Tiny nodes, with a power base,
// drive tray, switch and router shelves and a keystone Ethernet panel. Four steel M5 tie rods
// run through the posts, so the printed parts only carry compression.
//
// Rack frame, mm: x left -> right, y front -> rear, z up. z = 0 is the top of the base deck
// (the lower bay floor). The v1/v2 node trays hang on the same grid: screw holes at
// x 18.97 and 234.03, z = 25 + 10k, on the post faces at y = 3 (front) and y = 206 (rear).
//
//   openscad -D 'part="post_lower_a"' -o post_lower_a.stl soyrack.scad
//
// part    one of PARTS, or "assembly" to preview everything in place
// orient  "print" lays the part on the bed, "world" keeps its rack position
// web     true for the lighter meshes the browser guide uses

use <LiberationSans-Bold.ttf>

part = "assembly";
orient = "print";
web = false;

PARTS = ["base_tub", "base_deck", "post_lower_a", "post_lower_b", "mid_deck",
         "post_upper_a", "post_upper_b", "top_cap", "drive_tray", "switch_shelf",
         "router_shelf", "keystone_panel", "foot", "zigbee_mast",
         "coupon_post", "coupon_corner", "coupon_nut", "coupon_keystone"];

$fn = web ? 18 : 48;
E = 0.01;
FONT = "Liberation Sans:style=Bold";

// ------------------------------------------------------------------ frame

REF_W = 253;                 // width of the v1/v2 frame: the centre line stays at x = 126.5
CX = REF_W / 2;
DEPTH = 209;                 // decks span y 0..209
X0 = 4; X1 = REF_W - X0;     // outer faces of posts and decks: 245 mm
CR = 6;                      // plan corner radius

// Posts, front-left numbers. The others are mirrored (front-right) or turned (rear).
POST = [X0, 3, 20, 23];      // x, y, width, depth: x 4..24 clears the tray gussets at x 25
ROD = [12, 19];              // M5 tie rod axis
ROD_D = 5.6;
HOLE_X = 18.97;              // tray screw holes; the right-hand ones at REF_W - HOLE_X
PILOT_D = 5.6; PILOT_L = 10; // M4 x 8.1 heat-set insert, 6.3 mm OD (Ruthex size)
POCKET = 3; FIT = 0.25;      // post ends sit 3 mm deep in the decks
LOWER = [-3, 203];
UPPER = [205, 313];
LOWER_HOLES = [for (k = [0 : 17]) 25 + 10 * k];   // holes 1..18, hole n at z = 15 + 10n
UPPER_HOLES = [for (k = [0 : 6]) 235 + 10 * k];   // holes 1..7
COUPLER_TOP = 237;           // M5 washer + M5 x 30 coupling nut + 1 mm, inside the upper post
BORE_D = 10.4;

BASE_Z = [-84, -8];          // power base tub
BASE_DEPTH = 240;            // the rear 31 mm is the open board trough
TROUGH = [205, 237.6];
DECK_Z = [-8, 0];
MID_Z = [200, 208];
CAP_Z = [310, 320];
WALL = 2.4; FLOOR = 2.4;
NUT_AF = 8.25; NUT_POCKET = 7;   // M5 nut under each tub corner
HEAD_D = 9.5; HEAD_H = 5.2;      // M5 x 90 socket head in the top cap

// Bricks stand on edge, long side front to back, 14 mm apart, clear of the front corner blocks.
// The DC cord leaves the front end and turns up; the C5 inlet faces the board at the rear.
BRICK_X = [40, 83, 126];
BRICK_Y = [26, 138];

// Equipment envelopes (x, y, z sizes) and positions of their minimum corners.
SWITCH = [[158, 101, 26], [47.5, 10]];
ROUTER = [[148, 100.5, 30], [52.5, 10]];
SEAGATE = [[78, 114.8, 11.7], [40.5, 12]];
TOURO = [[80, 112, 20.5], [132.5, 12]];
ANTENNA_X = [CX - 62, CX, CX + 62];
ANTENNA_Y = ROUTER[1][1] + ROUTER[0][1] + 3;

function rods() = [[ROD[0], ROD[1]], [REF_W - ROD[0], ROD[1]],
                   [ROD[0], DEPTH - ROD[1]], [REF_W - ROD[0], DEPTH - ROD[1]]];
// post footprints [x0, y0, x1, y1]
function post_boxes() = [
  [POST[0], POST[1], POST[0] + POST[2], POST[1] + POST[3]],
  [REF_W - POST[0] - POST[2], POST[1], REF_W - POST[0], POST[1] + POST[3]],
  [POST[0], DEPTH - POST[1] - POST[3], POST[0] + POST[2], DEPTH - POST[1]],
  [REF_W - POST[0] - POST[2], DEPTH - POST[1] - POST[3], REF_W - POST[0], DEPTH - POST[1]]];

// ------------------------------------------------------------------ helpers

module rrect(size, r) {
  rr = min(r, size[0] / 2 - E, size[1] / 2 - E);
  if (rr <= 0) square(size);
  else translate([rr, rr]) offset(r = rr) square([size[0] - 2 * rr, size[1] - 2 * rr]);
}

module rbox(size, r) linear_extrude(size[2]) rrect([size[0], size[1]], r);

// Rectangle with 45-degree corners of size c.
module crect(size, c) translate([c, c]) offset(delta = c, chamfer = true) square([size[0] - 2 * c, size[1] - 2 * c]);

// Box with chamfered vertical edges (c) and chamfered ends (e).
module cbox(size, c = 1.2, e = 0.6) hull() {
  translate([e, e, 0]) linear_extrude(E) crect([size[0] - 2 * e, size[1] - 2 * e], max(c - e, 0.2));
  translate([0, 0, e]) linear_extrude(size[2] - 2 * e) crect([size[0], size[1]], c);
  translate([e, e, size[2] - E]) linear_extrude(E) crect([size[0] - 2 * e, size[1] - 2 * e], max(c - e, 0.2));
}

// Horizontal holes print round with a pointed roof: the point faces +y, which is up
// when a post lies on its front face.
module teardrop2d(d) {
  r = d / 2;
  circle(r = r);
  polygon([[-r * 0.7071, r * 0.7071], [r * 0.7071, r * 0.7071], [0, r * 1.4142]]);
}

module slot2d(l, w) hull() for (x = [-(l - w) / 2, (l - w) / 2]) translate([x, 0]) circle(d = w);

// Heat-set insert pilot drilled from a face along +y.
module pilot_y() rotate([-90, 0, 0]) {
  translate([0, 0, -E]) cylinder(d = PILOT_D, h = PILOT_L + E);
  translate([0, 0, -E]) cylinder(d1 = PILOT_D + 1.2, d2 = PILOT_D, h = 0.6 + E);
}

// Countersunk M4 clearance through a plate of thickness t, head on the y = 0 side.
module csk_y(t) rotate([-90, 0, 0]) {
  translate([0, 0, -1]) cylinder(d = 4.5, h = t + 2);
  translate([0, 0, -E]) cylinder(d1 = 9.0, d2 = 4.5, h = 2.25 + E);
}

// Engrave 2D children into a face that looks towards -y (front) at y = face.
module on_front(face, at, depth = 0.45)
  translate([at[0], face + depth, at[1]]) rotate([90, 0, 0]) linear_extrude(depth + E) children();

// Engrave into a face that looks towards +y (rear) at y = face.
module on_rear(face, at, depth = 0.45)
  translate([at[0], face - depth, at[1]]) rotate([90, 0, 180]) linear_extrude(depth + E) children();

module label(s, size) if (!web) text(s, size = size, font = FONT, halign = "center", valign = "center");

module mirror_x() translate([REF_W, 0, 0]) mirror([1, 0, 0]) children();
module turn() translate([CX, DEPTH / 2, 0]) rotate(180) translate([-CX, -DEPTH / 2, 0]) children();

// Pockets for the four post ends between z0 and z1.
module post_pockets(z0, z1) for (b = post_boxes())
  translate([b[0] - FIT, b[1] - FIT, z0]) linear_extrude(z1 - z0) crect([b[2] - b[0] + 2 * FIT, b[3] - b[1] + 2 * FIT], 1.2);

module rod_holes(z0, z1, d = ROD_D) for (p = rods()) translate([p[0], p[1], z0]) cylinder(d = d, h = z1 - z0);

// ------------------------------------------------------------------ posts

function holes_of(kind) = kind == "lower" ? LOWER_HOLES : UPPER_HOLES;
function z_of(kind) = kind == "lower" ? LOWER : UPPER;

// Front-left post in rack coordinates, without its engraving.
module post_raw(kind) {
  z = z_of(kind);
  difference() {
    translate([POST[0], POST[1], z[0]]) cbox([POST[2], POST[3], z[1] - z[0]]);
    translate([ROD[0], ROD[1], z[0] - 1]) linear_extrude(z[1] - z[0] + 2) teardrop2d(ROD_D);
    if (kind == "upper")
      translate([ROD[0], ROD[1], z[0] - 1]) linear_extrude(COUPLER_TOP - z[0] + 1) teardrop2d(BORE_D);
    for (h = holes_of(kind)) translate([HOLE_X, POST[1], h]) pilot_y();
  }
}

// Hole numbers and ticks on the strip left of the tray plates (x 5..14).
module post_marks(kind, right) {
  hs = holes_of(kind);
  fx = function (x) right ? REF_W - x : x;
  for (i = [0 : len(hs) - 1]) {
    on_front(POST[1], [fx(8.6), hs[i]]) label(str(i + 1), 3.3);
    on_front(POST[1], [fx(12.9), hs[i]]) square([2.4, 0.8], center = true);
  }
}

module post_a(kind) difference() { post_raw(kind); post_marks(kind, false); }
module post_b(kind) difference() { mirror_x() post_raw(kind); post_marks(kind, true); }

module posts(kind) {
  post_a(kind);
  post_b(kind);
  turn() post_a(kind);
  turn() post_b(kind);
}

// ------------------------------------------------------------------ power base

module tub_corner_blocks() {
  z0 = BASE_Z[0]; h = BASE_Z[1] - BASE_Z[0];
  for (b = post_boxes()) {
    front = b[1] < DEPTH / 2;
    y0 = front ? 0 : b[1];
    y1 = front ? b[3] : TROUGH[0] - 1;
    translate([b[0], y0, z0]) cube([b[2] - b[0], y1 - y0, h]);
  }
}

module brick_comb() {
  for (x = BRICK_X) for (s = [-1, 1])
    translate([x + s * 16.5 - 1, BRICK_Y[0] + 14, BASE_Z[0]]) cube([2, 80, FLOOR + 18]);
}

module tub_vents() {
  z0 = BASE_Z[0];
  // front grille and side grilles: vertical slots, only short bridges at their tops
  for (x = [40 : 9 : 213]) translate([x, -1, z0 + 16]) cube([4, WALL + 2, 44]);
  for (y = [40 : 9 : 175]) {
    translate([X0 - 1, y, z0 + 16]) cube([WALL + 2, 4, 44]);
    translate([X1 - WALL - 1, y, z0 + 16]) cube([WALL + 2, 4, 44]);
  }
  // floor: air between the bricks, strap slots for the bricks, coils and the board
  for (x = [BRICK_X[0] + 21.5, BRICK_X[1] + 21.5]) translate([x - 3, BRICK_Y[0] + 14, z0 - 1]) cube([6, 80, FLOOR + 2]);
  for (p = [[21, 76], [143, 76], [155, 30], [230, 30], [155, 150], [230, 150]])
    translate([p[0], p[1], z0 - 1]) cube([3, 22, FLOOR + 2]);
  for (x = [45, 185]) for (y = [TROUGH[0] + 1, TROUGH[1] - 4])
    translate([x, y, z0 - 1]) cube([22, 3, FLOOR + 2]);
  for (x = [146 : 10 : 226]) translate([x, 62, z0 - 1]) linear_extrude(FLOOR + 2) rrect([6, 76], 3);
}

// The board lies on its side in the trough, outlets forward. The trough side walls stop at
// 18 mm so the board's cord leaves over the wall at either end.
module trough_cut() translate([X0 - 1, TROUGH[0], BASE_Z[0] + 18]) cube([X1 - X0 + 2, BASE_DEPTH, 100]);

module base_tub() {
  z0 = BASE_Z[0]; h = BASE_Z[1] - BASE_Z[0];
  outer = [X1 - X0, BASE_DEPTH, h];
  difference() {
    intersection() {
      translate([X0, 0, z0]) rbox(outer, CR);
      union() {
        difference() {
          translate([X0, 0, z0]) rbox(outer, CR);
          translate([X0 + WALL, WALL, z0 + FLOOR]) rbox([outer[0] - 2 * WALL, BASE_DEPTH, h], CR - WALL);
        }
        translate([X0, BASE_DEPTH - WALL, z0]) cube([outer[0], WALL, 14]);                    // rear lip
        translate([X0, TROUGH[0] - 2, z0]) cube([outer[0], 2, 5]);                             // trough front rib
        tub_corner_blocks();
        brick_comb();
      }
    }
    for (p = rods()) translate([p[0], p[1], z0 - 1]) {
      cylinder(d = ROD_D, h = h + 2);
      rotate(30) cylinder(d = NUT_AF / cos(30), h = NUT_POCKET + 1, $fn = 6);
    }
    tub_vents();
    trough_cut();
    on_front(0, [CX, z0 + 8]) label("SOYRACK", 6);
  }
}

// ------------------------------------------------------------------ decks

// Decks are a 4 mm plate inside a 3 mm rim, with solid pads round the post ends.
module deck_plate(z, plate) {
  outline = [X1 - X0, DEPTH];
  translate([X0, 0, plate[0]]) rbox([outline[0], outline[1], plate[1] - plate[0]], CR);
  translate([X0, 0, z[0]]) linear_extrude(z[1] - z[0]) difference() {
    rrect(outline, CR);
    translate([3, 3]) rrect([outline[0] - 6, outline[1] - 6], CR - 3);
  }
  intersection() {
    translate([X0, 0, z[0]]) rbox([outline[0], outline[1], z[1] - z[0]], CR);
    for (b = post_boxes()) translate([b[0] - 6, b[1] - 6, z[0]]) rbox([b[2] - b[0] + 12, b[3] - b[1] + 12, z[1] - z[0]], 4);
  }
}

// Rear slots let leads pass between the bays behind the trays.
module rear_slots(z, y0, y1) for (s = [[32, 92], [97, 156], [161, 221]])
  translate([s[0], y0, z[0] - 1]) linear_extrude(z[1] - z[0] + 2) rrect([s[1] - s[0], y1 - y0], 4);

module vent_field(z, x0, x1, y0, y1, pitch = 9, w = 4.5) {
  n = floor((x1 - x0 - w) / pitch);
  for (i = [0 : n]) translate([x0 + i * pitch, y0, z[0] - 1]) linear_extrude(z[1] - z[0] + 2) rrect([w, y1 - y0], w / 2);
}

module base_deck() {
  z = DECK_Z;
  difference() {
    deck_plate(z, [z[0], z[0] + 4]);
    post_pockets(z[1] - POCKET, z[1] + 1);
    rod_holes(z[0] - 1, z[1] + 1);
    rear_slots(z, 186, 200);
    if (!web) vent_field(z, 34, 222, 34, 172, 10, 6);
  }
}

module mid_deck() {
  z = MID_Z;
  difference() {
    deck_plate(z, [z[0], z[0] + 4]);
    post_pockets(z[0] - 1, z[0] + POCKET);
    post_pockets(z[1] - POCKET, z[1] + 1);
    rod_holes(z[0] - 1, z[1] + 1);
    rear_slots(z, 150, 200);
    if (!web) vent_field(z, 34, 222, 32, 138, 10, 6);
  }
}

module top_cap() {
  z = CAP_Z;
  difference() {
    union() {
      deck_plate(z, [z[1] - 4, z[1]]);
      // the outer edge of each grip is a 10 x 16 mm beam between the corners
      for (x = [X0, X1 - 10]) translate([x, 30, z[1] - 16]) cube([10, DEPTH - 60, 16]);
    }
    post_pockets(z[0] - 11, z[0] + POCKET);
    rod_holes(z[0] - 1, z[1] + 1);
    for (p = rods()) translate([p[0], p[1], z[1] - HEAD_H]) cylinder(d = HEAD_D, h = HEAD_H + 1);
    // grips: lift the whole rack here, the rods carry the load down to the base
    for (x = [14, REF_W - 36]) translate([x, 55, z[1] - 30]) linear_extrude(32) rrect([22, 100], 11);
    for (x = ANTENNA_X) translate([x, ANTENNA_Y, z[0] - 1]) cylinder(d = 14, h = z[1] - z[0] + 2);
    if (!web) {
      vent_field(z, 46, 208, 28, 96, 10, 6);
      vent_field(z, 46, 208, 128, 196, 10, 6);
    }
    translate([CX, 14, z[1] - 0.6]) linear_extrude(1) label("SOYSPRAY", 7);
  }
}

// ------------------------------------------------------------------ shelves

SHELF_T = 2.4;                // shelf floor

// A shelf hangs from the front posts like the node trays: a 224 mm front plate with two
// countersunk M4 screws per side, a floor between the posts and side walls as beams.
module shelf(holes, depth, wall_h, window) {
  zb = holes[0] - 4.5;
  zt = holes[1] + 4.5;
  difference() {
    union() {
      translate([14.5, 0, zb]) cube([224, 3, zt - zb]);
      translate([26, 0, zb]) cube([201, depth, SHELF_T]);
      for (x = [26, 227 - 2.4]) hull() {
        translate([x, 0, zb]) cube([2.4, 3, zt - zb]);
        translate([x, 0, zb]) cube([2.4, depth - 6, 3 + wall_h]);
      }
      children();
    }
    for (x = [HOLE_X, REF_W - HOLE_X], z = holes) translate([x, 0, z]) csk_y(3);
    // three finger windows, so no bridge in the front plate is longer than about 45 mm
    w3 = (window[0] - 18) / 3;
    for (i = [0 : 2]) translate([CX - window[0] / 2 + i * (w3 + 9), -1, zb + 6]) rotate([-90, 0, 0])
      translate([0, -window[1], 0]) linear_extrude(5) rrect([w3, window[1]], 4);
    if (!web) for (x = [38 : 11 : 208]) translate([x, 16, zb - 1]) linear_extrude(5) rrect([6, depth - 32], 3);
  }
}

// Low rims around a device footprint: open at the rear for its leads.
module rims(dev, zb, h = 4, gap = 0.8) {
  s = dev[0]; p = dev[1];
  translate([p[0] - gap - 2, p[1] - gap - 2, zb + SHELF_T - E]) difference() {
    cube([s[0] + 2 * gap + 4, min(s[1], 60) + gap + 2, h + E]);
    translate([2, 2, -1]) cube([s[0] + 2 * gap, s[1] + 10, h + 2]);
    translate([s[0] / 2 + gap + 2 - 15, -1, -1]) cube([30, 4, h + 2]);   // finger notch
  }
}

module drive_tray() {
  zb = 175 - 4.5;
  shelf([175, 195], 135, 10, [150, 12]) {
    rims(SEAGATE, zb);
    rims(TOURO, zb);
  }
}

module switch_shelf() shelf([UPPER_HOLES[0], UPPER_HOLES[2]], 125, 12, [150, 14]) rims(SWITCH, UPPER_HOLES[0] - 4.5);
module router_shelf() shelf([UPPER_HOLES[4], UPPER_HOLES[6]], 125, 12, [136, 16]) rims(ROUTER, UPPER_HOLES[4] - 4.5);

// ------------------------------------------------------------------ keystone panel

KEY_HOLES = [UPPER_HOLES[0], UPPER_HOLES[2]];
KEY_X = [CX - 48, CX - 16, CX + 16, CX + 48];
KEY_Z = (KEY_HOLES[0] + KEY_HOLES[1]) / 2;
KEY_CUT = [14.9, 16.4];

module keystone_cut(t) translate([-KEY_CUT[0] / 2, -1, -KEY_CUT[1] / 2]) cube([KEY_CUT[0], t + 2, KEY_CUT[1]]);

// Rear panel on the outside of the upper rear posts, four RJ45 keystone couplers.
module keystone_panel() {
  y0 = DEPTH - 3; t = 2.4;
  zb = KEY_HOLES[0] - 7; zt = KEY_HOLES[1] + 7;
  difference() {
    union() {
      translate([14.5, y0, zb]) cube([224, t, zt - zb]);
      for (z = [zb, zt - 2.4]) translate([25.5, y0 - 7, z]) cube([202, 7 + E, 2.4]);   // flanges between the posts
    }
    for (x = [HOLE_X, REF_W - HOLE_X], z = KEY_HOLES) translate([x, y0 + t, z]) mirror([0, 1, 0]) csk_y(t);
    for (x = KEY_X) translate([x, y0, KEY_Z]) keystone_cut(t);
    for (i = [0 : 3]) on_rear(y0 + t, [KEY_X[3 - i], KEY_Z + 12.5]) label(str(i + 1), 4);   // 1 at the left seen from behind
  }
}

// ------------------------------------------------------------------ small parts

// Foot pad: its hex boss holds the M5 nut in its pocket; stick a 20 mm silicone pad underneath.
// The right-hand feet are the same part turned half a turn.
module foot(at = rods()[0]) translate([at[0], at[1], BASE_Z[0]]) rotate(at[0] > CX ? 180 : 0) {
  difference() {
    union() {
      translate([-8, -11, -4]) rbox([20, 22, 4], 3);
      rotate(30) cylinder(d = (NUT_AF - 0.15) / cos(30), h = 2.6, $fn = 6);
    }
    translate([0, 0, -5]) cylinder(d = 6.2, h = 10);
    translate([2, 0, -4 - E]) cylinder(d = 18.5, h = 1);
  }
}

// Zigbee mast: stands at least 1 m from the router. The USB 2 extension presses into the
// slot at the back, its socket sits in the top pocket and the dongle plugs in from above.
module zigbee_mast() translate([-300, 60, BASE_Z[0] - 4]) {
  difference() {
    union() {
      cylinder(d = 84, h = 9);
      cylinder(d = 28, h = 140);
      translate([0, 0, 9]) cylinder(d1 = 44, d2 = 28, h = 14);
    }
    for (a = [0 : 60 : 300]) rotate(a) translate([28, 0, -1]) cylinder(d = 21, h = 7);   // ballast: three M10 washers per pocket
    translate([-8.25, -4.5, 104]) cube([16.5, 9, 37]);          // extension socket, 16 x 8.5 mm housing
    translate([-3, 0, 14]) cube([6, 20, 127]);                  // cable slot along the back
    translate([-3, 0, 5.99]) cube([6, 50, 8]);                  // cable exit through the foot
  }
}

// ------------------------------------------------------------------ test coupons

module coupon_post() intersection() {
  post_a("lower");
  translate([0, 0, LOWER[0] - 1]) cube([60, 60, 76 + 1]);
}

module coupon_corner() intersection() {
  base_deck();
  translate([X0 - 1, -1, DECK_Z[0] - 1]) cube([46, 46, 10]);
}

module coupon_nut() intersection() {
  base_tub();
  translate([X0 - 1, -1, BASE_Z[0] - 1]) cube([34, 40, 16]);
}

// Two keystone openings: 2.4 mm plate (left) and 2.0 mm plate (right).
module coupon_keystone() {
  difference() {
    union() {
      translate([0, 0, 0]) cube([36, 2.4, 34]);
      translate([36, 0, 0]) cube([36, 2.0, 34]);
    }
    translate([18, 0, 17]) keystone_cut(3);
    translate([54, 0, 17]) keystone_cut(3);
    on_rear(2.4, [18, 29]) label("2.4", 4);
    on_rear(2.0, [54, 29]) label("2.0", 4);
  }
}

// ------------------------------------------------------------------ dispatch

module world_part(name) {
  if (name == "base_tub") base_tub();
  else if (name == "base_deck") base_deck();
  else if (name == "post_lower_a") post_a("lower");
  else if (name == "post_lower_b") post_b("lower");
  else if (name == "mid_deck") mid_deck();
  else if (name == "post_upper_a") post_a("upper");
  else if (name == "post_upper_b") post_b("upper");
  else if (name == "top_cap") top_cap();
  else if (name == "drive_tray") drive_tray();
  else if (name == "switch_shelf") switch_shelf();
  else if (name == "router_shelf") router_shelf();
  else if (name == "keystone_panel") keystone_panel();
  else if (name == "foot") foot();
  else if (name == "zigbee_mast") zigbee_mast();
  else if (name == "coupon_post") coupon_post();
  else if (name == "coupon_corner") coupon_corner();
  else if (name == "coupon_nut") coupon_nut();
  else if (name == "coupon_keystone") coupon_keystone();
  else assert(false, str("unknown part ", name));
}

// Bed orientation: posts lie on the face with the insert holes, the top cap prints upside
// down, the keystone panel lies on its outer face, everything else prints as it stands.
module print_part(name) {
  lying = ["post_lower_a", "post_lower_b", "post_upper_a", "post_upper_b", "coupon_post"];
  if (len([for (n = lying) if (n == name) n]) > 0)
    multmatrix([[0, 0, 1, 0], [1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 0, 1]]) world_part(name);
  else if (name == "top_cap") rotate([180, 0, 0]) world_part(name);
  else if (name == "keystone_panel" || name == "coupon_keystone") rotate([-90, 0, 0]) world_part(name);
  else world_part(name);
}

module assembly() {
  color("#3b4048") {
    base_tub();
    base_deck();
    posts("lower");
    mid_deck();
    posts("upper");
    top_cap();
    drive_tray();
    switch_shelf();
    router_shelf();
    keystone_panel();
    for (p = rods()) foot(p);
  }
}

if (part == "assembly") assembly();
else if (orient == "world") world_part(part);
else print_part(part);
