import { Group, Mesh, MeshStandardMaterial, BufferGeometry, BufferAttribute, BoxGeometry, Vector3, Quaternion, Box3, DynamicDrawUsage, CylinderGeometry, TubeGeometry, CatmullRomCurve3, ExtrudeGeometry, Shape, Path } from 'three';
import { CABLES } from './wiring.js';
import { CONNECTORS } from './ports.js';
import { cableCentreline, resample, leadingPlugPose, trailingPlugPose, coilPoints } from './cablepath.js';
import { basisQuat } from './math.js';
import { installationState } from './wiring-state.js';
import { buildConnector } from './hardware.js';
import { buildLivingRoom } from './room.js';
import { RETAINERS, retainerState } from './retainers.js';
import { UNIT } from './layout.js';
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

class Strap {
  constructor(def) {
    this.def=def;this.points=def.points;this.object=new Group();this.object.userData.retainer=def;
    this.material=new MeshStandardMaterial({color:def.kind==='keeper'?0x3d7771:0x35454a,roughness:.92});
    this.segments=this.points.map(()=>new Mesh(new BoxGeometry(12,1,.9),this.material));
    this.segments.forEach(o=>{o.castShadow=true;this.object.add(o);});
    // A fabric eye, with a real slot for the reusable tail. No ratchet head.
    const eye=new Shape();eye.moveTo(-7,-5);eye.lineTo(7,-5);eye.lineTo(7,5);eye.lineTo(-7,5);eye.closePath();
    const slot=new Path();slot.moveTo(-4,-1.5);slot.lineTo(4,-1.5);slot.lineTo(4,1.5);slot.lineTo(-4,1.5);slot.closePath();eye.holes.push(slot);
    this.eye=new Mesh(new ExtrudeGeometry(eye,{depth:1,bevelEnabled:false}),this.material);this.object.add(this.eye);
    this.tail=new Mesh(new BoxGeometry(12,16,.9),this.material);this.object.add(this.tail);
  }
  update(state) {
    this.object.visible=state.visible;if(!state.visible)return;
    const t=state.closed,anchor=new Vector3(...this.points[0]);
    const final=this.points.map(p=>new Vector3(...p));
    const normal=final[1].clone().sub(final[0]).cross(final[2].clone().sub(final[1])).normalize();
    const openDir=final[1].clone().sub(final[0]).normalize();
    const pts=final.map((p,i)=>{
      const f=Math.max(0,Math.min(1,t*1.9-i/final.length*.7));
      const open=anchor.clone().addScaledVector(openDir,i*20);
      return open.lerp(p,f*f*(3-2*f));
    });
    for(let i=0;i<pts.length;i++) {
      const a=pts[i],b=i===pts.length-1?anchor:pts[i+1],d=b.clone().sub(a);
      const o=this.segments[i];o.position.copy(a).add(b).multiplyScalar(.5);o.scale.y=Math.max(.01,d.length());
      const dir=d.normalize();o.quaternion.set(...basisQuat(dir.toArray(),dir.clone().cross(normal).normalize().toArray()));
    }
    this.eye.position.copy(anchor);this.eye.quaternion.copy(this.segments[0].quaternion);
    // Thread through the eye, pull snug, then press the overlap flat.
    this.tail.position.copy(anchor).addScaledVector(openDir,8).addScaledVector(normal,(1-t)*18+1.5);
    this.tail.quaternion.copy(this.segments[0].quaternion);
    this.material.emissive.setHex(0xffab5c);this.material.emissiveIntensity=state.glow*.55;
  }
}
class MagneticHook {
  constructor(def) {
    this.def=def;this.object=new Group();this.object.userData.retainer=def;
    this.object.quaternion.set(...basisQuat(def.n,[0,0,1]));
    this.material=new MeshStandardMaterial({color:0xe7e9e5,roughness:.37,metalness:.65});
    const base=new Mesh(new CylinderGeometry(16,16,5,24),this.material);base.position.y=2.5;this.object.add(base);
    const curve=new CatmullRomCurve3([new Vector3(0,5,0),new Vector3(0,22,-5),new Vector3(0,23,-15),new Vector3(0,28,-14),new Vector3(0,28,-8)]);
    const hook=new Mesh(new TubeGeometry(curve,20,2.4,8,false),this.material);this.object.add(hook);
    this.object.traverse(o=>{if(o.isMesh)o.castShadow=true;});
  }
  update(state) {
    this.object.visible=state.visible;if(!state.visible)return;
    this.object.position.set(...this.def.p).addScaledVector(new Vector3(...this.def.n),(1-state.closed)*35);
    this.material.emissive.setHex(0xffab5c);this.material.emissiveIntensity=state.glow*.6;
  }
}

