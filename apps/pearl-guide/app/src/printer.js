// Loading filament on Boris's P1S, which has no AMS: every filament goes in by hand through the PTFE tube at the
// back. The first load is the leftover PETG, about 2 m. Steps follow Bambu's P1 wiki (loading and replacing
// filament); temperatures are Bambu Studio's Generic PETG preset; door advice is Bambu's material table.
// Lengths come from Bambu Studio 2.8.2 on 1 November 2026: its P1S start G-code pushes 139 mm through the
// nozzle, and the side duct sliced with the settings in Files and Generic PETG needs 0.55 m, 1.69 g, 18 min.

export const PRINTER_LEDE =
  'Your P1S has no AMS, so each filament goes in by hand through the PTFE tube at the back. These steps load the leftover PETG, about 2 m, which is enough for one small part. PLA Matte loads the same way.';

export const LOAD = {
  title: 'Load the PETG',
  steps: [
    'Measure the PETG along a tape measure and write the length down.',
    'Snip the end at a slant with side cutters or strong scissors and straighten the first 10 cm, so it slides down the tube.',
    'If filament is still in the printer, choose Unload on the screen. It heats, cuts the filament and asks you to pull it out at the back.',
    'Push the PETG into the PTFE tube at the back until it stops at the extruder.',
    'Choose Load on the screen. When the nozzle reaches 250 °C, push again until the extruder grips the PETG and pulls it in.',
    'Watch the nozzle without touching it. When PETG flows out, choose Done. If nothing comes out, choose Retry.',
    'In Bambu Studio choose Generic PETG under Prepare. Under Device, click the external spool and choose it there too.',
  ],
};

export const PETG = {
  title: 'Print settings for PETG',
  rows: [
    ['Filament', 'Generic PETG, in Prepare and on the external spool'],
    ['Nozzle', '255 °C, set by the preset'],
    ['Plate', 'Textured PEI at 70 °C, washed with dish soap and dried'],
    ['Door', 'Open while it prints, so the extruder stays cool'],
    ['The rest', 'As in Files: 0.12 mm Fine, Arachne walls, tree supports'],
  ],
};

export const FIRST = {
  title: 'A first part that fits',
  file: 'pearl_v3_1_side_duct.stl',
  name: 'One side duct, in PETG',
  note: 'Bambu Studio puts it at about 0.55 m of PETG and 18 minutes, supports included. Keep it for the fan test.',
};

export const SHORT = {
  title: 'Make 2 m count',
  notes: [
    'Each print starts by pushing 14 cm through the nozzle to clean it. Loading uses a little more.',
    'After slicing, Bambu Studio shows the length the plate needs. Keep it 0.5 m under what you measured.',
    'If the PETG runs out mid-print, the sensor in the toolhead pauses the print and the part stays half made.',
    'A spool hangs on the holder at the back. Lay a loose coil in a box behind the printer so it unwinds without knots.',
    'Crackling at the nozzle and fine strings mean the PETG is damp. It still prints. Seal the rest in a bag.',
  ],
};

export const AFTER = {
  title: 'When it is done',
  notes: [
    'Let the plate cool, then flex it and the part comes off. Warm PETG clings to the plate.',
    'Choose Unload, pull the PETG out at the back and seal it in a bag. Load PLA Matte the same way when it arrives.',
  ],
  check: 'A PETG side duct off a cool plate, and the printer unloaded. Good place to stop.',
};
