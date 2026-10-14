// Physical purchase parts shared by geometry, animation and the shopping sheet.
import { CABLES, COIL_MOUNTS, RAILS } from './wiring.js';
import { UNIT } from './layout.js';
import { cableCentreline, coilPoints } from './cablepath.js';
import { clamp } from './math.js';

export const CHECKED = '2026-10-14';
export const SOURCES = {
  ties: {shop:'Mitre 10 NZ',size:'12 × 203 mm (200 mm equivalent)',pack:5,url:'https://www.mitre10.co.nz/shop/velcro-brand-one-wrap-brand-bundling-ties-12mm-x-203mm/p/246259'},
  walkIn: {shop:'Bunnings NZ',size:'13 × 200 mm, assorted colours',pack:60,url:'https://www.bunnings.co.nz/velcro-brand-one-wrap-13mm-x-200mm-multicolour-ties-60-pack_p0388962'},
  hooks: {shop:'Mitre 10 NZ',size:'32 mm, white, pack of 2',pack:2,url:'https://www.mitre10.co.nz/shop/magnet-source-magnectic-hook-32mm-pack-of-2-white/p/244346'},
  pads: {shop:'Bunnings NZ',size:'30 × 200 cm roll; two 253 × 21 mm strips',pack:1,url:'https://www.bunnings.co.nz/innova-30-x-200cm-black-grip-mat_p8905397'},
};
const rectangle=(x0,x1,y0,y1,z)=>[[x0,y0+2,z],[x0+2,y0,z],[x1-2,y0,z],[x1,y0+2,z],[x1,y1-2,z],[x1-2,y1,z],[x0+2,y1,z],[x0,y1-2,z]];
export const RETAINERS=[];
for(const [side,heights,wires] of [
  ['left',[70,170,225,280],['eth2','eth1','eth0','usbSeagate','usbTouro']],
  ['right',[45,120,225,320],['dc0','dc1','dc2','swPower','routerPower']],
])for(const z of heights) {
  const rail=RAILS[side];
  RETAINERS.push({id:`rail-${side}-${z}`,kind:'rail',rail:side,wires,
    points:rectangle(side==='left'?8:222,side==='left'?36:244,177,228,z),p:[(rail.x0+rail.x1)/2,219,z]});
}
for(const c of CABLES.filter(c=>c.stock)) {
  const result=cableCentreline(c,{sA:0,sB:c.routeCum.at(-1),dress:1});
  const pts=coilPoints(c.coil,result.turns,c.coil.aTight,c.coil.bTight);
  const top=pts.reduce((best,p)=>p[2]>best[2]?p:best,pts[0]);
  const axis=c.coil.AX.findIndex(v=>Math.abs(v)>.9);
  const min=Math.min(...pts.map(p=>p[axis]))-c.od/2-1, max=Math.max(...pts.map(p=>p[axis]))+c.od/2+1;
  const z0=top[2]-c.od/2-1,z1=top[2]+c.od/2+1;
  const usb=c.id.startsWith('usb');
  let points;
  if(usb)points=rectangle(8,32,177,Math.min(229,max),top[2]);
  else if(axis===0)points=[[min,top[1],z0],[max,top[1],z0],[max,top[1],z1],[min,top[1],z1]];
  else points=[[top[0],min,z0],[top[0],max,z0],[top[0],max,z1],[top[0],min,z1]];
  RETAINERS.push({id:`keeper-${c.id}`,kind:'keeper',coil:c.id,rail:usb?'left':null,wires:[c.id],points,p:top});
  const m=COIL_MOUNTS[c.id];
  if(m) {
    let p,n;
    if(m.face==='left'){p=[UNIT.bodyX0+2,top[1],top[2]+8];n=[1,0,0];}
    if(m.face==='partition'){p=[UNIT.partitions[0]-1,top[1],top[2]+8];n=[-1,0,0];}
    if(m.face==='inside-back'){p=[top[0],UNIT.back-2,top[2]+8];n=[0,-1,0];}
    if(m.face==='back'){p=[top[0],UNIT.back,top[2]+8];n=[0,1,0];}
    RETAINERS.push({id:`hook-${c.id}`,kind:'hook',coil:c.id,face:m.face,wires:[c.id],p,n});
  }
}
for(const z of [-72,-277])RETAINERS.push({id:`hook-rise-${z}`,kind:'hook',face:'back',p:[150,UNIT.back,z],n:[0,1,0],wires:['dc0','dc1','dc2','swPower','routerPower']});
for(const x of [430,760,1070])RETAINERS.push({id:`hook-zig-${x}`,kind:'hook',face:'back',p:[x,UNIT.back,-52],n:[0,1,0],wires:['zigbee']});

export const RETAINER_COUNTS = {
  rail:RETAINERS.filter(r=>r.kind==='rail').length,
  keeper:RETAINERS.filter(r=>r.kind==='keeper').length,
  hook:RETAINERS.filter(r=>r.kind==='hook').length,
};
export const KIT_CARDS = [
  {kind:'rail',name:'ONE-WRAP rail ties',size:'12 × 203 mm',quantity:RETAINER_COUNTS.rail,source:SOURCES.ties,anchor:'rail-left-225'},
  {kind:'keeper',name:'ONE-WRAP coil keepers',size:'Same reusable tie',quantity:RETAINER_COUNTS.keeper,source:SOURCES.ties,anchor:'keeper-usbSeagate'},
  {kind:'hook',name:'Magnet Source hooks',size:'Ø32 mm · steel faces',quantity:RETAINER_COUNTS.hook,source:SOURCES.hooks,anchor:'hook-rise--72'},
  {kind:'pads',name:'Loose grip-mat pads',size:'253 × 21 mm · no adhesive',quantity:2,source:SOURCES.pads,anchor:'pads'},
];
const smooth=t=>{const v=clamp(t,0,1);return v*v*(3-2*v);};
function inverseSmooth(v){let lo=0,hi=1;for(let i=0;i<20;i++){const m=(lo+hi)/2;if(smooth(m)<v)lo=m;else hi=m;}return (lo+hi)/2;}
const arrivals=new Map();
function arrival(r,c){
  const key=r.id+':'+c.id;if(arrivals.has(key))return arrivals.get(key);
  const p=r.p;let best=Infinity,s=0;
  for(let i=0;i<c.routeB.length;i++){
    const d=c.routeB[i].reduce((sum,v,k)=>sum+(v-p[k])**2,0);
    if(d<best){best=d;s=c.routeCum[i];}
  }
  const t=1.8+4*inverseSmooth(s/c.routeCum.at(-1));arrivals.set(key,t);return t;
}
export function retainerState(r,timeline,time){
  let closed=0,glow=0;
  for(const id of r.wires){
    const c=CABLES.find(c=>c.id===id), chapter=timeline.chapters.find(c=>c.wire===id);
    const age=time-chapter.start-(r.coil?(r.kind==='hook' ? .5 : 5.1):arrival(r,c));
    closed=Math.max(closed,smooth(age/.75));
    glow=Math.max(glow,age>0&&age<1.6?Math.sin(Math.PI*age/1.6):0);
  }
  const kit=timeline.chapters.find(c=>c.id==='retainer-kit');
  const demo=['rail-left-225','keeper-usbSeagate','hook-rise--72'].includes(r.id);
  const inKit=time>=kit.start&&time<kit.end;
  if(inKit&&demo){const age=time-kit.start-(r.kind==='hook'?3.2:r.kind==='keeper'?5:1);closed=smooth(age/2);glow=age>0&&age<3?Math.sin(Math.PI*age/3):0;}
  return {closed,glow,visible:closed>0.001};
}
