// Russian overlays (content/<book>/ru/) carry only the words. They must mirror the English shape exactly,
// so a missing question or an extra exercise fails the build instead of silently showing English.
function fail(where, message) { throw new Error(`${where}: ${message}`); }
const isObject = v => v && typeof v === 'object' && !Array.isArray(v);
function mirror(en, ru, where, skip = []) {
  if (en === null || en === undefined) { if (ru !== null && ru !== undefined) fail(where, 'must be null like the English'); return; }
  if (typeof en === 'string') { if (typeof ru !== 'string' || !ru.trim()) fail(where, 'expected Russian text'); return; }
  if (Array.isArray(en)) {
    if (!Array.isArray(ru) || ru.length !== en.length) fail(where, `expected ${en.length} items like the English`);
    en.forEach((x, i) => mirror(x, ru[i], `${where}[${i}]`, skip)); return;
  }
  if (isObject(en)) {
    if (!isObject(ru)) fail(where, 'expected an object');
    const keys = Object.keys(en).filter(k => !skip.includes(k));
    for (const k of keys) if (!(k in ru)) fail(where, `missing field ${k}`);
    for (const k of Object.keys(ru)) if (!keys.includes(k)) fail(where, `unknown field ${k}`);
    for (const k of keys) mirror(en[k], ru[k], `${where}.${k}`, skip);
  }
}
const pick = (o, keys) => Object.fromEntries(keys.filter(k => k in o).map(k => [k, o[k]]));
const words = ['title','art','setting','takeaway','carry','questions','exercises','objection','prompts','compare'];

export function localizeBook(book, ru) {
  const where = 'ru/book.json';
  if (!isObject(ru) || ru.schema !== 1) fail(where, 'expected schema 1');
  mirror(pick(book, ['author','volume','translator']), pick(ru, ['author','volume','translator']), where);
  mirror(Object.fromEntries(book.works.map(w => [w.id, {title: w.title, cite: w.cite}])), ru.works, where + '.works');
  mirror(Object.fromEntries(book.themes.map(t => [t.id, {title: t.title, about: t.about}])), ru.themes, where + '.themes');
  for (const k of Object.keys(ru)) if (!['schema','author','volume','translator','works','themes'].includes(k)) fail(where, `unknown field ${k}`);
  return {...book, author: ru.author, volume: ru.volume, translator: ru.translator, base: `/ru/${book.id}/`,
    works: book.works.map(w => ({...w, ...ru.works[w.id]})), themes: book.themes.map(t => ({...t, ...ru.themes[t.id]}))};
}
export function localizeGlossary(glossary, ru) {
  const where = 'ru/glossary.json';
  if (!isObject(ru) || ru.schema !== 1 || Object.keys(ru).some(k => !['schema','terms'].includes(k))) fail(where, 'expected schema 1 and terms');
  mirror(glossary.terms, ru.terms, where + '.terms', ['translit','greek']);
  return {terms: Object.fromEntries(Object.entries(glossary.terms).map(([k, g]) => [k, {...g, ...ru.terms[k]}]))};
}
export function localizeAbout(about, ru) {
  mirror(about, ru, 'ru/about.json'); return ru;
}
// The Russian page reads the Russian text first and keeps Hard's English as the second text.
export function localizeChapter(c, ru, where) {
  if (!isObject(ru) || ru.schema !== 1) fail(where, 'expected schema 1');
  const allowed = ['schema','sections','glosses','seeAlso',...words];
  for (const k of Object.keys(ru)) if (!allowed.includes(k)) fail(where, `unknown field ${k}`);
  mirror(pick(c, words), pick(ru, words), where);
  mirror(c.sections.map(s => ({n: s.n, text: s.original})), ru.sections, where + '.sections');
  ru.sections.forEach((s, i) => { if (s.n !== c.sections[i].n) fail(where, 'section numbers must match the English'); });
  mirror(c.glosses, ru.glosses, where + '.glosses', ['translit','greek']);
  mirror(c.seeAlso.map(r => ({why: r.why})), ru.seeAlso, where + '.seeAlso');
  const plain = s => s.replace(/\[\[([^|]+)\|[^\]]+\]\]/g, '$1');
  return {...c, ...pick(ru, words),
    sections: c.sections.map((s, i) => ({...s, original: ru.sections[i].text, modern: plain(s.original)})),
    glosses: Object.fromEntries(Object.entries(c.glosses).map(([k, g]) => [k, {...g, ...ru.glosses[k]}])),
    seeAlso: c.seeAlso.map((r, i) => ({...r, why: ru.seeAlso[i].why}))};
}
