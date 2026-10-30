// The three.js world: renderer, light, the bench set, the camera rig and the 3D labels.
// Units are metres, y is up. The bench top is y = 0; the soldering mat sits on it.

import {
  AgXToneMapping,
  CanvasTexture,
  DirectionalLight,
  Group,
  HemisphereLight,
  Mesh,
  MeshStandardMaterial,
  PCFShadowMap,
  PerspectiveCamera,
  PlaneGeometry,
  PMREMGenerator,
  BoxGeometry,
  RepeatWrapping,
  Scene,
  ShadowMaterial,
  SRGBColorSpace,
  Vector3,
  WebGLRenderer,
} from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { RoomEnvironment } from 'three/examples/jsm/environments/RoomEnvironment.js';
import { mix3, smooth } from './anim.js';

export const MAT = { w: 0.389, d: 0.263, t: 0.002 }; // Jaycar HM8102 silicone mat

function canvasTexture(w, h, draw) {
  const c = document.createElement('canvas');
  c.width = w;
  c.height = h;
  draw(c.getContext('2d'), w, h);
  const t = new CanvasTexture(c);
  t.colorSpace = SRGBColorSpace;
  t.anisotropy = 4;
  return t;
}

// Oak with a soft falloff to the dark room: the bench is lit like a product table, not a floor.
function oakTexture() {
  return canvasTexture(1024, 640, (g, w, h) => {
    g.fillStyle = '#9a7350';
    g.fillRect(0, 0, w, h);
    let seed = 7;
    const rnd = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);
    for (let i = 0; i < 260; i++) {
      const y = rnd() * h;
      g.strokeStyle = `rgba(${60 + rnd() * 40},${38 + rnd() * 25},${20 + rnd() * 15},${0.05 + rnd() * 0.12})`;
      g.lineWidth = 0.6 + rnd() * 2.2;
      g.beginPath();
      g.moveTo(0, y);
      for (let x = 0; x <= w; x += 32) g.lineTo(x, y + Math.sin(x * 0.004 + i) * 6 + (rnd() - 0.5) * 2);
      g.stroke();
    }
  });
}

function fadeTexture() {
  return canvasTexture(512, 512, (g, w, h) => {
    const r = g.createRadialGradient(w / 2, h / 2, 0, w / 2, h / 2, w / 2);
    r.addColorStop(0, 'rgba(255,255,255,1)');
    r.addColorStop(0.3, 'rgba(255,255,255,0.95)');
    r.addColorStop(0.62, 'rgba(255,255,255,0.45)');
    r.addColorStop(1, 'rgba(255,255,255,0)');
    g.fillStyle = r;
    g.fillRect(0, 0, w, h);
  });
}

function matTexture() {
  const px = 1600; // 4 px per mm
  const s = px / (MAT.w * 1000);
  return canvasTexture(px, Math.round(MAT.d * 1000 * s), (g, w, h) => {
    g.fillStyle = '#33495a';
    g.fillRect(0, 0, w, h);
    for (let mm = 10; mm < MAT.w * 1000; mm += 10) {
      g.fillStyle = mm % 50 === 0 ? 'rgba(220,232,240,0.30)' : 'rgba(220,232,240,0.13)';
      g.fillRect(mm * s - 1, 0, 2, h);
    }
    for (let mm = 10; mm < MAT.d * 1000; mm += 10) {
      g.fillStyle = mm % 50 === 0 ? 'rgba(220,232,240,0.30)' : 'rgba(220,232,240,0.13)';
      g.fillRect(0, mm * s - 1, w, 2);
    }
    g.strokeStyle = 'rgba(220,232,240,0.45)';
    g.lineWidth = 3;
    g.strokeRect(14 * s, 14 * s, w - 28 * s, h - 28 * s);
  });
}

