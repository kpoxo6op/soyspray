import { T, ui, lang } from '../i18n.js';
import { href } from '../router.js';
import { el, esc, askButton, setTitle, stitchChip } from './common.js';
import { FABRIC_LIST, fabricById } from '../data/fabrics.js';

export function render(root, route, ctx) {
  const t = (en, ru) => (lang === 'ru' ? ru : en);
  const f = route.id ? fabricById(route.id) : null;
  setTitle([f ? T(f.name) : ui('tabs.fabrics')]);
  const page = el(`<div class="page"></div>`);
  root.appendChild(page);

  if (!f) {
    page.innerHTML = `<h1>${t('Settings by fabric', 'Настройки по ткани')}</h1>
      <p class="lede">${t('Needle and thread first, then tension, then the stitch. Every number is a starting point: sew 10 cm on a scrap and look at both sides.', 'Сначала игла и нить, потом натяжение, потом строчка. Каждое число — стартовая точка: прошейте 10 см на лоскуте и посмотрите с обеих сторон.')}</p>
      <div class="table-wrap card" style="padding:0">
      <table class="fabric-table">
        <thead><tr><th>${ui('fabricsLabel')}</th><th>${ui('needle')}</th><th>${ui('tension')}</th><th>${ui('pressure')}</th><th>${ui('seam')}</th><th>${ui('edgeFinish')}</th><th>${ui('hem')}</th></tr></thead>
        <tbody>${FABRIC_LIST.map(
          (x) => `<tr>
            <td><a href="${href('fabrics', x.id)}">${esc(T(x.name))}</a><div class="muted">${esc(T(x.examples))}</div></td>
            <td>${esc(T(x.needle))}</td>
            <td>${esc(x.tension)}</td>
            <td>${esc(T(x.pressure))}</td>
            <td>${stitchChip(x.seam.no, { len: x.seam.len, wid: x.seam.wid ?? undefined })}</td>
            <td>${stitchChip(x.edge.no, { len: x.edge.len, wid: x.edge.wid })}</td>
            <td>${stitchChip(x.hem.no, { len: x.hem.len, wid: x.hem.wid ?? undefined })}</td>
          </tr>`,
        ).join('')}</tbody>
      </table></div>
      <div class="grid">${FABRIC_LIST.map((x) => `<a class="home-tile" href="${href('fabrics', x.id)}"><span class="t">${esc(T(x.name))}</span><span class="d">${esc(T(x.notes[0]))}</span></a>`).join('')}</div>
      <p class="muted">${t('Tension 4 and pressure N are the machine\'s factory settings. IDT on for every fabric here.', 'Натяжение 4 и давление N — заводские настройки. IDT включён для всех тканей здесь.')}</p>`;
  } else {
    const alt = (nos) => (nos && nos.length ? `<div class="muted small" style="margin-top:4px">${t('Also', 'Ещё')}: ${nos.map((n) => stitchChip(n)).join(' ')}</div>` : '');
    page.innerHTML = `<a class="back" href="${href('fabrics')}">‹ ${ui('backTo')} ${ui('tabs.fabrics')}</a>
      <h1>${esc(T(f.name))}</h1>
      <p class="lede">${esc(T(f.examples))}</p>
      <div class="card"><h2>${ui('settings')}</h2>
        <dl class="kv" style="margin-top:8px">
          <dt>${ui('needle')}</dt><dd>${esc(T(f.needle))} <a class="muted" href="${href('machine', 'needle', 0)}">›</a></dd>
          <dt>${ui('thread')}</dt><dd>${esc(T(f.thread))}</dd>
          <dt>${ui('tension')}</dt><dd>${esc(f.tension)}</dd>
          <dt>${ui('pressure')}</dt><dd>${esc(T(f.pressure))}</dd>
          <dt>${ui('foot')}</dt><dd>${esc(f.foot)} · ${f.idt ? ui('idtOn') : ui('idtOff')} <a class="muted" href="${href('machine', 'idt', 0)}">›</a></dd>
        </dl>
      </div>
      <div class="card"><h2>${t('Stitches', 'Строчки')}</h2>
        <dl class="kv" style="margin-top:8px">
          <dt>${ui('seam')}</dt><dd>${stitchChip(f.seam.no, { len: f.seam.len, wid: f.seam.wid ?? undefined })}${alt(f.seamAlt)}</dd>
          <dt>${ui('edgeFinish')}</dt><dd>${stitchChip(f.edge.no, { len: f.edge.len, wid: f.edge.wid })}${alt(f.edgeAlt)}</dd>
          <dt>${ui('hem')}</dt><dd>${stitchChip(f.hem.no, { len: f.hem.len, wid: f.hem.wid ?? undefined })}${alt(f.hemAlt)}</dd>
        </dl>
      </div>
      <div class="card"><h2>${ui('notes')}</h2><ul class="plain">${f.notes.map((n) => `<li>${esc(T(n))}</li>`).join('')}</ul></div>
      <p><a class="btn" href="${href('stitches', null, null, { fabric: f.id })}">${t('All stitches recommended for', 'Все строчки для')} ${esc(T(f.name)).toLowerCase()} ›</a></p>`;
  }
  askButton(page, ctx);
}
