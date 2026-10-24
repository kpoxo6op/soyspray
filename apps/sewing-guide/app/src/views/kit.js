import { T, ui, lang } from '../i18n.js';
import { href } from '../router.js';
import { el, esc, askButton, setTitle } from './common.js';
import { KIT, KIT_GROUPS, kitById } from '../data/kit.js';

const icon = (paths) => `<svg class="kit-icon" viewBox="0 0 64 64" aria-hidden="true">${paths}</svg>`;

export function render(root, route, ctx) {
  const t = (en, ru) => (lang === 'ru' ? ru : en);
  const item = route.id ? kitById(route.id) : null;
  setTitle([item ? T(item.name) : ui('tabs.kit')]);
  const page = el(`<div class="page"></div>`);
  root.appendChild(page);
  if (!item) {
    page.innerHTML = `<h1>${t('What is in the box', 'Что в коробке')}</h1>
      <p class="lede">${t('Every accessory that came with the machine, what it is for, and where it turns up in the first projects. Six feet, five bobbins, a handful of tools.', 'Каждый аксессуар из комплекта, для чего он и где пригодится в первых проектах. Шесть лапок, пять шпулек, горсть инструментов.')}</p>
      ${KIT_GROUPS.map(
        (g) => `<section>
          <h2 style="margin:10px 0 8px">${esc(T(g.name))}</h2>
          <div class="kit-grid">${KIT.filter((k) => k.group === g.id)
            .map((k) => `<a class="kit-tile" href="${href('kit', k.id)}">${icon(k.icon)}<span class="kit-text"><span class="kit-name">${k.code ? `<span class="key">${k.code}</span> ` : ''}${esc(T(k.name))}</span><span class="kit-what">${esc(T(k.examples[0]))}</span></span></a>`)
            .join('')}</div>
        </section>`,
      ).join('')}
      <p class="muted">${t('Feet 0A, 1A, 3 and 4 have the cut-out for IDT. 2A and 5B do not: release IDT before using them.', 'У лапок 0A, 1A, 3 и 4 есть вырез под IDT. У 2A и 5B нет: отключите IDT перед их использованием.')}</p>`;
  } else {
    const idx = KIT.indexOf(item);
    const prev = KIT[idx - 1];
    const next = KIT[idx + 1];
    page.innerHTML = `<a class="back" href="${href('kit')}">‹ ${ui('backTo')} ${ui('tabs.kit')}</a>
      <div class="kit-hero">${icon(item.icon)}<div><h1>${item.code ? `<span class="key" style="margin-right:8px">${item.code}</span>` : ''}${esc(T(item.name))}</h1>${item.idt != null ? `<span class="tag ${item.idt ? 'ok' : 'muted'}">${item.idt ? ui('idtOn') : ui('idtOff')}</span>` : ''}</div></div>
      <div class="card"><h3>${t('What it is', 'Что это')}</h3><p>${esc(T(item.what))}</p></div>
      <div class="card"><h3>${t('Use it for', 'Для чего')}</h3><ul class="plain">${item.examples.map((e) => `<li>${esc(T(e))}</li>`).join('')}</ul></div>
      ${item.link ? `<p><a class="btn" href="${href(item.link[0], item.link[1], item.link[0] === 'machine' ? 0 : undefined)}">${t('See it in the guide', 'Смотреть в гиде')} ›</a></p>` : ''}
      <div class="stitch-nav">${prev ? `<a class="btn" href="${href('kit', prev.id)}">‹ ${esc(T(prev.name))}</a>` : '<span></span>'}${next ? `<a class="btn" href="${href('kit', next.id)}">${esc(T(next.name))} ›</a>` : ''}</div>`;
  }
  askButton(page, ctx);
}
