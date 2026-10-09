import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

export const SOURCE = resolve(dirname(fileURLToPath(import.meta.url)), '..');
export const SITE = resolve(SOURCE, 'dist');

export const placements = JSON.parse(readFileSync(resolve(SOURCE, 'data/placements.json'), 'utf8'));
export const meshBytes = new Uint8Array(readFileSync(resolve(SOURCE, 'data/meshes.bin')));

/** Minimal DOM/canvas stand-ins so the Three.js scene graph can be built without a browser. */
export function installDomStubs() {
  const ctx = new Proxy(
    {},
    {
      get(target, key) {
        if (key in target) return target[key];
        if (key === 'createLinearGradient' || key === 'createRadialGradient') return () => ({ addColorStop() {} });
        if (key === 'measureText') return () => ({ width: 10 });
        return () => {};
      },
      set(target, key, value) {
        target[key] = value;
        return true;
      },
    },
  );
  const element = () => {
    const listeners = {};
    return {
      style: {},
      width: 300,
      height: 150,
      clientWidth: 1280,
      clientHeight: 800,
      setAttribute() {},
      addEventListener(type, fn) {
        (listeners[type] ||= []).push(fn);
      },
      removeEventListener() {},
      appendChild() {},
      getContext: () => ctx,
      getRootNode() {
        return { addEventListener() {}, removeEventListener() {} };
      },
      getBoundingClientRect: () => ({ left: 0, top: 0, width: 1280, height: 800 }),
      ownerDocument: { addEventListener() {}, removeEventListener() {} },
      listeners,
    };
  };
  globalThis.window = globalThis.window || { devicePixelRatio: 1, innerWidth: 1280, innerHeight: 800 };
  globalThis.document = { createElement: element, createElementNS: element };
  return element;
}

export function fakeRenderer(makeElement) {
  const domElement = makeElement();
  const calls = { render: 0, setSize: [] };
  return {
    calls,
    domElement,
    shadowMap: { enabled: false, type: null, autoUpdate: true, needsUpdate: false },
    capabilities: { getMaxAnisotropy: () => 8 },
    setPixelRatio() {},
    setClearColor() {},
    setSize(w, h) {
      calls.setSize.push([w, h]);
    },
    render() {
      calls.render++;
    },
  };
}
