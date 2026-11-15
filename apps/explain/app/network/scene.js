// The home network as simple blocks on a dark floor. Metres, y up; the rack is at the origin, the router 6 m
// behind it, the wireless devices to the left and Tailscale to the right. Nothing here is to scale except the
// address ruler: one tick per address.
//
// Performance: a handful of shared lambert materials, so every shader is compiled once behind the loading screen;
// focus swaps a mesh's material between two that share a program; packets and ruler ticks are instanced, so they
// cost two draw calls and one draw call.

import {
  BoxGeometry,
  BufferAttribute,
  BufferGeometry,
  CanvasTexture,
  Color,
  CylinderGeometry,
  DynamicDrawUsage,
  Group,
  IcosahedronGeometry,
  InstancedMesh,
  LineBasicMaterial,
  LineSegments,
  Mesh,
  MeshBasicMaterial,
  MeshLambertMaterial,
  Object3D,
  PlaneGeometry,
  SphereGeometry,
  SRGBColorSpace,
  TorusGeometry,
  Vector3,
} from 'three';

const AMBER = 0xe8ae62;
export const RULER_X0 = -4.48;
export const RULER_STEP = 0.035;
export const RULER_Z = 3.4;

const M = {
  body: new MeshLambertMaterial({ color: 0x4a443d }),
  dark: new MeshLambertMaterial({ color: 0x23211e }),
  light: new MeshLambertMaterial({ color: 0xb9b1a5 }),
  white: new MeshLambertMaterial({ color: 0xe6e0d6 }),
  cloud: new MeshLambertMaterial({ color: 0x7d8790 }),
  focus: new MeshLambertMaterial({ color: AMBER, emissive: 0x6a4210 }),
  faint: new MeshLambertMaterial({ color: 0x3e3a35 }),
  cable: new MeshLambertMaterial({ color: 0x8a8378 }),
  tick: new MeshLambertMaterial({ color: 0xffffff }),
};

const geo = {
  box: new BoxGeometry(1, 1, 1),
  cyl: new CylinderGeometry(1, 1, 1, 24),
  ball: new SphereGeometry(1, 20, 14),
  ico: new IcosahedronGeometry(1, 1),
};

function part(g, mat, size, pos, rot) {
  const m = new Mesh(g, mat);
  m.scale.set(...size);
  m.position.set(...pos);
  if (rot) m.rotation.set(...rot);
  return m;
}

// Each actor: a group, the meshes that light up, and an anchor at its top for labels and packets.
function actor(id, parts, top, opts = {}) {
  const obj = new Group();
  obj.name = id;
  for (const p of parts) obj.add(p);
  const anchor = new Object3D();
  anchor.position.set(0, top, 0);
  obj.add(anchor);
  if (opts.anchorAt) anchor.position.set(...opts.anchorAt);
  const meshes = parts.filter((p) => p.isMesh && p.userData.lit !== false);
  return { id, obj, meshes, base: meshes.map((m) => m.material), anchor, ...opts };
}

