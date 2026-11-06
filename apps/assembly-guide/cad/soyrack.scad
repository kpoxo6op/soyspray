// Soyrack (v3): a printable PETG rack for three Lenovo M920q Tiny nodes, with a power base that
// keeps every stock cord at full length, a drive tray, a switch shelf and a keystone Ethernet
// panel. It goes together with M4 screws and M4 nuts only: every nut pushes into a printed slot or
// drops into a printed hex, so nothing is pressed in and no rod runs through the posts.
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
         "keystone_panel", "zigbee_mast",
         "coupon_post", "coupon_corner", "coupon_base", "coupon_keystone"];

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
HOLE_X = 18.97;              // tray screw holes; the right-hand ones at REF_W - HOLE_X
POCKET = 3; FIT = 0.25;      // post ends sit 3 mm deep in the decks
LOWER = [-3, 203];
UPPER = [205, 275];
LOWER_HOLES = [for (k = [0 : 17]) 25 + 10 * k];   // holes 1..18, hole n at z = 15 + 10n
UPPER_HOLES = [for (k = [0 : 3]) 235 + 10 * k];   // holes 1..4

// M4 hardware. Screws pass a 4.5 mm hole; an M4 nut (DIN 934, 7 mm across flats, 3.2 mm thick)
// pushes into a slot 7.2 mm wide and 3.5 mm high and stops centred on its screw.
M4_D = 4.5;
NUT4 = [7.2, 3.5];
NUT4_R = 4.1;                // slot end, from the screw axis: a corner of the nut stops there
SLOT_Y = 6;                  // tray screw nuts sit behind the 3 mm front wall of a post
HOLE_DEPTH = 13;             // tray screw holes, from the post face
HEAD4 = [8, 4.4];            // counterbore for an M4 socket head in the top cap

// Each post end that meets a deck has a foot behind it, along the side of the rack. Per corner,
// one M4 x 25 socket screw goes down through a lower post's bottom foot and the base deck into a
// nut in the base, and one goes up through a lower post's top foot, the mid deck and the upper
// post's foot into a nut in the hex on top. Four more come down through the top cap into nuts
// near the tops of the upper posts.
FOOT = [12, 8];              // length behind the post, height (3 mm of it in the deck pocket)
LOWER_FEET = [[LOWER[0], LOWER[0] + FOOT[1]], [LOWER[1] - FOOT[1], LOWER[1]]];
UPPER_FEET = [[UPPER[0], UPPER[0] + FOOT[1]]];
BASE_NUT_Z = -17.5;          // underside of the nut slot in each base corner
CAP_BOLT = [12, 20];         // top cap screw axis in the front-left upper post
CAP_NUT_Z = 263.5;           // underside of its nut slot

BASE_Z = [-104, -8];         // power base tub: the cord loops set its height
BASE_DEPTH = 240;            // the rear 31 mm is the open board trough
TROUGH = [205, 237.6];
PLINTH = 6;                  // rails lift the board so the switch adapter stands on the floor
DECK_Z = [-8, 0];
MID_Z = [200, 208];
CAP_Z = [272, 282];
WALL = 2.4; FLOOR = 2.4;

// Bricks stand on edge, long side front to back, 14 mm apart, clear of the front corner blocks.
// The DC cord leaves the front end and turns up; the C5 inlet faces the board at the rear.
BRICK_X = [40, 83, 126];
BRICK_Y = [26, 138];

// Equipment envelopes (x, y, z sizes) and positions of their minimum corners.
SWITCH = [[158, 101, 26], [47.5, 10]];
SEAGATE = [[78, 114.8, 11.7], [40.5, 12]];
TOURO = [[80, 112, 20.5], [132.5, 12]];

// post footprints [x0, y0, x1, y1]
function post_boxes() = [
  [POST[0], POST[1], POST[0] + POST[2], POST[1] + POST[3]],
  [REF_W - POST[0] - POST[2], POST[1], REF_W - POST[0], POST[1] + POST[3]],
  [POST[0], DEPTH - POST[1] - POST[3], POST[0] + POST[2], DEPTH - POST[1]],
  [REF_W - POST[0] - POST[2], DEPTH - POST[1] - POST[3], REF_W - POST[0], DEPTH - POST[1]]];
