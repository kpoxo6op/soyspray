// Printed case for a 38-pin ESP-WROOM-32 DevKit (USB-C) with its pin headers
// soldered pins-down: the bathroom scale bridge.
//
// Two parts, held together by two M4 x 12 countersunk screws into two M4 nuts
// pushed into slots inside the base. No inserts, glue or soldering.
//
//   base: a tub. The headers drop into two trenches that also locate the board;
//         the PCB rests on the cradle between them. USB-C opens at the +X end,
//         where the two screw columns stand. The antenna end (-X) is plastic only.
//   lid:  a flat plate with ribs over the header rows, vent slots over the USB
//         chip, regulator and power LED, and pin holes over BOOT and EN. Its
//         tongue slides into the slot under the brow at the antenna end, then
//         the two screws go in at the USB end.
//
// Coordinates: X along the board (USB at +X), origin at the header centre,
// z = 0 under the base. Render with render.mjs.

part = "assembly";   // base | lid | assembly
orient = "print";    // print: on the bed origin, lid upside down | use: assembled position

$fn = 48;
use <LiberationSans-Bold.ttf>

// ---- knobs -------------------------------------------------------------------
FIT = 0.4;           // clearance around the board and between parts
WALL = 2.5;          // long walls
FLOOR = 1.6;

BOARD_W = 28.6;      // widest 38-pin board ("wide", rows 25.4 mm apart)
BOARD_L = 54.0;      // longest board that fits; shorter boards are located by their headers
PCB_T = 1.6;

PINS = 19;           // per row
PITCH = 2.54;
ROWS = [22.86, 25.4];   // narrow and wide boards: the trenches take either
HDR_BODY = 2.5;      // plastic strip of the header
HDR_PIN = 6.0;       // pin length below the plastic (standard 11.5 mm header)

TOP_CLEAR = 6.0;     // PCB top to lid underside (USB-C, module and buttons are under 3.5)
STUB_CLEAR = 2.7;    // PCB top to rib underside (solder stubs are about 1.5-2)
LID_T = 2.4;
BROW = 1.6;          // antenna-end wall stands this far above the lid

M4_D = 4.5;          // M4 clearance
NUT4 = [7.2, 3.5];   // across flats, slot height
CSK_D = 8.6;         // countersink top diameter for DIN 7991 M4 (8 mm head)
SCREW_X = 32;        // screw centres, both at the USB end
SCREW_Y = 12.2;

USB_W = 13.6;        // cable plug overmold opening
USB_H = 8.4;
END_X = 10;          // USB end block length (screw columns)
END_W = 2.4;         // antenna end wall
CORNER_R = 3;

// ---- derived -----------------------------------------------------------------
HDR_L = PINS * PITCH;
CX = BOARD_L / 2;                        // cavity half length
CY = BOARD_W / 2 + FIT / 2;              // cavity half width
TR_IN = ROWS[0] / 2 - HDR_BODY / 2 - FIT; // trench inner edge
TR_X = HDR_L / 2 + FIT;                  // trench half length
TR_D = HDR_BODY + HDR_PIN + 0.8;         // trench depth
ZC = FLOOR + TR_D;                       // cradle top = PCB underside
ZT = ZC + PCB_T;                         // PCB top
ZL = ZT + TOP_CLEAR;                     // top of the walls = lid underside
H = ZL + LID_T;                          // lid top
X0 = -CX - END_W;                        // outer -X
X1 = CX + END_X;                         // outer +X
OY = CY + WALL;                          // outer half width
USB_Z = ZT + 1.6;                        // USB-C centre (3.2 mm tall receptacle on the PCB)

SLOT_Y = 10.2;                           // tongue slot half width
TONGUE = END_W - 0.4;                    // tongue reach into the wall

PARTS = ["base", "lid", "assembly"];

module rbox(x0, x1, y, z0, z1, r = CORNER_R) {
  translate([0, 0, z0]) linear_extrude(z1 - z0)
    hull() for (x = [x0 + r, x1 - r], s = [-1, 1]) translate([x, s * (y - r)]) circle(r);
}

module stadium(x0, x1, w) {
  hull() for (x = [x0 + w / 2, x1 - w / 2]) translate([x, 0]) circle(d = w);
}

