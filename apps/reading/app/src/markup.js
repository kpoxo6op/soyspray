export const escape = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
export const refOf = c => [c.work, c.part, c.chapter].filter(v => v !== null && v !== undefined).join('/');
export function citation(ref, book) {
  const [work, ...numbers] = ref.split('/');
  return `${book?.works.find(w => w.id === work)?.cite || ({handbook:'Handbook',discourses:'Discourses',fragments:'Fragment'}[work])} ${numbers.join('.')}`;
}
export const plain = text => text.replace(/\[\[([^|]+)\|[^\]]+\]\]/g, '$1').replace(/_([^_]+)_/g, '$1');
export const glossIds = text => [...text.matchAll(/\[\[([^|]+)\|([a-z0-9-]+)\]\]/g)].map(m => m[2]);
// "section 4", "sections 2 and 3" (or «раздел 4», «разделы 2 и 3») in a chapter's own apparatus become links to that section of the original.
export const sectionRefs = /(?<![\p{L}\d])([Ss]ections?|[Рр]аздел(?:ами|ах|ам|ов|ом|ы|е|а|у)?)\s+(\d+(?:(?:,\s*|\s+(?:and|or|и|или)\s+|\s*[–-]\s*)\d+)*)(?![\p{L}\d])/gu;
function linkSections(s, sections) {
  let out = '', at = 0;
  for (const m of s.matchAll(sectionRefs)) {
    out += escape(s.slice(at, m.index)); at = m.index + m[0].length;
    m[2].split(/(\d+)/).forEach((part, i) => {
      const label = i === 1 ? `${m[1]} ${part}` : part;
      out += /^\d+$/.test(part) && sections.has(+part) ? `<a class="sref" href="#o${part}">${escape(label)}</a>` : escape(label);
    });
  }
  return out + escape(s.slice(at));
}
export function markup(text, {book, loaded = new Set(), glosses = {}, original = false, lead = false, sections = null, ru = false} = {}) {
  const token = /\[\[([^|]+)\|([a-z0-9-]+)\]\]|_([^_]+)_|\(\(([a-z]+\/[0-9]+(?:\/[0-9]+)?)\)\)/g;
  let result = '', offset = 0;
  function literal(s, first) {
    if (lead && first && !text.startsWith('[[')) {
      const m = s.match(/^[\p{L}\p{N}’]+(?:\s+[\p{L}\p{N}’]+){0,3}/u);
      if (m) return `<span class="lead">${escape(m[0])}</span>${escape(s.slice(m[0].length))}`;
    }
    // Russian typesetting: a dash never starts a line, a one-letter word never ends one.
    if (ru) s = s.replace(/ —/g, '\u00a0—').replace(/(^|[\s\u00a0«(])([вкосуияаВКОСУИЯА]) /g, '$1$2\u00a0').replace(/(^|[\s\u00a0«(])([вкосуияаВКОСУИЯА]) /g, '$1$2\u00a0');
    return sections && !original ? linkSections(s, sections) : escape(s);
  }
  for (const m of text.matchAll(token)) {
    result += literal(text.slice(offset, m.index), offset === 0);
    if (m[1] && original && glosses[m[2]]) {
      const g = glosses[m[2]];
      result += `<a class="g" href="#w-${m[2]}">${escape(m[1])}</a><span class="mn" role="note"><i>${markup(g.term,{book,loaded})}</i> ${markup(g.plain,{book,loaded})}</span>`;
    } else if (m[3]) result += `<i>${escape(m[3])}</i>`;
    else if (m[4] && !original) result += loaded.has(m[4]) ? `<a href="${book.base || `/${escape(book.id)}/`}${m[4]}/">${escape(citation(m[4], book))}</a>` : escape(citation(m[4], book));
    else result += escape(m[0]);
    offset = m.index + m[0].length;
  }
  return result + literal(text.slice(offset), offset === 0);
}
