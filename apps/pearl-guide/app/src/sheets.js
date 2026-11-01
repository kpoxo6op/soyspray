// The three panels: Chapters (the stage at a glance, with your progress), Kit (what to buy) and Files (what to
// print). Ticks are kept in this browser only; the page works the same when storage is blocked.

import { CHECKED, GROUPS, money, totals } from './kit.js';
import { PLATE_NOTE, SETTINGS, STL } from './files.js';

const KEY = { kit: 'pearl.stage0.kit', done: 'pearl.stage0.done' };

function load(key) {
  try {
    return new Set(JSON.parse(localStorage.getItem(key) || '[]'));
  } catch {
    return new Set();
  }
}
function save(key, set) {
  try {
    localStorage.setItem(key, JSON.stringify([...set]));
  } catch {
    /* private window or blocked storage: ticks last for this visit only */
  }
}

const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]);

function shell(dialog, title, body) {
  dialog.innerHTML = `<div class="sheet"><header class="sheet-head"><h2>${esc(title)}</h2><button class="sheet-close" type="button" aria-label="Close">Close</button></header><div class="sheet-body">${body}</div></div>`;
  dialog.querySelector('.sheet-close').addEventListener('click', () => dialog.close());
}

export function createSheets({ root, timeline, player, onOpen }) {
  const kitTicks = load(KEY.kit);
  const doneTicks = load(KEY.done);
  const dialogs = {
    chapters: root.querySelector('#chaptersSheet'),
    kit: root.querySelector('#kitSheet'),
    files: root.querySelector('#filesSheet'),
  };

  // ---------------------------------------------------------- chapters
  function renderChapters() {
    const items = timeline.chapters
      .map((c) => {
        const done = doneTicks.has(c.id);
        return `<li class="chap${done ? ' is-done' : ''}">
          <button class="chap-go" type="button" data-go="${c.index}"><span class="chap-no">${c.index + 1}</span><span class="chap-title">${esc(c.title)}</span><span class="chap-goal">${esc(c.goal)}</span><span class="chap-work">${esc(c.work)}</span></button>
          <label class="tick"><input type="checkbox" data-done="${c.id}"${done ? ' checked' : ''}><span>Done</span></label>
        </li>`;
      })
      .join('');
    shell(
      dialogs.chapters,
      'Stage 0: before the pod',
      `<p class="lede">Buy the tools, print Pearl’s pod, learn to solder and float your first orb. About three weeks with the post, and four evenings of work.</p><ol class="chaps">${items}</ol>`,
    );
    dialogs.chapters.querySelectorAll('[data-go]').forEach((b) =>
      b.addEventListener('click', () => {
        player.goToChapter(Number(b.dataset.go));
        dialogs.chapters.close();
      }),
    );
    dialogs.chapters.querySelectorAll('[data-done]').forEach((box) =>
      box.addEventListener('change', () => {
        if (box.checked) doneTicks.add(box.dataset.done);
        else doneTicks.delete(box.dataset.done);
        save(KEY.done, doneTicks);
        box.closest('.chap').classList.toggle('is-done', box.checked);
      }),
    );
  }

  // ---------------------------------------------------------- kit
  function renderKit() {
    const t = totals();
    const groups = GROUPS.map((g) => {
      const rows = g.items
        .map((i) => {
          const got = kitTicks.has(i.id);
          const price = i.price ? `${i.est ? 'about ' : ''}${money(i.price)}` : '';
          const where = i.url ? `<a href="${esc(i.url)}" target="_blank" rel="noopener">${esc(i.shop)}${i.code ? ` ${esc(i.code)}` : ''}</a>` : '';
          return `<li class="item${got ? ' is-got' : ''}"><label class="tick"><input type="checkbox" data-kit="${i.id}"${got ? ' checked' : ''}><span class="visually-hidden">Got it</span></label>
            <div class="item-main"><span class="item-name">${esc(i.name)}</span><span class="item-why">${esc(i.why)}</span></div>
            <div class="item-side"><span class="item-price">${price}</span>${where}</div></li>`;
        })
        .join('');
      const sub = t.by[g.id] ? `<span class="group-total">${g.items.some((i) => i.est) ? 'about ' : ''}${money(t.by[g.id])}</span>` : '';
      return `<section class="kgroup"><h3>${esc(g.title)}${sub}</h3><p class="group-when">${esc(g.when)}</p><ul class="items">${rows}</ul></section>`;
    }).join('');
    shell(
      dialogs.kit,
      'Kit for Stage 0',
      `<p class="lede">About ${money(Math.round(t.all / 10) * 10)} in all. The tools carry on through the whole build. Prices checked ${CHECKED}; AliExpress ones are typical asking prices.</p>${groups}`,
    );
    dialogs.kit.querySelectorAll('[data-kit]').forEach((box) =>
      box.addEventListener('change', () => {
        if (box.checked) kitTicks.add(box.dataset.kit);
        else kitTicks.delete(box.dataset.kit);
        save(KEY.kit, kitTicks);
        box.closest('.item').classList.toggle('is-got', box.checked);
      }),
    );
  }

  // ---------------------------------------------------------- files
  function renderFiles() {
    const rows = STL.map(
      (f) => `<li class="item"><div class="item-main"><span class="item-name">${esc(f.name)}${f.qty > 1 ? ` × ${f.qty}` : ''}</span><span class="item-why">${esc(f.note)} About ${f.grams} g each.</span></div>
        <div class="item-side"><a href="files/${esc(f.file)}" download>${esc(f.file)}</a></div></li>`,
    ).join('');
    const settings = SETTINGS.map(([k, v]) => `<div class="setting"><dt>${esc(k)}</dt><dd>${esc(v)}</dd></div>`).join('');
    shell(
      dialogs.files,
      'Files to print',
      `<p class="lede">Pearl v3.1’s printed parts, straight from the design model. ${esc(PLATE_NOTE)}</p>
       <section class="kgroup"><h3>Parts</h3><ul class="items">${rows}</ul></section>
       <section class="kgroup"><h3>Bambu Studio</h3><dl class="settings">${settings}</dl></section>`,
    );
  }

  renderChapters();
  renderKit();
  renderFiles();

  for (const d of Object.values(dialogs)) {
    d.addEventListener('click', (e) => {
      if (e.target === d) d.close(); // a click on the backdrop
    });
    d.addEventListener('close', () => onOpen?.(false));
  }
  const open = (name) => {
    for (const d of Object.values(dialogs)) if (d.open) d.close();
    dialogs[name].showModal();
    dialogs[name].querySelector('.sheet-body').scrollTop = 0;
    onOpen?.(true);
  };
  root.querySelector('#btnChapters').addEventListener('click', () => open('chapters'));
  root.querySelector('#crumbChapter').addEventListener('click', () => open('chapters'));
  root.querySelector('#btnKit').addEventListener('click', () => open('kit'));
  root.querySelector('#btnFiles').addEventListener('click', () => open('files'));
  return { open, anyOpen: () => Object.values(dialogs).some((d) => d.open) };
}