module base() {
  difference() {
    union() {
      rbox(X0, X1, OY, 0, ZL);
      // antenna-end wall rises over the lid, the brow over the tongue slot
      intersection() {
        rbox(X0, X1, OY, 0, H + BROW);
        translate([X0 - 1, -OY - 1, 0]) cube([END_W + 1, 2 * OY + 2, H + BROW]);
      }
    }
    // cavity above the cradle
    translate([-CX, -CY, ZC]) cube([2 * CX, 2 * CY, ZL]);
    // header trenches: either row spacing drops in
    for (s = [-1, 1]) translate([-TR_X, s > 0 ? TR_IN : -CY, FLOOR])
      cube([2 * TR_X, CY - TR_IN, TR_D + 0.01]);
    // hollow under the middle of the board
    translate([-CX + 7, -(TR_IN - 1.4), FLOOR]) cube([2 * CX - 14, 2 * (TR_IN - 1.4), TR_D + 0.01]);
    // relief under the USB end for connector legs
    translate([CX - 8, -5.5, ZC - 2.5]) cube([8.01, 11, 2.51]);
    // USB-C: open-topped notch through the end block, the lid closes it
    translate([CX - 1, -USB_W / 2, USB_Z - USB_H / 2]) cube([END_X + 2, USB_W, ZL]);
    // tongue slot under the brow
    translate([X0 - 1, -SLOT_Y, ZL]) cube([END_W + 2, 2 * SLOT_Y, LID_T + 0.2]);
    // screw holes, and nut slots open to the sides: a nut pushed in to the end
    // of its slot sits on the hole, flats against the slot walls so it cannot turn
    for (s = [-1, 1]) {
      translate([SCREW_X, s * SCREW_Y, ZL - 12]) cylinder(d = M4_D, h = 13);
      mirror([0, s < 0 ? 1 : 0, 0])
        translate([SCREW_X - (NUT4[0] + 0.3) / 2, SCREW_Y - NUT4[0] / sqrt(3), ZL - 6.7])
          cube([NUT4[0] + 0.3, OY, NUT4[1] + 0.2]);
    }
    // cross vents in the long walls, above the PCB
    for (s = [-1, 1], x = [-15 : 5 : 15])
      translate([x - 0.9, s > 0 ? CY - 0.5 : -OY - 0.5, ZT + 0.8]) cube([1.8, WALL + 1, ZL - ZT - 2]);
  }
}

module lid() {
  difference() {
    union() {
      // square at -X, where it sits against the antenna-end wall
      intersection() {
        rbox(-CX + 0.2 - CORNER_R, X1, OY, ZL, H);
        translate([-CX + 0.2, -OY, ZL]) cube([X1 + CX, 2 * OY, LID_T]);
      }
      // tongue into the antenna-end wall
      translate([-CX - TONGUE, -SLOT_Y + 0.4, ZL]) cube([TONGUE + 1, 2 * (SLOT_Y - 0.4), LID_T]);
      // ribs over the header solder stubs keep the board down
      for (s = [-1, 1]) translate([-22, s > 0 ? 10.4 : -CY + 0.2, ZT + STUB_CLEAR])
        cube([36, CY - 0.2 - 10.4, ZL - ZT - STUB_CLEAR + 0.01]);
    }
    // vents over the USB chip, regulator and power LED
    for (y = [-8 : 3.2 : 8.1]) translate([0, y, ZL - 1]) linear_extrude(LID_T + 2) stadium(-3, 15, 1.6);
    // BOOT (+Y) and EN (-Y) pin holes
    for (s = [-1, 1]) translate([0, s * 9, ZL - 1]) linear_extrude(LID_T + 2) stadium(17.5, 24.5, 3.6);
    // labels
    for (l = [["BOOT", 1], ["EN", -1]]) translate([21, l[1] * 13.4, H - 0.6])
      linear_extrude(1) text(l[0], size = 2.4, font = "Liberation Sans:style=Bold", halign = "center", valign = "center");
    // countersunk M4 screws
    for (s = [-1, 1]) translate([SCREW_X, s * SCREW_Y, 0]) {
      translate([0, 0, ZL - 1]) cylinder(d = M4_D, h = LID_T + 2);
      translate([0, 0, H - (CSK_D - M4_D) / 2]) cylinder(d1 = M4_D, d2 = CSK_D, h = (CSK_D - M4_D) / 2 + 0.01);
    }
  }
}

// Board stand-in for the assembled view (not printed).
module board() {
  color("#222") translate([-25.75, -14, ZC]) cube([51.5, 28, PCB_T]);
  color("silver") translate([-25.75, -9, ZT]) cube([25.5, 18, 3.1]);
  color("silver") translate([22.2, -4.5, ZT]) cube([7.5, 9, 3.2]);
  for (s = [-1, 1]) color("#111") translate([-HDR_L / 2, s * 12.7 - HDR_BODY / 2, ZC - HDR_BODY]) cube([HDR_L, HDR_BODY, HDR_BODY]);
}

module placed(p) {
  if (orient == "use") {
    if (p == "base") base();
    if (p == "lid") lid();
  } else {
    // on the bed origin
    if (p == "base") translate([-X0, OY, 0]) base();
    if (p == "lid") translate([X1, OY, H]) rotate([0, 180, 0]) lid();
  }
}

if (part == "assembly") {
  color("#e8e2d0") base();
  color("#cfd8dc", 0.6) lid();
  board();
} else {
  placed(part);
}
