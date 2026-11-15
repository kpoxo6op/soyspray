// Two panels: Chapters (with a Done tick each, shared with the catalog at explain.soyspray.vip/) and Words (every
// term the guide uses, in plain language). Ticks stay in this browser; the page works the same without storage.

import { WORDS } from './story.js';

export const DONE_KEY = 'explain.network.done';

function load() {
  try {
    return new Set(JSON.parse(localStorage.getItem(DONE_KEY) || '[]'));
  } catch {
    return new Set();
  }
}
function save(set) {
  try {
    localStorage.setItem(DONE_KEY, JSON.stringify([...set]));
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
  const done = load();
  const dialogs = { chapters: root.querySelector('#chaptersSheet'), words: root.querySelector('#wordsSheet') };
  const mins = (c) => Math.max(1, Math.round((c.end - c.start) / 60));

  const items = timeline.chapters
    .map(
      (c) => `<li class="chap${done.has(c.id) ? ' is-done' : ''}">
        <button class="chap-go" type="button" data-go="${c.index}"><span class="chap-no">${c.index + 1}</span><span class="chap-title">${esc(c.title)}</span><span class="chap-goal">${esc(c.goal)}</span><span class="chap-work">${mins(c)} min${c.index >= 11 ? ' · proposal' : ''}</span></button>
        <label class="tick"><input type="checkbox" data-done="${c.id}"${done.has(c.id) ? ' checked' : ''}><span>Done</span></label>
      </li>`,
    )
    .join('');
  shell(
    dialogs.chapters,
    'Your home network, explained',
    `<p class="lede">How your network is set up today, then what subnets, firewall rules and monitoring could add. Chapters 1 to 11 describe what is there now; 12 to 16 are ideas.</p><ol class="chaps">${items}</ol>`,
  );
  dialogs.chapters.querySelectorAll('[data-go]').forEach((b) =>
    b.addEventListener('click', () => {
      player.goToChapter(Number(b.dataset.go));
      dialogs.chapters.close();
    }),
  );
  dialogs.chapters.querySelectorAll('[data-done]').forEach((box) =>
    box.addEventListener('change', () => {
      if (box.checked) done.add(box.dataset.done);
      else done.delete(box.dataset.done);
      save(done);
      box.closest('.chap').classList.toggle('is-done', box.checked);
    }),
  );

  shell(
    dialogs.words,
    'Words',
    `<p class="lede">Every term the guide uses, in the order it comes up.</p><dl class="words">${WORDS.map(([t, d]) => `<div class="word"><dt>${esc(t)}</dt><dd>${esc(d)}</dd></div>`).join('')}</dl>`,
  );

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
  root.querySelector('#btnWords').addEventListener('click', () => open('words'));
  return { open, anyOpen: () => Object.values(dialogs).some((d) => d.open) };
}
