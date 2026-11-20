export const escape = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
export const refOf = c => [c.work, c.part, c.chapter].filter(v => v !== null && v !== undefined).join('/');
export function citation(ref, book) {
  const [work, ...numbers] = ref.split('/');
  return `${book?.works.find(w => w.id === work)?.cite || ({handbook:'Handbook',discourses:'Discourses',fragments:'Fragment'}[work])} ${numbers.join('.')}`;
}
export const plain = text => text.replace(/\[\[([^|]+)\|[^\]]+\]\]/g, '$1').replace(/_([^_]+)_/g, '$1');
export const glossIds = text => [...text.matchAll(/\[\[([^|]+)\|([a-z0-9-]+)\]\]/g)].map(m => m[2]);
export function markup(text, {book, loaded = new Set(), glosses = {}, original = false, lead = false} = {}) {
  const token = /\[\[([^|]+)\|([a-z0-9-]+)\]\]|_([^_]+)_|\(\(([a-z]+\/[0-9]+(?:\/[0-9]+)?)\)\)/g;
  let result = '', offset = 0;
  function literal(s, first) {
    if (lead && first && !text.startsWith('[[')) {
      const m = s.match(/^[\p{L}\p{N}’]+(?:\s+[\p{L}\p{N}’]+){0,3}/u);
      if (m) return `<span class="lead">${escape(m[0])}</span>${escape(s.slice(m[0].length))}`;
    }
    return escape(s);
  }
  for (const m of text.matchAll(token)) {
    result += literal(text.slice(offset, m.index), offset === 0);
    if (m[1] && original && glosses[m[2]]) {
      const g = glosses[m[2]];
      result += `<a class="g" href="#w-${m[2]}">${escape(m[1])}</a><span class="mn" role="note"><i>${markup(g.term,{book,loaded})}</i> ${markup(g.plain,{book,loaded})}</span>`;
    } else if (m[3]) result += `<i>${escape(m[3])}</i>`;
    else if (m[4] && !original) result += loaded.has(m[4]) ? `<a href="/${escape(book.id)}/${m[4]}/">${escape(citation(m[4], book))}</a>` : escape(citation(m[4], book));
    else result += escape(m[0]);
    offset = m.index + m[0].length;
  }
  return result + literal(text.slice(offset), offset === 0);
}