const BUILD = {
  router: () => actor('router', [part(geo.box, M.white, [0.9, 0.22, 0.6], [0, 0.11, 0]), part(geo.box, M.dark, [0.6, 0.02, 0.02], [0, 0.14, 0.305])], 0.3),
  switch: () => actor('switch', [part(geo.box, M.body, [0.9, 0.08, 0.32], [0, 0.04, 0])], 0.12),
  node: (id) => actor(id, [part(geo.box, M.body, [0.62, 0.22, 0.62], [0, 0.11, 0]), part(geo.box, M.dark, [0.5, 0.02, 0.02], [0, 0.11, 0.315])], 0.3),
  pikvm: () => actor('pikvm', [part(geo.box, M.light, [0.34, 0.1, 0.24], [0, 0.05, 0])], 0.16),
  laptop: (id = 'laptop') =>
    actor(id, [part(geo.box, M.light, [0.56, 0.03, 0.38], [0, 0.015, 0]), part(geo.box, M.dark, [0.56, 0.36, 0.025], [0, 0.19, -0.2], [-0.25, 0, 0])], 0.42),
  phone: (id) => actor(id, [part(geo.box, M.dark, [0.2, 0.4, 0.03], [0, 0.22, 0], [-0.3, 0, 0])], 0.46),
  mac: () => actor('mac', [part(geo.box, M.light, [0.42, 0.12, 0.42], [0, 0.06, 0])], 0.18),
  tv: () => actor('tv', [part(geo.box, M.dark, [1.3, 0.75, 0.05], [0, 0.6, 0]), part(geo.box, M.body, [0.08, 0.24, 0.08], [0, 0.12, 0])], 1.02),
  vacuum: () => actor('vacuum', [part(geo.cyl, M.body, [0.34, 0.1, 0.34], [0, 0.05, 0])], 0.16),
  bulb: () => actor('bulb', [part(geo.cyl, M.body, [0.03, 1, 0.03], [0, 0.5, 0]), part(geo.ball, M.white, [0.14, 0.14, 0.14], [0, 1.08, 0])], 1.26),
  voice: () => actor('voice', [part(geo.cyl, M.light, [0.15, 0.22, 0.15], [0, 0.11, 0])], 0.28),
  esp: () => actor('esp', [part(geo.box, M.body, [0.22, 0.05, 0.14], [0, 0.025, 0])], 0.1),
  internet: () =>
    actor(
      'internet',
      [
        part(geo.ico, M.cloud, [1.1, 0.8, 0.9], [0, 0, 0]),
        part(geo.ico, M.cloud, [0.8, 0.65, 0.7], [-1.1, -0.15, 0.1]),
        part(geo.ico, M.cloud, [0.85, 0.7, 0.75], [1.1, -0.1, -0.1]),
        part(geo.ico, M.cloud, [0.6, 0.5, 0.6], [0.4, 0.55, 0.2]),
      ],
      0.9,
      { anchorAt: [0, -0.45, 0.55] },
    ),
};

// Where each thing stands today (flat) and in the proposed split (subnets). Plates are [x0, z0, x1, z1].
const PLACES = {
  internet: { flat: [0, 2.6, -13] },
  router: { flat: [0, 0, -6] },
  switch: { flat: [0, 0, -1.7] },
  node0: { flat: [-1.2, 0, 0] },
  node1: { flat: [0, 0, 0] },
  node2: { flat: [1.2, 0, 0] },
  pikvm: { flat: [2.5, 0, -1.1] },
  laptop: { flat: [-3.2, 0, -3.4], split: [-3.4, 0, -2.8] },
  phone: { flat: [-4.6, 0, -4.3], split: [-4.8, 0, -3.5] },
  mac: { flat: [-3.0, 0, -5.6], split: [-6.0, 0, -2.9] },
  esp: { flat: [-5.5, 0, -3.0], split: [-3.4, 0, -7.4] },
  bulb: { flat: [-5.7, 0, -5.4], split: [-6.1, 0, -7.2] },
  tv: { flat: [-6.1, 0, -6.7], split: [-6.0, 0, -9.2] },
  vacuum: { flat: [-4.4, 0, -6.9], split: [-4.7, 0, -9.0] },
  voice: { flat: [-3.6, 0, -7.6], split: [-3.4, 0, -9.3] },
  guestphone: { flat: [5.0, 0, -8.6] },
  awayphone: { flat: [8.6, 0, 1.2] },
};
const PLATES = {
  lanPlate: [-7.3, -8.6, 3.4, 1.2],
  labPlate: [-2.0, -2.5, 3.4, 1.2],
  homePlate: [-7.3, -4.6, -2.4, -1.8],
  iotPlate: [-7.3, -10.3, -2.4, -6.3],
  guestPlate: [3.2, -10.0, 7.0, -7.4],
};
const CHIPS = [13, 20, 30, 32, 33, 35, 36];

function gridTexture() {
  const c = document.createElement('canvas');
  c.width = c.height = 512;
  const g = c.getContext('2d');
  const r = g.createRadialGradient(256, 256, 0, 256, 256, 256);
  r.addColorStop(0, 'rgba(255,255,255,0.10)');
  r.addColorStop(0.7, 'rgba(255,255,255,0.05)');
  r.addColorStop(1, 'rgba(255,255,255,0)');
  g.fillStyle = r;
  g.fillRect(0, 0, 512, 512);
  g.globalCompositeOperation = 'destination-in';
  g.fillStyle = '#fff';
  for (let i = 0; i <= 512; i += 16) {
    g.fillRect(i, 0, 1, 512);
    g.fillRect(0, i, 512, 1);
  }
  const t = new CanvasTexture(c);
  t.colorSpace = SRGBColorSpace;
  return t;
}

