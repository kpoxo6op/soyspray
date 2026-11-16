// The crimping explainer's timeline and scene: only the mat and the kit, with no rack around them.
import { Box3, Group, Vector3 } from 'three';
import { buildTimeline, chapterAt } from '../timeline.js';
import { FLOOR_Z } from '../soyrack/rack.js';
import { CRIMP_CHAPTERS, CRIMP_DEVICES, CRIMP_VIEWS, crimpPlacements } from './crimp.js';

export { legendHTML } from './legend.js';
export { FLOOR_Z };

export function buildCrimpTimeline() {
  return buildTimeline(crimpPlacements(), CRIMP_CHAPTERS, CRIMP_DEVICES);
}

/** No cords or straps here: the stage only frames each chapter. */
export class CrimpStage {
  constructor(timeline, parent) {
    this.timeline = timeline;
    this.root = new Group();
    parent.add(this.root);
    this.time = 0;
  }

  setTime(t) {
    this.time = t;
    return false;
  }

  camera() {
    const c = this.timeline.chapters[chapterAt(this.timeline, this.time || 0)];
    const v = CRIMP_VIEWS[c.view] || CRIMP_VIEWS['crimp-kit'];
    return { key: c.view, box: new Box3(new Vector3(...v.box[0]), new Vector3(...v.box[1])), view: v.view };
  }
}
