// The soldering bench: actors from bench.glb and the props drawn in code, and the context the soldering chapters
// pose them through. Modelled on ../scene.js: S.a, S.node, S.reset, S.commit, plus a few setters for prop state
// (tip, screen, meter, smoke, sponge, LEDs) that S.reset() puts back every frame.
//
// The work-holding frame: the practice board and everything on it live inside one Group (`frame`), so a chapter
// can clip the board in the helping hands, tilt it towards the camera or flip it over by posing that one actor.
// S.W(x, y, z) turns millimetres in the frame (board centre, board underside y = 0) into a world position.

import { Box3, Color, CylinderGeometry, Group, Mesh, Object3D, Vector3 } from 'three';
import { Cast } from '../cast.js';
import * as P from '../props.js';
import * as SP from './props.js';

const MM = 0.001;

/** Every actor the soldering chapters may ask for. buildScene checks the cast against it; the tests check the story. */
export const ACTORS = [
  'mat', 'frame',
  // bench.glb
  'stand', 'third_hand', 'multimeter', 'solder_tube', 'flux_pen', 'braid', 'cutters', 'tweezers', 'practice_board',
  'battery', 'driver1', 'driver2', 'driver3',
  // drawn in code
  'glasses', 'stripper', 'iron', 'cord', 'solder', 'bead', 'smoke', 'resistor', 'legCut', 'jointA', 'jointA2', 'jFix1', 'jFix3', 'jFix4',
  'jCold', 'jBridge', 'cutGood', 'cutCold', 'braidStrip', 'resT1', 'resT2', 'resT3', 'ledR', 'ledA', 'ledG', 'chip', 'cap',
  'jT1', 'jT2', 'jT3', 'probeR', 'probeB', 'cordR', 'cordB', 'wireL', 'wireR', 'slug', 'shrinkS', 'spliceJoint',
  'wireP1', 'wireP2', 'wireP3', 'wireP4', 'jointP1', 'jointP2', 'jointP3', 'jointP4', 'lead', 'dim3', 'dim40', 'dim254',
];

/** Actors that live in the work-holding frame (positions in board millimetres, as metres). */
const IN_FRAME = new Set([
  'practice_board', 'resistor', 'legCut', 'jointA', 'jointA2', 'jFix1', 'jFix3', 'jFix4', 'jCold', 'jBridge',
  'cutGood', 'cutCold', 'braidStrip', 'resT1', 'resT2', 'resT3', 'ledR', 'ledA', 'ledG', 'chip', 'cap', 'jT1', 'jT2', 'jT3',
]);

const DRY = new Color(0xd8c487);
const DAMP = new Color(0x8f7b45);

