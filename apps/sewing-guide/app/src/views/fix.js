import { T, ui, lang } from '../i18n.js';
import { href } from '../router.js';
import { el, esc, askButton, setTitle } from './common.js';
import { PROBLEMS, problemById } from '../data/troubleshooting.js';

export function render(root, route, ctx) {
  const t = (en, ru) => (lang === 'ru' ? ru : en);
  const p = route.id ? problemById(route.id) : null;
  setTitle([p ? T(p.title) : ui('tabs.fix')]);
  const page = el(`<div class="page"></div>`);
  root.appendChild(page);
  if (!p) {
    page.innerHTML = `<h1>${ui('symptom')}</h1>
      <p class="lede">${t('Look at the fabric, pick the line that matches. Before anything else: rethread the top with the foot UP, new needle, bobbin counter-clockwise. That fixes most of these.', 'Посмотрите на ткань и выберите строку. Прежде всего: перезаправьте верх с ПОДНЯТОЙ лапкой, новая игла, шпулька против часовой. Это чинит большинство из них.')}</p>
      <div class="problem-list">${PROBLEMS.map((x, i) => `<a href="${href('fix', x.id)}"><span class="ic">${i + 1}</span><span><strong>${esc(T(x.title))}</strong><div class="muted small">${esc(T(x.looks))}</div></span></a>`).join('')}</div>`;
  } else {
    page.innerHTML = `<a class="back" href="${href('fix')}">‹ ${ui('backTo')} ${ui('tabs.fix')}</a>
      <h1>${esc(T(p.title))}</h1>
      <p class="lede">${esc(T(p.looks))}</p>
      <div class="card"><h3>${t('Why it happens', 'Почему так')}</h3><p>${esc(T(p.why))}</p></div>
      <div class="card"><h2>${ui('causes')}</h2><ol class="steps" style="margin-top:10px">${p.fixes
        .map((f) => `<li>${esc(T(f))}${f.link ? ` <a href="${href(f.link[0], f.link[1], f.link[0] === 'machine' ? 0 : undefined)}">›</a>` : ''}</li>`)
        .join('')}</ol></div>`;
  }
  askButton(page, ctx);
}
