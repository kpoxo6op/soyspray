import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {runInNewContext} from 'node:vm';
import {frame} from '../src/templates.js';
const script=readFileSync(new URL('../src/site.js',import.meta.url),'utf8');
const theme=readFileSync(new URL('../src/theme.js',import.meta.url),'utf8');
const html=frame({title:'Test',body:'',assets:{}});
const labels=Object.fromEntries([...html.match(/<span id="labels"[^>]+>/)[0].matchAll(/data-([a-z-]+)="([^"]*)"/g)].map(([,k,v])=>[k.replace(/-([a-z])/g,(_,c)=>c.toUpperCase()),v]));
// The browser storage/event boundary owns persistence. Rendering and validator
// tests cannot catch a stale import overwriting writing or a blocked save crash.
function browser(page='chapter',initial={},blocked=false){
 const data=new Map(Object.entries(initial)),timers=new Map(),events={},nodes={},callbacks={};let serial=0;
 function element(tag='div'){
  const n={tagName:tag.toUpperCase(),dataset:{},children:[],attributes:{},hidden:false,value:'',textContent:'',
   append(...xs){this.children.push(...xs)},replaceChildren(...xs){this.children=xs},
   setAttribute(k,v){this.attributes[k]=String(v)},removeAttribute(k){delete this.attributes[k]},
   focus(){doc.activeElement=this},setSelectionRange(a,b){this.selectionStart=a;this.selectionEnd=b},
   remove(){},click(){},querySelector(s){return this.select?.[s]||null},querySelectorAll(){return []},
   cloneNode(){return {...this}},closest(){return null}};
  const classes=new Set();n.classList={add:x=>classes.add(x),remove:x=>classes.delete(x),contains:x=>classes.has(x)};return n;
 }
 for(const id of ['labels','sheet','saved'])nodes['#'+id]=element();nodes['#labels'].dataset=labels;
 nodes['#sheet'].select=Object.fromEntries(['.sheet-keep','.t','.d','.why','.close'].map(k=>[k,element('button')]));
 nodes['.disp']=element();nodes['meta[name="theme-color"]']=element();
 if(page==='chapter'){nodes['#notes']=element('textarea');nodes['#done']=element('input');}
 if(page==='notes')for(const id of ['entries','export','erase','erase-no','erase-yes','confirm-erase','message','import'])nodes['#'+id]=element();
 const doc={documentElement:{dataset:{theme:'auto',size:'0',view:'stacked',ru:'on'}},body:{dataset:{book:'epictetus',ref:page==='chapter'?'handbook/1':'',page},append(){}},createElement:element,createTextNode:t=>({textContent:t}),querySelector:s=>nodes[s]||null,querySelectorAll:()=>[]};
 const storage={get length(){if(blocked)throw Error('blocked');return data.size},getItem(k){if(blocked)throw Error('blocked');return data.get(k)??null},setItem(k,v){if(blocked)throw Error('blocked');data.set(k,v)},removeItem(k){if(blocked)throw Error('blocked');data.delete(k)},key:i=>[...data.keys()][i]};
 runInNewContext(script,{document:doc,localStorage:storage,window:{},innerWidth:1440,matchMedia:()=>({addEventListener(){}}),getComputedStyle:()=>({getPropertyValue:()=> '#FBFBF8'}),addEventListener:(k,f)=>events[k]=f,setTimeout:f=>{timers.set(++serial,f);return serial},clearTimeout:i=>timers.delete(i),Blob,URL,location:{},console});
 return {nodes,data,doc,events,flush(){for(const f of timers.values())f();timers.clear()},async import(v){const target={files:[{text:async()=>JSON.stringify(v)}],value:'file'};await nodes['#import'].onchange({target})}};
}
// The synchronous head script owns first-paint settings; rendered markup alone
// cannot catch a deferred or failed restoration that exposes hidden Russian.
test('head script restores Russian Off synchronously and defaults On with absent or blocked storage',()=>{
 for(const [storage,expected] of [[{'reading.ru':'off'},'off'],[{},'on'],[new Proxy({},{get(){throw Error('blocked')}}),'on']]){
  const document={documentElement:{dataset:{ru:'on'}}};
  runInNewContext(theme,{document,localStorage:storage});
  assert.equal(document.documentElement.dataset.ru,expected);
 }
});
// Display events and import/erase exercise the existing storage boundary for
// the new setting; build tests cannot detect lost preferences or import errors.
test('Russian Display control saves through settings and remains usable with blocked storage',()=>{
 for(const blocked of [false,true]){
  const b=browser('chapter',{},blocked);
  for(const value of ['off','on']){
   const button={dataset:{set:'ru',value},closest:s=>s==='button'?button:s==='.disp'?b.nodes['.disp']:null};
   b.doc.onclick({target:button});
   assert.equal(b.doc.documentElement.dataset.ru,value);
   if(!blocked){assert.equal(b.data.get('reading.ru'),value);assert.ok(JSON.parse(b.data.get('reading.updated')).ru>0)}
  }
  if(blocked)assert.equal(b.data.size,0);
 }
});
test('Russian preference imports with timestamps and resets to On when data is erased',async()=>{
 const b=browser('notes',{'reading.updated':'{"ru":20}'});
 await b.import({'reading.ru':'off','reading.updated':{ru:30}});
 assert.equal(b.doc.documentElement.dataset.ru,'off');assert.equal(b.data.get('reading.ru'),'off');
 await b.import({'reading.ru':'on','reading.updated':{ru:10}});
 assert.equal(b.doc.documentElement.dataset.ru,'off');
 await b.import({'reading.ru':'invalid','reading.updated':{ru:40}});
 assert.match(b.nodes['#message'].textContent,/Import failed/);
 b.nodes['#erase'].onclick();b.nodes['#erase-yes'].onclick();
 assert.equal(b.doc.documentElement.dataset.ru,'on');assert.equal(b.data.has('reading.ru'),false);
});
test('typing saves after debounce and pagehide flushes the final edit',()=>{
 const b=browser();b.nodes['#notes'].value='A first note';b.nodes['#notes'].oninput();assert.equal(b.data.size,0);b.flush();assert.equal(JSON.parse(b.data.get('reading.epictetus.notes.handbook/1')).text,'A first note');
 b.nodes['#notes'].value='Last edit';b.nodes['#notes'].oninput();b.events.pagehide();assert.equal(JSON.parse(b.data.get('reading.epictetus.notes.handbook/1')).text,'Last edit');assert.equal(b.nodes['#saved'].textContent,'Saved in this browser.');
});
test('read state changes only when the reader ticks and unticks the checkbox',()=>{
 const b=browser();assert.equal(b.data.has('reading.epictetus.done'),false);b.nodes['#done'].checked=true;b.nodes['#done'].onchange();assert.match(JSON.parse(b.data.get('reading.epictetus.done'))['handbook/1'],/^\d{4}-\d{2}-\d{2}$/);b.nodes['#done'].checked=false;b.nodes['#done'].onchange();assert.equal(JSON.parse(b.data.get('reading.epictetus.done'))['handbook/1'],null);
});
test('blocked storage keeps controls usable and never claims a successful save',()=>{
 const b=browser('chapter',{},true);b.nodes['#notes'].value='Unsaved';b.nodes['#notes'].oninput();assert.doesNotThrow(()=>b.flush());assert.notEqual(b.nodes['#saved'].textContent,'Saved in this browser.');b.doc.onkeydown({key:'t',target:{closest:()=>null}});assert.equal(b.doc.documentElement.dataset.theme,'light');assert.equal(b.data.size,0);
});
test('import preserves newer writing and positions, merges new entries and applies newer settings',async()=>{
 const b=browser('notes',{'reading.epictetus.notes.handbook/1':JSON.stringify({text:'Newer',t:20}),'reading.epictetus.pos':JSON.stringify({'handbook/1':{s:3,t:20}}),'reading.theme':'dark','reading.updated':JSON.stringify({theme:20})});
 await b.import({'reading.epictetus.notes.handbook/1':{text:'Older',t:10},'reading.epictetus.notes.handbook/2':{text:'Imported',t:30},'reading.epictetus.pos':{'handbook/1':{s:1,t:10},'handbook/2':{s:2,t:30}},'reading.theme':'paper','reading.updated':{theme:30}});
 assert.equal(JSON.parse(b.data.get('reading.epictetus.notes.handbook/1')).text,'Newer');assert.equal(JSON.parse(b.data.get('reading.epictetus.notes.handbook/2')).text,'Imported');assert.equal(JSON.parse(b.data.get('reading.epictetus.pos'))['handbook/1'].s,3);assert.equal(b.data.get('reading.theme'),'paper');
});
test('a malformed import is rejected before any writes, and other app keys are never imported',async()=>{
 const initial={'reading.epictetus.notes.handbook/1':JSON.stringify({text:'Keep',t:20})},b=browser('notes',initial);
 await b.import({'reading.epictetus.notes.handbook/1':{text:'Replace',t:30},'other.app':'bad'});assert.deepEqual(Object.fromEntries(b.data),initial);assert.match(b.nodes['#message'].textContent,/Import failed/);
});
test('erase requires the inline confirmation and preserves unrelated browser storage',()=>{
 const b=browser('notes',{'reading.epictetus.notes.handbook/1':'{"text":"Erase","t":1}','other.app':'keep'});b.nodes['#erase'].onclick();assert.ok(b.data.has('reading.epictetus.notes.handbook/1'));b.nodes['#erase-yes'].onclick();assert.deepEqual(Object.fromEntries(b.data),{'other.app':'keep'});
});