export function buildScene(stage, assets) {
  const cast = new Cast(stage.scene);
  const frame = new Group();
  frame.name = 'work frame';
  stage.scene.add(frame);
  const add = (name, obj, opts) => {
    if (!IN_FRAME.has(name)) return cast.add(name, obj, opts);
    obj.removeFromParent();
    frame.add(obj);
    return cast.wrap(name, obj, opts);
  };
  const bench = (name) => {
    const o = assets.bench.getObjectByName(name);
    if (!o) throw new Error(`bench.glb has no ${name}`);
    return o;
  };

  cast.wrap('mat', stage.benchMat, { own: false, shown: true });
  // his silicone mat is bright blue (21 Nov photos)
  stage.benchMat.material = stage.benchMat.material.map((m, i) => {
    const c = m.clone();
    c.color.setHex(i === 2 ? 0x8fd0ff : 0x1f86c4);
    return c;
  });
  cast.wrap('frame', frame, { own: false, shown: true });

  // the meter's screen rides on the meter, so it moves and fades with it
  const meter = bench('multimeter');
  const screen = SP.meterScreen();
  meter.add(screen);
  // the practice board's component side (its underside) carries the traffic light's printed marks
  bench('practice_board').add(SP.trafficPrint());
  add('stand', SP.restBoard());
  // the practice board is drawn as a plain green circuit board with tinned pads, like the kit's own board, so it does
  // not read as a wooden or special tool (Boris, 21 Nov)
  // colours of Boris's own tools, from his 21 Nov photos: blue cutters, black tweezers, a white flux pen with a blue
  // cap, a deeper orange meter holster
  const recolour = (name, re, hex) =>
    bench(name).traverse((o) => {
      if (!o.isMesh || !re.test(o.material.name)) return;
      o.material = o.material.clone();
      o.material.color.setHex(hex);
    });
  recolour('cutters', /handle/, 0x1f4fa8);
  recolour('tweezers', /steel/, 0x1c1c1e);
  recolour('flux_pen', /flux pen/, 0xeeeeea);
  recolour('flux_pen', /knob/, 0x1f3f9a);
  recolour('multimeter', /holster/, 0xc8501a);
  bench('practice_board').traverse((o) => {
    if (!o.isMesh) return;
    o.material = o.material.clone();
    if (/perfboard/.test(o.material.name)) o.material.color.setHex(0x1d6b3c);
    if (/copper/.test(o.material.name)) o.material.color.setHex(0xc9ccd0);
  });
  add('solder_tube', SP.solderSpool());
  for (const n of ['third_hand', 'multimeter', 'flux_pen', 'braid', 'cutters', 'tweezers', 'practice_board', 'battery']) add(n, bench(n));
  // a left hand on the cutters and the tweezers, at the handle end of their longest side, so neither floats
  const toolHands = new Map();
  const holdEnd = (name, end) => {
    const o = cast.get(name).obj;
    const box = new Box3();
    o.traverse((m) => m.isMesh && (m.geometry.computeBoundingBox(), box.union(m.geometry.boundingBox.clone().applyMatrix4(m.matrix))));
    const size = box.getSize(new Vector3());
    const axis = size.x >= size.y && size.x >= size.z ? 'x' : size.y >= size.z ? 'y' : 'z';
    const h = SP.hand({ r: Math.min(size.x, size.y, size.z) / MM / 2 + 2, left: true });
    const c = box.getCenter(new Vector3());
    c[axis] = end > 0 ? box.max[axis] - size[axis] * 0.3 : box.min[axis] + size[axis] * 0.3;
    h.position.copy(c);
    if (axis === 'y') h.rotation.z = end > 0 ? Math.PI / 2 : -Math.PI / 2;
    if (axis === 'z') h.rotation.y = end > 0 ? -Math.PI / 2 : Math.PI / 2;
    if (axis === 'x' && end < 0) h.rotation.y = Math.PI;
    h.visible = false;
    toolHands.set(name, h);
    o.add(h);
  };
  holdEnd('cutters', 1);
  holdEnd('tweezers', 1);
  add('glasses', SP.glasses());
  add('stripper', SP.stripper());
  for (const n of ['driver1', 'driver2', 'driver3']) add(n, bench('driver').clone(true));

  const iron = SP.penIron();
  // the right hand holds the iron by its grip, behind the hot metal
  const ironHand = SP.hand({ r: 11.4 });
  ironHand.position.set(84 * MM, 0, 0);
  iron.add(ironHand);
  add('iron', iron);
  add('cord', P.thread(1.4));
  cast.get('cord').mats.forEach((m) => m.color.setHex(0x1b1c1e));
  const solder = P.solderWire(70);
  // the left hand feeds the solder, pinching it near its far end
  const solderHand = SP.hand({ r: 0.4, left: true });
  solderHand.position.set(62 * MM, 10 * MM, -4.5 * MM);
  solderHand.rotation.set(0, 0.2, 0.3);
  solder.add(solderHand);
  add('solder', solder);
  add('bead', SP.bead());
  add('smoke', SP.smoke());
  add('resistor', SP.resistorT());
  add('legCut', SP.cutLeg());
  for (const n of ['jointA', 'jointA2', 'jFix1', 'jFix3', 'jFix4', 'jT1', 'jT2', 'jT3']) add(n, P.joint('good'));
  add('jCold', P.joint('cold'));
  add('jBridge', P.bridge());
  add('cutGood', SP.jointCut('good', 1.8));
  add('cutCold', SP.jointCut('cold', 1.8));
  add('braidStrip', SP.braidStrip());
  for (const n of ['resT1', 'resT2', 'resT3']) add(n, SP.resistorT());
  add('ledR', SP.led('red'));
  add('ledA', SP.led('amber'));
  add('ledG', SP.led('green'));
  add('chip', SP.dip());
  add('cap', SP.cap());
  // meter probes are always in a hand when they are out: right hand red, left hand black
  for (const [n, c, left] of [['probeR', 'red', false], ['probeB', 'black', true]]) {
    const pr = P.probe(c);
    const h = SP.hand({ r: 2.6, left });
    h.position.set(0, 40 * MM, 0);
    h.rotation.z = Math.PI / 2;
    pr.add(h);
    add(n, pr);
  }
  for (const [n, c] of [['cordR', 0xc3261f], ['cordB', 0x18191b]]) {
    add(n, P.thread(1.4));
    cast.get(n).mats.forEach((m) => m.color.setHex(c));
  }
  add('wireL', SP.wire2('red', 70, 3, 3));
  add('wireR', SP.wire2('red', 70, 3, 3));
  const slug = new Mesh(new CylinderGeometry(0.46 * MM, 0.46 * MM, 3 * MM, 12), P.MAT.red);
  slug.rotation.z = Math.PI / 2;
  const slugG = new Group();
  slugG.add(slug);
  add('slug', slugG);
  const shrink = P.heatshrink(12, 0.75, 'black');
  shrink.rotation.z = Math.PI / 2;
  const shrinkG = new Group();
  shrinkG.add(shrink);
  add('shrinkS', shrinkG);
  const splice = new Mesh(new CylinderGeometry(0.3 * MM, 0.3 * MM, 3.4 * MM, 12), P.MAT.tin);
  splice.rotation.z = Math.PI / 2;
  const spliceG = new Group();
  spliceG.add(splice);
  add('spliceJoint', spliceG);
  // onto GNDR, VIN, BOUT1, BOUT2: black on ground, red on the battery's plus, as on Pearl
  ['black', 'red', 'blue', 'white'].forEach((c, i) => add(`wireP${i + 1}`, P.wire(c, 30, 2)));
  for (const n of ['jointP1', 'jointP2', 'jointP3', 'jointP4']) add(n, P.joint('good', 0.85));
  add('lead', SP.splitLead());
  add('dim3', SP.dimBar(3));
  add('dim40', SP.dimBar(40, 3));
  add('dim254', SP.dimBar(2.54));

  const names = [...cast.map.keys()];
  const missing = ACTORS.filter((n) => !cast.has(n));
  const extra = names.filter((n) => !ACTORS.includes(n));
  if (missing.length || extra.length) throw new Error(`soldering cast differs from ACTORS: missing ${missing}, extra ${extra}`);

  // small parts throw no visible shadow; skipping them saves their shadow-pass draw calls
  for (const n of ['solder', 'bead', 'resistor', 'resT1', 'resT2', 'resT3', 'wireP1', 'wireP2', 'wireP3', 'wireP4', 'jointP1', 'jointP2', 'jointP3', 'jointP4', 'tweezers', 'cord', 'cordR', 'cordB', 'probeR', 'probeB', 'chip', 'cap', 'ledR', 'ledA', 'ledG', 'jointA', 'jointA2', 'jFix1', 'jFix3', 'jFix4', 'jCold', 'jBridge', 'jT1', 'jT2', 'jT3', 'shrinkS', 'slug', 'spliceJoint']) {
    cast.get(n).obj.traverse((o) => o.isMesh && (o.castShadow = false));
  }

  // state the story can set, and its rest values for reset()
  const sponge = cast.get('stand').mats.filter((m) => /sponge/.test(m.name));
  const roughRest = new Map();
  const wet = (n) => cast.get(n).mats.filter((m) => m.metalness > 0.5);
  for (const n of ['jointA', 'jointA2', 'jT1', 'jT2', 'jT3', 'jointP1', 'jointP2', 'jointP3', 'jointP4', 'jCold', 'jFix1']) for (const m of wet(n)) roughRest.set(m, [m.roughness, m.color.clone()]);
  const leds = ['ledR', 'ledA', 'ledG'].map((n) => cast.get(n).obj);
  const wires = ['wireL', 'wireR'].map((n) => cast.get(n).obj.userData);
  const resistors = ['resistor', 'resT1', 'resT2', 'resT3'].map((n) => cast.get(n).obj.userData);
  const [blobA, blobB, web] = cast.get('jBridge').obj.children;
  const webScale = web.scale.clone();
  const blobScale = blobA.scale.clone();

  // label anchors: an empty at the top centre of each actor's rest shape, made on first use
  const anchors = new Map();
  const box = new Box3();
  const out = new Vector3();
  const S = {
    t: 0,
    cast,
    a: (n) => cast.get(n),
    reset() {
      cast.reset();
      for (const h of toolHands.values()) h.visible = false;
      iron.userData.setReading('');
      SP.tipState(iron);
      screen.userData.setReading('', '');
      cast.get('smoke').obj.userData.setFlow(0, 0);
      cast.get('braidStrip').obj.userData.setSoak(0);
      for (const l of leds) SP.ledState(l, 0);
      for (const m of sponge) m.color.copy(DRY);
      for (const [m, [r, c]] of roughRest) {
        m.roughness = r;
        m.color.copy(c);
      }
      for (const w of wires) {
        SP.tinWire(w.copper, 0);
        SP.tinWire(w.copper0, 0);
      }
      for (const r of resistors) for (const i of [0, 1]) r.cut(i, r.rise);
      web.scale.copy(webScale);
      blobA.scale.copy(blobScale);
      blobB.scale.copy(blobScale);
    },
    commit() {
      cast.commit();
    },
    node(name, nodeName = null, offset = null) {
      const actor = cast.get(name);
      if (nodeName) {
        const o = actor.obj.getObjectByName(nodeName.replace(/\s/g, '_')); // GLTFLoader's sanitised node names
        if (!o) throw new Error(`${name} has no ${nodeName}`);
        return o;
      }
      const key = `${name}|${offset ? offset.join(',') : ''}`;
      let a = anchors.get(key);
      if (!a) {
        a = new Object3D();
        if (offset) a.position.fromArray(offset);
        else {
          const o = actor.obj;
          const saved = [o.position.clone(), o.quaternion.clone(), o.scale.clone()];
          const parent = o.parent;
          o.removeFromParent();
          o.position.set(0, 0, 0);
          o.quaternion.identity();
          o.scale.set(1, 1, 1);
          o.updateMatrixWorld(true);
          box.setFromObject(o, true);
          a.position.set((box.min.x + box.max.x) / 2, box.max.y, (box.min.z + box.max.z) / 2);
          [o.position, o.quaternion, o.scale].forEach((v, i) => v.copy(saved[i]));
          parent.add(o);
        }
        actor.obj.add(a);
        anchors.set(key, a);
      }
      return a;
    },
    /** World position of a point given in frame millimetres. A new Vector3 each call. */
    W(x, y, z) {
      frame.updateWorldMatrix(true, false);
      return frame.localToWorld(new Vector3(x * MM, y * MM, z * MM));
    },
    /** A label anchor at frame millimetres (moves with the frame). */
    F(x, y, z) {
      return S.node('frame', null, [x * MM, y * MM, z * MM]);
    },
    /** World position of an anchor or a child point of an actor. */
    at(obj) {
      obj.updateWorldMatrix(true, false);
      return obj.getWorldPosition(out).clone();
    },
    /** The pen iron: the tip at world point p, the handle leaving along yaw (about y) and pitch (up from level). */
    iron(p, yaw = 0, pitch = 0.6, alpha = 1, held = true) {
      ironHand.visible = held;
      const a = cast.get('iron').show(alpha).at(p.x ?? p[0], p.y ?? p[1], p.z ?? p[2]).turn(yaw, 0, pitch);
      const back = iron.userData.back;
      iron.updateWorldMatrix(true, false);
      const from = iron.localToWorld(back.clone());
      // the cord drops from the back of the handle to the back edge of the bench
      cast.get('cord').show(alpha).obj.userData.setEnds(from, new Vector3(from.x + 0.12, 0.003, Math.min(from.z - 0.25, -0.2)));
      return a;
    },
    /** Show the hand that holds a tool (cutters, tweezers) this frame. */
    hold(name) {
      const h = toolHands.get(name);
      if (h) h.visible = true;
    },
    /** Tip: { tin, black, heat } each 0..1. Screen: '' off, '330' etc. */
    tip(state) {
      SP.tipState(iron, state);
    },
    screen(text) {
      iron.userData.setReading(text);
    },
    meter(text, unit = '') {
      screen.userData.setReading(text, unit);
    },
    /** Flux smoke rising from world point p at strength 0..1, flowing with time k. */
    smoke(p, strength, k) {
      if (strength <= 0.01) return;
      cast.get('smoke').show().at(p.x, p.y, p.z);
      cast.get('smoke').obj.userData.setFlow((k * 0.9) % 1, strength);
    },
    sponge(f) {
      for (const m of sponge) m.color.copy(DRY).lerp(DAMP, f);
    },
    led(i, on) {
      SP.ledState(leds[i], on);
    },
    soak(f) {
      cast.get('braidStrip').obj.userData.setSoak(f);
    },
    /** Molten solder is glassy; it sets to a softer shine. f 1 = molten. */
    wet(name, f) {
      for (const m of wet(name)) m.roughness = roughRest.get(m)[0] * (1 - 0.65 * f);
    },
    /** A dull joint brightened: f 0 dull, 1 bright tin. */
    brighten(name, f) {
      for (const m of wet(name)) {
        m.color.copy(roughRest.get(m)[1]).lerp(SP.TIN, f);
        m.roughness = roughRest.get(m)[0] + (0.14 - roughRest.get(m)[0]) * f;
      }
    },
    /** Trim a resistor's leg i to h mm above its body's axis. */
    cutLeg(name, i, h) {
      cast.get(name).obj.userData.cut(i, h);
    },
    /** The solder web of the bridge, 1 whole, 0 soaked away. */
    bridgeWeb(f) {
      web.scale.set(webScale.x * Math.max(0.001, f), webScale.y, webScale.z * Math.max(0.001, f));
    },
    /** The bridge's two blobs: 1 as bridged, 0.5 two separate joints with a gap between them. */
    bridgeBlobs(f) {
      blobA.scale.copy(blobScale).multiplyScalar(f);
      blobB.scale.copy(blobScale).multiplyScalar(f);
    },
    tinWire(i, f, end = 'copper') {
      SP.tinWire(wires[i][end], f);
    },
  };
  return S;
}
