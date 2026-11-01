// Soyrack (v3): the timeline from the v3 meshes and the node trays that carry over from v2.
import { buildTimeline } from '../timeline.js';
import { DEVICES, soyrackPlacements } from './rack.js';
import { TEST_DEVICES, testPlacements } from './testprints.js';
import { SOYRACK_CHAPTERS } from './chapters.js';

export { SoyrackStage } from './stage.js';
export { soyrackSheetHTML } from './sheet.js';
export { FLOOR_Z } from './rack.js';

// The test prints and their checks come first, then the rack.
export function buildSoyrackTimeline(meshes, v2Placements) {
  const rack = soyrackPlacements(meshes, v2Placements);
  const tests = testPlacements();
  const placements = { groups: {}, instances: [...tests.instances, ...rack.instances], screws: [...tests.screws, ...rack.screws] };
  return buildTimeline(placements, SOYRACK_CHAPTERS, [...DEVICES, ...TEST_DEVICES]);
}
