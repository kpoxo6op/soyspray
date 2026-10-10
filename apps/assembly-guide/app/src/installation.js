import { Group, Mesh, MeshStandardMaterial, BufferGeometry, BufferAttribute, BoxGeometry, Vector3, Quaternion, Box3, DynamicDrawUsage } from 'three';
import { CABLES } from './wiring.js';
import { CONNECTORS } from './ports.js';
import { cableCentreline, resample, leadingPlugPose, trailingPlugPose, coilPoints } from './cablepath.js';
import { basisQuat } from './math.js';
import { installationState } from './wiring-state.js';
import { buildConnector } from './hardware.js';
import { buildLivingRoom } from './room.js';
import { chapterAt } from './timeline.js';

// Reuse tube buffers: no per-frame geometry allocations or temporal simulation.
class Lead {
  constructor(cable) {
    this.cable = cable; this.object = new Group(); this.key = '';
    const rings = Math.max(180, Math.ceil(cable.length / 4)), sides = 8;
    this.rings = rings; this.sides = sides; this.samples = [];
    const g = new BufferGeometry();
    g.setAttribute('position', new BufferAttribute(new Float32Array(rings * sides * 3), 3).setUsage(DynamicDrawUsage));
    g.setAttribute('normal', new BufferAttribute(new Float32Array(rings * sides * 3), 3).setUsage(DynamicDrawUsage));
    const indices = [];
    for (let i = 0; i < rings - 1; i++) for (let j = 0; j < sides; j++) {
      const a = i * sides + j, b = i * sides + (j + 1) % sides, c = a + sides, d = b + sides;
      indices.push(a, c, b, b, c, d);
    }
    g.setIndex(indices);
    this.material = new MeshStandardMaterial({ color: cable.colour, roughness: 0.53, metalness: 0.03 });
    this.tube = new Mesh(g, this.material); this.tube.frustumCulled = false; this.tube.castShadow = true; this.object.add(this.tube);
    this.plugs = {};
    for (const end of ['a', 'b']) if (cable.plugs[end]) {
      const plug = buildConnector(cable.plugs[end].type, cable.colour);
      this.object.add(plug); this.plugs[end] = plug;
    }
  }
  update(state) {
    const c = this.cable;
    this.object.visible = state.alpha > 0.003;
    if (!this.object.visible) return;
    this.object.traverse(o => {
      if (!o.isMesh) return;
      o.material.transparent = state.alpha < 0.995; o.material.opacity = state.alpha;
    });
    this.material.emissive.setHex(state.active ? 0x73502c : 0x000000); this.material.emissiveIntensity = state.active ? 0.19 : 0;
    const key = `${state.sA}:${state.sB}:${state.dress}`;
    if (this.key === key) return; this.key = key;
    const result = cableCentreline(c, state); this.curve = result;
    const pts = resample(result.points, this.rings, this.samples);
    const positions = this.tube.geometry.attributes.position, normals = this.tube.geometry.attributes.normal;
    const tangent = new Vector3(), prev = new Vector3(), n = new Vector3(), b = new Vector3(), q = new Quaternion(), v = new Vector3();
    for (let i = 0; i < pts.length; i++) {
      const a = pts[Math.max(0, i - 1)], z = pts[Math.min(pts.length - 1, i + 1)];
      tangent.set(z[0] - a[0], z[1] - a[1], z[2] - a[2]).normalize();
      if (i === 0) {
        n.set(Math.abs(tangent.z) > 0.9 ? 1 : 0, 0, Math.abs(tangent.z) > 0.9 ? 0 : 1);
        n.addScaledVector(tangent, -n.dot(tangent)).normalize();
      } else { q.setFromUnitVectors(prev, tangent); n.applyQuaternion(q); n.addScaledVector(tangent, -n.dot(tangent)).normalize(); }
      b.crossVectors(tangent, n).normalize(); prev.copy(tangent);
      for (let j = 0; j < this.sides; j++) {
        const angle = j * 2 * Math.PI / this.sides;
        v.copy(n).multiplyScalar(Math.cos(angle)).addScaledVector(b, Math.sin(angle));
        const k = i * this.sides + j;
        normals.setXYZ(k, v.x, v.y, v.z);
        positions.setXYZ(k, pts[i][0] + v.x * c.od / 2, pts[i][1] + v.y * c.od / 2, pts[i][2] + v.z * c.od / 2);
      }
    }
    positions.needsUpdate = normals.needsUpdate = true;
    for (const end of ['a', 'b']) if (this.plugs[end]) {
      const p = c.plugs[end], len = CONNECTORS[p.type].len;
      const pose = end === 'a' ? trailingPlugPose(c.aLead, c.aCum, state.sA, p.frame.u, len)
        : leadingPlugPose(c.routeB, c.routeCum, state.sB, p.frame.u, len);
      this.plugs[end].position.set(...pose.origin); this.plugs[end].quaternion.set(...basisQuat(pose.yDir, pose.up));
    }
  }
}

