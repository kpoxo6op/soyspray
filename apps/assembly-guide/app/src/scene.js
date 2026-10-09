// Three.js view of the assembly timeline: meshes, lighting, camera and orbit controls.

import {
  BufferAttribute,
  BufferGeometry,
  CanvasTexture,
  Color,
  DirectionalLight,
  Group,
  HemisphereLight,
  InstancedMesh,
  LatheGeometry,
  Matrix4,
  Mesh,
  MeshBasicMaterial,
  MeshStandardMaterial,
  NeutralToneMapping,
  Object3D,
  PCFShadowMap,
  PerspectiveCamera,
  PlaneGeometry,
  PMREMGenerator,
  Raycaster,
  Scene,
  ShadowMaterial,
  SRGBColorSpace,
  Vector2,
  Vector3,
  Box3,
  WebGLRenderer,
  DynamicDrawUsage,
} from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { RoomEnvironment } from 'three/examples/jsm/environments/RoomEnvironment.js';
import { toCreasedNormals } from 'three/examples/jsm/utils/BufferGeometryUtils.js';
import { evaluate } from './timeline.js';
import { buildDevice } from './devices.js';
import { FLOOR_Z } from './layout.js';

const GLOW_COLOR = new Color('#ffab5c');
const GROUND_Z = FLOOR_Z - 0.4; // the floor the feet stand on
// Default orbit (radians): front-right and slightly above; a little more frontal on portrait screens.
const VIEW = { azimuth: 0.55, elevation: 0.28 };
const VIEW_PORTRAIT = { azimuth: 0.42, elevation: 0.27 };
const SCREW_SPECS = {
  m3x16: { head: 3, headH: 1.7, shaft: 1.5, length: 16 },
  m3x12: { head: 3, headH: 1.7, shaft: 1.5, length: 12 },
  m4x12: { head: 4, headH: 2.3, shaft: 2, length: 12 },
};

// ---------------------------------------------------------------- materials

const glowColorUniform = { value: GLOW_COLOR };

function withGlow(material) {
  const glow = { value: 0 };
  material.userData.glow = glow;
  material.onBeforeCompile = (shader) => {
    shader.uniforms.uGlow = glow;
    shader.uniforms.uGlowColor = glowColorUniform;
    shader.fragmentShader = shader.fragmentShader
      .replace('#include <common>', '#include <common>\nuniform float uGlow;\nuniform vec3 uGlowColor;')
      .replace(
        '#include <opaque_fragment>',
        `#include <opaque_fragment>
        float glowRim = 1.0 - clamp( dot( normalize( normal ), normalize( vViewPosition ) ), 0.0, 1.0 );
        gl_FragColor.rgb += uGlowColor * uGlow * ( 0.012 + 0.34 * glowRim * glowRim * glowRim );`,
      );
  };
  material.customProgramCacheKey = () => 'soyspray-glow';
  return material;
}

const FINISH = {
  // Black PLA, lifted slightly so the shapes stay readable against the dark stage.
  new: { color: 0x3b4048, roughness: 0.56, metalness: 0 },
  // The existing 2024 frame: same filament look, a shade lighter so the two bays read apart.
  old: { color: 0x4a4b4f, roughness: 0.6, metalness: 0 },
};

function partGeometry(mesh) {
  const g = new BufferGeometry();
  g.setAttribute('position', new BufferAttribute(mesh.positions, 3));
  g.setIndex(new BufferAttribute(mesh.indices, 1));
  const creased = toCreasedNormals(g, (38 * Math.PI) / 180);
  g.dispose();
  creased.computeBoundingSphere();
  creased.computeBoundingBox();
  return creased;
}

function screwGeometry(spec) {
  const { head, headH, shaft, length } = spec;
  const pts = [
    [0, 0], [head * 0.86, 0], [head, 0.25], [shaft, headH], [shaft, length - 0.45], [shaft - 0.45, length], [0, length],
  ].map(([r, y]) => new Vector2(r, y));
  const g = new LatheGeometry(pts, 18);
  g.computeVertexNormals();
  return g;
}

