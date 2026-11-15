// Renderer, camera rig and HTML labels: Pearl's stage without the bench, shadows or environment map. The network
// is drawn as plain matte blocks, so lambert shading and two lights are enough and every frame stays cheap.

import { AmbientLight, DirectionalLight, PerspectiveCamera, Scene, SRGBColorSpace, Vector3, WebGLRenderer } from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';

export const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
export const smooth = (t) => {
  const x = clamp(t);
  return x * x * (3 - 2 * x);
};
const mix = (a, b, k) => a + (b - a) * k;

export class Stage {
  constructor({ container, labelLayer, reducedMotion = false, phone = false }) {
    this.container = container;
    this.labelLayer = labelLayer;
    this.phone = phone;
    this.insets = { top: 0, bottom: 0 };
    this.pristine = true;
    this.onPristineChange = null;

    const renderer = new WebGLRenderer({ antialias: true, alpha: true, powerPreference: 'high-performance' });
    // Phones have 2.5-3x screens and small GPUs: start at 1.5 and let adapt() trade resolution for frame rate.
    this.maxRatio = Math.min(window.devicePixelRatio || 1, phone ? 1.5 : 2);
    this.minRatio = Math.min(this.maxRatio, phone ? 0.85 : 1);
    this.ratio = this.maxRatio;
    this.frameMs = 16;
    this.slow = 0;
    this.quick = 0;
    renderer.setPixelRatio(this.ratio);
    renderer.setClearColor(0x000000, 0);
    renderer.outputColorSpace = SRGBColorSpace;
    container.appendChild(renderer.domElement);
    this.renderer = renderer;
    this.canvas = renderer.domElement;
    this.canvas.setAttribute('role', 'img');
    this.canvas.setAttribute('aria-label', 'Your home network, 3D view. Drag to turn, scroll or pinch to zoom.');

    const scene = new Scene();
    scene.add(new AmbientLight(0xf4efe6, 1.1));
    const key = new DirectionalLight(0xfff0de, 2.2);
    key.position.set(-6, 12, 8);
    const rim = new DirectionalLight(0xc6d8ff, 0.7);
    rim.position.set(8, 6, -10);
    scene.add(key, rim);
    this.scene = scene;

    this.camera = new PerspectiveCamera(40, 1, 0.1, 120);
    const controls = new OrbitControls(this.camera, this.canvas);
    controls.enableDamping = !reducedMotion;
    controls.dampingFactor = 0.08;
    controls.rotateSpeed = 0.7;
    controls.zoomSpeed = 0.9;
    controls.panSpeed = 0.8;
    controls.zoomToCursor = true;
    controls.screenSpacePanning = true;
    controls.minDistance = 1.5;
    controls.maxDistance = 40;
    controls.maxPolarAngle = Math.PI * 0.49;
    controls.addEventListener('start', () => this.setPristine(false));
    this.controls = controls;

    this.labels = new Map();
    this.pose = null;
    this.resize();
  }

  setPristine(on) {
    if (this.pristine === on) return;
    this.pristine = on;
    this.onPristineChange?.(on);
  }

  resetView() {
    this.setPristine(true);
    if (this.pose) this.applyPose(this.pose);
  }

  /** The story's camera for this moment; ignored while the reader is turning the view. */
  setPose(pose) {
    this.pose = pose;
    if (this.pristine) this.applyPose(pose);
  }

  applyPose({ p, t }) {
    // Portrait screens are narrow: step back along the same line so the subject still fits across.
    const k = this.camera.aspect < 1 ? Math.min(2.1, (1.25 / this.camera.aspect) ** 0.62) : 1;
    this.camera.position.set(t[0] + (p[0] - t[0]) * k, t[1] + (p[1] - t[1]) * k, t[2] + (p[2] - t[2]) * k);
    this.controls.target.set(t[0], t[1], t[2]);
    this.camera.lookAt(this.controls.target);
  }

  setInsets(top, bottom) {
    this.insets = { top, bottom };
    this.updateProjection();
  }

  updateProjection() {
    const w = this.container.clientWidth || window.innerWidth;
    const h = this.container.clientHeight || window.innerHeight;
    // Centre the picture in the space between the top bar and the caption/transport block.
    this.camera.setViewOffset(w, h, 0, (this.insets.bottom - this.insets.top) / 2, w, h);
    this.camera.aspect = w / h;
    this.camera.updateProjectionMatrix();
  }