function is_front(b) = b[1] < DEPTH / 2;
// the same with their feet: behind the front posts, in front of the rear ones
function foot_boxes() = [for (b = post_boxes())
  is_front(b) ? [b[0], b[1], b[2], b[3] + FOOT[0]] : [b[0], b[1] - FOOT[0], b[2], b[3]]];
// corner screw axes, one through each foot
function joints() = [for (b = post_boxes()) [(b[0] + b[2]) / 2, is_front(b) ? b[3] + FOOT[0] / 2 : b[1] - FOOT[0] / 2]];
function cap_bolts() = [[CAP_BOLT[0], CAP_BOLT[1]], [REF_W - CAP_BOLT[0], CAP_BOLT[1]],
                        [CAP_BOLT[0], DEPTH - CAP_BOLT[1]], [REF_W - CAP_BOLT[0], DEPTH - CAP_BOLT[1]]];

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

// Nut slot for a screw along z: from just behind the axis out through a face `to_face` mm away
// along +x (along -x when dir is -1), its underside at z = 0.
module nut_slot_x(to_face, dir = 1) mirror([dir < 0 ? 1 : 0, 0, 0])
  translate([-NUT4_R, -NUT4[0] / 2, 0]) cube([NUT4_R + to_face + 1, NUT4[0], NUT4[1]]);

