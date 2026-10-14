import { test } from 'node:test';
import assert from 'node:assert/strict';
import { Box3, Vector3, Raycaster, DoubleSide } from 'three';
import { installDomStubs, placements } from './helpers.mjs';
import { DRILLED } from '../src/variant.js';
import { UNIT, RACK, PADS, ROOM, HOUSE_FLOOR_Z } from '../src/layout.js';
import { CABLES, RAILS, POSES } from '../src/wiring.js';
import { cableCentreline, polyLength } from '../src/cablepath.js';
import { RETAINERS, retainerState } from '../src/retainers.js';
import { partsList } from '../src/parts.js';
import { buildLivingRoom } from '../src/room.js';
import { buildTimeline } from '../src/timeline.js';
import { wireState } from '../src/wiring-state.js';
import { qrotate } from '../src/math.js';

installDomStubs();
const room=buildLivingRoom();room.updateMatrixWorld(true);
const timeline=buildTimeline(placements),p=new Vector3();
const solids=room.userData.panels.filter(m=>m!==room.userData.back).map(m=>new Box3().setFromObject(m));
function panelAt(point) {
  p.set(...point);
  if(solids.some(b=>b.containsPoint(p)))return true;
  const [x,y,z]=point;
  if(x>=UNIT.bodyX0&&x<=UNIT.bodyX1&&y>=UNIT.back-2&&y<=UNIT.back&&z>=UNIT.bottom&&z<=UNIT.top-25)
    return !DRILLED || Math.hypot(x-UNIT.opening.x,z-UNIT.opening.z)>=UNIT.opening.radius;
  return false;
}
// Contract: payout and dressed leads clear steel; v1 may use its one drilled hole,
// v2 never enters a cupboard. An exterior endpoint alone cannot prove a safe route.
// Existing socket/length tests cannot detect a path which cuts through cabinet panels.
test('all cable samples clear the closed steel unit during payout and after dressing',()=>{
  for(const c of CABLES){
    const chapter=timeline.chapters.find(ch=>ch.wire===c.id);
    const times=[timeline.duration,...Array.from({length:25},(_,i)=>chapter.start+i*6.1/24)];
    const snug=timeline.chapters.find(ch=>ch.id==='snug-ties');
    times.push(...Array.from({length:25},(_,i)=>snug.start+i*6.2/24));
    for(const t of times)for(const point of cableCentreline(c,wireState(timeline,c,t)).points) {
      assert.ok(!panelAt(point),`${c.id} intersects steel at ${point.map(v=>v.toFixed(2))}, t=${t}`);
      if(!DRILLED) {
        const [x,y,z]=point;
        const cupboard=x>UNIT.bodyX0&&x<UNIT.bodyX1&&y>UNIT.front&&y<UNIT.back&&z>UNIT.bottom&&z<UNIT.top-UNIT.topThickness;
        assert.ok(!cupboard,`${c.id} enters a cupboard at ${point}, t=${t}`);
        assert.ok(y+c.od/2<ROOM.wallY,`${c.id} reaches the wall at ${point}, t=${t}`);
      }
    }
  }
});
// Contract: the visible top is uncut, while the modelled back opening actually passes a lead.
// The point collision check alone could pass when a renderer accidentally omits a steel face.
test('rendered panels have no apertures except the single optional v1 drilled hole',()=>{
  room.userData.top.material.side=DoubleSide;room.userData.back.material.side=DoubleSide;
  for(const x of [30,150,300,700,1100])for(const y of [-100,40,220]){
    const ray=new Raycaster(new Vector3(x,y,50),new Vector3(0,0,-1),0,120);
    assert.ok(ray.intersectObject(room.userData.top).length>0,`solid top ${x},${y}`);
  }
  const hole=UNIT.opening;
  const ray=new Raycaster(new Vector3(150,300,-425),new Vector3(0,-1,0),0,100);
  assert.equal(ray.intersectObject(room.userData.back).length>0,!DRILLED,'only v1 has an aperture');
  for(const m of room.userData.panels.filter(m=>m.parent===room.userData.cabinet)) {
    const shapes=m.geometry.parameters.shapes;
    if(shapes)assert.equal(shapes.holes.length,m===room.userData.back&&DRILLED?1:0,'no extra apertures');
    else assert.ok(['BoxGeometry','RoundedBoxGeometry'].includes(m.geometry.type),'solid bevelled panel');
  }
  for(const x of [0,150,500,900,1100])for(const z of [-490,-425,-200,-60]) {
    ray.set(new Vector3(x,300,z),new Vector3(0,-1,0));
    const inHole=hole&&Math.hypot(x-hole.x,z-hole.z)<hole.radius;
    assert.equal(ray.intersectObject(room.userData.back).length>0,!inHole,`back ${x},${z}`);
  }
});
// Contract: v1 retains the cupboard power option and actually uses its single hole.
// Clearance alone could pass after accidentally replacing v1 with exterior routes.
test('v1 service leads cross the back through the drilled hole', {skip:!DRILLED},()=>{
  for(const id of ['dc0','dc1','dc2','swPower','routerPower','boardCord']) {
    const c=CABLES.find(c=>c.id===id),hole=UNIT.opening;
    const crossings=cableCentreline(c,wireState(timeline,c,timeline.duration)).points.filter(([x,y,z])=>y>=UNIT.back-2&&y<=UNIT.back&&Math.hypot(x-hole.x,z-hole.z)<hole.radius);
    assert.ok(crossings.length>0,id+' uses the drilled hole');
  }
});
// Contract: purchase-sized rail ties wrap a real post rather than hovering behind the rack;
// every stock coil gets exactly one keeper and every magnet contacts steel. Cable tests omit supports.
test('rail ties enclose posts, hooks contact steel and stock coils have one keeper',()=>{
  for(const r of RETAINERS.filter(r=>r.rail)){
    const rail=RAILS[r.rail],b=new Box3().setFromPoints(r.points.map(p=>new Vector3(...p)));
    assert.ok(b.min.x<rail.x0&&b.max.x>rail.x1&&b.min.y<rail.y0&&b.max.y>rail.y1,r.id+' encloses rail');
    for(const point of r.points){const dx=Math.max(rail.x0-point[0],0,point[0]-rail.x1),dy=Math.max(rail.y0-point[1],0,point[1]-rail.y1);assert.ok(Math.hypot(dx,dy)<=25,r.id+' within 25 mm');}
    if(r.kind==='rail') {
      const band=b.clone();band.min.z-=6;band.max.z+=6;
      assert.ok(r.wires.some(id=>{
        const c=CABLES.find(c=>c.id===id);
        return cableCentreline(c,{sA:0,sB:c.routeCum.at(-1),dress:1}).points.some(point=>point[1]>rail.y1&&band.containsPoint(new Vector3(...point)));
      }),r.id+' encloses a real rear bundle');
    }
    assert.ok(r.p[2]>=12&&r.p[2]<=388&&!(r.p[2]>188&&r.p[2]<212),r.id+' at a post');
  }
  for(const r of RETAINERS.filter(r=>r.kind==='hook')){
    const inside=r.p.map((v,i)=>v-r.n[i]*.5);
    assert.ok(panelAt(inside),r.id+' magnet touches a steel face');
  }
  for(const c of CABLES.filter(c=>c.stock))assert.equal(RETAINERS.filter(r=>r.kind==='keeper'&&r.coil===c.id).length,1,c.id);
  for(const r of RETAINERS.filter(r=>r.points))assert.ok(polyLength([...r.points,r.points[0]])+16<=203,r.id+' fits the purchase tie with overlap');
});
// Contract: the actual CAD feet fit the top with >=30 mm at the rear, and the socket adapter
// clears the back with space for its lead. Assembly alignment tests do not cover furniture fit.
test('CAD footprint and pads fit the top; wall adapter and plug bend clear the back',()=>{
  const feet=placements.instances.filter(p=>p.part==='rackFeet');
  assert.equal(RACK.width,253);
  for(const foot of feet){
    assert.ok(foot.worldMin[0]>UNIT.x0&&foot.worldMax[0]<UNIT.x1);
    assert.ok(foot.worldMin[1]>UNIT.y0&&foot.worldMax[1]<=UNIT.y1-30);
  }
  for(const pad of PADS)assert.ok(pad.p[1]-pad.size[1]/2>=UNIT.y0&&pad.p[1]+pad.size[1]/2<=UNIT.y1);
  const d=POSES.powerline,ys=[];
  for(let i=0;i<8;i++)ys.push(d.p[1]+qrotate(d.q,[i&1?d.size[0]/2:-d.size[0]/2,i&2?d.size[1]/2:-d.size[1]/2,i&4?d.size[2]/2:-d.size[2]/2])[1]);
  assert.ok(Math.min(...ys)-UNIT.y1>40,'adapter and lead bend clearance');
  assert.ok(UNIT.rackMassKg<UNIT.topRatingKg,'explicit provisional load comparison');
});
// Contract: the sheet buys the scene's actual supports, not a separately maintained guess.
// No existing test sees the quantities exposed to the person buying the kit.
test('parts sheet quantities match scene supports and printed parts and screws',()=>{
  const list=partsList();
  assert.equal(list.kit[0].quantity,RETAINERS.filter(r=>r.kind==='rail').length);
  assert.equal(list.kit[1].quantity,RETAINERS.filter(r=>r.kind==='keeper').length);
  assert.equal(list.kit[2].quantity,RETAINERS.filter(r=>r.kind==='hook').length);
  assert.equal(list.kit[3].quantity,PADS.length);
  assert.equal(list.printed.reduce((sum,p)=>sum+p.quantity,0),placements.instances.length);
  assert.equal(list.fasteners.filter(p=>p.name.includes(' × ')).reduce((sum,p)=>sum+p.quantity,0),placements.screws.length);
});
// Contract: retainers install with the lead that uses them, glow, and retrace on rewind.
// The existing timeline test only owns printed parts; late fading supports could go unnoticed.
test('every retainer installs during a wire chapter and arbitrary seek reverses it',()=>{
  for(const r of RETAINERS){
    const samples=r.wires.flatMap(id=>{const c=timeline.chapters.find(c=>c.wire===id);return Array.from({length:40},(_,i)=>c.start+i*(c.end-c.start)/40);});
    const states=samples.map(t=>retainerState(r,timeline,t));
    assert.ok(states.some(s=>s.closed>0&&s.closed<1),r.id+' closes');
    assert.ok(states.some(s=>s.glow>0),r.id+' glows');
    assert.equal(retainerState(r,timeline,timeline.duration).closed,1,r.id+' installed');
    for(let i=samples.length-1;i>=0;i--)assert.deepEqual(retainerState(r,timeline,samples[i]),states[i]);
  }
});

