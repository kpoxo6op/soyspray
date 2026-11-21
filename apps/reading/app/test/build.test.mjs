import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFileSync,readdirSync,rmSync,cpSync,mkdirSync,writeFileSync} from 'node:fs';
import {join,dirname} from 'node:path';
import {fileURLToPath} from 'node:url';
import {gzipSync} from 'node:zlib';
import {test,after} from 'node:test';
import {build} from '../build.mjs';
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
 add('site.css',bytes('assets/site.css'),14*1024,4*1024);
 add('site.js + theme.js',Buffer.concat([bytes('assets/site.js'),bytes('assets/theme.js')]),10*1024,4*1024);
 rows.at(-1).gzip=gzipSync(bytes('assets/site.js'),{level:9}).length+gzipSync(bytes('assets/theme.js'),{level:9}).length;
 add('theme.js',bytes('assets/theme.js'),400);
 const fonts=files(join(out,'assets/fonts')).filter(p=>p.endsWith('.woff2'));assert.equal(fonts.length,3);
 add('Fonts (3)',Buffer.concat(fonts.map(p=>readFileSync(p))),80*1024);
 const first=gzipSync(bytes('epictetus/handbook/1/index.html')).length+gzipSync(bytes('assets/site.css')).length+gzipSync(bytes('assets/site.js')).length+gzipSync(bytes('assets/theme.js')).length+readFileSync(fonts.find(p=>p.includes('roman'))).length;
 rows.push({item:'Core visit (roman only)',bytes:first,gzip:first,budget:110*1024,gzipBudget:''});
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
 const content=join(app,'test/.route-content');cpSync(join(app,'test/fixtures/content'),content,{recursive:true});
 try {
  const c=JSON.parse(read(join(content,'epictetus/handbook/002.json')));
  for(const [work,part,titleBy,path] of [['discourses',1,'source','discourses/1/01.json'],['discourses',2,'source','discourses/2/01.json'],['fragments',null,'editor','fragments/01.json']]) {
   const pathOut=join(content,'epictetus',path);mkdirSync(dirname(pathOut),{recursive:true});
   writeFileSync(pathOut,JSON.stringify({...c,work,part,titleBy,chapter:1}));
  }
  build({content,out});
  const first=read(join(out,'epictetus/discourses/1/1/index.html')),last=read(join(out,'epictetus/discourses/2/1/index.html'));
  assert.match(first,/Chapter 1 of 30/);assert.match(first,/href="\/epictetus\/discourses\/2\/1\/" rel="next"/);
  assert.match(first,/Condensed as <a href="\/epictetus\/handbook\/1\/">Handbook 1/);
  assert.match(last,/href="\/epictetus\/" rel="next"/);
  assert.match(read(join(out,'epictetus/fragments/1/index.html')),/<title>Fragment 1/);
  assert.match(read(join(out,'epictetus/handbook/2/index.html')),/href="\/epictetus\/" rel="next"/);
  for(const p of htmls)assert.ok(readFileSync(p).length<150*1024);
  assert.ok(Buffer.byteLength(first)<150*1024);assert.ok(Buffer.byteLength(last)<150*1024);
 } finally {rmSync(content,{recursive:true,force:true});}
});
