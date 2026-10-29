// Soyrack (v3): the timeline from the v3 meshes and the node trays that carry over from v2.
import { buildTimeline } from '../timeline.js';
import { DEVICES, soyrackPlacements } from './rack.js';
import { SOYRACK_CHAPTERS } from './chapters.js';

export { SoyrackStage } from './stage.js';
export { soyrackSheetHTML } from './sheet.js';
export { FLOOR_Z } from './rack.js';

export function buildSoyrackTimeline(meshes, v2Placements) {
  return buildTimeline(soyrackPlacements(meshes, v2Placements), SOYRACK_CHAPTERS, DEVICES);
}
