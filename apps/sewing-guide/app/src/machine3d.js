// A simplified PFAFF passport 3.0 built from primitives, with the thread paths, movable
// parts and camera presets the chapters need. Units are millimetres; x runs to the
// handwheel, y up, z to the front (towards the person sewing).
import {
  Scene, PerspectiveCamera, WebGLRenderer, Color, HemisphereLight, DirectionalLight, PointLight,
  Group, Mesh, MeshStandardMaterial, MeshPhysicalMaterial, BoxGeometry, CylinderGeometry, TorusGeometry,
  TubeGeometry, CatmullRomCurve3, Vector3, PlaneGeometry, SRGBColorSpace, ACESFilmicToneMapping,
} from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { RoundedBoxGeometry } from 'three/examples/jsm/geometries/RoundedBoxGeometry.js';

const CREAM = new MeshStandardMaterial({ color: 0xf4f1ea, roughness: 0.55, metalness: 0.02 });
const CREAM2 = new MeshStandardMaterial({ color: 0xe9e4da, roughness: 0.6 });
const DARK = new MeshStandardMaterial({ color: 0x2b2b2e, roughness: 0.5 });
const GREY = new MeshStandardMaterial({ color: 0x8d8f94, roughness: 0.35, metalness: 0.7 });
const STEEL = new MeshStandardMaterial({ color: 0xc9cbd0, roughness: 0.25, metalness: 0.9 });
const ORANGE = new MeshStandardMaterial({ color: 0xe8930c, roughness: 0.5 });
const RED = new MeshStandardMaterial({ color: 0xc8302a, roughness: 0.55 });
const THREAD = new MeshStandardMaterial({ color: 0xd42a2a, roughness: 0.8 });
const CLEAR = new MeshPhysicalMaterial({ color: 0xffffff, transparent: true, opacity: 0.28, roughness: 0.1, transmission: 0.2 });
const DISPLAY = new MeshStandardMaterial({ color: 0x15171a, roughness: 0.3, emissive: 0x1a0d00 });
const TABLE = new MeshStandardMaterial({ color: 0xa87f52, roughness: 0.9 });
const CORD = new MeshStandardMaterial({ color: 0x1f1f22, roughness: 0.7 });

const box = (w, h, d, mat = CREAM, r = 0) => new Mesh(r ? new RoundedBoxGeometry(w, h, d, 3, r) : new BoxGeometry(w, h, d), mat);
const cyl = (rt, rb, h, mat = GREY, seg = 24) => new Mesh(new CylinderGeometry(rt, rb, h, seg), mat);
const at = (m, x, y, z) => {
  m.position.set(x, y, z);
  return m;
};
const v = (x, y, z) => new Vector3(x, y, z);

export const CAMERAS = {
  front: { pos: [40, 260, 640], target: [0, 150, 0] },
  head: { pos: [-190, 250, 430], target: [-150, 190, 30] },
  needle: { pos: [-150, 140, 280], target: [-160, 100, 50] },
  'foot-side': { pos: [-360, 130, 230], target: [-160, 95, 40] },
  top: { pos: [0, 640, 170], target: [0, 290, -10] },
  'top-left': { pos: [-230, 520, 230], target: [-130, 295, -5] },
  'top-right': { pos: [170, 520, 230], target: [130, 295, -15] },
  bobbin: { pos: [-140, 190, 320], target: [-160, 66, 70] },
  'right-low': { pos: [460, 120, 320], target: [200, 50, 40] },
  'back-low': { pos: [-120, 160, -400], target: [-120, 45, -60] },
  right: { pos: [540, 230, 160], target: [200, 160, -30] },
};

const DEFAULT_STATE = {
  thread: 0, winder: 0, bobbinThread: 0, winderLever: 0, bobbinOnSpindle: 0, bobbinSpin: 0,
  cover: 0, bobbinIn: 1, idt: 0, footLift: 0, footOn: 1, feedDogs: 1, needleIn: 1, threaderDown: 0,
  pedalPlugged: 1, cordPlugged: 1, power: 1, spoolOn: 1, spoolVertical: 0, hardCover: 0, trayOn: 1,
  cordCoiled: 0, buttonholeFoot: 0, buttonPlate: 0, bhLever: 0, plateOff: 0,
};

