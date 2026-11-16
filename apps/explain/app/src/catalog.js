// What both versions of the page share: ticks kept per guide in this browser, and the filter over the chapter list.
// The guides live on the same site, so the Pearl guide's own Done ticks (pearl.stage0.done) show here too.
import guides from '../data/guides.json';

export { guides };

export function loadTicks(key) {
  try {
    return new Set(JSON.parse(localStorage.getItem(key) || '[]'));
  } catch {
    return new Set();
  }
}

export function saveTicks(key, set) {
  try {
    localStorage.setItem(key, JSON.stringify([...set]));
  } catch {
    /* private window or blocked storage: ticks last for this visit only */
  }
}

export function createCatalog(root, { showMeter }) {
  const ticks = new Map(guides.map((g) => [g.slug, loadTicks(g.store)]));
  const rows = [...root.querySelectorAll('li[data-id]')];
  const lists = [...root.querySelectorAll('section.list')];
  const count = root.querySelector('[data-count]');
  const empty = root.querySelector('[data-empty]');
  const filter = { text: '', guide: 'all', hideDone: false };

  const isDone = (row) => ticks.get(row.dataset.guide).has(row.dataset.id);

  function apply() {
    const words = filter.text.toLowerCase().split(/\s+/).filter(Boolean);
    let shown = 0;
    for (const row of rows) {
      const hide =
        (filter.guide !== 'all' && row.dataset.guide !== filter.guide) ||
        (filter.hideDone && isDone(row)) ||
        !words.every((w) => row.dataset.words.includes(w));
      row.hidden = hide;
      // The agent bridge leaves out what the filter hides, as a screen reader does.
      row.toggleAttribute('data-agent-hidden', hide);
      if (!hide) shown++;
    }
    for (const list of lists) {
      const any = list.querySelector('li[data-id]:not([hidden])');
      list.hidden = !any;
      for (const h of list.querySelectorAll('h4')) {
        let el = h.nextElementSibling;
        h.hidden = !(el && el.querySelector('li:not([hidden])'));
      }
    }
    count.textContent = `${shown} ${shown === 1 ? 'chapter' : 'chapters'}`;
    empty.hidden = shown > 0;
  }

  function meters() {
    for (const g of guides) showMeter(g.slug, ticks.get(g.slug).size, g.chapters.length);
  }

  return {
    filter,
    isDone,
    setFilter(patch) {
      Object.assign(filter, patch);
      apply();
    },
    setDone(slug, id, done) {
      const set = ticks.get(slug);
      if (done) set.add(id);
      else set.delete(id);
      saveTicks(guides.find((g) => g.slug === slug).store, set);
      meters();
      if (filter.hideDone) apply();
    },
    start() {
      meters();
      apply();
    },
  };
}
