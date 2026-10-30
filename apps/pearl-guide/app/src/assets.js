// Loads the three glTF files exported from Pearl's Blender model and gives their materials a web finish.

import { Color, MeshPhysicalMaterial, MeshStandardMaterial, DoubleSide } from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { DRACOLoader } from 'three/examples/jsm/loaders/DRACOLoader.js';

// File names carry a content revision added by the build (see build.mjs).
const FILES = typeof __PEARL_ASSETS__ !== 'undefined' ? __PEARL_ASSETS__ : { pearl: 'data/pearl.glb', prints: 'data/prints.glb', bench: 'data/bench.glb' };

export const PLA = new MeshStandardMaterial({ color: 0xf3f1ec, roughness: 0.66, metalness: 0, side: DoubleSide });

// Four heat-sealed seams run pole to pole, 45 degrees off the pod's axis (parts_v3.foil_sphere_4d).
function seams(material) {
  material.onBeforeCompile = (shader) => {
    shader.vertexShader = shader.vertexShader
      .replace('#include <common>', '#include <common>\nvarying vec3 vFoil;')
      .replace('#include <begin_vertex>', '#include <begin_vertex>\nvFoil = position;');
    shader.fragmentShader = shader.fragmentShader
      .replace('#include <common>', '#include <common>\nvarying vec3 vFoil;')
      .replace(
        '#include <color_fragment>',
        `#include <color_fragment>
        float rxz = length(vFoil.xz);
        float phi = atan(-vFoil.z, vFoil.x) - 0.7853982;
        float s = mod(phi, 1.5707963);
        float arc = min(s, 1.5707963 - s) * rxz;
        float seam = 1.0 - smoothstep(0.0012, 0.0032, arc);
        diffuseColor.rgb = mix(diffuseColor.rgb, vec3(0.8, 0.79, 0.77), seam * 0.65);`,
      );
  };
  material.customProgramCacheKey = () => 'pearl-foil-seams';
  return material;
}

function foil() {
  // White 4D foil: a satin metallised film with a faint pearly thin-film sheen.
  return seams(new MeshPhysicalMaterial({
    color: 0xf0ede7,
    roughness: 0.3,
    metalness: 0.22,
    clearcoat: 0.55,
    clearcoatRoughness: 0.22,
    iridescence: 0.32,
    iridescenceIOR: 1.32,
    iridescenceThicknessRange: [260, 420],
    sheen: 0.25,
    sheenColor: new Color(0xeee6f4),
  }));
}

function finish(root) {
  const cache = new Map();
  root.traverse((o) => {
    if (!o.isMesh) return;
    o.castShadow = true;
    o.receiveShadow = true;
    const fix = (m) => {
      if (cache.has(m)) return cache.get(m);
      let out = m;
      const name = m.name || '';
      if (/4D foil/.test(name)) out = foil();
      else if (/printed PLA|white heatshrink|prop white/.test(name)) out = PLA;
      else if (m.transmission > 0 || m.opacity < 1) {
        // Transmission needs an extra render pass; plain transparency reads the same at this size.
        const glasses = /glasses/.test(name);
        out = new MeshStandardMaterial({ color: glasses ? 0xbfd6e6 : m.color, roughness: glasses ? 0.08 : m.roughness, metalness: m.metalness, transparent: true, opacity: glasses ? 0.5 : 0.45, depthWrite: false });
        o.castShadow = false;
      }
      out.name = name;
      cache.set(m, out);
      return out;
    };
    o.material = Array.isArray(o.material) ? o.material.map(fix) : fix(o.material);
  });
  return root;
}

export async function loadAssets(onProgress) {
  const draco = new DRACOLoader();
  draco.setDecoderPath('draco/');
  const loader = new GLTFLoader();
  loader.setDRACOLoader(draco);
  let done = 0;
  const names = Object.keys(FILES);
  const out = {};
  await Promise.all(
    names.map(async (k) => {
      const gltf = await loader.loadAsync(FILES[k]);
      out[k] = finish(gltf.scene);
      onProgress?.(++done / names.length);
    }),
  );
  draco.dispose();
  return out;
}