function tube(points, radius = 0.9, segments = 160) {
  const curve = new CatmullRomCurve3(points.map((p) => v(...p)), false, 'catmullrom', 0.3);
  const geo = new TubeGeometry(curve, segments, radius, 8, false);
  const m = new Mesh(geo, THREAD);
  m.userData.indexCount = geo.index.count;
  m.userData.radialStride = 8 * 6; // indices per tubular segment
  return m;
}

function setTubeProgress(mesh, p) {
  const total = mesh.userData.indexCount;
  const stride = mesh.userData.radialStride;
  const count = Math.max(0, Math.min(total, Math.round((total * p) / stride) * stride));
  mesh.geometry.setDrawRange(0, count);
  mesh.visible = count > 0;
}

export class Machine3D {
  constructor(container, { reducedMotion = false, onPart = null } = {}) {
    this.container = container;
    this.onPart = onPart;
    this.reducedMotion = reducedMotion;
    this.state = { ...DEFAULT_STATE };
    this.target = { ...DEFAULT_STATE };
    this.hotspots = new Map();
    this.hotspotLayer = document.createElement('div');
    this.hotspotLayer.className = 'hotspot-layer';
    this.hotspotLayer.style.cssText = 'position:absolute;inset:0;pointer-events:none;';

    this.renderer = new WebGLRenderer({ antialias: true, alpha: true, powerPreference: 'low-power' });
    this.renderer.outputColorSpace = SRGBColorSpace;
    this.renderer.toneMapping = ACESFilmicToneMapping;
    this.renderer.toneMappingExposure = 0.95;
    this.renderer.setPixelRatio(Math.min(2, window.devicePixelRatio || 1));
    container.appendChild(this.renderer.domElement);
    container.appendChild(this.hotspotLayer);

    this.scene = new Scene();
    this.scene.background = new Color(0xd9d2c5);
    this.camera = new PerspectiveCamera(38, 1, 10, 6000);
    this.controls = new OrbitControls(this.camera, this.renderer.domElement);
    this.controls.enableDamping = !reducedMotion;
    this.controls.dampingFactor = 0.08;
    this.controls.maxPolarAngle = Math.PI * 0.95;
    this.controls.minDistance = 120;
    this.controls.maxDistance = 1800;
    this.controls.addEventListener('change', () => this.requestFrame());
    this.controls.addEventListener('start', () => {
      this.cameraTween = null;
    });

    const hemi = new HemisphereLight(0xfdfbff, 0x6e5f4c, 0.9);
    const sun = new DirectionalLight(0xffffff, 1.1);
    sun.position.set(300, 700, 500);
    const fill = new DirectionalLight(0xdfe8ff, 0.35);
    fill.position.set(-500, 200, -300);
    this.lamp = new PointLight(0xfff0d0, 0, 400, 2);
    this.lamp.position.set(-160, 120, 70);
    this.scene.add(hemi, sun, fill, this.lamp);

    this.build();
    this.goCamera('front', true);
    this.resize();
    this.apply(this.state);
    this.raf = 0;
    this.last = 0;
    this.cameraTween = null;
    this.requestFrame();
  }