  resize() {
    const w = this.container.clientWidth || window.innerWidth;
    const h = this.container.clientHeight || window.innerHeight;
    this.size = { w, h };
    this.renderer.setSize(w, h, false);
    this.updateProjection();
  }

  /** Feed the time between played frames. Sustained slow frames lower the resolution a step; quick ones restore it. */
  adapt(ms) {
    this.frameMs += (Math.min(ms, 100) - this.frameMs) * 0.1;
    this.slow = this.frameMs > 24 ? this.slow + 1 : 0;
    this.quick = this.frameMs < 13 ? this.quick + 1 : 0;
    let next = this.ratio;
    if (this.slow > 45 && this.ratio > this.minRatio) next = Math.max(this.minRatio, this.ratio - 0.25);
    if (this.quick > 120 && this.ratio < this.maxRatio) next = Math.min(this.maxRatio, this.ratio + 0.25);
    if (next !== this.ratio) {
      this.ratio = next;
      this.slow = this.quick = 0;
      this.renderer.setPixelRatio(next);
      this.resize();
    }
  }

  /** Labels for this moment: [{ id, text, at: Object3D | Vector3, side: 'r' | 'l' | 't' | 'b' }]. DOM is touched only when the list changes. */
  setLabels(list) {
    const want = new Set();
    for (const l of list) {
      want.add(l.id);
      let rec = this.labels.get(l.id);
      if (!rec) {
        const el = document.createElement('div');
        el.className = 'label';
        el.innerHTML = '<i></i><span></span>';
        this.labelLayer.appendChild(el);
        rec = { el, text: '', shownSide: null, width: 0 };
        this.labels.set(l.id, rec);
      }
      if (rec.text !== l.text) {
        rec.text = l.text;
        rec.el.lastChild.textContent = l.text;
        rec.width = 0; // measured once on the next placement, not every frame
      }
      rec.side = l.side || 'r';
      rec.at = l.at;
    }
    for (const [id, rec] of this.labels) {
      if (!want.has(id)) {
        rec.el.remove();
        this.labels.delete(id);
      }
    }
  }

  placeLabels() {
    const { w, h } = this.size;
    const v = this.tmp || (this.tmp = new Vector3());
    for (const rec of this.labels.values()) {
      if (rec.at.isObject3D) rec.at.getWorldPosition(v);
      else v.copy(rec.at);
      v.project(this.camera);
      const x = (v.x * 0.5 + 0.5) * w;
      const y = (-v.y * 0.5 + 0.5) * h;
      const off = v.z > 1 || x < -40 || x > w + 40 || y < -40 || y > h + 40;
      // the DOM is written only when a label actually moves or appears
      const op = off ? '0' : '1';
      if (op !== rec.op) rec.el.style.opacity = rec.op = op;
      const tf = `translate(${x.toFixed(1)}px, ${y.toFixed(1)}px)`;
      if (tf !== rec.tf) rec.el.style.transform = rec.tf = tf;
      // keep the text on screen: a label near an edge reads towards the middle instead
      if (!rec.width) rec.width = rec.el.lastChild.offsetWidth;
      const room = rec.width + 24;
      const side = rec.side === 'r' && x > w - room ? 'l' : rec.side === 'l' && x < room ? 'r' : rec.side;
      if (side !== rec.shownSide) {
        rec.shownSide = side;
        rec.el.classList.remove('side-r', 'side-l', 'side-t', 'side-b');
        rec.el.classList.add(`side-${side}`);
      }
      if (side === 't' || side === 'b') {
        const half = (room - 24) / 2;
        const dx = Math.max(0, 10 + half - x) - Math.max(0, x + half - (w - 10));
        const ml = `${dx.toFixed(0)}px`;
        if (ml !== rec.ml) rec.el.lastChild.style.marginLeft = rec.ml = ml;
      } else if (rec.ml) rec.el.lastChild.style.marginLeft = rec.ml = '';
    }
  }

  render() {
    this.renderer.render(this.scene, this.camera);
    this.placeLabels();
  }
}

/** Blend two camera poses into `out`, which is reused every frame. */
export function mixPose(a, b, t, out = { p: [0, 0, 0], t: [0, 0, 0] }) {
  const k = smooth(t);
  for (let i = 0; i < 3; i++) {
    out.p[i] = mix(a.p[i], b.p[i], k);
    out.t[i] = mix(a.t[i], b.t[i], k);
  }
  return out;
}
