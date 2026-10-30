// Printable parts for Stage 0: Pearl v3.1, exported from the Blender model on 30 October 2026.
// Grams are a slicer estimate for PLA Matte without supports; weigh yours and compare.

export const STL = [
  { file: 'pearl_v3_1_shell.stl', name: 'Pod shell', qty: 1, grams: 6.3, note: 'Prints dome up with supports inside.' },
  { file: 'pearl_v3_1_pole_cap.stl', name: 'Pole cap', qty: 1, grams: 4.1, note: 'Prints dish down with supports under it.' },
  { file: 'pearl_v3_1_hatch.stl', name: 'Hatch', qty: 1, grams: 2.5, note: 'Prints flat.' },
  { file: 'pearl_v3_1_side_duct.stl', name: 'Side duct', qty: 2, grams: 1.2, note: 'Print two.' },
  { file: 'pearl_v3_1_lift_duct.stl', name: 'Lift duct', qty: 1, grams: 1.2, note: 'Prints flat.' },
];

export const SETTINGS = [
  ['Printer', 'Bambu Lab P1S, 0.4 mm nozzle, textured PEI plate'],
  ['Filament', 'Bambu PLA Matte'],
  ['Process', '0.12 mm Fine'],
  ['Wall generator', 'Arachne'],
  ['Supports', 'On, tree (auto), build plate only'],
  ['Orientation', 'As loaded. The files are already the right way up.'],
];

export const PLATE_NOTE = 'All six fit one plate: about 4 hours and 40 g of filament, most of it support (slicer estimate).';
