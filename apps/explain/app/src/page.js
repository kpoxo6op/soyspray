// The catalog page as HTML, rendered at build time from data/guides.json so the chapters show before any script
// runs. `bridge: true` uses UI SDK elements; `bridge: false` renders the same page with native controls only,
// which the agent comparison in tools/agent-bench uses as its baseline.

const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]);
export const minutes = (s) => `${Math.max(1, Math.round(s / 60))} min`;
const clock = (s) => `${Math.floor(s / 60)}:${String(Math.round(s % 60)).padStart(2, '0')}`;

export function chapterHref(guide, c) {
  return guide.link === 'id' ? `${guide.path}#${c.id}` : `${guide.path}#t=${c.start}`;
}

function guideBlock(g, bridge) {
  const total = g.chapters.reduce((t, c) => t + c.length, 0);
  const n = g.chapters.length;
  const meter = bridge
    ? `<ui-meter value="0" min="0" max="${n}" data-meter="${g.slug}"><ui-meter-label>${esc(g.title)} done</ui-meter-label><ui-meter-value></ui-meter-value><ui-meter-track><ui-meter-indicator></ui-meter-indicator></ui-meter-track></ui-meter>`
    : `<label class="meter">${esc(g.title)} done <meter value="0" min="0" max="${n}" data-meter="${g.slug}"></meter> <output data-meter-text="${g.slug}">0 of ${n}</output></label>`;
  const open = `<a class="open" href="${g.path}">Open ${esc(g.title)}</a>`;
  return `<article class="guide" data-guide="${g.slug}">
  <h2>${esc(g.title)}</h2>
  <p>${esc(g.summary)}</p>
  <p class="meta">${n} chapters · ${minutes(total)} of 3D</p>
  ${meter}
  ${bridge ? `<ui-button>${open}</ui-button>` : open}
</article>`;
}

function chapterRow(g, c, bridge) {
  const href = chapterHref(g, c);
  const body = `<a href="${href}"><span class="t">${esc(c.title)}</span><span class="d">${clock(c.length)}</span></a>${c.goal ? `<p class="goal">${esc(c.goal)}</p>` : ''}`;
  const words = `${g.title} ${c.section} ${c.title} ${c.goal || ''} ${c.id}`.toLowerCase();
  if (bridge) {
    return `<li data-guide="${g.slug}" data-id="${c.id}" data-words="${esc(words)}"><soy-chapter href="${href}" aria-label="${esc(c.title)}">${body}<soy-chapter-done><button type="button" aria-pressed="false">Done</button></soy-chapter-done></soy-chapter></li>`;
  }
  return `<li data-guide="${g.slug}" data-id="${c.id}" data-words="${esc(words)}"><div class="chapter" role="group" aria-label="${esc(c.title)}">${body}<button type="button" class="done" aria-pressed="false" aria-label="Done: ${esc(c.title)}">Done</button></div></li>`;
}

function chapterList(g, bridge) {
  const sections = [];
  for (const c of g.chapters) {
    if (!sections.length || sections.at(-1).title !== c.section) sections.push({ title: c.section, chapters: [] });
    sections.at(-1).chapters.push(c);
  }
  return `<section class="list" data-guide="${g.slug}" aria-label="${esc(g.title)} chapters">
  <h3>${esc(g.title)}</h3>
  ${sections.map((s) => `<h4>${esc(s.title)}</h4><ol>${s.chapters.map((c) => chapterRow(g, c, bridge)).join('')}</ol>`).join('\n  ')}
</section>`;
}

function controls(guides, bridge) {
  const options = [{ value: 'all', label: 'All' }, ...guides.map((g) => ({ value: g.slug, label: g.title.split(/[ ,]/)[0] }))];
  if (bridge) {
    return `<div class="controls">
  <ui-field class="search"><ui-field-label>Find a chapter</ui-field-label><ui-input-group><ui-input><input type="search" placeholder="crimp, solder, node-1" autocomplete="off" spellcheck="false"></ui-input><ui-input-clear><button type="button" aria-label="Clear search">×</button></ui-input-clear></ui-input-group></ui-field>
  <ui-segmented-control aria-label="Guide" default-value="all"><ui-segmented-control-indicator></ui-segmented-control-indicator>${options.map((o) => `<ui-segmented-control-item value="${o.value}">${esc(o.label)}</ui-segmented-control-item>`).join('')}</ui-segmented-control>
  <label class="toggle">Hide done <ui-switch><ui-switch-thumb></ui-switch-thumb></ui-switch></label>
</div>`;
  }
  return `<div class="controls">
  <label class="search"><span>Find a chapter</span><input type="search" placeholder="crimp, solder, node-1" autocomplete="off" spellcheck="false"></label>
  <fieldset class="segments"><legend class="sr">Guide</legend>${options.map((o) => `<label><input type="radio" name="guide" value="${o.value}"${o.value === 'all' ? ' checked' : ''}><span>${esc(o.label)}</span></label>`).join('')}</fieldset>
  <label class="toggle">Hide done <input type="checkbox" role="switch" name="hide-done"></label>
</div>`;
}

export function renderPage(guides, { bridge, css, js }) {
  const count = guides.reduce((t, g) => t + g.chapters.length, 0);
  return `<!doctype html>
<html lang="en-NZ">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="color-scheme" content="dark">
<meta name="theme-color" content="#100e0c">
<meta name="robots" content="noindex">
<title>Soyspray explainers</title>
<link rel="icon" href="data:,">
<link rel="stylesheet" href="${css}">
</head>
<body>
<main id="app" class="${bridge ? 'bridge' : 'plain'}">
<header class="top">
  <h1>Soyspray explainers</h1>
  <p class="lede">3D guides for things built and run at home. Open a guide, or find a chapter and start the guide there. Ticks stay in this browser.</p>
</header>
<section class="guides" aria-label="Guides">
${guides.map((g) => guideBlock(g, bridge)).join('\n')}
</section>
<section class="finder" aria-labelledby="chapters-h">
<h2 id="chapters-h">Chapters</h2>
${controls(guides, bridge)}
<p class="count" aria-live="polite" data-count>${count} chapters</p>
${guides.map((g) => chapterList(g, bridge)).join('\n')}
<p class="empty" data-empty hidden>No chapter matches. Clear the search or pick All.</p>
</section>
</main>
<script src="${js}"></script>
</body>
</html>
`;
}
