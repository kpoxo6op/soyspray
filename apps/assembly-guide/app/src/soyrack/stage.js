// v3 scene extras for the Viewer: the leads (fading in with the chapter that connects them) and
// the camera framing of each chapter. Takes the place of the v1/v2 Installation.

import { Box3, CatmullRomCurve3, Group, Mesh, MeshStandardMaterial, TubeGeometry, Vector3 } from 'three';
import { buildConnector } from '../hardware.js';
import { chapterAt } from '../timeline.js';
import { polyLength } from '../cablepath.js';
import { CABLES } from './cables.js';

const box = ([min, max]) => new Box3(new Vector3(...min), new Vector3(...max));

// Rack-millimetre boxes to frame, and the orbit direction (radians) for each chapter view.
export const VIEWS = {
  prints: { box: [[0, 40, -92], [250, 120, -25]], view: { azimuth: 0.45, elevation: 0.62 } },
  base: { box: [[-5, -5, -95], [258, 245, 10]], view: { azimuth: 0.55, elevation: 0.5 } },
  'base-rear': { box: [[-5, -5, -95], [262, 262, 10]], view: { azimuth: 2.55, elevation: 0.66 } },
  frame: { box: [[-5, -5, -95], [258, 245, 330]], view: { azimuth: 0.55, elevation: 0.28 } },
  lower: { box: [[-5, -5, -15], [258, 215, 215]], view: { azimuth: 0.5, elevation: 0.24 } },
  upper: { box: [[-5, -5, 195], [258, 215, 335]], view: { azimuth: 0.5, elevation: 0.3 } },
  'rear-upper': { box: [[-5, -5, 195], [258, 262, 335]], view: { azimuth: 2.6, elevation: 0.26 } },
  tall: { box: [[-5, -5, -95], [258, 245, 425]], view: { azimuth: 0.55, elevation: 0.26 } },
  rear: { box: [[-5, -5, -95], [262, 252, 425]], view: { azimuth: 2.6, elevation: 0.3 } },
  zigbee: { box: [[-990, -10, -95], [262, 280, 425]], view: { azimuth: 0.3, elevation: 0.42 } },
};

const FADE_IN = 1.1;

class Lead {
  constructor(cable, chapter) {
    this.cable = cable;
    this.chapter = chapter;
    this.object = new Group();
    this.materials = [];
    const pts = cable.points.map((p) => new Vector3(...p));
    const curve = new CatmullRomCurve3(pts, false, 'centripetal');
    const segments = Math.max(16, Math.ceil(polyLength(cable.points) / 3));
    this.material = new MeshStandardMaterial({ color: cable.colour, roughness: 0.53, metalness: 0.03 });
    const tube = new Mesh(new TubeGeometry(curve, segments, cable.od / 2, 8, false), this.material);
    tube.castShadow = true;
    this.object.add(tube);
    for (const plug of cable.plugs) {
      const g = buildConnector(plug.type, cable.colour);
      g.position.set(...plug.pose.p);
      g.quaternion.set(...plug.pose.q);
      this.object.add(g);
    }
    this.object.traverse((o) => {
      if (!o.isMesh) return;
      o.castShadow = true;
      if (!this.materials.includes(o.material)) this.materials.push(o.material);
    });
    this.alpha = -1;
    this.active = null;
  }

  update(t) {
    const c = this.chapter;
    const alpha = Math.max(0, Math.min(1, (t - (c.start - 0.3)) / FADE_IN));
    const active = t >= c.start && t < c.end;
    this.object.visible = alpha > 0.003;
    if (alpha !== this.alpha) {
      this.alpha = alpha;
      for (const m of this.materials) {
        const transparent = alpha < 0.995;
        if (m.transparent !== transparent) {
          m.transparent = transparent;
          m.needsUpdate = true;
        }
        m.opacity = alpha;
      }
    }
    if (active !== this.active) {
      this.active = active;
      this.material.emissive.setHex(active ? 0x73502c : 0x000000);
      this.material.emissiveIntensity = active ? 0.19 : 0;
    }
  }
}

export class SoyrackStage {
  constructor(timeline, parent) {
    this.timeline = timeline;
    this.root = new Group();
    parent.add(this.root);
    const byId = Object.fromEntries(timeline.chapters.map((c) => [c.id, c]));
    this.leads = CABLES.map((cable) => {
      const chapter = byId[cable.chapter];
      if (!chapter) throw new Error(`lead ${cable.id} names no chapter`);
      const lead = new Lead(cable, chapter);
      this.root.add(lead.object);
      return lead;
    });
    this.time = 0;
  }

  setTime(t) {
    this.time = t;
    for (const lead of this.leads) lead.update(t);
    return { room: 0 };
  }

  camera() {
    const c = this.timeline.chapters[chapterAt(this.timeline, this.time || 0)];
    const v = VIEWS[c.view] || VIEWS.tall;
    return { key: c.view || 'tall', box: box(v.box), view: v.view };
  }

  anchor() {
    return new Vector3();
  }
}
