import { Group, Mesh, BoxGeometry, ExtrudeGeometry, Shape, Path, MeshStandardMaterial, MeshPhysicalMaterial, DirectionalLight, TubeGeometry, CatmullRomCurve3, Vector3, PlaneGeometry, CanvasTexture, MeshBasicMaterial } from 'three';
import { RoundedBoxGeometry } from 'three/examples/jsm/geometries/RoundedBoxGeometry.js';
import { HOUSE_FLOOR_Z as GROUND, ROOM, UNIT, PADS, houseToRack } from './layout.js';

export function buildLivingRoom() {
  const root=new Group(),context=new Group(),cabinet=new Group();root.add(context,cabinet);
  root.userData.context=context;root.userData.cabinet=cabinet;
  const steel=new MeshPhysicalMaterial({color:0xa4b2a6,roughness:.78,metalness:.32,clearcoat:.12,clearcoatRoughness:.8});
  const metal=new MeshStandardMaterial({color:0xbfc8c0,roughness:.4,metalness:.75});
  const oak=new MeshStandardMaterial({color:0xb19272,roughness:.83}),wood=new MeshStandardMaterial({color:0x997754,roughness:.68});
  const cloth=new MeshStandardMaterial({color:0x797b7d,roughness:.97}),cushion=new MeshStandardMaterial({color:0xa09c97,roughness:.96});
  const wall=new MeshStandardMaterial({color:0xd7d5ce,roughness:1,transparent:true,opacity:.055,depthWrite:false});
  const white=new MeshStandardMaterial({color:0xcac7bf,roughness:.83}),padMat=new MeshStandardMaterial({color:0x343e3d,roughness:.95});
  const panels=[];root.userData.panels=panels;
  function box(size,p,mat,parent=cabinet,panel=false) {
    const soft=mat===cloth||mat===cushion;
    const radius=soft?Math.min(42,Math.min(...size)/4):Math.min(1,Math.min(...size)/4);
    const o=new Mesh(new RoundedBoxGeometry(...size,2,radius),mat);
    o.position.set(...p);o.receiveShadow=true;o.castShadow=true;parent.add(o);
    if(panel)panels.push(o);return o;
  }
  for(let y=-3670;y<ROOM.wallY;y+=180)box([5600,178,12],[450,y+89,GROUND-6.4],oak,context);
  box([5600,16,70],[450,ROOM.wallY-8,GROUND+35],white,context);
  box([5600,60,1800],[450,ROOM.wallY+30,GROUND+900],wall,context);
  box([30,4000,70],[3250,-1570,GROUND+35],white,context);
  for(let y=-2940;y<=60;y+=1500)box([28,26,1900],[3250,y,GROUND+950],white,context);
  box([28,3026,26],[3250,-1440,GROUND+1900],white,context);
  const cx=(UNIT.x0+UNIT.x1)/2,cy=(UNIT.front+UNIT.back)/2;
  root.userData.top=box([UNIT.x1-UNIT.x0,UNIT.y1-UNIT.y0,UNIT.topThickness],[cx,(UNIT.y0+UNIT.y1)/2,UNIT.top-UNIT.topThickness/2],steel,cabinet,true);
  box([1190,390,2],[cx,cy,UNIT.bottom+1],steel,cabinet,true);
  for(const x of [UNIT.bodyX0+1,...UNIT.partitions,UNIT.bodyX1-1])
    box([2,390,475],[x,cy,(UNIT.bottom-45)/2],steel,cabinet,true);
  // One factory opening in the back. The top is a single solid slab.
  const back=new Shape();back.moveTo(UNIT.bodyX0,UNIT.bottom);back.lineTo(UNIT.bodyX1,UNIT.bottom);
  back.lineTo(UNIT.bodyX1,-45);back.lineTo(UNIT.bodyX0,-45);back.closePath();
  const opening=new Path();opening.absarc(UNIT.opening.x,UNIT.opening.z,UNIT.opening.radius,0,Math.PI*2,true);back.holes.push(opening);
  const rear=new Mesh(new ExtrudeGeometry(back,{depth:2,bevelEnabled:false,curveSegments:48}),steel);
  rear.rotation.x=Math.PI/2;rear.position.y=UNIT.back;rear.castShadow=rear.receiveShadow=true;cabinet.add(rear);panels.push(rear);
  root.userData.back=rear;
  const edges=[UNIT.bodyX0,...UNIT.partitions,UNIT.bodyX1];
  for(let i=0;i<3;i++) {
    const lo=edges[i]+7,hi=edges[i+1]-7;
    box([hi-lo,350,2],[(lo+hi)/2,35,UNIT.shelf-1],steel,cabinet,true);
    for(const x of [lo+2,hi-2])for(const z of [-370,-310,-250])
      box([2,9,4],[x,35,z],metal);
  }
  // The folded side panels continue into four square corner legs. No middle legs.
  for(const x of [UNIT.bodyX0+15,UNIT.bodyX1-15])for(const y of [UNIT.front+15,UNIT.back-15])
    box([30,30,100],[x,y,GROUND+50],steel);
  const socketWall=new Mesh(new BoxGeometry(1360,8,1100),new MeshStandardMaterial({color:0x68787b,roughness:1,transparent:true,opacity:.085,depthWrite:false}));
  socketWall.position.set(500,ROOM.wallY+4,GROUND+550);root.add(socketWall);
  const doors=[];root.userData.doors=doors;
  for(let i=0;i<3;i++) {
    const width=edges[i+1]-edges[i]-UNIT.doorGap*2, height=470;
    const door=new Group();door.position.set(edges[i+1]-UNIT.doorGap,UNIT.front,-282.5);cabinet.add(door);doors.push(door);
    const face=new Shape();face.moveTo(-width,-height/2);face.lineTo(0,-height/2);face.lineTo(0,height/2);face.lineTo(-width,height/2);face.closePath();
    for(const bank of [-120,110])for(let slot=0;slot<5;slot++) {
      const z=bank+slot*11;
      const hole=new Path();hole.moveTo(-145,z);hole.lineTo(-40,z);hole.lineTo(-40,z+5);hole.lineTo(-145,z+5);hole.closePath();face.holes.push(hole);
      // A pressed return lip behind each opening gives real depth and a self shadow.
      const lip=box([105,6,1],[-92.5,4,z+4],steel,door);lip.rotation.x=-.55;lip.receiveShadow=false;
    }
    const panel=new Mesh(new ExtrudeGeometry(face,{depth:2,bevelEnabled:true,bevelSize:.35,bevelThickness:.35,bevelSegments:2,steps:1}),steel);
    panel.rotation.x=Math.PI/2;panel.castShadow=true;panel.receiveShadow=false;door.add(panel);panels.push(panel);
    const x=-width+35;
    const curve=new CatmullRomCurve3([new Vector3(x,-2,-35),new Vector3(x,-18,-30),new Vector3(x,-22,0),new Vector3(x,-18,30),new Vector3(x,-2,35)]);
    const pull=new Mesh(new TubeGeometry(curve,24,4,10,false),metal);pull.castShadow=true;door.add(pull);
    for(const z of [-180,180])box([5,5,22],[-2,0,z],metal,door);
  }
  const pads=new Group();root.add(pads);root.userData.pads=pads;
  for(const p of PADS)box(p.size,p.p,padMat,pads);
  // Soft contact shadows supplement the stage's directional shadows at both contact planes.
  function contact(size,p,opacity,parent=root) {
    const canvas=document.createElement('canvas');canvas.width=canvas.height=128;
    const ctx=canvas.getContext('2d'),grad=ctx.createRadialGradient(64,64,0,64,64,64);
    grad.addColorStop(0,`rgba(0,0,0,${opacity})`);grad.addColorStop(.6,`rgba(0,0,0,${opacity*.55})`);grad.addColorStop(1,'rgba(0,0,0,0)');
    ctx.fillStyle=grad;ctx.fillRect(0,0,128,128);
    const o=new Mesh(new PlaneGeometry(...size),new MeshBasicMaterial({map:new CanvasTexture(canvas),transparent:true,depthWrite:false}));
    o.position.set(...p);parent.add(o);
  }
  contact([1340,480],[cx,45,GROUND+.2],.6);
  contact([290,250],[126,104,UNIT.top+.2],.32);
  const sofa=houseToRack([4.2,7.2,0]);
  box([2220,1110,260],[sofa[0],sofa[1],GROUND+240],cloth,context);box([2220,190,610],[sofa[0],sofa[1]-455,GROUND+540],cloth,context);
  for(const x of [sofa[0]-1010,sofa[0]+1010])box([200,1110,530],[x,sofa[1],GROUND+395],cloth,context);
  for(const x of [sofa[0]-455,sofa[0]+455]) {box([895,820,130],[x,sofa[1]+45,GROUND+435],cushion,context);const b=box([895,145,445],[x,sofa[1]-335,GROUND+705],cushion,context);b.rotation.x=-.09;}
  const foot=houseToRack([3.15,7.9,0]);box([1110,1100,350],[foot[0],foot[1],GROUND+235],cloth,context);box([1110,1100,100],[foot[0],foot[1],GROUND+460],cushion,context);
  const table=houseToRack([3.35,4.45,0]);box([2100,1000,32],[table[0],table[1],GROUND+734],wood,context);
  for(const x of [-880,880])for(const y of [-350,350])box([65,65,718],[table[0]+x,table[1]+y,GROUND+359],wood,context);
  const light=new DirectionalLight(0xe1eaff,.7);light.position.set(3300,-1700,3500);light.target.position.set(400,-1200,0);root.add(light,light.target);return root;
}
