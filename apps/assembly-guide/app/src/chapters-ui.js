// The Chapters button lists every chapter by section; picking one jumps there. A link to
// `#<chapter id>` (say #crimp-plan) opens the guide at that chapter too.
import { formatTime } from './player.js';

const escape = (s) => s.replace(/[&<>"]/g, (ch) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[ch]);

export function createChaptersUI({ player, timeline }) {
  const dialog = document.getElementById('chaptersSheet');
  const button = document.getElementById('btnChapters');
  const pad = (n) => String(n).padStart(2, '0');
  const groups = [];
  for (const c of timeline.chapters) {
    if (c.section || !groups.length) groups.push({ title: c.section || 'Chapters', chapters: [] });
    groups.at(-1).chapters.push(c);
  }
  dialog.innerHTML = `<header><div><span class="sheet-eyebrow">SOYRACK · ${timeline.chapters.length} CHAPTERS</span><h2 id="chaptersTitle">Chapters</h2></div><button id="closeChapters" type="button" aria-label="Close chapter list">×</button></header>
    <div class="sheet-body">${groups.map((g) => `<h3>${escape(g.title)}</h3><ol class="chapter-list">${g.chapters.map((c) => `<li><a href="#${c.id}" data-index="${c.index}"><span class="cl-no">${pad(c.index + 1)}</span><span class="cl-title">${escape(c.title)}</span><span class="cl-time">${formatTime(c.start)}</span></a></li>`).join('')}</ol>`).join('')}</div>`;
  const links = [...dialog.querySelectorAll('a[data-index]')];
  const close = document.getElementById('closeChapters');

  button.addEventListener('click', () => {
    player.pause();
    const current = player.chapterIndex;
    for (const a of links) a.toggleAttribute('aria-current', Number(a.dataset.index) === current);
    dialog.showModal();
    const here = links[current];
    here.scrollIntoView({ block: 'center' });
    here.focus({ preventScroll: true });
  });
  dialog.addEventListener('click', (e) => {
    const a = e.target.closest('a[data-index]');
    if (a) {
      e.preventDefault();
      player.goToChapter(Number(a.dataset.index));
      dialog.close();
    } else if (e.target === dialog) dialog.close();
  });
  close.addEventListener('click', () => dialog.close());
  dialog.addEventListener('close', () => button.focus({ preventScroll: true }));
  return { open: () => button.click() };
}

/** The chapter a `#<chapter id>` link names, or null. */
export function chapterFromHash(timeline, hash) {
  const id = decodeURIComponent(hash.replace(/^#/, ''));
  return timeline.chapters.find((c) => c.id === id) || null;
}