function radialTexture(stops, size = 256) {
  const c = document.createElement('canvas');
  c.width = c.height = size;
  const g = c.getContext('2d');
  const grad = g.createRadialGradient(size / 2, size / 2, 0, size / 2, size / 2, size / 2);
  for (const [o, col] of stops) grad.addColorStop(o, col);
  g.fillStyle = grad;
  g.fillRect(0, 0, size, size);
  const t = new CanvasTexture(c);
  t.colorSpace = SRGBColorSpace;
  return t;
}

// ---------------------------------------------------------------- viewer

export class Viewer {
  constructor({ container, timeline, meshes, reducedMotion = false, phone = false, renderer: injected = null }) {
    this.timeline = timeline;
    this.reducedMotion = reducedMotion;
    this.container = container;
    this.state = new Map();
    this.bottomInset = 0;
    this.pristine = true;
    this.dirty = true;
    this.shadowDirty = true;
    this.tween = null;

    const renderer = injected || new WebGLRenderer({ antialias: true, alpha: true, powerPreference: 'high-performance' });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.setClearColor(0x000000, 0);
    renderer.outputColorSpace = SRGBColorSpace;
    renderer.toneMapping = NeutralToneMapping;
    renderer.toneMappingExposure = 1.08;
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = PCFShadowMap;
    renderer.shadowMap.autoUpdate = false;
    container.appendChild(renderer.domElement);
    this.renderer = renderer;
    this.canvas = renderer.domElement;
    this.canvas.setAttribute('aria-label', 'Soyspray rack, 3D view. Drag to rotate, scroll or pinch to zoom, right-drag or two fingers to pan.');
    this.canvas.setAttribute('role', 'img');
    this.canvas.tabIndex = -1;

    const scene = new Scene();
    this.scene = scene;
    if (!injected) {
      const pmrem = new PMREMGenerator(renderer);
      scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
      pmrem.dispose();
    }
    scene.environmentIntensity = 0.42;

    this.camera = new PerspectiveCamera(30, 1, 20, 20000);
    this.camera.up.set(0, 1, 0);

    // z-up rack frame -> three's y-up world
    this.root = new Group();
    this.root.rotation.x = -Math.PI / 2;
    scene.add(this.root);

    this.addLights(phone);
    this.addStage();
    this.buildNodes(meshes, renderer.capabilities.getMaxAnisotropy());

    const controls = new OrbitControls(this.camera, this.canvas);
    controls.enableDamping = !reducedMotion;
    controls.dampingFactor = 0.085;
    controls.rotateSpeed = 0.7;
    controls.zoomSpeed = 0.9;
    controls.panSpeed = 0.85;
    controls.zoomToCursor = true;
    controls.screenSpacePanning = true;
    controls.minDistance = 90;
    controls.maxDistance = 9000;
    controls.maxPolarAngle = Math.PI * 0.94;
    controls.addEventListener('change', () => {
      this.dirty = true;
    });
    controls.addEventListener('start', () => {
      this.setPristine(false);
      this.tween = null;
    });
    this.controls = controls;

    this.raycaster = new Raycaster();
    this.canvas.addEventListener('dblclick', (e) => this.focusAt(e.clientX, e.clientY));
    this.installDoubleTap();

    this.contentBox = this.computeContentBox();
    this.resize();
  }

  addLights(phone) {
    const hemi = new HemisphereLight(0xcfd8e6, 0x1a1612, 0.55);
    this.scene.add(hemi);

    // Warm key from front-left, casting the only shadows.
    const key = new DirectionalLight(0xfff0e0, 2.4);
    key.position.set(-420, 820, 620);
    key.target.position.set(130, 120, -100);
    key.castShadow = true;
    key.shadow.mapSize.set(phone ? 1024 : 2048, phone ? 1024 : 2048);
    const sc = key.shadow.camera;
    sc.left = -520;
    sc.right = 520;
    sc.top = 520;
    sc.bottom = -520;
    sc.near = 200;
    sc.far = 2600;
    key.shadow.bias = -0.0004;
    key.shadow.normalBias = 0.6;
    key.shadow.radius = 3;
    this.scene.add(key, key.target);

    // Cool rim from behind-right keeps black parts separated from the background.
    const rim = new DirectionalLight(0x9cc4ff, 1.5);
    rim.position.set(700, 520, -820);
    this.scene.add(rim);

    // Soft fill from the right front.
    const fill = new DirectionalLight(0xffffff, 0.55);
    fill.position.set(760, 160, 420);
    this.scene.add(fill);
  }