// Tray screw hole drilled from a face along +y, and the slot its nut pushes into from the side
// face `to_face` mm away along +x, 3 mm behind the face.
module tray_hole(to_face) {
  rotate([-90, 0, 0]) {
    translate([0, 0, -E]) cylinder(d = M4_D, h = HOLE_DEPTH + E);
    translate([0, 0, -E]) cylinder(d1 = M4_D + 1, d2 = M4_D, h = 0.5 + E);
  }
  translate([0, SLOT_Y - POST[1] + NUT4[1], 0]) rotate([90, 0, 0]) nut_slot_x(to_face);
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

// Pockets for the four post ends (by default without their feet) between z0 and z1.
module post_pockets(z0, z1, boxes = post_boxes()) for (b = boxes)
  translate([b[0] - FIT, b[1] - FIT, z0]) linear_extrude(z1 - z0) crect([b[2] - b[0] + 2 * FIT, b[3] - b[1] + 2 * FIT], 1.2);

module screw_holes(at, z0, z1) for (p = at) translate([p[0], p[1], z0]) cylinder(d = M4_D, h = z1 - z0);

// ------------------------------------------------------------------ posts

function holes_of(kind) = kind == "lower" ? LOWER_HOLES : UPPER_HOLES;
function z_of(kind) = kind == "lower" ? LOWER : UPPER;

// Front-left post in rack coordinates, without its engraving. Tray screw nuts push into slots in
// its inner side face; the feet carry the corner screws.
module post_raw(kind) {
  z = z_of(kind);
  feet = kind == "lower" ? LOWER_FEET : UPPER_FEET;
  j = joints()[0];
  side = POST[0] + POST[2];
  back = POST[1] + POST[3];
  difference() {
    union() {
      translate([POST[0], POST[1], z[0]]) cbox([POST[2], POST[3], z[1] - z[0]]);
      for (f = feet) translate([POST[0], back - 3, f[0]]) cbox([POST[2], FOOT[0] + 3, f[1] - f[0]]);
    }
    for (h = holes_of(kind)) translate([HOLE_X, POST[1], h]) tray_hole(side - HOLE_X);
    for (f = feet) translate([j[0], j[1], f[0] - 1]) linear_extrude(f[1] - f[0] + 2) teardrop2d(M4_D);
    if (kind == "upper") {
      // the mid screw's nut drops into a hex on top of the foot
      translate([j[0], j[1], UPPER_FEET[0][1] - NUT4[1]]) rotate(30) cylinder(d = NUT4[0] / cos(30), h = NUT4[1] + 1, $fn = 6);
      // the top cap screw comes down the post into a nut pushed in from the back
      translate([CAP_BOLT[0], CAP_BOLT[1], CAP_NUT_Z - 14]) linear_extrude(z[1] - CAP_NUT_Z + 15) teardrop2d(M4_D);
      translate([CAP_BOLT[0], CAP_BOLT[1], CAP_NUT_Z]) rotate(90) nut_slot_x(back - CAP_BOLT[1]);
    }
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

// Solid corners under the posts and their feet: each holds the nut of a corner screw.
module tub_corner_blocks() {
  z0 = BASE_Z[0]; h = BASE_Z[1] - BASE_Z[0];
  for (b = foot_boxes()) {
    y0 = is_front(b) ? 0 : b[1] - 2;
    y1 = is_front(b) ? b[3] + 2 : TROUGH[0] - 1;
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
  for (x = [40 : 9 : 213]) translate([x, -1, z0 + 16]) cube([4, WALL + 2, 60]);
  for (y = [40 : 9 : 157]) {
    translate([X0 - 1, y, z0 + 16]) cube([WALL + 2, 4, 60]);
    translate([X1 - WALL - 1, y, z0 + 16]) cube([WALL + 2, 4, 60]);
  }
  // floor: air between the bricks and under the cord loops, strap slots for the bricks and the board
  for (x = [BRICK_X[0] + 21.5, BRICK_X[1] + 21.5]) translate([x - 3, BRICK_Y[0] + 14, z0 - 1]) cube([6, 80, FLOOR + 2]);
  // beside the outer comb fins, not under them: each fin would cross its slot in a 22 mm span
  for (p = [[19.5, 76], [143.5, 76]]) translate([p[0], p[1], z0 - 1]) cube([3, 22, FLOOR + 2]);
  for (x = [64, 217]) for (y = [TROUGH[0] + 1, TROUGH[1] - 4])
    translate([x, y, z0 - 1]) cube([22, 3, FLOOR + PLINTH + 2]);
  for (x = [146 : 10 : 226]) translate([x, 62, z0 - 1]) linear_extrude(FLOOR + 2) rrect([6, 76], 3);
}

// The board lies on its side on two rails in the trough, outlets forward, strapped down between
// outlets 1 and 2 and beyond outlet 4. The trough side walls stop at 18 mm so the board's cord
// leaves over the wall at either end.
module trough_cut() translate([X0 - 1, TROUGH[0], BASE_Z[0] + 18]) cube([X1 - X0 + 2, BASE_DEPTH, 100]);

// The P1S bed excludes its corner at x < 18, y < 28, and the slicer places and validates a part by
// its convex hull, so only a straight cut can clear it. The rear left corner is cut from
// `along the side` mm in front of the rear face to `along the rear` mm from the side. The cut leaves
// the board's footprint and everything in front of the trough alone. The rear lip stops where the
// cut would thin it below half its thickness; the floor runs on to the cut.
TUB_RELIEF = [6.8, 72];
module tub_relief() {
  z0 = BASE_Z[0]; h = BASE_Z[1] - BASE_Z[0];
  a = TUB_RELIEF[0]; b = TUB_RELIEF[1];
  translate([0, 0, z0 - 1]) linear_extrude(h + 2)
    polygon([[X0 - 1, BASE_DEPTH - a - a / b], [X0 + b + b / a, BASE_DEPTH + 1], [X0 - 1, BASE_DEPTH + 1]]);
  translate([X0 - 1, BASE_DEPTH - WALL, z0 + FLOOR]) cube([1 + b * (1 - WALL / 2 / a), WALL + 1, h]);
}

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
        for (y = [TROUGH[0] + 4, TROUGH[1] - 8])                                                 // board rails
          translate([X0, y, z0]) cube([outer[0], 4, FLOOR + PLINTH]);
        tub_corner_blocks();
        brick_comb();
      }
    }
    // corner screws: each nut pushes into its slot from inside the base
    for (j = joints()) translate([j[0], j[1], 0]) {
      translate([0, 0, BASE_NUT_Z - 4.5]) cylinder(d = M4_D, h = BASE_Z[1] - BASE_NUT_Z + 5.5);
      translate([0, 0, BASE_NUT_Z]) nut_slot_x(POST[2] / 2, j[0] < CX ? 1 : -1);
      // The slot ceiling would close as a ring round the screw hole, over air. Two layers step it
      // down to the hole: a strip as wide as the hole across the slot, then a square. The ceiling
      // beside the strip stays the nut's seat plane; the hole only gets larger, by the strip and square.
      if (!web) translate([-M4_D / 2, 0, BASE_NUT_Z + NUT4[1]]) {
        translate([0, -NUT4[0] / 2, -E]) cube([M4_D, NUT4[0], 0.2 + E]);
        translate([0, -M4_D / 2, 0.2 - E]) cube([M4_D, M4_D, 0.2 + E]);
      }
    }
    tub_vents();
    trough_cut();
    on_front(0, [CX, z0 + 8]) label("SOYRACK", 6);
    if (!web) tub_relief();
  }
}

