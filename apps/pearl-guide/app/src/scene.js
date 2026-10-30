// Builds the cast from the loaded models and the props drawn in code, and the small context the story poses it
// through (S.a, S.node, S.clip, S.glow).

import { Box3, BoxGeometry, Color, CylinderGeometry, Group, Mesh, Object3D, SphereGeometry } from 'three';
import { Cast } from './cast.js';
import * as P from './props.js';

const MM = 0.001;

function patchClip(material, uniform) {
  material.onBeforeCompile = (shader) => {
    shader.uniforms.uClip = uniform;
    shader.vertexShader = shader.vertexShader
      .replace('#include <common>', '#include <common>\nvarying float vClipY;')
      .replace('#include <project_vertex>', '#include <project_vertex>\nvClipY = (modelMatrix * vec4(transformed, 1.0)).y;');
    shader.fragmentShader = shader.fragmentShader
      .replace('#include <common>', '#include <common>\nuniform float uClip;\nvarying float vClipY;')
      .replace('#include <clipping_planes_fragment>', '#include <clipping_planes_fragment>\nif (vClipY > uClip) discard;')
      .replace(
        '#include <opaque_fragment>',
        'float band = 1.0 - smoothstep(0.0, 0.0007, uClip - vClipY);\noutgoingLight += vec3(1.0, 0.52, 0.18) * band * 1.4;\n#include <opaque_fragment>',
      );
  };
  material.customProgramCacheKey = () => 'pearl-print-clip';
}

