import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {test} from 'node:test';
import {validateBook,validateGlossary,validateChapter} from '../src/validate.js';
import {markup} from '../src/markup.js';
import {localizeChapter} from '../src/localize.js';
const read = p => JSON.parse(readFileSync(new URL(`fixtures/content/epictetus/${p}`,import.meta.url)));
const chapter=read('handbook/001.json'), book=read('book.json'), glossary=read('glossary.json');
const options={book,glossary,path:'epictetus/handbook/001.json'};
// Authoring is a public boundary: invalid content must fail before publishing.
// Each mutation isolates a different authoring failure; render tests cannot own it.
test('fixture satisfies the schema',()=>{validateBook(book);validateGlossary(glossary);assert.doesNotThrow(()=>validateChapter(chapter,options));});
const cases = [
 ['unknown field',c=>c.extra=1,/unknown field/],
 ['missing field',c=>delete c.title,/missing field/],
 ['book path',c=>c.book='other',/path mismatch/],
 ['work path',c=>c.work='fragments',/path mismatch/],
 ['part path',c=>c.part=1,/path mismatch/],
 ['chapter path',c=>c.chapter=2,/path mismatch/],
 ['section sequence',c=>c.sections[1].n=3,/section numbers/],
 ['paragraph order',c=>c.sections[4].para=1,/para/],
 ['missing plain version',c=>delete c.sections[0].modern,/missing field modern/],
 ['art without alt',c=>c.art={caption:'A jug.'},/missing field alt/],
 ['art with an unknown field',c=>c.art={alt:'Wood engraving of a jug.',src:'jug.png'},/unknown field src/],
 ['art alt that does not say what is drawn',c=>c.art={alt:'A jug on a table.'},/Wood engraving of/],
 ['art caption too long',c=>c.art={alt:'Wood engraving of a jug.',caption:'A plain earthenware jug that stands much too near the edge of the table.'},/at most 60 characters/],
 ['art caption quoting',c=>c.art={alt:'Wood engraving of a jug.',caption:'‘This is a jug.’'},/no quotation/],
 ['art caption with HTML',c=>c.art={alt:'Wood engraving of a jug.',caption:'A <b>jug</b>.'},/HTML tags/],
 ['missing gloss',c=>c.sections[0].original+=' [[word|unknown]]',/unresolved gloss/],
 ['unused gloss',c=>c.glosses.unused={term:'word',plain:'A word.'},/unused gloss/],
 ['gloss outside original',c=>c.carry='[[word|opinion]]',/gloss outside/],
 ['duplicate gloss',c=>c.sections[1].original+=' [[opinion|opinion]]',/duplicate gloss/],
 ['straight quote',c=>c.carry='A "word".',/straight quotes/],
 ['straight apostrophe',c=>c.carry="Don't react.",/straight quotes/],
 ['double dash',c=>c.carry='Pause -- then act.',/ASCII punctuation/],
 ['three dots',c=>c.carry='Pause...',/ASCII punctuation/],
 ['double space',c=>c.carry='Pause  first.',/double spaces/],
 ['HTML',c=>c.carry='<b>Pause</b>',/HTML tags/],
 ['length',c=>c.carry='word '.repeat(16)+'word',/exceeds 16/],
 ['reference structure',c=>c.seeAlso[0].ref='handbook/54',/outside book/],
 ['inline reference structure',c=>c.questions[0]='Read ((handbook/54)).',/outside book/],
 ['unknown theme',c=>c.themes=['other'],/unknown theme/],
 ['banned phrase',c=>c.carry='Embrace timeless wisdom.',/banned phrase/],
 ['inline reference in original',c=>c.sections[0].original+=' ((handbook/2))',/cross-reference in original/],
 ['unknown exercise field',c=>c.exercises[0].extra='x',/unknown field/],
 ['unknown gloss field',c=>c.glosses.opinion={...glossary.terms.opinion,extra:'x'},/unknown field/],
 ['gloss length',c=>c.glosses.opinion={term:'opinion',plain:'word '.repeat(22)+'word'},/exceeds 22/],
 ['Greek pairing',c=>c.glosses.opinion={term:'opinion',plain:'A judgment.',greek:'ὑπόληψις'},/together/],
 ['setting length',c=>c.setting='word '.repeat(45)+'word',/exceeds 45/],
 ['stop rule length',c=>c.exercises[0].stopIf='word '.repeat(20)+'word',/exceeds 20/],
 ['objection length',c=>c.objection={says:'word '.repeat(30)+'word',reply:'A reply.'},/exceeds 30/],
];
for(const [name,change,message] of cases)test(`rejects ${name}`,()=>{const c=structuredClone(chapter);change(c);assert.throws(()=>validateChapter(c,options),message);});
test('a Russian overlay must mirror the English chapter, and its references still have to resolve',()=>{
 const ru=JSON.parse(readFileSync(new URL('./fixtures/content/epictetus/ru/handbook/001.json',import.meta.url)));
 const r=localizeChapter(chapter,ru,'ru/001');
 assert.equal(r.sections[0].original,ru.sections[0].text);assert.doesNotMatch(r.sections[0].modern,/\[\[/);
 for(const [k,g] of Object.entries(chapter.glosses))assert.equal(r.glosses[k].greek,g.greek);
 for(const [name,change,message] of [
  ['missing question',x=>x.questions.pop(),/expected \d+ items/],
  ['extra field',x=>x.note='Лишнее',/unknown field note/],
  ['empty text',x=>x.carry='',/expected Russian text/],
  ['renumbered section',x=>x.sections[0].n=9,/section numbers must match/],
 ]){const x=structuredClone(ru);change(x);assert.throws(()=>localizeChapter(chapter,x,'ru/001'),message,name);}
 const bad=structuredClone(r);bad.questions[0]='Что сказано в разделе 9 и почему это важно для тебя сегодня?';
 assert.throws(()=>validateChapter(bad,{...options,lang:'ru'}),/раздел.? 9" names a section/);
 bad.questions[0]='Чем это отличается от того, что сказано в главе 2, и чему ты веришь?';
 assert.throws(()=>validateChapter(bad,{...options,lang:'ru'}),/inline ref like/);
});
test('density and expansive plain text are warnings, not failures',()=>{
 const c=structuredClone(chapter);c.sections=[{n:1,para:1,original:'[[A|opinion]] [[B|impulse]] [[C|office]] [[D|slavish]] [[E|impression]].',modern:'This is a deliberately much longer plain version.'}];
 for(const k of ['questions','prompts','exercises','takeaway','carry','objection'])c[k]=JSON.parse(JSON.stringify(c[k]).replace(/\b[Ss]ections? \d+/g,'that passage'));
 const warnings=validateChapter(c,options);assert.equal(warnings.length,3);assert.ok(warnings.some(w=>w.includes('four glosses')));assert.ok(warnings.some(w=>w.includes('25 words')));assert.ok(warnings.some(w=>w.includes('1.3')));
});
test('inline rendering escapes literal HTML and resolves only loaded citations',()=>{
 assert.equal(markup('<img src=x> _care_'), '&lt;img src=x&gt; <i>care</i>');
 assert.equal(markup('((handbook/5))',{book}), 'Handbook 5');
 assert.match(markup('((handbook/2))',{book,loaded:new Set(['handbook/2'])}),/href="\/epictetus\/handbook\/2\/"/);
});
test('section references link to the original and must exist in the chapter',()=>{
 const secs=new Set([1,2,3,4]);
 assert.equal(markup('Section 4 says',{book,sections:secs}),'<a class="sref" href="#o4">Section 4</a> says');
 assert.equal(markup('sections 2 and 3',{book,sections:secs}),'<a class="sref" href="#o2">sections 2</a> and <a class="sref" href="#o3">3</a>');
 assert.equal(markup('Section 4 says',{book}),'Section 4 says');
 assert.equal(markup('Section 4 says',{book,sections:secs,original:true}),'Section 4 says');
 const c=structuredClone(chapter);c.questions[0]='Which part of section 99 matters here, and why does it matter to you today?';
 assert.throws(()=>validateChapter(c,options),/section 99" names a section/);
 const d=structuredClone(chapter);d.questions[0]='How does this differ from what he said in chapter 2, and which do you believe?';
 assert.throws(()=>validateChapter(d,options),/inline ref like/);
});
test('art is optional; alt alone, or alt with a caption or a null caption, is accepted',()=>{
 for(const art of [{alt:'Wood engraving of a jug on a table.'},{alt:'Wood engraving of a jug on a table.',caption:'A jug. Jugs break.'},{alt:'Wood engraving of a jug on a table.',caption:null}]){
  const c=structuredClone(chapter);c.art=art;assert.doesNotThrow(()=>validateChapter(c,options));
 }
});
// Boris shares the reader with friends: examples must be general, never drawn from one person's job or home lab.
test('personal and technical examples fail; the same words inside other words do not',()=>{
 for (const [k,v] of [['carry','Before the deploy today, ask what is yours.'],['carry','When the disk dies, ask what is yours.'],['carry','Перед релизом спроси себя, что твоё.']]) {
  const c=structuredClone(chapter);c[k]=v;assert.throws(()=>validateChapter(c,options),/personal or technical example/);
 }
 const c=structuredClone(chapter);c.carry='Give a plain description of the event before you react.';
 assert.doesNotThrow(()=>validateChapter(c,options));
});