// ------------------------------------------------------------------ decks

// Decks are a 4 mm plate inside a 3 mm rim, with solid pads round the post ends.
module deck_plate(z, plate, boxes = foot_boxes()) {
  outline = [X1 - X0, DEPTH];
  translate([X0, 0, plate[0]]) rbox([outline[0], outline[1], plate[1] - plate[0]], CR);
  translate([X0, 0, z[0]]) linear_extrude(z[1] - z[0]) difference() {
    rrect(outline, CR);
    translate([3, 3]) rrect([outline[0] - 6, outline[1] - 6], CR - 3);
  }
  intersection() {
    translate([X0, 0, z[0]]) rbox([outline[0], outline[1], z[1] - z[0]], CR);
    for (b = boxes) translate([b[0] - 6, b[1] - 6, z[0]]) rbox([b[2] - b[0] + 12, b[3] - b[1] + 12, z[1] - z[0]], 4);
  }
}

// Rear slots let leads pass between the bays behind the trays.
module rear_slots(z, y0, y1) for (s = [[32, 92], [97, 156], [161, 221]])
  translate([s[0], y0, z[0] - 1]) linear_extrude(z[1] - z[0] + 2) rrect([s[1] - s[0], y1 - y0], 4);

// pointed: each slot ends in a 45 degree point at y0 instead of its rounding
module vent_field(z, x0, x1, y0, y1, pitch = 9, w = 4.5, pointed = false) {
  n = floor((x1 - x0 - w) / pitch);
  for (i = [0 : n]) translate([x0 + i * pitch, y0, z[0] - 1]) linear_extrude(z[1] - z[0] + 2)
    if (pointed) hull() {
      polygon([[0, w / 2], [w / 2, 0], [w, w / 2]]);
      translate([0, w / 2]) rrect([w, y1 - y0 - w / 2], w / 2);
    }
    else rrect([w, y1 - y0], w / 2);
}

module base_deck() {
  z = DECK_Z;
  difference() {
    deck_plate(z, [z[0], z[0] + 4]);
    post_pockets(z[1] - POCKET, z[1] + 1, foot_boxes());
    screw_holes(joints(), z[0] - 1, z[1] + 1);
    rear_slots(z, 186, 200);
    if (!web) vent_field(z, 34, 222, 34, 172, 10, 6);
  }
}

// The mid deck prints standing on its rear edge, the front of the rack up. Every face that then
// looks down slopes at 45 degrees or closes in a short bridge, so nothing is printed over air:
// - Each post pocket keeps its seat plane and its exact outline there (z 203 below, z 205 on top).
//   Only its front wall slopes away from the seat, 3 mm over the 3 mm pocket depth.
// - The front rim and the rear faces of the front pads stand on 4 mm fillets on the plate.
// - Each lead slot keeps its 60 mm rear end and closes in a pointed roof towards the front.
// - Each vent slot ends in a 45 degree point at the front instead of its rounding.
// - The two rear corners meet the bed in a 45 degree chamfer instead of their flat rounding.
module mid_deck() {
  z = MID_Z;
  difference() {
    union() {
      deck_plate(z, [z[0], z[0] + 4]);
      mid_fillets(z, z[0] + 4);
      translate([0, 0, z[0]]) linear_extrude(z[1] - z[0]) { edge_corner(); mirror_x() edge_corner(); }
    }
    sloped_pockets(z[0] + POCKET, -1);
    sloped_pockets(z[1] - POCKET, 1);
    screw_holes(joints(), z[0] - 1, z[1] + 1);
    lead_slots(z, 141, 200);
    if (!web) vent_field(z, 34, 222, 32, 138, 10, 6, pointed = true);
  }
}