// Contract: v2 powered equipment fits outside closed cupboards, above the room floor
// and in front of the wall. Cable-centreline tests cannot detect a penetrating device body.
test('v2 powered device envelopes clear the unit, floor and wall', {skip:DRILLED},()=>{
  const boxes=[];
  for(const id of ['brick0','brick1','brick2','board','psuSwitch','psuRouter','powerline']) {
    const d=POSES[id],corners=[];
    for(let i=0;i<8;i++)corners.push(new Vector3(...qrotate(d.q,d.size.map((v,k)=>(i&(1<<k)?1:-1)*v/2)).map((v,k)=>v+d.p[k])));
    const b=new Box3().setFromPoints(corners);boxes.push([id,b]);
    assert.ok(b.min.z>=HOUSE_FLOOR_Z-.01,id+' above floor');
    assert.ok(b.max.y<ROOM.wallY,id+' before wall');
    for(const solid of [...solids,new Box3().setFromObject(room.userData.back)])assert.ok(!b.intersectsBox(solid),id+' clear of steel');
    assert.ok(b.max.z<=UNIT.bottom||b.min.y>=UNIT.back,id+' outside cupboards');
  }
  for(let i=0;i<boxes.length;i++)for(let j=i+1;j<boxes.length;j++) {
    // Plug-in adapters mate with the board's sloped faces, within its rectangular envelope.
    if(boxes[i][0]==='board'&&['psuSwitch','psuRouter'].includes(boxes[j][0]))continue;
    assert.ok(!boxes[i][1].intersectsBox(boxes[j][1]),boxes[i][0]+' clear of '+boxes[j][0]);
  }
});
// Contract: all v2 doors stay closed through installation; no lead blocks a shut door.
// The original scene tests own rack transforms, not door state during service chapters.
test('v2 doors remain shut through every chapter', {skip:DRILLED},async()=>{
  const {Installation}=await import('../src/installation.js');
  const {Group}=await import('three');
  const installation=new Installation(timeline,new Group());
  for(let t=0;t<=timeline.duration;t+=.5){
    installation.setTime(t);
    for(const door of installation.room.userData.doors)assert.equal(door.rotation.z,0);
  }
});
