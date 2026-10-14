import { KIT_CARDS } from './retainers.js';
import { partsSheetHTML } from './parts.js';

export function createKitUI({root,player,timeline,viewer}) {
  const cards=document.createElement('div');cards.className='kit-cards';cards.hidden=true;root.appendChild(cards);
  const lines=document.createElementNS('http://www.w3.org/2000/svg','svg');lines.classList.add('kit-leaders');root.appendChild(lines);
  const entries=KIT_CARDS.map(card=>{
    const el=document.createElement('article');el.className=`kit-card kit-${card.kind}`;
    el.innerHTML=`<span class="kit-count">${card.quantity}×</span><strong>${card.name}</strong><span>${card.size}</span><a href="${card.source.url}" target="_blank" rel="noopener noreferrer">${card.source.shop} ↗</a>`;
    cards.appendChild(el);
    const line=document.createElementNS(lines.namespaceURI,'path'),dot=document.createElementNS(lines.namespaceURI,'circle');dot.setAttribute('r','3');lines.append(line,dot);
    return {card,el,line,dot};
  });
  const dialog=document.getElementById('partsSheet');dialog.innerHTML=partsSheetHTML();
  const button=document.getElementById('btnParts');
  button.addEventListener('click',()=>{player.pause();dialog.showModal();document.getElementById('closeParts').focus();});
  document.getElementById('closeParts').addEventListener('click',()=>dialog.close());
  dialog.addEventListener('click',e=>{if(e.target===dialog)dialog.close();});
  dialog.addEventListener('close',()=>button.focus());
  const chapter=timeline.chapters.find(c=>c.id==='retainer-kit');
  function update() {
    const active=player.time>=chapter.start&&player.time<chapter.end;
    cards.hidden=!active;lines.style.display=active?'block':'none';if(!active)return;
    const bounds=root.getBoundingClientRect();lines.setAttribute('viewBox',`0 0 ${bounds.width} ${bounds.height}`);
    for(const {card,el,line,dot} of entries) {
      const rect=el.getBoundingClientRect(),p=viewer.projectRackPoint(viewer.installation.anchor(card.anchor));
      const x=rect.left-bounds.left+rect.width/2,y=rect.bottom-bounds.top;
      line.setAttribute('d',`M ${x} ${y} L ${p.x} ${p.y}`);dot.setAttribute('cx',p.x);dot.setAttribute('cy',p.y);
      line.style.opacity=dot.style.opacity=p.visible?'1':'0';
    }
  }
  return {update};
}