  // ---------------------------------------------------------------- model
  build() {
    const s = this.scene;
    const parts = (this.parts = {});

    // table
    const table = new Mesh(new PlaneGeometry(1600, 1100), TABLE);
    table.rotation.x = -Math.PI / 2;
    table.position.set(0, -1, 120);
    s.add(table);

    // bed and free arm
    s.add(at(box(400, 62, 170, CREAM, 6), 0, 31, 0)); // base
    parts.tray = at(box(170, 44, 150, CREAM2, 5), -115, 40, 0); // accessory tray around the free arm
    s.add(parts.tray);
    s.add(at(box(175, 46, 96, CREAM, 5), -112, 40, 8)); // free arm itself
    s.add(at(box(90, 2, 60, STEEL), -160, 64, 50)); // stitch plate
    parts.plate = s.children[s.children.length - 1];
    const plateLines = at(box(60, 0.4, 0.8, DARK), -150, 65.3, 70);
    s.add(plateLines);
    // feed dogs
    parts.feedDogs = new Group();
    for (let i = 0; i < 3; i++) parts.feedDogs.add(at(box(2, 2, 14, GREY), -168 + i * 8, 65.5, 52));
    s.add(parts.feedDogs);
    // bobbin cover (clear) and bobbin inside
    s.add(at(box(54, 6, 32, DARK), -160, 61, 76)); // bobbin recess
    parts.cover = at(box(56, 1.5, 34, CLEAR), -160, 64.2, 76);
    s.add(parts.cover);
    const bobbin = new Group();
    bobbin.add(at(cyl(9, 9, 7, new MeshStandardMaterial({ color: 0xe8e8ee, transparent: true, opacity: 0.8 })), 0, 0, 0));
    bobbin.add(at(cyl(7.5, 7.5, 7.2, THREAD), 0, 0, 0));
    parts.bobbin = at(bobbin, -160, 58, 74);
    s.add(parts.bobbin);
    parts.bobbinThread = tube([[-153, 61, 74], [-146, 62, 84], [-160, 63, 90], [-178, 63, 86], [-180, 62, 75], [-172, 62, 68]], 0.7, 80);
    s.add(parts.bobbinThread);
    // feed dog slide (back of free arm)
    parts.feedSlide = at(box(18, 8, 4, DARK), -120, 40, -41);
    s.add(parts.feedSlide);
    s.add(at(box(40, 10, 1, CREAM2), -120, 40, -41.5));

    // pillar, arm, head
    s.add(at(box(140, 236, 150, CREAM, 8), 130, 180, -5)); // pillar
    s.add(at(box(400, 86, 150, CREAM, 8), 0, 258, -5)); // arm
    s.add(at(box(100, 170, 155, CREAM, 8), -150, 213, -2)); // head (open space below it for the needle area)
    s.add(at(box(100, 10, 155, CREAM2, 3), -150, 298, -2)); // head top trim
    // top recess and spool
    s.add(at(box(150, 6, 60, CREAM2), 30, 299, -10));
    parts.spoolPin = new Group();
    const pin = at(cyl(2.2, 2.2, 95, STEEL), 0, 0, 0);
    pin.rotation.z = Math.PI / 2;
    parts.spoolPin.add(pin);
    const spool = new Group();
    const spoolBody = cyl(13, 13, 42, THREAD);
    spoolBody.rotation.z = Math.PI / 2;
    spool.add(spoolBody);
    const cap1 = cyl(16, 16, 3, CREAM2);
    cap1.rotation.z = Math.PI / 2;
    cap1.position.x = -24;
    const cap2 = cap1.clone();
    cap2.position.x = 24;
    spool.add(cap1, cap2);
    parts.spool = spool;
    parts.spoolPin.add(spool);
    parts.spoolPin.position.set(30, 306, -10);
    s.add(parts.spoolPin);
    // top-deck details
    parts.pressureDial = at(cyl(8, 8, 3, GREY), -150, 302, -35);
    s.add(parts.pressureDial);
    s.add(at(box(6, 6, 5, GREY), -120, 302, -20)); // thread guide 22
    s.add(at(cyl(6, 6, 2, GREY), -135, 302, -5)); // winder tension disc 28
    parts.tensionDial = at(cyl(11, 11, 6, CREAM2), -100, 299, 22);
    s.add(parts.tensionDial);
    s.add(at(box(16, 2, 1, DARK), -100, 302.5, 22));
    s.add(at(cyl(2, 2, 8, DARK), 150, 302, -45)); // aux spool pin hole
    parts.winderSpindle = at(cyl(2.2, 2.2, 14, STEEL), 160, 306, -15);
    s.add(parts.winderSpindle);
    parts.winderLever = at(box(10, 5, 8, DARK), 148, 303, -15);
    s.add(parts.winderLever);
    const wb = new Group();
    wb.add(cyl(9, 9, 7, new MeshStandardMaterial({ color: 0xe8e8ee, transparent: true, opacity: 0.8 })));
    parts.winderBobbin = at(wb, 160, 310, -15);
    s.add(parts.winderBobbin);
    parts.winderBobbinThread = cyl(7.5, 7.5, 7.2, THREAD);
    parts.winderBobbin.add(parts.winderBobbinThread);
    // handle
    s.add(at(box(140, 8, 20, CREAM2, 3), 0, 305, -5));
    // handwheel
    const wheel = cyl(44, 44, 26, CREAM2, 40);
    wheel.rotation.z = Math.PI / 2;
    s.add(at(wheel, 212, 255, -5));
    const wheelRim = new Mesh(new TorusGeometry(40, 3, 10, 48), CREAM);
    wheelRim.rotation.y = Math.PI / 2;
    s.add(at(wheelRim, 226, 255, -5));
    // stitch card (right side)
    parts.card = at(box(2, 110, 70, new MeshStandardMaterial({ color: 0xfafafa })), 201, 160, -40);
    s.add(parts.card);
    s.add(at(box(2.2, 12, 10, ORANGE), 201.5, 110, -8));
    // power switch and sockets
    parts.switch = at(box(3, 12, 8, DARK), 201, 48, 60);
    s.add(parts.switch);
    s.add(at(box(3, 14, 10, GREY), 201, 48, 45)); // rear socket (power)
    const frontSocket = at(cyl(5, 5, 3, GREY), 201, 30, 60); // front socket (foot control)
    frontSocket.rotation.z = Math.PI / 2;
    s.add(frontSocket);
    // cords
    parts.cord = tube([[203, 48, 45], [240, 40, 45], [300, 20, 60], [420, 2, 120], [600, 2, 180]], 2.2, 60);
    s.add(parts.cord);
    parts.pedalCord = tube([[203, 30, 60], [230, 20, 90], [240, 6, 160], [150, 2, 210], [80, 8, 195]], 2.2, 60);
    s.add(parts.pedalCord);
    parts.pedal = at(box(90, 18, 60, DARK, 4), 60, 9, 190);
    s.add(parts.pedal);
    s.add(at(box(80, 4, 54, GREY), 60, 20, 190));
    parts.coil = new Mesh(new TorusGeometry(34, 2.4, 10, 48), CORD);
    parts.coil.rotation.x = Math.PI / 2;
    parts.coil.position.set(-60, 3, 125);
    s.add(parts.coil);
    parts.coil2 = parts.coil.clone();
    parts.coil2.position.y = 8;
    parts.coil2.rotation.z = 0.4;
    s.add(parts.coil2);
    // hard cover
    parts.hardCover = at(box(420, 320, 190, new MeshPhysicalMaterial({ color: 0xf5f1ea, transparent: true, opacity: 0.55, roughness: 0.6 }), 10), 0, 182, -2);
    s.add(parts.hardCover);

    // head front: threading slots, panel, buttons
    s.add(at(box(3, 190, 2, DARK), -150, 200, 75.5)); // right slot
    s.add(at(box(3, 190, 2, DARK), -166, 200, 75.5)); // left slot
    parts.takeUp = at(box(8, 3, 6, STEEL), -168, 290, 78);
    s.add(parts.takeUp);
    s.add(at(box(8, 2, 1, STEEL), -200, 125, 48)); // thread cutter
    // panel
    const panel = at(box(96, 90, 2, CREAM2, 2), -72, 245, 76);
    s.add(panel);
    s.add(at(box(22, 18, 1, DISPLAY), -84, 252, 77.2)); // display
    for (let r = 0; r < 4; r++)
      for (let c = 0; c < 3; c++) {
        if (r === 3 && c !== 1) continue;
        const k = at(cyl(4, 4, 1.4, CREAM, 16), -56 + c * 13, 270 - r * 12, 77.2);
        k.rotation.x = Math.PI / 2;
        s.add(k);
      }
    for (let r = 0; r < 3; r++) for (let c = 0; c < 3; c++) s.add(at(box(8, 5, 1.2, CREAM), -112 + c * 13, 272 - r * 12, 77.2));
    s.add(at(box(7, 5, 1.2, CREAM), -84, 232, 77.2)); // info button
    for (let i = 0; i < 2; i++) {
      const b = at(cyl(6, 6, 1.6, CREAM, 20), -128, 170 - i * 20, 77);
      b.rotation.x = Math.PI / 2;
      s.add(b);
    }
    s.add(at(box(8, 44, 2, DARK), -20, 175, 77)); // speed slider track
    parts.speed = at(box(10, 10, 3, GREY), -20, 175, 78);
    s.add(parts.speed);
    s.add(at(box(14, 3, 3, ORANGE), -100, 110, 77)); // PFAFF accent
    // LED strip under head
    s.add(at(box(60, 2, 10, new MeshStandardMaterial({ color: 0xfff4d6, emissive: 0xffe3a0, emissiveIntensity: 0.6 })), -150, 63 + 0, 60));

    // needle area: needle bar, needle, foot holder, foot, IDT, lift, threader, buttonhole lever
    s.add(at(box(46, 40, 60, CREAM2, 3), -160, 140, 30)); // lower head block above the needle bar
    s.add(at(box(100, 10, 140, CREAM2, 3), -150, 124, -10)); // underside of the head
    parts.needleBar = at(cyl(2.5, 2.5, 60, STEEL), -160, 120, 56);
    s.add(parts.needleBar);
    parts.needleClamp = at(box(9, 10, 9, GREY), -160, 112, 56);
    s.add(parts.needleClamp);
    const needleScrew = at(cyl(2, 2, 7, GREY), -153, 112, 56);
    needleScrew.rotation.z = Math.PI / 2;
    s.add(needleScrew);
    parts.needle = at(cyl(0.5, 0.2, 40, STEEL, 8), -160, 90, 56);
    s.add(parts.needle);
    s.add(at(box(6, 2, 4, GREY), -160, 134, 60)); // needle thread guide G
    s.add(at(box(5, 5, 2, GREY), -160, 150, 60)); // lower thread guide F
    parts.threader = at(box(5, 12, 4, GREY), -176, 118, 58);
    s.add(parts.threader);
    parts.bhLever = at(box(3, 30, 3, DARK), -181, 125, 38);
    s.add(parts.bhLever);
    // foot group (lifts together)
    parts.footGroup = new Group();
    parts.footGroup.add(at(cyl(3, 3, 40, STEEL), -160, 100, 48)); // presser bar
    parts.footGroup.add(at(box(12, 10, 12, GREY), -160, 82, 48)); // holder
    parts.foot = new Group();
    parts.foot.add(at(box(14, 2, 30, STEEL), 0, 0, 0));
    parts.foot.add(at(box(4, 6, 8, STEEL), 0, 3, -8));
    parts.foot.position.set(-160, 67, 50);
    parts.footGroup.add(parts.foot);
    parts.buttonPlate = at(box(12, 3, 20, STEEL), -160, 68, 72);
    parts.footGroup.add(parts.buttonPlate);
    s.add(parts.footGroup);
    parts.lift = at(box(4, 26, 6, DARK), -132, 120, 18);
    s.add(parts.lift);
    parts.idt = new Group();
    const idtArm = at(box(5, 56, 5, DARK), 0, 28, 0);
    const idtFoot = at(box(8, 4, 10, DARK), 0, 2, 6);
    parts.idt.add(idtArm, idtFoot);
    parts.idt.position.set(-160, 72, 26);
    s.add(parts.idt);

    // thread paths
    parts.topThread = tube([
      [34, 320, -10], [-60, 318, -16], [-118, 306, -20], [-138, 306, -10], [-150, 302, -8], [-150, 296, 20],
      [-150, 280, 77], [-150, 120, 77], [-158, 112, 77], [-166, 140, 77], [-166, 282, 77], [-168, 290, 79],
      [-166, 280, 78], [-166, 160, 70], [-160, 150, 62], [-160, 134, 62], [-160, 100, 57], [-160, 86, 58], [-160, 80, 50],
    ], 0.9, 220);
    s.add(parts.topThread);
    parts.winderThread = tube([[34, 320, -10], [-60, 318, -16], [-118, 306, -22], [-128, 303, -12], [-140, 300, 0], [-132, 296, 2], [-60, 303, -20], [90, 305, -18], [150, 308, -16], [160, 312, -8]], 0.9, 140);
    s.add(parts.winderThread);
  }

