import { T, ui, lang } from '../i18n.js';
import { href } from '../router.js';
import { el, esc, askButton, setTitle, stitchChip } from './common.js';
import { PROJECTS, projectById } from '../data/projects.js';
import { fabricById } from '../data/fabrics.js';

export function render(root, route, ctx) {
  const t = (en, ru) => (lang === 'ru' ? ru : en);
  const p = route.id ? projectById(route.id) : null;
  setTitle([p ? T(p.title) : ui('tabs.projects')]);
  const page = el(`<div class="page"></div>`);
  root.appendChild(page);
  if (!p) {
    page.innerHTML = `<h1>${t('First projects', 'Первые проекты')}</h1>
      <p class="lede">${t('In this order. Each one adds a technique you will use in the next.', 'В этом порядке. Каждый добавляет приём, который пригодится в следующем.')}</p>
      <div class="grid">${PROJECTS.map((x) => `<a class="home-tile" href="${href('projects', x.id)}"><span class="tag" style="align-self:flex-start">${x.order}</span><span class="t">${esc(T(x.title))}</span><span class="d">${esc(T(x.teaches))}</span><span class="d muted">${esc(T(fabricById(x.fabric).name))}</span></a>`).join('')}</div>`;
  } else {
    const fab = fabricById(p.fabric);
    page.innerHTML = `<a class="back" href="${href('projects')}">‹ ${ui('backTo')} ${ui('tabs.projects')}</a>
      <div class="row"><span class="tag">${t('Project', 'Проект')} ${p.order}</span><a class="tag muted" href="${href('fabrics', fab.id)}" style="text-decoration:none">${esc(T(fab.name))} ›</a></div>
      <h1>${esc(T(p.title))}</h1>
      <p class="lede">${esc(T(p.teaches))}</p>
      <div class="card"><h2>${ui('youNeed')}</h2><ul class="plain">${p.need.map((n) => `<li>${esc(T(n))}</li>`).join('')}</ul></div>
      <div class="card"><h2>${ui('settings')}</h2><dl class="kv" style="margin-top:8px">${p.settings
        .map((s) => `<dt>${esc(T(s.label))}</dt><dd>${s.no != null ? stitchChip(s.no, { len: s.len, wid: s.wid ?? undefined }) : esc(T(s.text))}</dd>`)
        .join('')}</dl></div>
      <div class="card"><h2>${ui('steps')}</h2><ol class="steps" style="margin-top:10px">${p.steps.map((s) => `<li>${esc(T(s))}</li>`).join('')}</ol></div>
      <div class="card"><h3>${t('Stitches used', 'Используемые строчки')}</h3><div class="row" style="gap:14px">${p.stitchLinks.map((n) => stitchChip(n)).join('')}</div></div>`;
  }
  askButton(page, ctx);
}