class Tie {
  constructor(points, removable = false) {
    this.points = points; this.object = new Group();
    this.material = new MeshStandardMaterial({ color: removable ? 0x3d5552 : 0x17191b, roughness: 0.67 });
    this.segments = points.map(() => new Mesh(new BoxGeometry(removable ? 12 : 3.6, 1, 0.9), this.material));
    this.segments.forEach(o => this.object.add(o));
    this.head = new Mesh(new BoxGeometry(6, 6, 4), this.material); this.object.add(this.head);
  }
  update(t) {
    this.object.visible = t > 0.001; if (!this.object.visible) return;
    const centre = this.points.reduce((a,p) => a.add(new Vector3(...p)), new Vector3()).multiplyScalar(1 / this.points.length);
    const pts = this.points.map(p => new Vector3(...p).sub(centre).multiplyScalar(1 + (1 - t) * 0.38).add(centre));
    const planeNormal = pts[1].clone().sub(pts[0]).cross(pts[2].clone().sub(pts[1])).normalize();
    for (let i = 0; i < pts.length; i++) {
      const a = pts[i], b = pts[(i + 1) % pts.length], d = b.clone().sub(a);
      const o = this.segments[i]; o.position.copy(a).add(b).multiplyScalar(0.5); o.scale.y = d.length();
      // A flat strap, with its broad side facing out from the bundle.
      const direction = d.normalize(), up = direction.clone().cross(planeNormal).normalize();
      o.quaternion.set(...basisQuat(direction.toArray(),up.toArray()));
    }
    this.head.position.copy(pts[0]); this.head.quaternion.copy(this.segments[0].quaternion);
    this.material.transparent = t < 0.99; this.material.opacity = Math.min(1, t * 3);
  }
}

export class Installation {
  constructor(timeline, parent) {
    this.timeline = timeline; this.root = new Group(); parent.add(this.root);
    this.room = buildLivingRoom(); this.root.add(this.room);
    this.roomMaterials = new Map();
    this.room.traverse(o => { if (o.isMesh) this.roomMaterials.set(o.material,o.material.opacity); });
    this.leads = new Map(CABLES.map(c => [c.id, new Lead(c)]));
    for (const lead of this.leads.values()) this.root.add(lead.object);
    this.ties = [];
    const rail = (xy,z) => this.ties.push(new Tie(xy.map(p => [...p,z])));
    // The rail straps sit above the tray side walls and surround the rear cable lanes.
    for (const z of [100,175,225,360]) rail([[7,177],[34.4,177],[34.4,211],[40,226],[40,322],[7,322]],z);
    for (const z of [100,175,225,360]) rail([[218.6,177],[244.5,177],[244.5,337],[198,337],[198,215],[218.6,210]],z);
    // Stock coils are secured individually; their lower band clears the support surface.
    for (const c of CABLES.filter(c => c.stock)) {
      const res = cableCentreline(c, {sA:0,sB:c.routeCum.at(-1),dress:1});
      const a = c.coil.aTight, b = c.coil.bTight;
      const pts = coilPoints(c.coil,res.turns,a,b);
      const bb = new Box3().setFromPoints(pts.map(p => new Vector3(...p))).expandByScalar(c.od / 2 + 0.9);
      const centre = bb.getCenter(new Vector3());
      if (c.coil.AX[2] > 0.9) {
        this.ties.push(new Tie([[bb.min.x,centre.y,bb.min.z],[bb.max.x,centre.y,bb.min.z],
          [bb.max.x,centre.y,bb.max.z],[bb.min.x,centre.y,bb.max.z]], true));
      } else {
        this.ties.push(new Tie([[centre.x,bb.min.y,bb.min.z],[centre.x,bb.max.y,bb.min.z],
          [centre.x,bb.max.y,bb.max.z],[centre.x,bb.min.y,bb.max.z]], true));
      }
    }
    this.ties.forEach(t => this.root.add(t.object));
  }
  setTime(time) {
    this.time = time; const state = installationState(this.timeline,time);
    this.room.visible = state.room > 0.001;
    const roomChapter=this.timeline.chapters.find(c=>c.id==='room-view');
    this.room.userData.context.visible = time >= roomChapter.start - 0.6;
    this.room.userData.extension.visible = time >= this.timeline.chapters.find(c=>c.id==='living-placement').start - 0.6;
    this.room.userData.boardBands.visible = time >= this.timeline.chapters.find(c=>c.id==='power-board').start + 3.4;
    this.room.userData.brickBands.visible = time >= this.timeline.chapters.find(c=>c.id==='zip-ties').start + 1.5;
    const endChapter=this.timeline.chapters.find(c=>c.id==='installed');
    const close=Math.max(0,Math.min(1,(time-endChapter.start)/2));
    this.room.userData.door.rotation.z = -(Math.PI/2)*(1-close*close*(3-2*close));
    for (const [material,opacity] of this.roomMaterials) {
      material.opacity = opacity * state.room;
      const transparent = material.opacity < 0.995;
      if (material.transparent !== transparent) { material.transparent = transparent; material.needsUpdate = true; }
    }
    for (const [id,lead] of this.leads) lead.update(state.wires[id]);
    this.ties.forEach(t => t.update(state.ties));
    return state;
  }
  camera() {
    const c = this.timeline.chapters[chapterAt(this.timeline,this.time || 0)];
    const box = (min,max) => new Box3(new Vector3(...min),new Vector3(...max));
    if (c.view === 'room') return {key:c.id,box:box([-2500,-3720,-520],[3670,490,580]),view:{azimuth:0.2,elevation:0.77}};
    if (c.wire === 'spareCord') return {key:'spare-board',box:box([815,-5,-430],[1280,430,-225]),view:{azimuth:0.2,elevation:0.15}};
    if (c.view === 'service') return {key:'service',box:box([-75,-120,-435],[435,420,-20]),view:{azimuth:0.35,elevation:0.16}};
    if (c.view === 'installation' || c.wire === 'zigbee') return {key:'installation',box:box([-70,-85,-520],[1750,470,440]),view:{azimuth:0.22,elevation:0.38}};
    if (c.wire?.startsWith('dc') || ['swPower','routerPower','boardCord','wan'].includes(c.wire)) return {key:'power-wiring',box:box([-35,-25,-420],[410,465,440]),view:{azimuth:2.6,elevation:0.2}};
    if (c.view === 'rear') return {key:'rear-wiring',box:box([-25,-20,-20],[290,280,435]),view:{azimuth:2.75,elevation:0.28}};
    return {key:'build',box:null};
  }
}
