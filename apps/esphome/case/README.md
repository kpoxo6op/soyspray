# ESP32 case

A printed case for the scale bridge: a 38-pin ESP-WROOM-32 DevKit with USB-C
and its pin headers soldered pins-down. Two parts, two M4 screws, two M4 nuts.
No inserts, glue or soldering, the same rule as Soyrack.

- **Base** (66 × 34 × 22.5 mm, about 15 g). The headers drop into two trenches
  that locate the board; the PCB rests on the cradle between them. The trenches
  take either 38-pin layout: rows 22.86 mm apart (narrow) or 25.4 mm (wide).
  USB-C opens at one end, where the two screw columns stand. The other end,
  where the PCB antenna is, has plastic only.
- **Lid** (66 × 34 × 5.7 mm, about 6 g). Ribs over the header rows keep the
  board down, vent slots sit over the USB chip, regulator and power LED, and two
  labelled holes reach BOOT and EN with a pin. Its tongue slides under the brow
  at the antenna end; the screws go in at the USB end.

## Print

PETG, 0.4 mm nozzle, 0.2 mm layers, 4 walls, 5 top and bottom layers, 15 %
gyroid, no supports. `stl/base.stl` prints standing as it is; `stl/lid.stl` is
already upside down. Both lie on the bed origin.

## Assemble

1. Take the board off its foam.
2. Push an M4 nut (DIN 934, 7 mm) into each side slot at the USB end until it
   stops; it then sits over the screw hole.
3. Drop the board in, USB-C to the open end, headers into the trenches.
4. Set the lid on about 2 mm toward the USB end, then slide it toward the
   antenna end so its tongue goes under the brow.
5. Two M4 × 12 countersunk screws (DIN 7991) down through the lid into the nuts,
   2.5 mm hex key, snug only.

Keep the antenna end clear of metal and pointing at the scale.

## Change it

`esp32-case.scad` is parametric: `FIT`, the board limits (`BOARD_W` 28.6,
`BOARD_L` 54), `ROWS`, the header sizes, `TOP_CLEAR`, `NUT4`, and the USB
plug opening (`USB_W` × `USB_H`, 13.6 × 8.4 mm). Then:

```sh
npm ci
node render.mjs                         # stl/base.stl, stl/lid.stl for printing
ORIENT=use node render.mjs /tmp/case    # assembled position, for checks
```

Limits: designed from a photo and common board sizes, not a measured board.
A 30-pin board (15 pins a side) would sit loose along its length, and a cable
plug wider than 13.6 mm or thicker than 8.4 mm will not reach the socket.
