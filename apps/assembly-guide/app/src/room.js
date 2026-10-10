import { Group, Mesh, BoxGeometry, CylinderGeometry, ExtrudeGeometry, Shape, Path, MeshStandardMaterial, DirectionalLight } from 'three';
import { RoundedBoxGeometry } from 'three/examples/jsm/geometries/RoundedBoxGeometry.js';
import { FLOOR_Z, HOUSE_FLOOR_Z as GROUND, ROOM, SERVICE, houseToRack } from './layout.js';
import { TV } from './wiring.js';

// Current-house cutaway and proposed console. Provisional dimensions are in README.
export function buildLivingRoom() {
  const root=new Group(),context=new Group();root.add(context);root.userData.context=context;
  const extension=new Group();root.add(extension);root.userData.extension=extension;
  const oak=new MeshStandardMaterial({color:0xb19272,roughness:.83}),wood=new MeshStandardMaterial({color:0x997754,roughness:.68});
  const cloth=new MeshStandardMaterial({color:0x797b7d,roughness:.97}),cushion=new MeshStandardMaterial({color:0xa09c97,roughness:.96});
  const wall=new MeshStandardMaterial({color:0xd7d5ce,roughness:1,transparent:true,opacity:.055,depthWrite:false});
  const white=new MeshStandardMaterial({color:0xcac7bf,roughness:.83}),strap=new MeshStandardMaterial({color:0x323d3d,roughness:.9}),metal=new MeshStandardMaterial({color:0x737d7e,roughness:.42,metalness:.55});
  function box(size,p,mat,parent=root) {
    const round=mat===cloth||mat===cushion;
    const o=new Mesh(round?new RoundedBoxGeometry(...size,3,Math.min(42,Math.min(...size)/4)):new BoxGeometry(...size),mat);
    o.position.set(...p);o.receiveShadow=true;o.castShadow=true;parent.add(o);return o;
  }
  for(let y=-3670;y<ROOM.wallY;y+=180)box([5600,178,12],[450,y+89,GROUND-6.4],oak,context);
  box([5600,16,70],[450,ROOM.wallY-8,GROUND+35],white,context);
  box([5600,60,1800],[450,ROOM.wallY+30,GROUND+900],wall,context);
  box([30,4000,70],[3250,-1570,GROUND+35],white,context);
  for(let y=-2940;y<=60;y+=1500)box([28,26,1900],[3250,y,GROUND+950],white,context);
  box([28,3026,26],[3250,-1440,GROUND+1900],white,context);
  const cabinet=new Group();root.add(cabinet);
  const cx=(TV.x0+TV.x1)/2,cy=(TV.y0+TV.y1)/2;
  const top=new Shape();top.moveTo(TV.x0,TV.y0);top.lineTo(440,TV.y0);top.lineTo(440,TV.y1);top.lineTo(TV.x0,TV.y1);top.closePath();
  const hole=new Path();hole.absarc(...SERVICE.hole,SERVICE.holeRadius,0,Math.PI*2,true);top.holes.push(hole);
  const tm=new Mesh(new ExtrudeGeometry(top,{depth:25,bevelEnabled:false,curveSegments:48}),wood);tm.position.z=TV.top-25;tm.castShadow=true;tm.receiveShadow=true;cabinet.add(tm);
  box([500,450,25],[190,cy,SERVICE.floor-12.5],wood,cabinet);
  box([1300,450,25],[1090,cy,TV.top-12.5],wood,extension);
  box([1300,450,25],[1090,cy,SERVICE.floor-12.5],wood,extension);
  for(const x of [TV.x0+12.5,427.5])box([25,450,350],[x,cy,-218],wood,cabinet);
  for(const x of [TV.x0+65,427.5,TV.x1-65])for(const y of [TV.y0+55,TV.y1-55])box([38,38,100],[x,y,GROUND+50],wood,x>440?extension:cabinet);
  // No back panel in the service bay. No power-board daisy chain.
  box([1265,420,25],[1095,cy,-205],wood,extension);
  box([25,450,350],[TV.x1-12.5,cy,-218],wood,extension);
  const door=new Group();door.position.set(-35,TV.y0-1,-218);root.add(door);root.userData.door=door;
  for(let x=8;x<445;x+=20)box([12,18,334],[x,0,0],wood,door);
  box([445,20,15],[222.5,0,-166],wood,door);box([445,20,15],[222.5,0,166],wood,door);box([8,25,50],[417,-13,0],metal,door);
  const boardBands=new Group(),brickBands=new Group();root.add(boardBands,brickBands);root.userData.boardBands=boardBands;root.userData.brickBands=brickBands;
  // Cleat attaches to the floor and end panel; its face supports the photographed board.
  box([155,15,300],[337.5,370,-243],wood);
  for(const z of [-342,-108]) {
    box([96,12,3],[310,332,z],strap,boardBands);box([3,44,12],[262,348,z],strap,boardBands);box([3,44,12],[358,348,z],strap,boardBands);
    for(const x of [262,358])box([16,3,16],[x,361,z],metal);
  }
  for(const [x,y,z] of [[65,120,-155],[175,120,-155],[285,120,-155],[65,268,-60],[175,340,-60]]) {
    box([25,25,3],[x,y,-44.5],metal);box([10,2,Math.max(4,-46-z)],[x,y+19,(-46+z)/2],strap);box([10,27,3],[x,y+8,z-2],metal);
    const screw=new Mesh(new CylinderGeometry(2.5,2.5,2,12),metal);screw.rotation.x=Math.PI/2;screw.position.set(x,y,-46);root.add(screw);
  }
  for(const x of [65,175,285]) {
    box([42,72,1.2],[x,150,SERVICE.floor+.6],strap);box([55,12,2],[x,150,-348.8],strap,brickBands);
    for(const dx of [-27,27])box([2,12,43],[x+dx,150,-371.5],strap,brickBands);
    for(const dx of [-32,32])box([14,18,2],[x+dx,150,SERVICE.floor+1],metal);
  }
  for(const y of [12,197])box([192,12,1],[126.5,y,FLOOR_Z+.5],strap);
  for(const x of [350,750,1150])box([20,12,12],[x,TV.y1-1,FLOOR_Z+6],metal,x>440?extension:root);
  for(const [x,z] of [[63,224],[158,227.5]]) {box([6,70,4],[x,215,z-23],metal);box([6,4,28],[x,189,z-10],metal);}
  const sofa=houseToRack([4.2,7.2,0]);
  box([2220,1110,260],[sofa[0],sofa[1],GROUND+240],cloth,context);box([2220,190,610],[sofa[0],sofa[1]-455,GROUND+540],cloth,context);
  for(const x of [sofa[0]-1010,sofa[0]+1010])box([200,1110,530],[x,sofa[1],GROUND+395],cloth,context);
  for(const x of [sofa[0]-455,sofa[0]+455]) {box([895,820,130],[x,sofa[1]+45,GROUND+435],cushion,context);const b=box([895,145,445],[x,sofa[1]-335,GROUND+705],cushion,context);b.rotation.x=-.09;}
  const foot=houseToRack([3.15,7.9,0]);box([1110,1100,350],[foot[0],foot[1],GROUND+235],cloth,context);box([1110,1100,100],[foot[0],foot[1],GROUND+460],cushion,context);
  const table=houseToRack([3.35,4.45,0]);box([2100,1000,32],[table[0],table[1],GROUND+734],wood,context);
  for(const x of [-880,880])for(const y of [-350,350])box([65,65,718],[table[0]+x,table[1]+y,GROUND+359],wood,context);
  const light=new DirectionalLight(0xe1eaff,.7);light.position.set(3300,-1700,3500);light.target.position.set(400,-1200,0);root.add(light,light.target);return root;
}
