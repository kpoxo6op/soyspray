import {createHash} from 'node:crypto';
import {existsSync,mkdirSync,readFileSync,readdirSync,writeFileSync,copyFileSync,rmSync} from 'node:fs';
import {resolve,dirname,join,relative,sep} from 'node:path';
import {fileURLToPath} from 'node:url';
import {validateBook,validateGlossary,validateChapter,validateAbout} from './src/validate.js';
import {refOf} from './src/markup.js';
import {chapterPage,otherPages,shelf,notFound} from './src/templates.js';
const app=dirname(fileURLToPath(import.meta.url));
const hash=b=>createHash('sha256').update(b).digest('hex');
const json=p=>{try{return JSON.parse(readFileSync(p,'utf8'));}catch(e){throw new Error(`${p}: ${e.message}`);}};
const files=p=>readdirSync(p,{withFileTypes:true}).flatMap(d=>d.isDirectory()?files(join(p,d.name)):[join(p,d.name)]);
export function build({content=join(app,'content'),out=join(app,'dist'),art=join(app,'art')}={}) {
 content=resolve(content);out=resolve(out);art=resolve(art);
 if(!existsSync(content))throw new Error(`Content directory does not exist: ${content}. Provide content/ or use --content test/fixtures/content.`);
 // Refuse recursive deletion outside a dedicated output directory in this app.
 const rel=relative(app,out);
 if(!rel || rel.startsWith('..'+sep) || rel==='..' || ['src','fonts','content','test','art'].includes(rel.split(sep)[0]) || content===out || content.startsWith(out+sep))throw new Error('Output must be a dedicated directory inside the app, outside source and content.');
 const library=json(join(content,'library.json'));
 if(!library || library.schema!==1 || !Array.isArray(library.books) || !library.books.length || Object.keys(library).some(k=>!['schema','books'].includes(k)) || new Set(library.books).size!==library.books.length || library.books.some(id=>typeof id!=='string'||!/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(id)))throw new Error('library.json: expected schema 1 and unique book ids in books');
 const books=library.books.map(id=>{
  const dir=join(content,id),book=json(join(dir,'book.json')),glossary=json(join(dir,'glossary.json')),about=json(join(dir,'about.json'));
  validateBook(book,id);validateGlossary(glossary,book);
  validateAbout(about,book);
  const chapters=files(dir).filter(p=>p.endsWith('.json')&&!['book.json','glossary.json','about.json'].some(n=>p===join(dir,n))).map(p=>{
   const c=json(p);for(const w of validateChapter(c,{book,glossary,path:relative(content,p).split(sep).join('/')}))console.warn(`Warning: ${w}`);return c;
  }).sort((a,b)=>book.works.findIndex(w=>w.id===a.work)-book.works.findIndex(w=>w.id===b.work)||(a.part||0)-(b.part||0)||a.chapter-b.chapter);
  return {book,glossary,about,chapters};
 });
 rmSync(out,{recursive:true,force:true});mkdirSync(join(out,'assets/fonts'),{recursive:true});
 const assets={};
 for(const name of ['site.css','site.js','theme.js']){
  const body=readFileSync(join(app,'src',name));writeFileSync(join(out,'assets',name),body);assets[name]=`/assets/${name}?v=${hash(body).slice(0,16)}`;
 }
 const fonts=readdirSync(join(app,'fonts')).filter(n=>n.endsWith('.woff2'));
 const families=['roman','italic','greek','cyrillic','cyrillic-italic'];
 if(fonts.length!==families.length || families.some(f=>!fonts.some(n=>n.startsWith(`literata-${f}.`))))throw new Error('Expected Latin roman/italic, Greek and Cyrillic roman/italic Literata fonts');
 for(const name of fonts){const body=readFileSync(join(app,'fonts',name));if(!name.includes('.'+hash(body).slice(0,8)+'.'))throw new Error(`Font hash mismatch: ${name}`);copyFileSync(join(app,'fonts',name),join(out,'assets/fonts',name));if(name.startsWith('literata-roman.'))assets.roman=`/assets/fonts/${name}`;}
 copyFileSync(join(app,'fonts/OFL.txt'),join(out,'assets/fonts/OFL.txt'));
 // Illustrations are cut once by tools/art.py and committed; the build only checks, copies and sizes them.
 // A chapter that declares art must have all six files: three widths, AVIF and WebP, one shape.
 assets.art={};
 for(const {book,chapters} of books)for(const c of chapters.filter(c=>c.art)){
  const slug=[c.work,c.part,String(c.chapter).padStart(c.part===null?3:2,'0')].filter(x=>x!==null).join('-'),dir=join(art,book.id),set={avif:[],webp:[]};
  for(const name of existsSync(dir)?readdirSync(dir).sort():[]){
   const m=name.match(/^(.+)-(\d+)x(\d+)\.([0-9a-f]{8})\.(avif|webp)$/);if(!m||m[1]!==slug)continue;
   const body=readFileSync(join(dir,name));if(hash(body).slice(0,8)!==m[4])throw new Error(`Art hash mismatch: ${name}`);
   mkdirSync(join(out,'assets/art',book.id),{recursive:true});writeFileSync(join(out,'assets/art',book.id,name),body);
   set[m[5]].push({w:+m[2],h:+m[3],url:`/assets/art/${book.id}/${name}`});
  }
  for(const k of ['avif','webp'])set[k].sort((a,b)=>a.w-b.w);
  for(const k of ['avif','webp']){if(set[k].map(x=>x.w).join()!=='480,960,1440'||set[k].some(x=>Math.abs(x.h/x.w-set.webp[1]?.h/960)>.01))throw new Error(`${book.id}/${refOf(c)}: art needs ${slug} at 480, 960 and 1440 wide as AVIF and WebP in one shape`);}
  assets.art[`${book.id}/${refOf(c)}`]=set;
 }
 const pages={'/':shelf(books,assets),'/404.html':notFound(assets)};
 for(const data of books){Object.assign(pages,otherPages({...data,assets}));for(const c of data.chapters)pages[`/${data.book.id}/${refOf(c)}/`]=chapterPage(c,data.book,data.glossary,data.chapters,assets);}
 for(const [url,html] of Object.entries(pages)){const p=join(out,url.slice(1)+(url.endsWith('/')?'index.html':''));mkdirSync(dirname(p),{recursive:true});writeFileSync(p,html);}
 return {out,pages:Object.keys(pages).length};
}
if(process.argv[1] && resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 try{const options={};for(let i=2;i<process.argv.length;i+=2){const k=process.argv[i];if(!['--content','--out','--art'].includes(k)||!process.argv[i+1])throw new Error('Usage: node build.mjs [--content <dir>] [--out <dir>] [--art <dir>]');options[k.slice(2)]=process.argv[i+1];}const result=build(options);console.log(`Built ${result.pages} pages in ${result.out}`);}catch(e){console.error(e.message);process.exitCode=1;}
}