export class Stage {
  constructor({ container, labelLayer, reducedMotion = false, phone = false }) {
    this.container = container;
    this.labelLayer = labelLayer;
    this.reducedMotion = reducedMotion;
    this.phone = phone;
    this.insets = { top: 0, bottom: 0 };
    this.pristine = true;
    this.dirty = true;
    this.onPristineChange = null;

    const renderer = new WebGLRenderer({ antialias: true, alpha: true, powerPreference: 'high-performance' });
    // Phones have 2.5-3x screens and small GPUs: start at 1.5 and let adapt() trade resolution for frame rate.
    this.maxRatio = Math.min(window.devicePixelRatio || 1, phone ? 1.5 : 2);
    this.minRatio = Math.min(this.maxRatio, phone ? 0.85 : 1);
    this.ratio = this.maxRatio;
    this.frameMs = 16;
    this.slow = 0;
    this.quick = 0;
    this.frameNo = 0;
    renderer.setPixelRatio(this.ratio);
    renderer.setClearColor(0x000000, 0);
    renderer.outputColorSpace = SRGBColorSpace;
    renderer.toneMapping = AgXToneMapping;
    renderer.toneMappingExposure = 1.12;
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = PCFShadowMap;
    renderer.shadowMap.autoUpdate = false;
    renderer.localClippingEnabled = true;
    container.appendChild(renderer.domElement);
    this.renderer = renderer;
    this.canvas = renderer.domElement;
    this.canvas.setAttribute('role', 'img');
    this.canvas.setAttribute('aria-label', 'Pearl, 3D view. Drag to turn, scroll or pinch to zoom.');

    const scene = new Scene();
    const pmrem = new PMREMGenerator(renderer);
    scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
    pmrem.dispose();
    scene.environmentIntensity = 0.6;
    this.scene = scene;

    this.camera = new PerspectiveCamera(32, 1, 0.004, 40);
    this.addLights();
    this.addBench();

    const controls = new OrbitControls(this.camera, this.canvas);
    controls.enableDamping = !reducedMotion;
    controls.dampingFactor = 0.08;
    controls.rotateSpeed = 0.7;
    controls.zoomSpeed = 0.9;
    controls.panSpeed = 0.8;
    controls.zoomToCursor = true;
    controls.screenSpacePanning = true;
    controls.minDistance = 0.04;
    controls.maxDistance = 6;
    controls.addEventListener('change', () => (this.dirty = true));
    controls.addEventListener('start', () => this.setPristine(false));
    this.controls = controls;

    this.labels = new Map();
    this.pose = null;
    this.resize();
  }

  addLights() {
    const s = this.scene;
    s.add(new HemisphereLight(0xf4efe6, 0x2b241d, 0.45));
    const key = new DirectionalLight(0xfff0de, 2.9);
    key.position.set(-0.9, 1.7, 1.0);
    key.castShadow = true;
    const size = this.phone ? 1024 : 2048;
    key.shadow.mapSize.set(size, size);
    Object.assign(key.shadow.camera, { left: -0.85, right: 0.85, top: 0.85, bottom: -0.85, near: 0.3, far: 4.5 });
    key.shadow.bias = -0.0003;
    key.shadow.normalBias = 0.002;
    key.shadow.radius = 4;
    s.add(key, key.target);
    this.key = key;
    const rim = new DirectionalLight(0xc6d8ff, 1.1);
    rim.position.set(1.1, 1.0, -1.3);
    s.add(rim);
    const fill = new DirectionalLight(0xffffff, 0.4);
    fill.position.set(1.3, 0.5, 0.9);
    s.add(fill);
  }