  // ---------------------------------------------------------------- state
  setState(partial, immediate = false) {
    Object.assign(this.target, partial);
    if (immediate || this.reducedMotion) {
      Object.assign(this.state, partial);
      this.apply(this.state);
    }
    this.requestFrame();
  }

  resetState() {
    this.setState({ ...DEFAULT_STATE });
  }

  apply(st) {
    const p = this.parts;
    setTubeProgress(p.topThread, st.thread);
    setTubeProgress(p.winderThread, st.winder);
    setTubeProgress(p.bobbinThread, st.bobbinThread * st.bobbinIn);
    p.winderLever.position.x = 148 + 10 * st.winderLever;
    p.winderBobbin.visible = st.bobbinOnSpindle > 0.5;
    p.winderBobbinThread.scale.setScalar(0.3 + 0.7 * st.bobbinSpin);
    p.cover.position.z = 76 + 50 * st.cover;
    p.cover.position.y = 64.2 + 12 * st.cover;
    p.bobbin.visible = st.bobbinIn > 0.5;
    p.bobbin.position.y = 58 + 30 * (1 - Math.min(1, st.bobbinIn * 1.2)) * st.cover;
    p.idt.rotation.x = -0.55 * (1 - st.idt);
    p.idt.position.y = 72 + 14 * st.footLift;
    p.footGroup.position.y = 8 * st.footLift;
    p.foot.position.z = 50 + 28 * (1 - st.footOn);
    p.foot.position.y = 67 - 10 * (1 - st.footOn) * (1 + st.footLift);
    p.foot.scale.z = 1 + 1.4 * st.buttonholeFoot;
    p.foot.position.z += 10 * st.buttonholeFoot;
    p.buttonPlate.visible = st.buttonPlate > 0.5;
    p.feedSlide.position.x = -126 + 12 * st.feedDogs;
    p.feedDogs.position.y = -3 * (1 - st.feedDogs);
    p.needle.position.y = 90 - 18 * (1 - st.needleIn);
    p.needle.visible = st.needleIn > 0.05;
    p.threader.position.y = 118 - 20 * st.threaderDown;
    p.cord.visible = st.cordPlugged > 0.5;
    p.pedalCord.visible = st.pedalPlugged > 0.5;
    p.switch.rotation.x = 0.4 * (st.power - 0.5);
    this.lamp.intensity = 1.2 * st.power;
    p.spool.visible = st.spoolOn > 0.5;
    p.spoolPin.rotation.z = (Math.PI / 2) * st.spoolVertical;
    p.spoolPin.position.y = 306 + 20 * st.spoolVertical;
    p.hardCover.visible = st.hardCover > 0.05;
    p.hardCover.material.opacity = 0.55 * st.hardCover;
    p.tray.visible = st.trayOn > 0.5;
    p.coil.visible = p.coil2.visible = st.cordCoiled > 0.5;
    p.pedal.position.set(60 - 180 * st.cordCoiled, 9, 190 - 160 * st.cordCoiled);
    p.bhLever.position.y = 125 - 22 * st.bhLever;
    p.plate.position.z = 50 + 40 * st.plateOff;
    p.plate.position.y = 64 + 6 * st.plateOff;
  }