  addStage() {
    const y = GROUND_Z;
    const pool = new Mesh(
      new PlaneGeometry(1800, 1800),
      new MeshBasicMaterial({
        map: radialTexture([[0, 'rgba(120,128,140,0.16)'], [0.45, 'rgba(70,76,86,0.08)'], [1, 'rgba(0,0,0,0)']]),
        transparent: true,
        depthWrite: false,
      }),
    );
    pool.rotation.x = -Math.PI / 2;
    pool.position.set(126, y - 0.5, -104);
    pool.renderOrder = -2;
    this.scene.add(pool);

    const contact = new Mesh(
      new PlaneGeometry(420, 360),
      new MeshBasicMaterial({
        map: radialTexture([[0, 'rgba(0,0,0,0.55)'], [0.55, 'rgba(0,0,0,0.25)'], [1, 'rgba(0,0,0,0)']]),
        transparent: true,
        depthWrite: false,
      }),
    );
    contact.rotation.x = -Math.PI / 2;
    contact.position.set(140, y - 0.3, -104);
    contact.renderOrder = -1;
    this.scene.add(contact);

    const catcher = new Mesh(new PlaneGeometry(2400, 2400), new ShadowMaterial({ opacity: 0.32, depthWrite: false }));
    catcher.rotation.x = -Math.PI / 2;
    catcher.position.set(126, y, -104);
    catcher.receiveShadow = true;
    catcher.renderOrder = -1;
    this.scene.add(catcher);
  }

  buildNodes(meshes, anisotropy) {
    const geos = {};
    for (const [name, m] of Object.entries(meshes)) geos[name] = partGeometry(m);
    this.partGeometries = geos;

    const screwNodes = {};
    for (const n of this.timeline.nodes.values()) {
      if (n.kind === 'screw') (screwNodes[n.mesh] ||= []).push(n.id);
    }
    const screwMat = new MeshStandardMaterial({ color: 0xc9cdd3, metalness: 1, roughness: 0.3 });
    this.screwSets = Object.entries(screwNodes).map(([type, ids]) => {
      const im = new InstancedMesh(screwGeometry(SCREW_SPECS[type]), screwMat, ids.length);
      im.instanceMatrix.setUsage(DynamicDrawUsage);
      im.frustumCulled = false;
      this.scene.add(im);
      return { im, ids };
    });

    this.objects = new Map();
    this.inner = new Map();
    this.pickable = [];
    for (const id of this.timeline.order) {
      const n = this.timeline.nodes.get(id);
      const parent = n.parent ? this.inner.get(n.parent) : this.root;
      let obj;
      let materials = [];
      if (n.kind === 'group') {
        obj = new Group();
        const inner = new Group();
        inner.position.set(-n.pivot[0], -n.pivot[1], -n.pivot[2]);
        obj.add(inner);
        this.inner.set(id, inner);
      } else if (n.kind === 'part') {
        const mat = withGlow(new MeshStandardMaterial({ ...FINISH[n.finish] }));
        obj = new Mesh(geos[n.mesh], mat);
        obj.castShadow = true;
        obj.receiveShadow = true;
        materials = [mat];
        this.pickable.push(obj);
      } else if (n.kind === 'device') {
        const spec = n.device || { model: n.mesh, size: [0, 0, 0] };
        const built = buildDevice(spec, anisotropy);
        obj = built.object;
        materials = built.materials.map(withGlow);
        obj.traverse((o) => o.isMesh && this.pickable.push(o));
      } else {
        obj = new Object3D();
      }
      if (!this.inner.has(id)) this.inner.set(id, obj);
      parent.add(obj);
      this.objects.set(id, { node: n, obj, materials, shown: true });
    }
  }