  addBench() {
    const bench = new Group();
    bench.name = 'bench set';
    const oak = oakTexture();
    oak.wrapS = oak.wrapT = RepeatWrapping;
    oak.repeat.set(1.6, 1.6);
    const top = new Mesh(
      new PlaneGeometry(3.0, 1.9),
      new MeshStandardMaterial({ map: oak, alphaMap: fadeTexture(), transparent: true, roughness: 0.62, metalness: 0, depthWrite: false }),
    );
    top.rotation.x = -Math.PI / 2;
    top.renderOrder = -2;
    const catcher = new Mesh(new PlaneGeometry(3.0, 1.9), new ShadowMaterial({ opacity: 0.38, depthWrite: false }));
    catcher.rotation.x = -Math.PI / 2;
    catcher.position.y = 0.0004;
    catcher.receiveShadow = true;
    catcher.renderOrder = -1;
    const mat = new Mesh(new BoxGeometry(MAT.w, MAT.t, MAT.d), [
      new MeshStandardMaterial({ color: 0x2c4152, roughness: 0.8 }),
      new MeshStandardMaterial({ color: 0x2c4152, roughness: 0.8 }),
      new MeshStandardMaterial({ map: matTexture(), roughness: 0.78 }),
      new MeshStandardMaterial({ color: 0x2c4152, roughness: 0.8 }),
      new MeshStandardMaterial({ color: 0x2c4152, roughness: 0.8 }),
      new MeshStandardMaterial({ color: 0x2c4152, roughness: 0.8 }),
    ]);
    mat.position.y = MAT.t / 2;
    mat.receiveShadow = true;
    mat.name = 'mat';
    bench.add(top, catcher, mat);
    this.scene.add(bench);
    this.bench = bench;
    this.benchMat = mat;
  }

  /** Show or hide the bench (the opening chapter floats Pearl in an empty room). */
  setBench(on, matOn = on) {
    this.bench.visible = on;
    this.benchMat.visible = matOn;
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

  applyPose({ p, t, fov }) {
    // Portrait screens are narrow: step back along the same line so the subject still fits across.
    const k = this.camera.aspect < 1 ? Math.min(2.1, (1.25 / this.camera.aspect) ** 0.62) : 1;
    this.camera.position.set(t[0] + (p[0] - t[0]) * k, t[1] + (p[1] - t[1]) * k, t[2] + (p[2] - t[2]) * k);
    this.controls.target.set(t[0], t[1], t[2]);
    if (fov && this.camera.fov !== fov) {
      this.camera.fov = fov;
      this.camera.updateProjectionMatrix();
    }
    this.camera.lookAt(this.controls.target);
    this.dirty = true;
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
    this.dirty = true;
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

  /** Labels for this moment: [{ id, text, at: Vector3 | Object3D, side }]. */
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
        rec = { el, text: '', shownSide: null, strong: null, width: 0 };
        this.labels.set(l.id, rec);
      }
      if (rec.text !== l.text) {
        rec.text = l.text;
        rec.el.lastChild.textContent = l.text;
        rec.width = 0; // measured once on the next placement, not every frame
      }
      const strong = !!l.strong;
      if (rec.strong !== strong) {
        rec.strong = strong;
        rec.el.classList.toggle('strong', strong);
      }
      rec.side = l.side || 'r';
      rec.at = l.at;
      rec.alpha = l.alpha ?? 1;
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
    const v = new Vector3();
    for (const rec of this.labels.values()) {
      if (rec.at.isObject3D) rec.at.getWorldPosition(v);
      else v.copy(rec.at);
      v.project(this.camera);
      const behind = v.z > 1;
      const x = (v.x * 0.5 + 0.5) * w;
      const y = (-v.y * 0.5 + 0.5) * h;
      const off = behind || x < -40 || x > w + 40 || y < -40 || y > h + 40;
      rec.el.style.opacity = off ? '0' : String(rec.alpha);
      rec.el.style.transform = `translate(${x.toFixed(1)}px, ${y.toFixed(1)}px)`;
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
        rec.el.lastChild.style.marginLeft = `${dx.toFixed(0)}px`;
      } else rec.el.lastChild.style.marginLeft = '';
    }
  }

  render() {
    // Only the bench catches shadows. Phones refresh them every other frame, which nobody sees at this pace.
    const sm = this.renderer.shadowMap;
    sm.needsUpdate = this.bench.visible && (!this.phone || this.frameNo % 2 === 0);
    this.frameNo++;
    this.renderer.render(this.scene, this.camera);
    this.placeLabels();
    this.dirty = false;
  }
}

/** Blend two camera poses. */
export function mixPose(a, b, t) {
  const k = smooth(t);
  return { p: mix3(a.p, b.p, k), t: mix3(a.t, b.t, k), fov: (a.fov ?? 32) + ((b.fov ?? 32) - (a.fov ?? 32)) * k };
}