  // ---------------------------------------------------------------- camera
  goCamera(name, immediate = false) {
    const preset = CAMERAS[name] || CAMERAS.front;
    const aspect = this.camera.aspect || 1;
    const k = aspect < 1.2 ? Math.min(2.2, 1.2 / aspect) : 1;
    const c = { target: preset.target, pos: preset.target.map((t, i) => t + (preset.pos[i] - t) * k) };
    if (immediate || this.reducedMotion) {
      this.camera.position.set(...c.pos);
      this.controls.target.set(...c.target);
      this.controls.update();
      this.cameraTween = null;
    } else {
      this.cameraTween = { from: this.camera.position.clone(), fromT: this.controls.target.clone(), to: v(...c.pos), toT: v(...c.target), t: 0 };
    }
    this.requestFrame();
  }

  // ---------------------------------------------------------------- hotspots
  setHotspots(list, activeId = null) {
    this.hotspotLayer.innerHTML = '';
    this.hotspots.clear();
    for (const part of list) {
      const el = document.createElement('button');
      el.type = 'button';
      el.className = 'hotspot' + (part.id === activeId ? ' active' : '');
      el.dataset.no = part.no ?? '•';
      el.style.pointerEvents = 'auto';
      el.setAttribute('aria-label', part.name.en);
      el.addEventListener('click', (e) => {
        e.stopPropagation();
        this.onPart && this.onPart(part.id);
      });
      this.hotspotLayer.appendChild(el);
      this.hotspots.set(part.id, { el, at: v(...part.at) });
    }
    this.requestFrame();
  }