  /** Apply the timeline state at time t. */
  setTime(t) {
    evaluate(this.timeline, t, this.state);
    for (const [id, rec] of this.objects) {
      const s = this.state.get(id);
      rec.obj.position.set(s.p[0], s.p[1], s.p[2]);
      rec.obj.quaternion.set(s.q[0], s.q[1], s.q[2], s.q[3]);
      const kind = rec.node.kind;
      if (kind === 'group' || kind === 'screw') continue;
      const visible = s.alpha > 0.004;
      if (rec.obj.visible !== visible) rec.obj.visible = visible;
      if (!visible) continue;
      const transparent = s.alpha < 0.995;
      for (const m of rec.materials) {
        if (m.transparent !== transparent) {
          m.transparent = transparent;
          m.needsUpdate = true;
        }
        m.opacity = s.alpha;
        m.userData.glow.value = s.glow;
      }
      rec.obj.castShadow = s.alpha > 0.6;
    }
    this.root.updateMatrixWorld(true);
    const hidden = new Matrix4().makeScale(0, 0, 0);
    for (const { im, ids } of this.screwSets) {
      ids.forEach((id, i) => {
        const s = this.state.get(id);
        im.setMatrixAt(i, s.alpha > 0.5 ? this.objects.get(id).obj.matrixWorld : hidden);
      });
      im.instanceMatrix.needsUpdate = true;
    }
    this.dirty = true;
    this.shadowDirty = true;
  }

  /** World-space box enclosing everything the timeline ever shows. */
  computeContentBox() {
    const box = new Box3();
    const tmp = new Box3();
    const steps = Math.ceil(this.timeline.duration / 0.5);
    for (let i = 0; i <= steps; i++) {
      this.setTime((i / steps) * this.timeline.duration);
      for (const rec of this.objects.values()) {
        const k = rec.node.kind;
        if ((k !== 'part' && k !== 'device') || !rec.obj.visible) continue;
        if (this.state.get(rec.node.id).alpha < 0.5) continue;
        box.union(tmp.setFromObject(rec.obj));
      }
    }
    // The finished rack (last sample) decides how far the brief lifts above it and the power
    // board's run-in on the right may reach: those moments may brush the frame edge, nothing else.
    const finished = new Box3();
    for (const rec of this.objects.values()) {
      if ((rec.node.kind === 'part' || rec.node.kind === 'device') && rec.obj.visible) finished.union(tmp.setFromObject(rec.obj));
    }
    this.frameBox = box.clone();
    this.frameBox.max.y = Math.min(box.max.y, finished.max.y + 15);
    this.frameBox.max.x = Math.min(box.max.x, finished.max.x + 10);
    return box;
  }

  setBottomInset(px) {
    if (Math.abs(px - this.bottomInset) < 1) return;
    this.bottomInset = px;
    this.resize();
  }

  resize() {
    const w = this.container.clientWidth || window.innerWidth;
    const h = this.container.clientHeight || window.innerHeight;
    this.renderer.setSize(w, h, false);
    this.canvas.style.width = '100%';
    this.canvas.style.height = '100%';
    const portrait = h > w * 1.15;
    this.camera.fov = portrait ? 40 : 30;
    this.camera.aspect = w / h;
    // Keep the content centred in the area above the transport bar.
    this.camera.setViewOffset(w, h, 0, this.bottomInset / 2, w, h);
    this.camera.updateProjectionMatrix();
    if (this.pristine) this.applyHomeView(false);
    this.dirty = true;
  }

