// The crimping explainer at explain.soyspray.vip/crimping/: making the rack's Ethernet leads with the crimp kit.
import { startGuide } from './boot.js';
import { buildCrimpTimeline, CrimpStage, FLOOR_Z, legendHTML } from './crimping/index.js';

startGuide({ timeline: buildCrimpTimeline(), Stage: CrimpStage, floorZ: FLOOR_Z, legends: { t568b: legendHTML() }, eyebrow: 'CRIMPING' });