function dashTexture() {
  const c = document.createElement('canvas');
  c.width = 512;
  c.height = 320;
  const g = c.getContext('2d');
  g.fillStyle = '#16140f';
  g.fillRect(0, 0, 512, 320);
  g.strokeStyle = 'rgba(239,235,228,0.12)';
  for (let y = 60; y < 320; y += 64) {
    g.beginPath();
    g.moveTo(24, y);
    g.lineTo(488, y);
    g.stroke();
  }
  const line = (seed, base, amp, color) => {
    g.strokeStyle = color;
    g.lineWidth = 4;
    g.beginPath();
    for (let x = 24; x <= 488; x += 8) {
      const y = base - amp * (0.5 + 0.5 * Math.sin(x * 0.03 + seed) * Math.cos(x * 0.011 + seed * 2));
      if (x === 24) g.moveTo(x, y);
      else g.lineTo(x, y);
    }
    g.stroke();
  };
  line(1, 150, 90, '#e8ae62');
  line(4, 290, 70, 'rgba(239,235,228,0.55)');
  const t = new CanvasTexture(c);
  t.colorSpace = SRGBColorSpace;
  return t;
}

export function buildScene(stage) {
  const { scene } = stage;
  const actors = new Map();
  const add = (a, place) => {
    a.place = place;
    a.obj.position.set(...place.flat);
    actors.set(a.id, a);
    scene.add(a.obj);
    return a;
  };

  // floor
  const floor = new Mesh(new PlaneGeometry(40, 40), new MeshBasicMaterial({ map: gridTexture(), transparent: true, depthWrite: false }));
  floor.rotation.x = -Math.PI / 2;
  floor.position.set(0, -0.001, -4);
  floor.renderOrder = -3;
  scene.add(floor);

  add(BUILD.internet(), PLACES.internet);
  add(BUILD.router(), PLACES.router);
  add(BUILD.switch(), PLACES.switch);
  for (const id of ['node0', 'node1', 'node2']) add(BUILD.node(id), PLACES[id]);
  add(BUILD.pikvm(), PLACES.pikvm);
  add(BUILD.laptop(), PLACES.laptop);
  add(BUILD.phone('phone'), PLACES.phone);
  add(BUILD.mac(), PLACES.mac);
  add(BUILD.esp(), PLACES.esp);
  add(BUILD.bulb(), PLACES.bulb);
  add(BUILD.tv(), PLACES.tv);
  add(BUILD.vacuum(), PLACES.vacuum);
  add(BUILD.voice(), PLACES.voice);
  add(BUILD.phone('guestphone'), PLACES.guestphone);
  add(BUILD.phone('awayphone'), PLACES.awayphone);

  // cables: the WAN line and the uplink are actors (they light up); the rest are thin lines
  const cable = (id, a, b, r) => {
    const va = new Vector3(...a);
    const vb = new Vector3(...b);
    const len = va.distanceTo(vb);
    const m = new Mesh(geo.cyl, M.cable);
    m.scale.set(r, len, r);
    const obj = new Group();
    obj.position.copy(va).add(vb).multiplyScalar(0.5);
    obj.quaternion.setFromUnitVectors(new Vector3(0, 1, 0), vb.clone().sub(va).normalize());
    obj.add(m);
    const a2 = actor(id, [], 0);
    a2.obj = obj;
    a2.meshes = [m];
    a2.base = [M.cable];
    obj.add(a2.anchor);
    a2.place = { flat: obj.position.toArray(), fixed: true };
    actors.set(id, a2);
    scene.add(obj);
  };
  cable('wan', [0, 0.12, -6.3], [0, 2.0, -12.4], 0.035);
  cable('uplink', [0, 0.06, -5.7], [0, 0.04, -1.86], 0.03);
  const thin = [];
  const seg = (a, b) => thin.push(...a, ...b);
  for (const x of [-1.2, 0, 1.2]) seg([x * 0.3, 0.04, -1.55], [x, 0.04, -0.31]);
  seg([0.45, 0.04, -1.65], [2.33, 0.04, -1.1]);
  const thinGeo = new BufferGeometry();
  thinGeo.setAttribute('position', new BufferAttribute(new Float32Array(thin), 3));
  scene.add(new LineSegments(thinGeo, new LineBasicMaterial({ color: 0x8a8378 })));

  // Wi-Fi: three faint rings around the router
  const wifi = new Group();
  const wifiRings = [0.9, 1.5, 2.1].map((r) => {
    const m = new Mesh(new TorusGeometry(r, 0.008, 6, 64), M.faint);
    m.rotation.x = -Math.PI / 2;
    m.position.y = 0.5;
    wifi.add(m);
    return m;
  });
  wifi.position.set(...PLACES.router.flat);
  const wifiActor = actor('wifi', [], 0.5);
  Object.assign(wifiActor, { obj: wifi, meshes: wifiRings, base: wifiRings.map(() => M.faint), place: { flat: PLACES.router.flat, fixed: true } });
  wifi.add(wifiActor.anchor);
  actors.set('wifi', wifiActor);
  scene.add(wifi);

  // MetalLB and kube-vip addresses: small tiles floating above the rack
  const chipsGroup = new Group();
  CHIPS.forEach((n, i) => {
    const x = -2.1 + i * 0.7;
    const a = actor(`chip${n}`, [part(geo.box, n === 13 ? M.white : M.light, [0.46, 0.04, 0.3], [0, 0, 0])], 0.06);
    a.obj.position.set(x, 1.2, -0.8);
    a.place = { flat: [x, 1.2, -0.8], fixed: true };
    actors.set(a.id, a);
    chipsGroup.add(a.obj);
  });
  scene.add(chipsGroup);

  // Kubernetes layer: pods above each node, the services ring, a DNS cache by each node
  const k8s = new Group();
  [-1.2, 0, 1.2].forEach((x, i) => {
    const pods = new InstancedMesh(geo.box, M.light, 6);
    const d = new Object3D();
    for (let k = 0; k < 6; k++) {
      d.position.set(((k % 3) - 1) * 0.2, Math.floor(k / 3) * 0.2, 0);
      d.scale.setScalar(0.14);
      d.updateMatrix();
      pods.setMatrixAt(k, d.matrix);
    }
    const a = actor(`pods${i}`, [pods], 0.38);
    a.obj.position.set(x, 1.85, 0.1);
    a.place = { flat: [x, 1.85, 0.1], fixed: true };
    actors.set(a.id, a);
    k8s.add(a.obj);
    const dns = actor(`dns${i}`, [part(geo.ball, M.white, [0.08, 0.08, 0.08], [0, 0, 0])], 0.1);
    dns.obj.position.set(x + 0.36, 0.45, 0.36);
    dns.place = { flat: [x + 0.36, 0.45, 0.36], fixed: true };
    actors.set(dns.id, dns);
    k8s.add(dns.obj);
  });
  const ring = new Mesh(new TorusGeometry(2.0, 0.025, 6, 96), M.light);
  ring.rotation.x = -Math.PI / 2;
  const services = actor('services', [ring], 0.1);
  services.obj.position.set(0, 2.75, 0.1);
  services.anchor.position.set(1.42, 0.1, -1.42);
  services.place = { flat: [0, 2.75, 0.1], fixed: true };
  actors.set('services', services);
  k8s.add(services.obj);
  scene.add(k8s);

  // Tailscale: a wire ball linked to the router, the nodes and a phone away from home
  const tail = new Group();
  const ball = new Mesh(new IcosahedronGeometry(1, 1), new MeshBasicMaterial({ color: 0xb9b1a5, wireframe: true }));
  const tailnet = actor('tailnet', [ball], 1.2);
  tailnet.base = [ball.material];
  tailnet.focusMat = new MeshBasicMaterial({ color: AMBER, wireframe: true });
  tailnet.obj.position.set(5.8, 2.4, -2.4);
  tailnet.place = { flat: [5.8, 2.4, -2.4], fixed: true };
  actors.set('tailnet', tailnet);
  tail.add(tailnet.obj);
  const tl = [];
  const link = (a, b) => tl.push(...a, ...b);
  link([5.8, 2.4, -2.4], [0, 0.3, -6]);
  for (const x of [-1.2, 0, 1.2]) link([5.8, 2.4, -2.4], [x, 0.3, 0]);
  link([5.8, 2.4, -2.4], [8.6, 0.46, 1.2]);
  const tlGeo = new BufferGeometry();
  tlGeo.setAttribute('position', new BufferAttribute(new Float32Array(tl), 3));
  tail.add(new LineSegments(tlGeo, new LineBasicMaterial({ color: 0x6f6a62 })));
  scene.add(tail);

  // Monitoring: a graph panel standing beside the rack
  const dashMat = new MeshBasicMaterial({ map: dashTexture() });
  const panel = new Mesh(new PlaneGeometry(1.6, 1), dashMat);
  panel.userData.lit = false;
  const dash = actor('dash', [panel, part(geo.box, M.body, [1.7, 1.1, 0.04], [0, 0, -0.03])], 0.62);
  dash.obj.position.set(3.7, 1.2, -0.6);
  dash.obj.rotation.y = -0.5;
  dash.place = { flat: [3.7, 1.2, -0.6], fixed: true };
  actors.set('dash', dash);
  scene.add(dash.obj);

  // Street plates
  const plates = {};
  for (const [id, [x0, z0, x1, z1]] of Object.entries(PLATES)) {
    const mat = new MeshBasicMaterial({ color: 0xe6e0d6, transparent: true, opacity: 0.06, depthWrite: false });
    const m = new Mesh(new PlaneGeometry(x1 - x0, z1 - z0), mat);
    m.rotation.x = -Math.PI / 2;
    m.renderOrder = -2;
    const a = actor(id, [m], 0);
    a.obj.position.set((x0 + x1) / 2, 0.002, (z0 + z1) / 2);
    a.anchor.position.set(0, 0, (z1 - z0) / 2 - 0.3); // front middle: on screen even on a narrow phone
    a.base = [mat];
    a.plate = mat;
    a.place = { flat: a.obj.position.toArray(), fixed: true };
    actors.set(id, a);
    scene.add(a.obj);
    plates[id] = a;
  }

  // The address ruler: one tick per address of 192.168.20.0/24
  const ruler = new InstancedMesh(geo.box, M.tick, 256);
  const d = new Object3D();
  for (let i = 0; i < 256; i++) {
    d.position.set(RULER_X0 + i * RULER_STEP, 0.06, RULER_Z);
    d.scale.set(RULER_STEP * 0.7, 0.12, 0.5);
    d.updateMatrix();
    ruler.setMatrixAt(i, d.matrix);
    ruler.setColorAt(i, new Color(0x5a554e));
  }
  scene.add(ruler);

  // Packets: amber for allowed, grey for refused
  const packetGeo = new SphereGeometry(0.075, 12, 8);
  const packets = {
    ok: new InstancedMesh(packetGeo, new MeshBasicMaterial({ color: AMBER }), 48),
    no: new InstancedMesh(packetGeo, new MeshBasicMaterial({ color: 0xa8a198 }), 24),
  };
  for (const p of Object.values(packets)) {
    p.instanceMatrix.setUsage(DynamicDrawUsage);
    p.count = 0;
    p.frustumCulled = false;
    scene.add(p);
  }
  // The path each flow takes, drawn faintly while its packets run
  const flowLines = new LineSegments(new BufferGeometry(), new LineBasicMaterial({ color: AMBER, transparent: true, opacity: 0.35 }));
  flowLines.geometry.setAttribute('position', new BufferAttribute(new Float32Array(64 * 6), 3).setUsage(DynamicDrawUsage));
  flowLines.geometry.setDrawRange(0, 0);
  flowLines.frustumCulled = false;
  scene.add(flowLines);

  const layers = { ruler: [ruler], k8s: [k8s], tailnet: [tail, actors.get('awayphone').obj], dash: [dash.obj] };
  const rulerAnchor = (i) => new Vector3(RULER_X0 + i * RULER_STEP, 0.14, RULER_Z);

  return { actors, plates, ruler, packets, flowLines, layers, chips: chipsGroup, rulerAnchor, materials: M };
}

/** Every id a beat may name (focus, labels, flows), for the story tests. Ruler ticks are `ruler<0-255>`. */
export const ACTOR_IDS = [
  ...Object.keys(PLACES),
  ...Object.keys(PLATES),
  ...CHIPS.map((n) => `chip${n}`),
  ...['wan', 'uplink', 'wifi', 'services', 'tailnet', 'dash'],
  ...[0, 1, 2].flatMap((i) => [`pods${i}`, `dns${i}`]),
];