  homeView() {
    const box = this.frameBox;
    const center = box.getCenter(new Vector3());
    const w = this.container.clientWidth || window.innerWidth;
    const h = this.container.clientHeight || window.innerHeight;
    const view = h > w * 1.15 ? VIEW_PORTRAIT : VIEW;
    const dir = new Vector3(
      Math.sin(view.azimuth) * Math.cos(view.elevation),
      Math.sin(view.elevation),
      Math.cos(view.azimuth) * Math.cos(view.elevation),
    );
    const up = new Vector3(0, 1, 0);
    const right = new Vector3().crossVectors(up, dir).normalize();
    const camUp = new Vector3().crossVectors(dir, right).normalize();
    const tanV = Math.tan((this.camera.fov * Math.PI) / 360);
    const tanH = tanV * (w / h);
    const tanVAvail = tanV * Math.max(0.35, 1 - this.bottomInset / h);
    let dist = 0;
    const v = new Vector3();
    for (let i = 0; i < 8; i++) {
      v.set(i & 1 ? box.max.x : box.min.x, i & 2 ? box.max.y : box.min.y, i & 4 ? box.max.z : box.min.z).sub(center);
      const x = v.dot(right);
      const y = v.dot(camUp);
      const z = v.dot(dir);
      dist = Math.max(dist, Math.abs(x) / tanH + z, Math.abs(y) / tanVAvail + z);
    }
    dist *= 1.06;
    return { target: center, position: center.clone().addScaledVector(dir, dist) };
  }

  applyHomeView(animate) {
    const home = this.homeView();
    this.moveCamera(home.position, home.target, animate);
  }

  resetView() {
    this.setPristine(true);
    this.applyHomeView(!this.reducedMotion);
  }

  setPristine(on) {
    if (this.pristine === on) return;
    this.pristine = on;
    this.onPristineChange?.();
  }

  moveCamera(position, target, animate) {
    if (!animate) {
      this.tween = null;
      this.camera.position.copy(position);
      this.controls.target.copy(target);
      this.controls.update();
      this.dirty = true;
      return;
    }
    this.tween = {
      t: 0,
      dur: 0.6,
      p0: this.camera.position.clone(),
      p1: position.clone(),
      c0: this.controls.target.clone(),
      c1: target.clone(),
    };
  }

  focusAt(clientX, clientY) {
    const rect = this.canvas.getBoundingClientRect();
    const ndc = new Vector2(((clientX - rect.left) / rect.width) * 2 - 1, -((clientY - rect.top) / rect.height) * 2 + 1);
    this.raycaster.setFromCamera(ndc, this.camera);
    const hits = this.raycaster.intersectObjects(this.pickable.filter((o) => o.visible && this.isShown(o)), false);
    if (!hits.length) return;
    const p = hits[0].point;
    const offset = p.clone().sub(this.controls.target);
    this.setPristine(false);
    this.moveCamera(this.camera.position.clone().add(offset), p, !this.reducedMotion);
  }

  isShown(o) {
    for (let a = o; a; a = a.parent) if (!a.visible) return false;
    return true;
  }

  installDoubleTap() {
    let last = 0;
    let lx = 0;
    let ly = 0;
    let downX = 0;
    let downY = 0;
    this.canvas.addEventListener('pointerdown', (e) => {
      downX = e.clientX;
      downY = e.clientY;
    });
    this.canvas.addEventListener('pointerup', (e) => {
      if (e.pointerType !== 'touch') return;
      if (Math.hypot(e.clientX - downX, e.clientY - downY) > 10) return;
      const now = performance.now();
      if (now - last < 320 && Math.hypot(e.clientX - lx, e.clientY - ly) < 30) {
        this.focusAt(e.clientX, e.clientY);
        last = 0;
      } else {
        last = now;
        lx = e.clientX;
        ly = e.clientY;
      }
    });
  }

  /** Advance camera easing and damping; returns true while the view still needs frames. */
  update(dt) {
    let active = false;
    if (this.tween) {
      const tw = this.tween;
      tw.t = Math.min(1, tw.t + dt / tw.dur);
      const e = tw.t < 0.5 ? 4 * tw.t ** 3 : 1 - (-2 * tw.t + 2) ** 3 / 2;
      this.camera.position.lerpVectors(tw.p0, tw.p1, e);
      this.controls.target.lerpVectors(tw.c0, tw.c1, e);
      if (tw.t >= 1) this.tween = null;
      this.dirty = true;
      active = true;
    }
    if (this.controls.update(dt)) active = true;
    return active;
  }

  render() {
    if (this.shadowDirty) {
      this.renderer.shadowMap.needsUpdate = true;
      this.shadowDirty = false;
    }
    this.renderer.render(this.scene, this.camera);
    this.dirty = false;
  }
}