// Post pockets from their seat plane out through the face on side `dir` (-1 below, +1 above).
// The front wall moves forwards with the depth below the seat; the other walls stay vertical.
module sloped_pockets(seat, dir) for (b = foot_boxes()) hull() {
  size = [b[2] - b[0] + 2 * FIT, b[3] - b[1] + 2 * FIT];
  translate([b[0] - FIT, b[1] - FIT, dir < 0 ? seat - E : seat]) linear_extrude(E) crect(size, 1.2);
  translate([b[0] - FIT, b[1] - FIT - 4, seat + dir * 4 - (dir < 0 ? 0 : E)]) linear_extrude(E) crect(size + [0, 4], 1.2);
}

// Fillets under the faces that look down when the deck stands on its rear edge: in front of the
// recess between the rims, and behind each front pad. Each grows 1 mm per mm towards the plate.
module mid_fillets(z, plate) {
  inner = [X1 - X0 - 6, DEPTH - 6];
  intersection() {
    translate([X0, 0, plate]) rbox([X1 - X0, DEPTH, z[1] - plate], CR);
    union() {
      difference() {
        translate([X0 + 3, 3, plate]) linear_extrude(z[1] - plate) rrect(inner, CR - 3);
        hull() {
          translate([X0 + 3, 3 - 1, z[1] + 1]) linear_extrude(E) rrect(inner, CR - 3);
          translate([X0 + 3, 3 + z[1] - plate + 1, plate - 1]) linear_extrude(E) rrect(inner, CR - 3);
        }
      }
      for (b = foot_boxes()) if (is_front(b)) hull() {
        translate([b[0] - 6, b[1] - 6, plate]) linear_extrude(z[1] - plate) rrect([b[2] - b[0] + 12, b[3] - b[1] + 12], 4);
        translate([b[0] - 6, b[1] - 6 + z[1] - plate, plate]) linear_extrude(E) rrect([b[2] - b[0] + 12, b[3] - b[1] + 12], 4);
      }
    }
  }
}

// Rear left plan corner, down to the bed: the rounding below its 45 degree point becomes a chamfer.
module edge_corner() {
  t = CR / sqrt(2);
  polygon([[X0 + CR - t, DEPTH - CR + t], [X0 + 2 * CR - 2 * t, DEPTH], [X0 + CR, DEPTH], [X0 + CR, DEPTH - CR + t]]);
}

// Rear slots in the mid deck: the 60 mm rear end of each stays, its sides close in a 45 degree
// roof that peaks at y = apex.
module lead_slots(z, apex, rear) for (s = [[32, 92], [97, 156], [161, 221]])
  translate([0, 0, z[0] - 1]) linear_extrude(z[1] - z[0] + 2)
    polygon([[s[0], rear], [s[0], apex + (s[1] - s[0]) / 2], [(s[0] + s[1]) / 2, apex],
             [s[1], apex + (s[1] - s[0]) / 2], [s[1], rear]]);

// Print-only: the mid deck lying flat on its underside, turned a quarter in plan so its corner
// clears the bed's excluded corner. Flat, each underside post pocket would close in a 20.5 mm
// ceiling over air, so a breakaway lattice stands in it from the bed to the seat plane: 2 mm ribs
// running front to back, the boss round the screw hole and a rib along the side face, where the
// pocket opens. Its cells are 3 to 5 mm wide, so the ceiling bridges short spans across rib tops.
// The ribs fuse to the seat plane and the pocket walls: break them out and scrape the seat flat
// before fitting the posts. The underside pockets are straight, as in the base deck: lying flat
// their sloped front walls would thin to nothing at the bed. Seat planes, outlines, holes and
// everything above z 203 are the mid deck's.
RIB = 2; EDGE_RIB = 2.5; INNER_RIB = 1.25; RIB_INTO_WALL = 0.3;
module mid_deck_flat() rotate(90) {
  mid_deck();
  // fill each underside pocket's front wall back to straight, 0.2 mm into the existing wall
  intersection() {
    translate([X0, 0, MID_Z[0]]) rbox([X1 - X0, DEPTH, POCKET], CR);
    difference() {
      translate([0, -0.2, 0]) sloped_pockets(MID_Z[0] + POCKET, -1);
      post_pockets(MID_Z[0] - 1, MID_Z[0] + POCKET + 1, foot_boxes());
    }
  }
  // each rib stands on a 0.4 mm foot 0.5 mm wider on each side, to hold the bed
  for (f = [[POCKET + E, 0], [0.4, 0.5]]) translate([0, 0, MID_Z[0]]) linear_extrude(f[0]) intersection() {
    translate([X0 + 0.3, 0.3]) rrect([X1 - X0 - 0.6, DEPTH - 0.6], CR - 0.3);
    for (k = [0 : 3]) pocket_lattice(k, f[1]);
  }
}

