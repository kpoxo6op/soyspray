import { glossIds, plain } from './markup.js';
const id = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;
const banned = /\b(?:fast-paced world|timeless wisdom|ancient wisdom|journey|unlock|mindset|game-changer|dive in|deep dive|delve|resilience hack|level up|toolkit|navigate (?:life|challenges|complexities|relationships)|powerful insight|it[’']s important to note|in other words|at its core|simply put|let that sink in)\b/i;
const words = s => plain(s).trim().split(/\s+/u).filter(Boolean).length;
function fail(where, message) { throw new Error(`${where}: ${message}`); }
function shape(v, required, optional, where) {
  if (!v || typeof v !== 'object' || Array.isArray(v)) fail(where, 'expected an object');
  for (const k of required) if (!(k in v)) fail(where, `missing field ${k}`);
  for (const k of Object.keys(v)) if (![...required,...optional].includes(k)) fail(where, `unknown field ${k}`);
}
function text(v, where, max, original = false, nullable = false) {
  if (nullable && v == null) return;
  if (typeof v !== 'string' || !v.trim()) fail(where, 'expected nonempty text');
  if (/["']|--|\.\.\.| {2}|<\/?[a-z][^>]*>/i.test(v)) fail(where, 'straight quotes, ASCII punctuation, double spaces or HTML tags');
  if (banned.test(v)) fail(where, 'banned phrase');
  if (!original && /\[\[/.test(v)) fail(where, 'gloss outside original');
  if (original && /\(\(/.test(v)) fail(where, 'cross-reference in original');
  if (max && words(v) > max) fail(where, `exceeds ${max} words`);
}
function list(v, min, max, where) {
  if (!Array.isArray(v) || v.length < min || v.length > max) fail(where, `expected ${min}–${max} items`);
}
function identifier(v, where) { if (typeof v !== 'string' || !id.test(v)) fail(where, 'invalid id'); }
export function validRef(ref, book) {
  if (typeof ref !== 'string' || !/^[a-z0-9-]+\/[1-9]\d*(?:\/[1-9]\d*)?$/.test(ref)) return false;
  const [w,a,b] = ref.split('/'); const work = book.works.find(x => x.id === w);
  if (!work) return false;
  if (work.parts) return b !== undefined && +a <= work.parts.length && +b <= work.parts[+a-1];
  return b === undefined && (work.chapters === null || +a <= work.chapters);
}
export function validateBook(book, expectedId = book?.id) {
  shape(book,['schema','id','author','volume','translator','works','themes'],[],'book');
  if (book.schema !== 1 || book.id !== expectedId) fail('book','schema or directory mismatch');
  identifier(book.id,'book.id');
  for (const k of ['author','volume','translator']) text(book[k],`book.${k}`);
  list(book.works,1,100,'works'); const ids = new Set();
  for (const w of book.works) {
    shape(w,['id','title','cite','parts'],['chapters'],'work'); identifier(w.id,'work.id');
    if (ids.has(w.id)) fail('work','duplicate id'); ids.add(w.id);
    text(w.title,'work.title'); text(w.cite,'work.cite');
    if (w.parts !== null) { list(w.parts,1,4,'parts'); if (w.parts.some(n => !Number.isInteger(n) || n < 1)) fail('parts','invalid counts'); }
    else if (!('chapters' in w) || (w.chapters !== null && (!Number.isInteger(w.chapters) || w.chapters < 1))) fail('work','invalid chapters');
  }
  list(book.themes,1,100,'themes'); const themes = new Set();
  for (const t of book.themes) {
    shape(t,['id','title','about'],[],'theme'); identifier(t.id,'theme.id');
    if (themes.has(t.id)) fail('theme','duplicate id'); themes.add(t.id);
    text(t.title,'theme.title'); text(t.about,'theme.about');
  }
}
export function validateGlossary(glossary, book) {
  shape(glossary,['terms'],[],'glossary');
  if (!glossary.terms || Array.isArray(glossary.terms) || typeof glossary.terms !== 'object') fail('glossary','expected terms');
  for (const [key,g] of Object.entries(glossary.terms)) { identifier(key,'glossary id'); gloss(g,`glossary.${key}`,true); }
  if (book) checkRefs(glossary,book,'glossary');
}
function gloss(g, where, shared) {
  shape(g,['term','plain'],['why','translit','greek','not',...(shared ? ['long','also'] : [])],where);
  text(g.term,where+'.term'); text(g.plain,where+'.plain',22);
  for (const [k,max] of [['why',30],['not',16],['long',120]]) if (k in g) text(g[k],where+'.'+k,max,false,true);
  if (Boolean(g.translit) !== Boolean(g.greek)) fail(where,'translit and greek must be together');
  for (const k of ['translit','greek']) if (g[k] != null) text(g[k],where+'.'+k);
  if (g.also !== undefined) { list(g.also,0,30,where+'.also'); g.also.forEach(s => text(s,where+'.also')); }
}
export function validateChapter(c, {book, glossary = {terms:{}}, path}) {
  const where = path || 'chapter', warnings = [];
  shape(c,['schema','book','work','part','chapter','title','titleBy','themes','sections','glosses','takeaway','carry','questions','exercises','prompts','seeAlso'],['setting','objection','compare'],where);
  if (c.schema !== 1) fail(where,'schema must be 1');
  const work = book.works.find(w => w.id === c.work);
  const expected = c.part === null ? `${c.book}/${c.work}/${String(c.chapter).padStart(c.work === 'handbook' ? 3 : 2,'0')}.json` : `${c.book}/${c.work}/${c.part}/${String(c.chapter).padStart(2,'0')}.json`;
  if (c.book !== book.id || !work || !Number.isInteger(c.chapter) || c.chapter < 1 || (path && path !== expected)) fail(where,'book/work/part/chapter path mismatch');
  if ((c.work === 'discourses' && (!Number.isInteger(c.part) || c.part < 1 || c.part > 4)) || (c.work !== 'discourses' && c.part !== null)) fail(where,'invalid part');
  const ref = [c.work,c.part,c.chapter].filter(x => x !== null).join('/');
  if (!validRef(ref,book)) fail(where,'chapter outside book structure');
  text(c.title,where+'.title');
  if (c.title.length > 60 || /[.]$/.test(c.title) || !/^\p{Lu}/u.test(c.title) || c.title === c.title.toUpperCase()) fail(where,'title must be sentence case, at most 60 characters, without a full stop');
  if (!['editor','source'].includes(c.titleBy) || (c.work === 'handbook' && c.titleBy !== 'editor') || (c.work === 'discourses' && c.titleBy !== 'source')) fail(where,'invalid titleBy');
  if ('setting' in c) text(c.setting,where+'.setting',45,false,true);
  list(c.themes,1,3,where+'.themes');
  for (const t of c.themes) if (!book.themes.some(x => x.id === t)) fail(where,'unknown theme');
  if (!c.glosses || Array.isArray(c.glosses) || typeof c.glosses !== 'object') fail(where,'invalid glosses');
  list(c.sections,1,79,where+'.sections'); let para = 1, total = 0, count = 0; const used = new Set();
  for (const [i,s] of c.sections.entries()) {
    shape(s,['n','para','original','modern'],[],where+'.sections');
    if (s.n !== i+1) fail(where,'section numbers must be 1…n');
    if (!Number.isInteger(s.para) || s.para < para || (i === 0 && s.para !== 1)) fail(where,'para must start at 1 and never decrease'); para = s.para;
    text(s.original,where+'.original',0,true); text(s.modern,where+'.modern');
    const ids = glossIds(s.original);
    if (/\[\[|\]\]/.test(s.original.replace(/\[\[[^|\[\]]+\|[a-z0-9-]+\]\]/g,''))) fail(where,'malformed gloss');
    for (const key of ids) {
      if (!(Object.hasOwn(c.glosses,key) || Object.hasOwn(glossary.terms,key))) fail(where,`unresolved gloss ${key}`);
      if (used.has(key)) fail(where,`duplicate gloss ${key}`); used.add(key);
    }
    count += ids.length; total += words(s.original);
    if (ids.length > 4) warnings.push(`${where} section ${s.n}: more than four glosses`);
    if (words(s.modern) > words(s.original)*1.3) warnings.push(`${where} section ${s.n}: modern exceeds 1.3 times original`);
  }
  if (count*25 > total) warnings.push(`${where}: more than one gloss per 25 words`);
  if (!c.glosses || Array.isArray(c.glosses) || typeof c.glosses !== 'object') fail(where,'invalid glosses');
  for (const [key,g] of Object.entries(c.glosses)) { identifier(key,where+'.glosses'); gloss(g,where+'.'+key,false); if (!used.has(key)) fail(where,`unused gloss ${key}`); }
  text(c.takeaway,where+'.takeaway',45); text(c.carry,where+'.carry',16);
  for (const [k,max] of [['takeaway',2],['carry',1]]) if ((c[k].match(/[.!?][’”]?(?:\s|$)/g)||[]).length > max) fail(where,`${k} exceeds ${max} sentences`);
  for (const [k,min,max] of [['questions',3,5],['prompts',2,3]]) { list(c[k],min,max,where+'.'+k); c[k].forEach(s => text(s,where+'.'+k)); }
  list(c.exercises,1,2,where+'.exercises');
  for (const e of c.exercises) { shape(e,['title','do','time','doneWhen'],['stopIf'],where+'.exercise'); for (const k of ['title','do','time','doneWhen']) text(e[k],where+'.exercise.'+k); if ('stopIf' in e) text(e.stopIf,where+'.stopIf',20,false,true); }
  if (c.objection != null) { shape(c.objection,['says','reply'],['open'],where+'.objection'); for (const [k,max] of [['says',30],['reply',90],['open',30]]) if (k in c.objection) text(c.objection[k],where+'.objection.'+k,max,false,k === 'open'); }
  list(c.seeAlso,0,4,where+'.seeAlso');
  for (const r of c.seeAlso) { shape(r,['ref','why'],['relation'],where+'.seeAlso'); if (!validRef(r.ref,book)) fail(where,'seeAlso ref outside book structure'); text(r.why,where+'.seeAlso.why'); if (r.relation && !['source','echo','contrast'].includes(r.relation)) fail(where,'invalid relation'); }
  if (c.compare != null) { list(c.compare,0,10,where+'.compare'); for (const r of c.compare) { shape(r,['n','by','text'],[],where+'.compare'); if (!Number.isInteger(r.n) || r.n < 1 || r.n > c.sections.length) fail(where,'invalid compare section'); text(r.by,where+'.compare.by'); text(r.text,where+'.compare.text'); } }
  checkRefs(c,book,where); return warnings;
}

function checkRefs(v,book,where) {
  if (typeof v === 'string') {
    for (const m of v.matchAll(/\(\((.*?)\)\)/g)) if (!validRef(m[1],book)) fail(where,'inline ref outside book structure');
  } else if (v && typeof v === 'object') Object.values(v).forEach(x=>checkRefs(x,book,where));
}
export function validateAbout(about,book) {
  shape(about,['schema','title','sections'],[],'about');
  if (about.schema !== 1) fail('about','schema must be 1');
  text(about.title,'about.title');list(about.sections,1,100,'about.sections');
  for (const s of about.sections) {
    shape(s,['title','paragraphs'],[],'about.section');text(s.title,'about.section.title');
    list(s.paragraphs,1,100,'about.paragraphs');s.paragraphs.forEach(p=>text(p,'about.paragraph'));
  }
  checkRefs(about,book,'about');
}
