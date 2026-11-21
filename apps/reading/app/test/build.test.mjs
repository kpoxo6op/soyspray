import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFileSync,readdirSync,rmSync,cpSync,mkdirSync,writeFileSync} from 'node:fs';
import {join,dirname} from 'node:path';
import {fileURLToPath} from 'node:url';
import {gzipSync} from 'node:zlib';
import {test,after} from 'node:test';
import {build} from '../build.mjs';
import {chapterPage} from '../src/templates.js';
const app=fileURLToPath(new URL('../',import.meta.url)),out=join(app,'dist-test');
build({content:join(app,'test/fixtures/content'),out});
after(()=>rmSync(out,{recursive:true,force:true}));
const files=p=>readdirSync(p,{withFileTypes:true}).flatMap(d=>d.isDirectory()?files(join(p,d.name)):[join(p,d.name)]);
const htmls=files(out).filter(p=>p.endsWith('.html'));
const read=p=>readFileSync(p,'utf8');
const chapter=read(join(out,'epictetus/handbook/1/index.html'));
// Public rendered documents own the no-JS reading and navigation contracts.
// Validator tests cannot detect omissions or unsafe HTML introduced by templates.
test('Handbook 1 renders the complete paired document, margin notes and editorial sections',()=>{
 assert.equal((chapter.match(/<h1>/g)||[]).length,1);
 for(let n=1;n<=5;n++){
  assert.match(chapter,new RegExp(`id="o${n}"><a class="n" href="#m${n}"`));
  assert.match(chapter,new RegExp(`id="m${n}"><a class="n" href="#o${n}"`));
 }
 assert.equal((chapter.match(/class="mn" role="note"/g)||[]).length,8);
 for(const title of ['In plain English','The point','Questions','Practice','Write','Words in this chapter'])assert.ok(chapter.includes('>'+title+'</h2>'),title);
 assert.match(chapter,/class="o same" id="o3"/);assert.match(chapter,/class="o" id="o4"/);
 assert.match(chapter,/<span class="lead">Some things are<\/span>/);
 assert.match(chapter,/href="\/epictetus\/handbook\/2\/" rel="next"/);
 assert.doesNotMatch(chapter,/href="\/epictetus\/handbook\/5\//);
 assert.ok(chapter.includes('you’ll do nothing whatever against your will'));
 assert.ok(chapter.indexOf('id="o5"')<chapter.indexOf('id="m1"'));
});
const ruChapter=read(join(out,'ru/epictetus/handbook/1/index.html'));
test('the Russian chapter is the whole page in Russian, with Hard’s English only as the side-by-side column',()=>{
 assert.match(ruChapter,/<html lang="ru" data-alt="\/epictetus\/handbook\/1\/"/);
 for(const title of ['Главное','Вопросы','Практика','Напиши','Понятия главы'])assert.ok(ruChapter.includes('>'+title+'</h2>'),title);
 for(const title of ['The point','Questions','In plain English'])assert.ok(!ruChapter.includes('>'+title),title);
 for(let n=1;n<=5;n++){assert.match(ruChapter,new RegExp(`class="o[^"]*" id="o${n}"><a class="n" href="#m${n}"`));assert.match(ruChapter,new RegExp(`id="m${n}" lang="en">`));}
 assert.ok(ruChapter.includes('Одно зависит от нас'));assert.ok(ruChapter.includes('you’ll do nothing whatever against your will'));
 assert.match(ruChapter,/data-keep="1" aria-pressed="false">Отметить</);
 assert.match(ruChapter,/href="\/ru\/epictetus\/handbook\/2\/" rel="next"/);
 assert.match(ruChapter,/<a class="lang" href="\/epictetus\/handbook\/1\/" data-lang="en"/);
 assert.match(ruChapter,/data-of=" из "/);
});
test('every English page links its Russian twin, and the old inline Russian block and toggle are gone',()=>{
 for(const p of htmls.filter(p=>!p.includes('/ru/')&&!p.endsWith('404.html'))){
  const html=read(p),twin=html.match(/data-alt="([^"]+)"/)?.[1];assert.ok(twin,p);
  assert.ok(htmls.some(q=>q===join(out,twin.slice(1),'index.html')),`${p} → ${twin}`);
  assert.match(html,new RegExp(`<a class="lang" href="${twin}" data-lang="ru"`));
 }
 assert.doesNotMatch(read(join(out,'404.html')),/data-alt|class="lang"/);
 for(const html of [chapter,ruChapter])assert.doesNotMatch(html,/data-ru|class="russian"|Русский<\/span>/);
});
test('every internal href, asset and fragment resolves in the built output',()=>{
 for(const p of htmls){const html=read(p);for(const [,href]of html.matchAll(/(?:href|src)="([^"]+)"/g)){
  assert.ok(!/^[a-z]+:/i.test(href),`${p}: ${href}`);
  const [path,anchor]=href.split('#');let target=path?join(out,path.split('?')[0]):p;
  if(path?.endsWith('/'))target=join(target,'index.html');
  const body=readFileSync(target,'utf8');if(anchor)assert.ok(body.includes(`id="${anchor}"`),`${p}: ${href}`);
 }}
 for(const [,url]of read(join(out,'assets/site.css')).matchAll(/url\(([^)]+)\)/g))assert.ok(readFileSync(join(out,url)).length);
});
test('pages and assets meet the strict self-only CSP and content revision contract',()=>{
 for(const p of files(out).filter(p=>/\.(html|css|js)$/.test(p))){const body=read(p);assert.doesNotMatch(body,/https?:\/\//,p);if(p.endsWith('.html')){
  assert.doesNotMatch(body,/\sstyle\s*=|\son\w+\s*=/i,p);
  for(const [,attrs,content]of body.matchAll(/<script([^>]*)>([\s\S]*?)<\/script>/g)){assert.match(attrs,/src="\/assets\//);assert.equal(content,'');}
  for(const [,url,rev]of body.matchAll(/(?:src|href)="(\/assets\/[^?"]+)\?v=([0-9a-f]{16})"/g))assert.equal(createHash('sha256').update(readFileSync(join(out,url))).digest('hex').slice(0,16),rev);
 }}
 for(const p of files(join(out,'assets/fonts')).filter(p=>p.endsWith('.woff2')))assert.ok(p.includes('.'+createHash('sha256').update(readFileSync(p)).digest('hex').slice(0,8)+'.'));
});
// Published bytes own the payload budget: source size does not protect delivery.
export function budgets(){
 const rows=[];const bytes=p=>readFileSync(join(out,p));
 const add=(name,b,max,gzmax)=>{rows.push({item:name,bytes:b.length,gzip:gzipSync(b,{level:9}).length,budget:max,gzipBudget:gzmax||''});};
 add('Handbook 1 HTML',bytes('epictetus/handbook/1/index.html'),30*1024);
 add('site.css',bytes('assets/site.css'),15.5*1024,4.3*1024);
 add('site.js + theme.js',Buffer.concat([bytes('assets/site.js'),bytes('assets/theme.js')]),10*1024,4.25*1024);
 rows.at(-1).gzip=gzipSync(bytes('assets/site.js'),{level:9}).length+gzipSync(bytes('assets/theme.js'),{level:9}).length;
 add('theme.js',bytes('assets/theme.js'),512);
 const fonts=files(join(out,'assets/fonts')).filter(p=>p.endsWith('.woff2'));assert.equal(fonts.length,5);
 const fontBytes=Buffer.concat(fonts.map(p=>readFileSync(p)));
 add('Fonts (5)',fontBytes,104*1024);
 const assets=['assets/site.css','assets/site.js','assets/theme.js'].reduce((n,p)=>n+gzipSync(bytes(p)).length,0);
 const first=assets+gzipSync(bytes('epictetus/handbook/1/index.html')).length+fontBytes.length;
 rows.push({item:'Russian visit (all five fonts)',bytes:first,gzip:first,budget:110*1024,gzipBudget:''});
 const english=assets+gzipSync(bytes('epictetus/handbook/2/index.html')).length+fonts.filter(p=>!p.includes('cyrillic')).reduce((n,p)=>n+readFileSync(p).length,0);
 rows.push({item:'English visit (three fonts)',bytes:english,gzip:english,budget:110*1024,gzipBudget:''});
 return rows;
}
test('chapter, stylesheet, script, font and first-visit budgets',()=>{
 const rows=budgets();console.table(rows);
 for(const r of rows){assert.ok(r.bytes<=r.budget,`${r.item}: ${r.bytes} > ${r.budget}`);if(r.gzipBudget)assert.ok(r.gzip<=r.gzipBudget,`${r.item} gzip: ${r.gzip} > ${r.gzipBudget}`);}
 for(const p of htmls.filter(p=>/\/handbook\/\d+\//.test(p)))assert.ok(readFileSync(p).length<=30*1024,p);
});

// Real routes own work boundaries: the Handbook must not chain into Discourses,
// while Discourses navigation crosses its numbered books. The Handbook golden
// case cannot exercise either branch of that contract.
test('Discourses and Fragments build from the schema and preserve work boundaries',()=>{
 const content=join(app,'test/.route-content');cpSync(join(app,'test/fixtures/content'),content,{recursive:true});rmSync(join(content,'epictetus/ru'),{recursive:true,force:true});
 try {
  const c=JSON.parse(read(join(content,'epictetus/handbook/002.json')));
  for(const [work,part,titleBy,path] of [['discourses',1,'source','discourses/1/01.json'],['discourses',2,'source','discourses/2/01.json'],['fragments',null,'editor','fragments/01.json']]) {
   const pathOut=join(content,'epictetus',path);mkdirSync(dirname(pathOut),{recursive:true});
   writeFileSync(pathOut,JSON.stringify({...c,work,part,titleBy,chapter:1}));
  }
  const out=join(app,'dist-test-routes');build({content,out});
  const first=read(join(out,'epictetus/discourses/1/1/index.html')),last=read(join(out,'epictetus/discourses/2/1/index.html'));
  assert.match(first,/Chapter 1 of 30/);assert.match(first,/href="\/epictetus\/discourses\/2\/1\/" rel="next"/);
  assert.match(first,/Condensed as <a href="\/epictetus\/handbook\/1\/">Handbook 1/);
  assert.match(last,/href="\/epictetus\/" rel="next"/);
  assert.match(read(join(out,'epictetus/fragments/1/index.html')),/<title>Fragment 1/);
  assert.match(read(join(out,'epictetus/handbook/2/index.html')),/href="\/epictetus\/" rel="next"/);
  for(const p of files(out).filter(p=>p.endsWith('.html')))assert.ok(readFileSync(p).length<150*1024);
  assert.ok(Buffer.byteLength(first)<150*1024);assert.ok(Buffer.byteLength(last)<150*1024);
 } finally {rmSync(content,{recursive:true,force:true});rmSync(join(app,'dist-test-routes'),{recursive:true,force:true});}
});
// The published site owns the illustration contract: a reserved box, both formats, real hashed files within budget.
test('declared art renders one lazy tailpiece after the text; its files exist, match their hashes and fit the budgets',()=>{
 const live=join(app,'dist-test-art');
 try{
  build({out:live});
  const limits={480:20,960:40,1440:70};let figures=0;
  for(const p of files(join(live,'epictetus/handbook')).filter(p=>p.endsWith('.html'))){
   const html=read(p),json=JSON.parse(read(join(app,'content/epictetus/handbook',p.match(/handbook\/(\d+)\//)[1].padStart(3,'0')+'.json')));
   const found=html.match(/<figure class="art">[\s\S]*?<\/figure>/g)||[];
   assert.equal(found.length,json.art?1:0,p);if(!json.art)continue;figures++;
   const fig=found[0];
   assert.ok(html.indexOf('id="plain"')<html.indexOf(fig)&&html.indexOf(fig)<html.indexOf('id="h-point"'),p);
   assert.match(fig,/<source type="image\/avif" srcset="[^"]+" sizes="[^"]+"><img src="[^"]+-960x\d+\.[0-9a-f]{8}\.webp" srcset=/);
   assert.match(fig,/ loading="lazy" decoding="async">/);assert.ok(fig.includes(`alt="${json.art.alt}"`));
   if(json.art.caption)assert.ok(fig.includes(`<figcaption>${json.art.caption}</figcaption>`));
   const [,w,h]=fig.match(/ width="(\d+)" height="(\d+)"/),urls=[...fig.matchAll(/(\/assets\/art\/[^ "]+) (\d+)w/g)];
   assert.equal(urls.length,6);assert.equal(w,'960');
   for(const [,url,width] of urls){
    const body=readFileSync(join(live,url)),[,fw,fh,rev]=url.match(/-(\d+)x(\d+)\.([0-9a-f]{8})\.(?:avif|webp)$/);
    assert.equal(fw,width);assert.ok(Math.abs(fh/fw-h/w)<.01,url);
    assert.equal(createHash('sha256').update(body).digest('hex').slice(0,8),rev);
    assert.ok(body.length<=limits[width]*1024,`${url}: ${body.length}`);
   }
  }
  assert.ok(figures>0);
 } finally {rmSync(live,{recursive:true,force:true});}
 assert.doesNotMatch(chapter,/class="art"/);
});
test('a chapter that declares art without its six files fails the build',()=>{
 const content=join(app,'dist-test-content-art'),empty=join(app,'dist-test-no-art');
 try{
  cpSync(join(app,'test/fixtures/content'),content,{recursive:true});rmSync(join(content,'epictetus/ru'),{recursive:true,force:true});mkdirSync(empty,{recursive:true});
  const p=join(content,'epictetus/handbook/001.json'),c=JSON.parse(read(p));c.art={alt:'Wood engraving of a boat.'};writeFileSync(p,JSON.stringify(c));
  assert.throws(()=>build({content,out:join(app,'dist-test-art-out'),art:empty}),/art needs handbook-001 at 480, 960 and 1440/);
 } finally {for(const d of [content,empty,join(app,'dist-test-art-out')])rmSync(d,{recursive:true,force:true});}
});