  setActiveHotspot(id) {
    for (const [pid, h] of this.hotspots) h.el.classList.toggle('active', pid === id);
  }

  projectHotspots() {
    if (!this.hotspots.size) return;
    const w = this.container.clientWidth;
    const h = this.container.clientHeight;
    const tmp = new Vector3();
    const camDir = new Vector3();
    this.camera.getWorldDirection(camDir);
    for (const { el, at: p } of this.hotspots.values()) {
      tmp.copy(p).project(this.camera);
      const behind = tmp.z > 1;
      el.style.display = behind ? 'none' : '';
      if (behind) continue;
      el.style.left = `${((tmp.x + 1) / 2) * w}px`;
      el.style.top = `${((1 - tmp.y) / 2) * h}px`;
      const toPoint = p.clone().sub(this.camera.position).normalize();
      el.classList.toggle('dim', toPoint.dot(camDir) < 0.6);
    }
  }

  // ---------------------------------------------------------------- loop
  requestFrame() {
    if (!this.raf) this.raf = requestAnimationFrame((t) => this.frame(t));
  }

  frame(now) {
    this.raf = 0;
    const dt = this.last ? Math.min(0.1, (now - this.last) / 1000) : 0.016;
    this.last = now;
    let moving = false;
    // tween state
    const k = this.reducedMotion ? 1 : 1 - Math.exp(-dt * 6);
    for (const key of Object.keys(this.target)) {
      const a = this.state[key];
      const b = this.target[key];
      if (Math.abs(a - b) > 0.002) {
        this.state[key] = a + (b - a) * k;
        moving = true;
      } else if (a !== b) this.state[key] = b;
    }
    if (this.target.bobbinSpin > 0.5) {
      this.parts.winderBobbin.rotation.y += dt * 12;
      moving = true;
    }
    this.apply(this.state);
    // tween camera
    if (this.cameraTween) {
      const tw = this.cameraTween;
      tw.t = Math.min(1, tw.t + dt / 0.9);
      const e = 1 - Math.pow(1 - tw.t, 3);
      this.camera.position.lerpVectors(tw.from, tw.to, e);
      this.controls.target.lerpVectors(tw.fromT, tw.toT, e);
      if (tw.t >= 1) this.cameraTween = null;
      moving = true;
    }
    if (this.controls.update()) moving = true;
    this.renderer.render(this.scene, this.camera);
    this.projectHotspots();
    if (moving) this.requestFrame();
    else this.last = 0;
  }

  resize() {
    const w = this.container.clientWidth || 300;
    const h = this.container.clientHeight || 300;
    this.camera.aspect = w / h;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(w, h, false);
    this.requestFrame();
  }

  dispose() {
    cancelAnimationFrame(this.raf);
    this.raf = 0;
    this.controls.dispose();
    this.renderer.dispose();
    this.renderer.domElement.remove();
    this.hotspotLayer.remove();
  }
}
