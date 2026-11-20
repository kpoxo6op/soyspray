import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {test} from 'node:test';
import {validateBook,validateGlossary,validateChapter} from '../src/validate.js';
import {markup} from '../src/markup.js';
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
test('density and expansive plain text are warnings, not failures',()=>{
 const c=structuredClone(chapter);c.sections=[{n:1,para:1,original:'[[A|opinion]] [[B|impulse]] [[C|office]] [[D|slavish]] [[E|impression]].',modern:'This is a deliberately much longer plain version.'}];
 const warnings=validateChapter(c,options);assert.equal(warnings.length,3);assert.ok(warnings.some(w=>w.includes('four glosses')));assert.ok(warnings.some(w=>w.includes('25 words')));assert.ok(warnings.some(w=>w.includes('1.3')));
});
test('inline rendering escapes literal HTML and resolves only loaded citations',()=>{
 assert.equal(markup('<img src=x> _care_'), '&lt;img src=x&gt; <i>care</i>');
 assert.equal(markup('((handbook/5))',{book}), 'Handbook 5');
 assert.match(markup('((handbook/2))',{book,loaded:new Set(['handbook/2'])}),/href="\/epictetus\/handbook\/2\/"/);
});