export function buildScene(stage, assets) {
  const cast = new Cast(stage.scene);
  const bench = (name) => {
    const o = assets.bench.getObjectByName(name);
    if (!o) throw new Error(`bench.glb has no ${name}`);
    return o;
  };
  const prints = (name) => assets.prints.getObjectByName(name);

  // the robot, with the parts the opening chapter moves
  const orb = assets.pearl.getObjectByName('balloon').clone(true);
  cast.add('pearl', assets.pearl.getObjectByName('pearl'));
  cast.part('hatch', 'pearl', 'pod_hatch');
  cast.part('coins', 'pearl', 'pod_coins');
  cast.part('propL', 'pearl', 'pod_prop_L_hub');
  cast.part('propR', 'pearl', 'pod_prop_R_hub');
  cast.part('propT', 'pearl', 'pod_prop_T_hub');
  cast.add('orb', orb);
  // what sits inside the shell: drawn only while the hatch is open
  const INSIDE = ['pod_xiao', 'pod_antenna', 'pod_drv_L', 'pod_drv_R', 'pod_sensor', 'pod_battery', 'pod_socket_lead', 'pod_wires_power', 'pod_wires_signal', 'pod_wires_sensor'];
  for (const n of INSIDE) cast.part(n, 'pearl');
  // Pearl floats with no bench under it, so it never needs the shadow map: it only casts onto the bench (the orb)
  for (const n of ['pearl', 'orb']) cast.get(n).obj.traverse((o) => o.isMesh && (o.receiveShadow = false));
  cast.wrap('mat', stage.benchMat, { own: false, shown: true });

  // tools and loose parts from the Blender bench
  for (const n of ['station', 'stand', 'third_hand', 'multimeter', 'iron', 'solder_tube', 'flux_pen', 'braid', 'cutters', 'tweezers', 'practice_board', 'helium_tank', 'balloon_flat', 'battery', 'stripper']) {
    cast.add(n, bench(n));
  }
  const twins = (src, names) => names.forEach((n) => cast.add(n, bench(src).clone(true)));
  twins('coin_2', ['coin1', 'coin2', 'coin3', 'coin4', 'coin5', 'coin6']);
  twins('coin_10c', ['coin7', 'coin8']);
  twins('motor', ['motor1', 'motor2', 'motor_rig']);
  twins('prop', ['prop1', 'prop2', 'prop3', 'prop4', 'prop_rig']);
  twins('socket_lead', ['lead1', 'lead2']);
  twins('driver', ['driver1', 'driver2', 'driver3']);

  // printed parts, in print orientation
  const clip = { value: 1e3 };
  const printNames = ['print_shell', 'print_hatch', 'print_duct', 'print_tail', 'print_collar'];
  const ductTwin = prints('print_duct').clone(true);
  const testDuct = prints('print_duct').clone(true);
  for (const n of printNames) cast.add(n, prints(n));
  cast.add('print_duct2', ductTwin);
  cast.add('test_duct', testDuct);
  for (const n of [...printNames, 'print_duct2']) cast.get(n).mats.forEach((m) => patchClip(m, clip));

  // props drawn in code
  cast.add('scale', P.pocketScale());
  cast.add('cup', P.paperCup());
  cast.add('spool', P.filamentSpool());
  cast.add('plate', P.buildPlate());
  cast.add('head', P.toolhead());
  cast.add('lamp', P.lamp());
  cast.add('solder', P.solderWire(70));
  cast.add('bead', new Mesh(new SphereGeometry(0.9 * MM, 16, 10), P.MAT.tin));
  cast.add('resistor', P.resistor());
  for (const [n, kind] of [['jointA', 'good'], ['jointA2', 'good'], ['jGood', 'good'], ['jCold', 'cold'], ['jBlob', 'blob']]) cast.add(n, P.joint(kind));
  cast.add('jBridge', P.bridge());
  cast.add('jointP', P.joint('good', 0.85));
  cast.add('wireL', P.wire('red', 45, 5));
  cast.add('wireR', P.wire('red', 45, 5));
  cast.add('wireP', P.wire('red', 30, 2));
  cast.add('shrinkS', P.heatshrink(12, 1.4, 'black'));
  const splice = new Mesh(new CylinderGeometry(0.75 * MM, 0.75 * MM, 5 * MM, 16), P.MAT.tin);
  splice.rotation.z = Math.PI / 2;
  const spliceGroup = new Group();
  spliceGroup.add(splice);
  cast.add('spliceJoint', spliceGroup);
  cast.add('sleeve1', P.heatshrink(14, 0.75, 'white'));
  cast.add('sleeve2', P.heatshrink(14, 0.75, 'white'));
  const wires = new Group();
  ['red', 'black', 'blue', 'white', 'red'].forEach((c, i) => {
    const w = P.wire(c, 80, 0);
    w.position.set(0, 0.0005, i * 4 * MM);
    wires.add(w);
  });
  cast.add('wires', wires);
  const shrink = new Group();
  [[1.5, 'black'], [3, 'black'], [1.5, 'white']].forEach(([r, c], i) => {
    const h = P.heatshrink(40, r, c);
    h.rotation.z = Math.PI / 2;
    h.position.set(0.02, r * MM, i * 7 * MM);
    shrink.add(h);
  });
  cast.add('shrink', shrink);
  cast.add('thread', P.thread());
  cast.add('dim', P.dimension(0.56));
  cast.add('block', P.block(50, 30, 40));
  cast.add('tape', new Mesh(new BoxGeometry(30 * MM, 0.25 * MM, 12 * MM), P.MAT.tape));
  cast.add('air', P.airflow(15, 90));

  // label anchors: an empty at the top centre of each actor's rest shape, made on first use
  const anchors = new Map();
  const box = new Box3();
  const S = {
    t: 0,
    cast,
    a: (n) => cast.get(n),
    reset() {
      cast.reset();
      clip.value = 1e3;
      for (const [n, on] of glowing) if (on) setGlow(n, 0);
    },
    commit() {
      cast.commit();
    },
    internals(on) {
      for (const n of INSIDE) cast.get(n).obj.visible = on;
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
          o.position.set(0, 0, 0);
          o.quaternion.identity();
          o.scale.set(1, 1, 1);
          o.updateMatrixWorld(true);
          box.setFromObject(o, true);
          a.position.set((box.min.x + box.max.x) / 2, box.max.y, (box.min.z + box.max.z) / 2);
          [o.position, o.quaternion, o.scale].forEach((v, i) => v.copy(saved[i]));
        }
        actor.obj.add(a);
        anchors.set(key, a);
      }
      return a;
    },
    clip(y) {
      clip.value = y == null ? 1e3 : y;
    },
    glow(name, amount) {
      setGlow(name, amount);
    },
  };
  const glowing = new Map();
  const warm = new Color(1, 0.82, 0.58);
  function setGlow(name, amount) {
    for (const m of cast.get(name).mats) if (m.emissive) m.emissive.copy(warm).multiplyScalar(amount);
    glowing.set(name, amount > 0);
  }
  return S;
}

