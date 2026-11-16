// The Soyrack assembly guide: the printed rack parts and the node trays that carry over from the old rack.
import trayMeshBytes from '../data/trays.bin';
import rackMeshBytes from '../data/v3/meshes.bin';
import { decodeMeshes } from './meshes.js';
import { startGuide } from './boot.js';
import { buildSoyrackTimeline, SoyrackStage, soyrackSheetHTML, FLOOR_Z } from './soyrack/index.js';

const meshes = { ...decodeMeshes(trayMeshBytes), ...decodeMeshes(rackMeshBytes) };
startGuide({ timeline: buildSoyrackTimeline(meshes), meshes, Stage: SoyrackStage, floorZ: FLOOR_Z, sheet: soyrackSheetHTML, eyebrow: 'SOYRACK' });
