// Soyrack: the timeline from the rack meshes and the node trays that carry over.
import { buildTimeline } from '../timeline.js';
import { DEVICES, soyrackPlacements } from './rack.js';
import { TEST_DEVICES, testPlacements } from './testprints.js';
import { SOYRACK_CHAPTERS } from './chapters.js';
import { CRIMP_DEVICES, crimpPlacements } from './crimp.js';

export { SoyrackStage } from './stage.js';
export { soyrackSheetHTML } from './sheet.js';
export { FLOOR_Z } from './rack.js';

// The test prints and their checks come first, then the rack; the Ethernet leads are crimped on a
// mat beside it before they go in.
export function buildSoyrackTimeline(meshes) {
  const rack = soyrackPlacements(meshes);
  const tests = testPlacements();
  const crimp = crimpPlacements();
  const placements = {
    groups: { ...rack.groups, ...crimp.groups },
    instances: [...tests.instances, ...rack.instances],
    screws: [...tests.screws, ...rack.screws],
  };
  return buildTimeline(placements, SOYRACK_CHAPTERS, [...DEVICES, ...TEST_DEVICES, ...CRIMP_DEVICES]);
}
