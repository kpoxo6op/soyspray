// The three panels: Chapters (the stage at a glance, with your progress), Kit (what to buy) and Files (what to
// print). Ticks are kept in this browser only; the page works the same when storage is blocked.

// Only the old Pearl origin may supply carried ticks. Panel keys are supplied by the page.
const KEY = { kit: 'pearl.stage0.kit', done: 'pearl.stage0.done' };

function load(key, fallback = new Set()) {
  try {
    return new Set(JSON.parse(localStorage.getItem(key) || '[]'));
  } catch {
    return new Set(fallback);
  }
}

// Merge this one change with the latest saved ticks, including changes from another page.
export function updateTick(key, id, checked, fallback) {
  const fresh = load(key, fallback);
  if (checked) fresh.add(id);
  else fresh.delete(id);
  save(key, fresh);
  return fresh;
}
function save(key, set) {
  try {
    localStorage.setItem(key, JSON.stringify([...set]));
  } catch {
    /* private window or blocked storage: ticks last for this visit only */
  }
}

/**
 * Ticks saved on the old pearl.soyspray.vip arrive once as ?carry={"pearl.stage0.done":[...]} from
 * public/moved.html. Merge them into this site's storage and drop the parameter from the address.
 */
export function adoptCarried(loc = window.location, hist = window.history) {
  const raw = new URLSearchParams(loc.search).get('carry');
  if (raw === null) return false;
  try {
    const data = JSON.parse(raw);
    for (const key of Object.values(KEY)) {
      const list = Array.isArray(data?.[key]) ? data[key].filter((v) => typeof v === 'string' && v.length <= 64).slice(0, 200) : [];
      if (!list.length) continue;
      const set = load(key);
      list.forEach((v) => set.add(v));
      save(key, set);
    }
  } catch {
    /* a damaged link carries nothing */
  }
  try {
    hist.replaceState(null, '', loc.pathname + loc.hash);
  } catch {
    /* some browsers refuse replaceState on file:// */
  }
  return true;
}

const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]);

function shell(dialog, title, body) {
  dialog.innerHTML = `<div class="sheet"><header class="sheet-head"><h2>${esc(title)}</h2><button class="sheet-close" type="button" aria-label="Close">Close</button></header><div class="sheet-body">${body}</div></div>`;
  dialog.querySelector('.sheet-close').addEventListener('click', () => dialog.close());
}

