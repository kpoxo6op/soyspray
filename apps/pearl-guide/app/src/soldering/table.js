// "What is what": Boris's own kit, filmed laid out on his kitchen table on 21 Nov 2026 (frame at 1:41 of
// PXL_20261121_035948930.mp4, cropped). Each mark is a percentage of the photo's width and height. Bags that were
// still closed when filmed say "probably": open them and match the contents to the Kit list below.

/** Groups, in the order the legend shows them. */
export const TABLE_GROUPS = [
  { id: 'solder', title: 'For this page' },
  { id: 'pearl', title: 'For Pearl, later. Keep them off the mat' },
  { id: 'other', title: 'Not for soldering' },
  { id: 'check', title: 'Open and check' },
];

// [group, x %, y %, name, what it looks like on the table, what it is for]
const MARKS = [
  ['solder', 72.1, 15.4, 'Soldering iron, CXG E60WT', 'Red handle with a small screen. Its Euro plug sits in a white adapter.', 'Every chapter. Push the plug fully into the adapter.'],
  ['solder', 20.9, 83.0, 'Silicone mat', 'The big blue sheet.', 'You work on it. Heat does not mark it.'],
  ['solder', 50.0, 70.5, 'Solder, 0.8 mm', 'The reel with the red and blue label.', 'Every joint. It contains lead: no food at the bench.'],
  ['solder', 48.8, 79.8, 'Flux pen', 'White pen with a blue cap.', 'Chapter 3, to make a dull joint flow.'],
  ['solder', 16.9, 58.0, 'Desolder braid, Goot 1.5 mm', 'Small reel on a red and white card, from Jaycar.', 'Chapter 3, to lift extra solder.'],
  ['solder', 30.2, 72.1, 'Second desolder braid', 'Orange reel lying on the mat.', 'A spare. Use either one.'],
  ['solder', 57.0, 93.1, 'Flush cutters', 'Blue handles.', 'Chapter 2, to cut legs. Glasses on.'],
  ['solder', 54.1, 85.6, 'Helping hands', 'Two bags of jointed arms with clips.', 'Fit the arms to their base before chapter 2.'],
  ['solder', 41.9, 50.5, 'Tweezers, set of 6', 'Black tweezers on a yellow card.', 'Chapter 6, to hold a wire on a pad.'],
  ['solder', 38.4, 63.3, 'Wire stripper', 'Teal handles.', 'Chapter 5. Use the notch marked 28.'],
  ['solder', 51.2, 97.3, 'Multimeter, ANENG M126', 'Black and orange box.', 'Chapters 4 to 6: the beep checks a joint.'],
  ['solder', 50.6, 29.8, 'Heatshrink, 127 pieces', 'Black bag with a white label.', 'Chapter 5, over a splice.'],
  ['solder', 59.3, 58.0, 'Practice kit, probably', 'Silver bag, a printed board shows through it.', 'Chapter 4, the traffic light.'],
  ['solder', 81.4, 39.6, 'Driver boards, probably', 'Silver bag with a white label.', 'Chapter 6. Keep two boards untouched for Pearl.'],
  ['solder', 74.4, 69.1, '28 AWG silicone wire, probably', 'The big white bag.', 'Chapters 5 and 6.'],
  ['solder', 18.6, 38.0, 'JST battery leads, 10 pairs', 'Red and black wires in a small bag.', 'Chapter 6, to read the battery.'],
  ['pearl', 27.9, 48.9, 'LiPo battery, 300 mAh', 'Small yellow battery in a white zip bag.', 'Stays in its bag until chapter 6 reads it. Never near the iron.'],
  ['pearl', 30.8, 32.4, '10 kΩ resistors, 8', 'Blue resistors taped on a strip, Jaycar label.', 'Pearl’s battery divider.'],
  ['pearl', 9.5, 76.6, 'White heatshrink, 1.5 mm', 'The long white tube across the table.', 'Pearl’s motor leads.'],
  ['pearl', 52.3, 11.2, 'Pocket scale', 'Gold case.', 'Weighing prints and lift.'],
  ['pearl', 15.1, 20.7, 'Foil balloons, white, 5', 'Folded white sheets in a clear bag.', 'Pearl’s orb. Foil melts: keep it away from the iron.'],
  ['pearl', 14.0, 51.9, 'Motors, probably', 'Small bubble-wrapped bundle.', 'The thrust test.'],
  ['pearl', 25.0, 55.9, 'Props, Gemfan 31 mm', 'Two small bags with red labels.', 'Press onto the motors.'],
  ['other', 23.3, 26.3, 'ESP32 board', 'Silver bag with a yellow caution sticker.', 'Home sensors. Not on this page.'],
  ['other', 10.5, 63.8, 'ESP32 board', 'Silver bag, ESP32 on the label.', 'Home sensors. Not on this page.'],
  ['other', 34.3, 25.5, 'ESP32 boards, probably', 'Dark bag marked 3 in pen.', 'Home sensors. Not on this page.'],
  ['other', 59.3, 38.3, 'Radar, LD2410C', 'Silver bag, HLK-LD2410C on the label.', 'Home sensors. Not on this page.'],
  ['other', 54.7, 19.7, 'Jumper wires', 'Rainbow ribbon of wires.', 'Plug-in wires for the ESP32. No solder.'],
  ['check', 40.1, 38.6, 'Bubble envelope', 'Something black inside.', 'Open it and find it in the Kit list.'],
  ['check', 88.4, 11.7, 'Long clear bag with papers', 'Next to the iron.', 'Open it and find it in the Kit list.'],
];

export const TABLE = {
  title: 'What is what',
  lede: 'Your table, filmed on 21 Nov. Open the bags marked probably, then put the “For this page” things on the mat.',
  // The build adds a content revision (build.mjs).
  src: typeof __PEARL_PHOTOS__ !== 'undefined' ? __PEARL_PHOTOS__.table : 'data/table.jpg',
  alt: 'Boris’s soldering tools and Pearl parts laid out on an oak table, with numbered marks.',
  missing: 'No stand came with the iron: an old board with two blocks is its rest, as chapter 1 shows. Still to buy: safety glasses and slide switches.',
  groups: TABLE_GROUPS,
  marks: MARKS.map(([group, x, y, name, looks, use], i) => ({ n: i + 1, group, x, y, name, looks, use })),
};