export class Installation {
  constructor(timeline, parent) {
    this.timeline = timeline; this.root = new Group(); parent.add(this.root);
    this.room = buildLivingRoom(); this.root.add(this.room);
    this.roomMaterials = new Map();
    this.room.traverse(o => { if (o.isMesh) this.roomMaterials.set(o.material,{opacity:o.material.opacity,transparent:o.material.transparent}); });
    this.leads = new Map(CABLES.map(c => [c.id, new Lead(c)]));
    for (const lead of this.leads.values()) this.root.add(lead.object);
    this.retainers=new Map(RETAINERS.map(r=>[r.id,r.kind==='hook'?new MagneticHook(r):new Strap(r)]));
    for(const r of this.retainers.values())this.root.add(r.object);
    // A short demonstration bundle stays against the post during the kit chapter.
    this.demo=new Mesh(new CylinderGeometry(3,3,60,12),new MeshStandardMaterial({color:0xe6e5e0,roughness:.55}));
    this.demo.rotation.x=Math.PI/2;this.demo.position.set(21,219,225);this.root.add(this.demo);
    const cable=CABLES.find(c=>c.id==='usbSeagate');
    const curve=cableCentreline(cable,{sA:0,sB:cable.routeCum.at(-1),dress:1});
    this.demoCoil=new Mesh(new TubeGeometry(new CatmullRomCurve3(coilPoints(cable.coil,curve.turns,cable.coil.aTight,cable.coil.bTight).map(p=>new Vector3(...p))),64,cable.od/2,8,false),new MeshStandardMaterial({color:cable.colour,roughness:.55}));
    this.root.add(this.demoCoil);
  }
  setTime(time) {
    this.time=time;const state=installationState(this.timeline,time);
    this.room.visible=state.room>.001;
    this.room.userData.context.visible=time>=this.timeline.chapters.find(c=>c.id==='room-view').start-.6;
    this.room.userData.socketWall.visible=!this.room.userData.context.visible;
    const installed=this.timeline.chapters.find(c=>c.id==='installed');
    const close=Math.max(0,Math.min(1,(time-installed.start)/2));
    this.room.userData.doors.forEach((door,i)=>{door.rotation.z=i===0?(Math.PI*.55)*(1-close*close*(3-2*close)):0;});
    for(const [material,original] of this.roomMaterials) {
      material.opacity=original.opacity*state.room;
      const transparent=original.transparent||material.opacity<.995;
      if(material.transparent!==transparent){material.transparent=transparent;material.needsUpdate=true;}
    }
    for(const [id,lead] of this.leads)lead.update(state.wires[id]);
    for(const r of this.retainers.values())r.update(retainerState(r.def,this.timeline,time));
    const kit=this.timeline.chapters.find(c=>c.id==='retainer-kit');
    this.demo.visible=this.demoCoil.visible=time>=kit.start&&time<kit.end;
    this.room.userData.pads.visible=time>=this.timeline.chapters.find(c=>c.id==='living-placement').start;
    return state;
  }
  anchor(id) {
    if(id==='pads')return new Vector3(126,197,UNIT.top+2);
    const r=this.retainers.get(id);return r?(r.def.kind==='hook'?r.object.position.clone():new Vector3(...r.def.p)):new Vector3();
  }
  camera() {
    const c = this.timeline.chapters[chapterAt(this.timeline,this.time || 0)];
    const box = (min,max) => new Box3(new Vector3(...min),new Vector3(...max));
    if(c.view==='kit') {const dt=(this.time-c.start)/(c.end-c.start);return {key:'kit',box:box([-20,165,-110],[280,290,285]),view:{azimuth:2.85+dt*.08,elevation:.2}};}
    if (c.view === 'room') return {key:c.id,box:box([-2500,-3720,-520],[3670,490,580]),view:{azimuth:0.2,elevation:0.77}};
    if (c.wire === 'spareCord') return {key:'spare-board',box:box([725,-190,-530],[1135,250,-295]),view:{azimuth:0.2,elevation:0.15}};
    if (c.view === 'service') return {key:'service',box:box([-85,-560,-535],[405,250,-35]),view:{azimuth:-0.35,elevation:0.16}};
    if (c.view === 'installation' || c.wire === 'zigbee') return {key:'installation',box:box([-90,-180,-625],[1140,430,440]),view:{azimuth:0.22,elevation:0.38}};
    if (c.wire?.startsWith('dc') || ['swPower','routerPower','boardCord','wan'].includes(c.wire)) return {key:'power-wiring',box:box([-70,-160,-530],[350,425,440]),view:{azimuth:2.6,elevation:0.2}};
    if (c.view === 'rear') return {key:'rear-wiring',box:box([-25,-20,-20],[290,245,435]),view:{azimuth:2.75,elevation:0.28}};
    return {key:'build',box:null};
  }
}
