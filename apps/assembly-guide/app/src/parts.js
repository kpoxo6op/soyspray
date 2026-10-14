import placements from '../data/placements.json' with { type: 'json' };
import { SOURCES, CHECKED, RETAINER_COUNTS } from './retainers.js';
import { PROVISIONAL } from './layout.js';

export const FASTENER_LINKS = {
  m3x12:'https://www.blacksfasteners.co.nz/ufhss0312',
  m3x16:'https://www.blacksfasteners.co.nz/ufhss0316',
  m4x12:'https://www.blacksfasteners.co.nz/ufhss0412',
  m3nut:'https://www.jaycar.co.nz/m3-steel-nuts-pack-of-25/p/HP0425',
};
export function partsList(data=placements) {
  const printed=Object.entries(data.instances.reduce((acc,p)=>{acc[p.part]=(acc[p.part]||0)+1;return acc;},{}))
    .map(([name,quantity])=>({name,quantity,detail:'Printed separately · RackStack mini',url:'https://github.com/jazwa/rackstack'}));
  const screws=Object.entries(data.screws.reduce((acc,p)=>{acc[p.type]=(acc[p.type]||0)+1;return acc;},{}))
    .map(([name,quantity])=>({name:name.replace('x',' × '),quantity,detail:'Flat-head socket screw · rack only',url:FASTENER_LINKS[name],shop:'Blacks Fasteners NZ'}));
  const nuts=[{name:'M3 hex nuts',quantity:60},{name:'M4 hex nuts',quantity:24}].map(p=>({...p,detail:'Captured in the printed rack · rack only',url:p.name.startsWith('M3')?FASTENER_LINKS.m3nut:'https://github.com/jazwa/rackstack',shop:p.name.startsWith('M3')?'Jaycar NZ':'RackStack specification'}));
  return {printed,fasteners:[...screws,...nuts],kit:[
    {name:'VELCRO® ONE-WRAP® rail ties',quantity:RETAINER_COUNTS.rail,source:SOURCES.ties},
    {name:'VELCRO® ONE-WRAP® coil keepers',quantity:RETAINER_COUNTS.keeper,source:SOURCES.ties},
    {name:'Magnet Source magnetic hooks',quantity:RETAINER_COUNTS.hook,source:SOURCES.hooks},
    {name:'Innova loose grip-mat pads',quantity:2,source:SOURCES.pads},
  ]};
}
const link=(url,label)=>`<a href="${url}" target="_blank" rel="noopener noreferrer">${label} ↗</a>`;
export function partsSheetHTML() {
  const parts=partsList();
  const row=p=>`<li><span class="part-qty">${p.quantity}×</span><div><strong>${p.name}</strong><p>${p.detail||p.source.size}</p>${p.source?link(p.source.url,p.source.shop)+' · checked '+CHECKED:link(p.url,p.shop||'RackStack specification')+' · checked '+CHECKED}</div></li>`;
  return `<header><div><span class="sheet-eyebrow">ASSEMBLY KIT</span><h2 id="partsTitle">Parts and where to buy</h2></div><button id="closeParts" type="button" aria-label="Close parts sheet">×</button></header>
    <div class="sheet-body"><p class="sheet-intro">Gravity, magnets and reusable hook-and-loop. No holes, screws, cuts or adhesive on the steel unit.</p>
    <h3>Retainer kit</h3><ul class="parts-list">${parts.kit.map(row).join('')}</ul>
    <p class="sheet-note">Buy ${Math.ceil((RETAINER_COUNTS.rail+RETAINER_COUNTS.keeper)/5)} packs of 5 ONE-WRAP ties and ${Math.ceil(RETAINER_COUNTS.hook/2)} packs of 2 hooks. One grip-mat roll makes both loose pads. Hook ratings depend on the steel face: test each with the cable load.</p>
    <p class="sheet-note">Walk-in alternative: ${link(SOURCES.walkIn.url,'Bunnings ONE-WRAP 13 × 200 mm, 60-pack')} · checked ${CHECKED}. Store stock needs checking.</p>
    <h3>Printed separately</h3><ul class="parts-list">${parts.printed.map(row).join('')}</ul>
    <h3>RackStack fasteners</h3><ul class="parts-list">${parts.fasteners.map(row).join('')}</ul><p class="sheet-note">Fasteners join the printed rack only. No new printed cable supports.</p>
    <h3>Provisional fit — measure first</h3><ul class="assumptions">${PROVISIONAL.map(s=>`<li>${s}</li>`).join('')}</ul>
    <p class="sheet-note">Rack footprint 253 × 209 mm; rear foot margin 30 mm. Zigbee spacing about 940 mm here, below 1 m. Shelf and bricks stay ventilated; the powerline adapter stays directly in the wall socket.</p></div>`;
}