// Lattice in underside pocket k, drawn in place.
module pocket_lattice(k, grow = 0) {
  b = foot_boxes()[k];
  j = joints()[k];
  lo = [b[0] - FIT, b[1] - FIT] - [RIB_INTO_WALL, RIB_INTO_WALL];
  hi = [b[2] + FIT, b[3] + FIT] + [RIB_INTO_WALL, RIB_INTO_WALL];
  h = M4_D / 2 + RIB + 0.25;                 // half the boss
  left = b[0] <= X0;
  // the boss's rib towards the middle is wider, so that cell is as narrow as the others
  ribs = left ? [[X0, EDGE_RIB], [j[0] - h, RIB], [j[0] + h - RIB, RIB + INNER_RIB]]
              : [[X1 - EDGE_RIB, EDGE_RIB], [j[0] + h - RIB, RIB], [j[0] - h - INNER_RIB, RIB + INNER_RIB]];
  difference() {
    offset(delta = grow) union() {
      translate(j - [h, h]) square(2 * h);
      for (r = ribs) translate([r[0], lo[1]]) square([r[1], hi[1] - lo[1]]);
    }
    translate(j) circle(d = M4_D);
  }
}

module top_cap() {
  z = CAP_Z;
  difference() {
    union() {
      deck_plate(z, [z[1] - 4, z[1]], post_boxes());
      // the outer edge of each grip is a 10 x 16 mm beam between the corners
      for (x = [X0, X1 - 10]) translate([x, 30, z[1] - 16]) cube([10, DEPTH - 60, 16]);
    }
    post_pockets(z[0] - 11, z[0] + POCKET);
    // corner screws down into the upper posts, their socket heads flush with the top
    for (p = cap_bolts()) translate([p[0], p[1], z[0] - 1]) {
      cylinder(d = M4_D, h = z[1] - z[0] + 2);
      translate([0, 0, z[1] - z[0] + 1 - HEAD4[1]]) cylinder(d = HEAD4[0], h = HEAD4[1] + 1);
      // The cap prints upside down, so each head seat is a ring-shaped ceiling. Two layers step it
      // down to the screw hole: a slot as wide as the hole across the seat, then a square. Each
      // layer bridges at most 6.6 mm between solid edges; the seat and the hole only get larger.
      if (!web) translate([0, 0, z[1] - z[0] + 1 - HEAD4[1]]) {
        translate([0, 0, -0.2]) intersection() {
          cylinder(d = HEAD4[0], h = 0.2 + E);
          translate([-HEAD4[0] / 2, -M4_D / 2, 0]) cube([HEAD4[0], M4_D, 0.2 + E]);
        }
        translate([-M4_D / 2, -M4_D / 2, -0.4]) cube([M4_D, M4_D, 0.2 + E]);
      }
    }
    // grips: lift the whole rack here, the corner screws carry the load down to the base
    for (x = [14, REF_W - 36]) translate([x, 55, z[1] - 30]) linear_extrude(32) rrect([22, 100], 11);
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
    // Six openings with 45-degree roofs. Each new wall layer rests on the one
    // below; the old rounded windows ended in unqualified 37 mm bridges.
    opening_w = (window[0] - 5 * 9) / 6;
    shoulder_h = window[1] - opening_w / 2;
    for (i = [0 : 5]) translate([CX - window[0] / 2 + i * (opening_w + 9), -1, zb + 6]) rotate([-90, 0, 0])
      linear_extrude(5) polygon([[0, 0], [opening_w, 0], [opening_w, -shoulder_h],
        [opening_w / 2, -window[1]], [0, -shoulder_h]]);
    // Keep a floor rib under each device rim. Cutting uninterrupted vent slots
    // through the children removes their roots and leaves long walls in mid-air.
    if (!web) difference() {
      for (x = [38 : 11 : 208]) translate([x, 16, zb - 1])
        linear_extrude(SHELF_T + 2) rrect([6, depth - 32], 3);
      translate([0, 0, zb - 2]) linear_extrude(SHELF_T + 4)
        offset(r = 0.8) projection(cut = false) children();
    }
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

// Zigbee mast: stands at least 1 m from every USB 3 port. The USB 2 extension presses into the
// slot at the back, its socket sits in the top pocket and the dongle plugs in from above.
// Three M10 washers push up into each of six ballast pockets from below. Each pocket closes in a
// 45 degree cone to an 8 mm vent through the 13 mm foot, so no ring of it is printed over air.
MAST_FOOT = 13;
module zigbee_mast() translate([-300, 60, BASE_Z[0] - 4]) {
  difference() {
    union() {
      cylinder(d = 84, h = MAST_FOOT);
      cylinder(d = 28, h = 140);
      translate([0, 0, 9]) cylinder(d1 = 44, d2 = 28, h = 14);
    }
    for (a = [0 : 60 : 300]) rotate(a) translate([28, 0, 0]) {
      translate([0, 0, -1]) cylinder(d = 21, h = 7);            // ballast: three M10 washers per pocket
      translate([0, 0, 6]) cylinder(d1 = 21, d2 = 8, h = 6.5);
      translate([0, 0, 12]) cylinder(d = 8, h = MAST_FOOT - 11);
    }
    translate([-8.25, -4.5, 104]) cube([16.5, 9, 37]);          // extension socket, 16 x 8.5 mm housing
    translate([-3, 0, 14]) cube([6, 20, 127]);                  // cable slot along the back
    translate([-3, 0, 5.99]) cube([6, 50, MAST_FOOT - 4.99]);   // cable exit: a groove through the foot
  }
}

// ------------------------------------------------------------------ test coupons

// The bottom of a lower post: its foot, and tray holes 1 and 2 with their nut slots.
module coupon_post() intersection() {
  post_a("lower");
  translate([0, 0, LOWER[0] - 1]) cube([60, 60, 45]);
}

module coupon_corner() intersection() {
  base_deck();
  translate([X0 - 1, -1, DECK_Z[0] - 1]) cube([46, 52, 10]);
}

// The top of the base's front-left corner with its nut slot, cut 19 mm down: prints as it stands.
module coupon_base() intersection() {
  base_tub();
  translate([X0 - 1, -1, BASE_Z[1] - 19]) cube([21, 41, 20]);
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
  else if (name == "keystone_panel") keystone_panel();
  else if (name == "zigbee_mast") zigbee_mast();
  else if (name == "coupon_post") coupon_post();
  else if (name == "coupon_corner") coupon_corner();
  else if (name == "coupon_base") coupon_base();
  else if (name == "coupon_keystone") coupon_keystone();
  else assert(false, str("unknown part ", name));
}

// Bed orientation: posts lie on the face with the tray holes, the top cap prints upside
// down, the mid deck stands on its rear edge, the keystone panel lies on its outer face,
// the power base is turned a quarter in plan so its relief meets the excluded bed corner,
// everything else prints as it stands.
module print_part(name) {
  lying = ["post_lower_a", "post_lower_b", "post_upper_a", "post_upper_b", "coupon_post"];
  if (len([for (n = lying) if (n == name) n]) > 0)
    multmatrix([[0, 0, 1, 0], [1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 0, 1]]) world_part(name);
  else if (name == "top_cap") rotate([180, 0, 0]) world_part(name);
  else if (name == "mid_deck") rotate([-90, 0, 0]) world_part(name);
  else if (name == "mid_deck_flat") mid_deck_flat();
  else if (name == "base_tub") rotate(90) world_part(name);
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
    keystone_panel();
  }
}

if (part == "assembly") assembly();
else if (orient == "world") world_part(part);
else print_part(part);
