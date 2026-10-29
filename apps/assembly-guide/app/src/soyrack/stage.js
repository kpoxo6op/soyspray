// v3 scene extras for the Viewer: the cords (each part fading in with the chapter that lays it),
// the straps round their loops, and the camera framing of each chapter. Takes the place of the
// v1/v2 Installation.

import { Box3, CatmullRomCurve3, Group, Mesh, MeshStandardMaterial, TubeGeometry, Vector3 } from 'three';
import { buildConnector } from '../hardware.js';
import { chapterAt } from '../timeline.js';
import { polyLength } from '../cablepath.js';
import { CABLES, TIES } from './cables.js';
import { buildTie } from './models.js';

const box = ([min, max]) => new Box3(new Vector3(...min), new Vector3(...max));

// Rack-millimetre boxes to frame, and the orbit direction (radians) for each chapter view.
export const VIEWS = {
  prints: { box: [[0, 40, -112], [250, 120, -45]], view: { azimuth: 0.45, elevation: 0.62 } },
  base: { box: [[-5, -5, -115], [258, 245, 10]], view: { azimuth: 0.55, elevation: 0.5 } },
  'base-rear': { box: [[-5, -5, -115], [262, 262, 10]], view: { azimuth: 2.55, elevation: 0.66 } },
  cords: { box: [[-5, -5, -112], [262, 262, 12]], view: { azimuth: 0.5, elevation: 1.02 } },
  frame: { box: [[-5, -5, -115], [258, 245, 290]], view: { azimuth: 0.55, elevation: 0.28 } },
  lower: { box: [[-5, -5, -15], [258, 215, 215]], view: { azimuth: 0.5, elevation: 0.24 } },
  upper: { box: [[-5, -5, 195], [258, 215, 290]], view: { azimuth: 0.5, elevation: 0.3 } },
  'rear-upper': { box: [[-5, -5, 195], [258, 262, 290]], view: { azimuth: 2.6, elevation: 0.26 } },
  tall: { box: [[-5, -5, -115], [258, 245, 295]], view: { azimuth: 0.55, elevation: 0.26 } },
  rear: { box: [[-5, -5, -115], [262, 252, 295]], view: { azimuth: 2.6, elevation: 0.3 } },
  zigbee: { box: [[-990, -10, -115], [262, 320, 295]], view: { azimuth: 3.6, elevation: 0.42 } },
};

const FADE_IN = 1.1;

/** Something that fades in from just before its chapter and glows while the chapter runs. */
class Laid {
  constructor(object, chapter, glowing) {
    this.object = object;
    this.chapter = chapter;
    this.glowing = glowing;
    this.materials = [];
    object.traverse((o) => {
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
      for (const m of this.glowing) {
        m.emissive.setHex(active ? 0x73502c : 0x000000);
        m.emissiveIntensity = active ? 0.19 : 0;
      }
    }
  }
}

/** One part of a cord: its tube and the plugs it seats. */
class Lead extends Laid {
  constructor(cable, part, chapter) {
    const object = new Group();
    const curve = new CatmullRomCurve3(part.points.map((p) => new Vector3(...p)), false, 'centripetal');
    const segments = Math.max(16, Math.ceil(polyLength(part.points) / 3));
    const material = new MeshStandardMaterial({ color: cable.colour, roughness: 0.53, metalness: 0.03 });
    object.add(new Mesh(new TubeGeometry(curve, segments, cable.od / 2, 8, false), material));
    for (const plug of part.plugs) {
      const g = buildConnector(plug.type, cable.colour);
      g.position.set(...plug.pose.p);
      g.quaternion.set(...plug.pose.q);
      object.add(g);
    }
    super(object, chapter, [material]);
    this.cable = cable;
    this.part = part;
  }
}

export class SoyrackStage {
  constructor(timeline, parent) {
    this.timeline = timeline;
    this.root = new Group();
    parent.add(this.root);
    const byId = Object.fromEntries(timeline.chapters.map((c) => [c.id, c]));
    const chapter = (id, what) => {
      if (!byId[id]) throw new Error(`${what} names no chapter ${id}`);
      return byId[id];
    };
    this.leads = CABLES.flatMap((cable) => cable.parts.map((part) => new Lead(cable, part, chapter(part.chapter, cable.id))));
    this.ties = TIES.map((tie, i) => {
      const { object, materials } = buildTie(tie);
      return new Laid(object, chapter(tie.chapter, `tie ${i}`), materials);
    });
    for (const l of [...this.leads, ...this.ties]) this.root.add(l.object);
    this.time = 0;
  }

  setTime(t) {
    this.time = t;
    for (const l of this.leads) l.update(t);
    for (const l of this.ties) l.update(t);
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