export function createSheets({ root, timeline, player, onOpen, keys, chapters, kit, files, carry }) {
  if (carry) adoptCarried();
  let kitTicks = kit ? load(keys.kit) : new Set();
  let doneTicks = load(keys.done);
  const dialogs = {
    chapters: root.querySelector('#chaptersSheet'),
    ...(kit ? { kit: root.querySelector('#kitSheet') } : {}),
    ...(files ? { files: root.querySelector('#filesSheet') } : {}),
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
      chapters.title,
      `<p class="lede">${esc(chapters.lede)}</p><ol class="chaps">${items}</ol>`,
    );
    dialogs.chapters.querySelectorAll('[data-go]').forEach((b) =>
      b.addEventListener('click', () => {
        player.goToChapter(Number(b.dataset.go));
        dialogs.chapters.close();
      }),
    );
    dialogs.chapters.querySelectorAll('[data-done]').forEach((box) =>
      box.addEventListener('change', () => {
        doneTicks = updateTick(keys.done, box.dataset.done, box.checked, doneTicks);
        syncTicks(dialogs.chapters, 'done', doneTicks, '.chap', 'is-done');
      }),
    );
  }

  // ---------------------------------------------------------- kit
  function renderKit() {
    const money = (n) => `$${n.toFixed(2).replace(/\.00$/, '')}`;
    const groups = kit.groups.map((g) => {
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
      const total = g.items.reduce((s, i) => s + (i.price || 0), 0);
      const sub = total ? `<span class="group-total">${g.items.some((i) => i.est) ? 'about ' : ''}${money(total)}</span>` : '';
      return `<section class="kgroup"><h3>${esc(g.title)}${sub}</h3><p class="group-when">${esc(g.when)}</p><ul class="items">${rows}</ul></section>`;
    }).join('');
    shell(
      dialogs.kit,
      kit.title,
      `<p class="lede">${esc(kit.lede)}</p>${kit.table ? renderTable(kit.table) : ''}${groups}`,
    );
    if (kit.table) wireTable(dialogs.kit);
    dialogs.kit.querySelectorAll('[data-kit]').forEach((box) =>
      box.addEventListener('change', () => {
        kitTicks = updateTick(keys.kit, box.dataset.kit, box.checked, kitTicks);
        syncTicks(dialogs.kit, 'kit', kitTicks, '.item', 'is-got');
      }),
    );
  }

  // ---------------------------------------------------------- what is what (a photo of the real kit)
  function renderTable(t) {
    const marks = t.marks
      .map((m) => `<button type="button" class="tmark" data-mark="${m.n}" style="left:${m.x}%;top:${m.y}%" aria-label="${m.n}: ${esc(m.name)}">${m.n}</button>`)
      .join('');
    const legend = t.groups
      .map((g) => {
        const rows = t.marks
          .filter((m) => m.group === g.id)
          .map((m) => `<li class="trow" data-row="${m.n}"><span class="tno">${m.n}</span><div class="item-main"><span class="item-name">${esc(m.name)}</span><span class="item-why">${esc(m.looks)} ${esc(m.use)}</span></div></li>`)
          .join('');
        return rows ? `<h4 class="tgroup">${esc(g.title)}</h4><ol class="items tlist">${rows}</ol>` : '';
      })
      .join('');
    const sort = t.sort
      ? `<figure class="tsort"><a href="${esc(t.sort.src)}" target="_blank" rel="noopener"><img src="${esc(t.sort.src)}" alt="${esc(t.sort.alt)}" width="860" height="2193" decoding="async"></a><figcaption class="group-when">${esc(t.sort.caption)}</figcaption></figure>`
      : '';
    return `<section class="kgroup ktable"><h3>${esc(t.title)}</h3>${sort}<p class="group-when">${esc(t.lede)}</p>
      <figure class="tphoto"><img src="${esc(t.src)}" alt="${esc(t.alt)}" width="640" height="1399" loading="lazy" decoding="async">${marks}</figure>
      ${legend}<p class="tmissing">${esc(t.missing)}</p></section>`;
  }
  // A tap on a number marks its row and a tap on a row marks its number, so the photo and the list point at each other.
  function wireTable(dialog) {
    const pick = (n, scrollTo) => {
      dialog.querySelectorAll('.tmark, .trow').forEach((el) => el.classList.toggle('is-on', (el.dataset.mark || el.dataset.row) === n));
      const target = dialog.querySelector(scrollTo === 'row' ? `[data-row="${n}"]` : `[data-mark="${n}"]`);
      target?.scrollIntoView({ block: 'center', behavior: 'smooth' });
    };
    dialog.querySelectorAll('.tmark').forEach((b) => b.addEventListener('click', () => pick(b.dataset.mark, 'row')));
    dialog.querySelectorAll('.trow').forEach((r) => r.addEventListener('click', () => pick(r.dataset.row, 'mark')));
  }

  // ---------------------------------------------------------- files
  function renderFiles() {
    const rows = files.parts.map(
      (f) => `<li class="item"><div class="item-main"><span class="item-name">${esc(f.name)}${f.qty > 1 ? ` × ${f.qty}` : ''}</span><span class="item-why">${esc(f.note)} About ${f.grams} g each.</span></div>
        <div class="item-side"><a href="files/${esc(f.file)}" download>${esc(f.file)}</a></div></li>`,
    ).join('');
    const settings = files.settings.map(([k, v]) => `<div class="setting"><dt>${esc(k)}</dt><dd>${esc(v)}</dd></div>`).join('');
    shell(
      dialogs.files,
      files.title,
      `<p class="lede">${esc(files.lede)}</p>
       <section class="kgroup"><h3>${esc(files.partsTitle)}</h3><ul class="items">${rows}</ul></section>
       <section class="kgroup"><h3>${esc(files.settingsTitle)}</h3><dl class="settings">${settings}</dl></section>`,
    );
  }

  renderChapters();
  if (kit) renderKit();
  if (files) renderFiles();

  function syncTicks(dialog, kind, ticks, row, className) {
    dialog.querySelectorAll(`[data-${kind}]`).forEach((box) => {
      box.checked = ticks.has(box.dataset[kind]);
      box.closest(row).classList.toggle(className, box.checked);
    });
  }
  window.addEventListener('storage', (event) => {
    if (event.storageArea !== localStorage) return;
    if (event.key === null || event.key === keys.done) {
      doneTicks = load(keys.done, doneTicks);
      syncTicks(dialogs.chapters, 'done', doneTicks, '.chap', 'is-done');
    }
    if (kit && (event.key === null || event.key === keys.kit)) {
      kitTicks = load(keys.kit, kitTicks);
      syncTicks(dialogs.kit, 'kit', kitTicks, '.item', 'is-got');
    }
  });

  for (const d of Object.values(dialogs)) {
    d.addEventListener('click', (e) => {
      if (e.target === d) d.close(); // a click on the backdrop
    });
    d.addEventListener('close', () => onOpen?.(false));
  }
  const open = (name) => {
    if (!dialogs[name]) return;
    for (const d of Object.values(dialogs)) if (d.open) d.close();
    dialogs[name].showModal();
    dialogs[name].querySelector('.sheet-body').scrollTop = 0;
    onOpen?.(true);
  };
  root.querySelector('#btnChapters').addEventListener('click', () => open('chapters'));
  root.querySelector('#crumbChapter').addEventListener('click', () => open('chapters'));
  if (kit) root.querySelector('#btnKit')?.addEventListener('click', () => open('kit'));
  if (files) root.querySelector('#btnFiles')?.addEventListener('click', () => open('files'));
  return {
    open,
    close: () => {
      for (const d of Object.values(dialogs)) if (d.open) d.close();
    },
    anyOpen: () => Object.values(dialogs).some((d) => d.open),
  };
}
