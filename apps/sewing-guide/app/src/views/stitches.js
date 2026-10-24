// Stitch library: grid with filters and search; detail page with the live simulator.
import { T, ui, lang } from '../i18n.js';
import { href } from '../router.js';
import { el, esc, askButton, setTitle, pad, fabricLabel } from './common.js';
import { STITCHES, byNo, CATEGORIES, TASKS, FABRICS } from '../data/stitches.js';
import { renderStitchSVG } from '../stitch-render.js';

const FOOT_NAMES = {
  '0A': { en: 'Standard foot 0A (IDT)', ru: 'Стандартная лапка 0A (IDT)' },
  '1A': { en: 'Fancy stitch foot 1A (IDT)', ru: 'Лапка для декоративных строчек 1A (IDT)' },
  '2A': { en: 'Fancy stitch foot 2A', ru: 'Лапка для декоративных строчек 2A' },
  3: { en: 'Blindhem foot 3 (IDT)', ru: 'Лапка для потайного шва 3 (IDT)' },
  4: { en: 'Zipper foot 4 (IDT)', ru: 'Лапка для молнии 4 (IDT)' },
  '5B': { en: 'One-step buttonhole foot 5B', ru: 'Лапка для петли 5B' },
  none: { en: 'No foot (remove it)', ru: 'Без лапки (снять)' },
};

function matches(s, q) {
  if (!q) return true;
  const hay = [pad(s.no), s.name.en, s.name.ru, s.manual?.en, s.manual?.ru, ...s.uses.flatMap((u) => [u.en, u.ru])].join(' ').toLowerCase();
  return q.split(/\s+/).every((w) => hay.includes(w));
}

export function render(root, route, ctx) {
  if (route.id) return renderDetail(root, route, ctx);
  const t = (en, ru) => (lang === 'ru' ? ru : en);
  setTitle([ui('tabs.stitches')]);
  const cat = route.params.get('cat') || '';
  const task = route.params.get('task') || '';
  const fabric = route.params.get('fabric') || '';
  const q = (route.params.get('q') || '').toLowerCase();

  let list = STITCHES;
  if (cat) list = list.filter((s) => s.cat === cat);
  if (task) {
    const tk = TASKS.find((x) => x.id === task);
    if (tk) list = tk.nos.map(byNo);
  }
  if (fabric) list = list.filter((s) => s.uses.some((u) => u.fabrics.includes(fabric)));
  list = list.filter((s) => matches(s, q));

  const link = (over) => href('stitches', null, null, Object.fromEntries(Object.entries({ cat, task, fabric, q, ...over }).filter(([, v]) => v)));
  const page = el(`<div class="page">
    <h1>${t('All 100 stitches', 'Все 100 строчек')}</h1>
    <p class="lede">${t('Each drawing is the needle path at the suggested width and length. Open a stitch to change them and see what the machine will sew.', 'Каждый рисунок — путь иглы при рекомендуемых ширине и длине. Откройте строчку, чтобы их менять и видеть, что сошьёт машина.')}</p>
    <input class="search" type="search" id="q" value="${esc(route.params.get('q') || '')}" placeholder="${ui('search')}" aria-label="${ui('search')}">
    <div>
      <p class="muted" style="margin-bottom:6px">${ui('byTask')}</p>
      <div class="chips"><a class="chip${!task ? ' active' : ''}" href="${link({ task: '' })}">${ui('all')}</a>${TASKS.map((x) => `<a class="chip${task === x.id ? ' active' : ''}" href="${link({ task: x.id, cat: '' })}">${esc(T(x.name))}</a>`).join('')}</div>
    </div>
    <div>
      <p class="muted" style="margin-bottom:6px">${ui('byCategory')}</p>
      <div class="chips"><a class="chip${!cat ? ' active' : ''}" href="${link({ cat: '' })}">${ui('all')}</a>${CATEGORIES.map((c) => `<a class="chip${cat === c.id ? ' active' : ''}" href="${link({ cat: c.id, task: '' })}">${esc(T(c.name))} <span class="muted">${c.range}</span></a>`).join('')}</div>
    </div>
    <div>
      <p class="muted" style="margin-bottom:6px">${ui('fabricsLabel')}</p>
      <div class="chips"><a class="chip${!fabric ? ' active' : ''}" href="${link({ fabric: '' })}">${ui('all')}</a>${FABRICS.map((f) => `<a class="chip${fabric === f ? ' active' : ''}" href="${link({ fabric: f })}">${esc(fabricLabel(f))}</a>`).join('')}</div>
    </div>
    <div class="stitch-grid">${list
      .map((s) => `<a class="stitch-tile" href="${href('stitches', pad(s.no))}">${renderStitchSVG(s, { heightMm: 26, pxPerMm: 3 })}<span class="no">${pad(s.no)}</span><span class="nm">${esc(T(s.name))}</span></a>`)
      .join('')}</div>
    ${list.length ? '' : `<p class="card">${t('Nothing matches.', 'Ничего не найдено.')}</p>`}
  </div>`);
  root.appendChild(page);
  const input = page.querySelector('#q');
  let timer = 0;
  input.addEventListener('input', () => {
    clearTimeout(timer);
    timer = setTimeout(() => {
      window.location.hash = link({ q: input.value.trim() });
    }, 250);
  });
  askButton(page, ctx);
}

function renderDetail(root, route, ctx) {
  const t = (en, ru) => (lang === 'ru' ? ru : en);
  const no = Number(route.id);
  const s = byNo(no);
  if (!s) {
    root.innerHTML = `<p class="card">${t('No such stitch.', 'Нет такой строчки.')} <a href="${href('stitches')}">${ui('backTo')} ${ui('tabs.stitches')}</a></p>`;
    return;
  }
  setTitle([`${pad(no)} ${T(s.name)}`]);
  const catName = T(CATEGORIES.find((c) => c.id === s.cat).name);
  const isStraight = !!s.positionOnly;
  const widthLabel = isStraight ? ui('position') : ui('width');
  const page = el(`<div class="page">
    <a class="back" href="${href('stitches')}">‹ ${ui('backTo')} ${ui('tabs.stitches')}</a>
    <div class="row" style="justify-content:space-between">
      <h1><span class="key" style="margin-right:8px">${pad(no)}</span>${esc(T(s.name))}</h1>
      <div class="stitch-nav">
        ${no > 0 ? `<a class="btn" href="${href('stitches', pad(no - 1))}">‹ ${pad(no - 1)}</a>` : ''}
        ${no < 99 ? `<a class="btn" href="${href('stitches', pad(no + 1))}">${pad(no + 1)} ›</a>` : ''}
      </div>
    </div>
    <div class="row"><span class="tag muted">${esc(catName)}</span><span class="tag ${s.idt ? 'ok' : 'muted'}">${s.idt ? ui('idtOn') : ui('idtOff')}</span><span class="tag">${ui('foot')} ${esc(s.foot)}</span>${s.wing ? `<span class="tag warn">${ui('wing')}</span>` : ''}</div>
    <div class="stitch-detail">
      <div class="sticky">
        <div class="sim">
          <div class="sim-stage" id="simStage"></div>
          <div class="sliders">
            <div class="slider"><label for="w">${widthLabel}</label><output id="wo"></output><input id="w" type="range" min="${s.width.min}" max="${s.width.max}" step="0.5" value="${s.width.def}" ${s.countOnly ? 'disabled' : ''}></div>
            <div class="slider"><label for="l">${s.countOnly ? ui('stitches') : ui('length')}</label><output id="lo"></output><input id="l" type="range" min="${s.length.min}" max="${s.length.max}" step="0.1" value="${s.length.def}" ${s.countOnly ? 'disabled' : ''}></div>
          </div>
          <div class="row" style="justify-content:space-between;width:100%"><span class="muted">${ui('recommended')}: ${isStraight ? '' : `${ui('width')} ${s.width.def} · `}${ui('length')} ${s.length.def} ${ui('mm')}</span><button class="btn" type="button" id="reset">${ui('reset')}</button></div>
        </div>
        <p class="muted small" style="margin-top:8px">${s.geom.kind === 'line' ? t('Orange dots: where the needle goes in.', 'Оранжевые точки: куда входит игла.') : ui('approx')}</p>
      </div>
      <div>
        <div class="card">
          <h3>${ui('selectOnMachine')}</h3>
          <div class="row"><span class="keypad"><span class="key">${String(no).padStart(2, '0')[0]}</span><span class="key">${String(no).padStart(2, '0')[1]}</span></span><span class="muted">${ui('thenAdjust')}</span></div>
          <dl class="kv" style="margin-top:10px">
            <dt>${ui('foot')}</dt><dd>${esc(T(FOOT_NAMES[s.foot] || { en: s.foot, ru: s.foot }))} <a class="muted" href="${href('machine', 'foot', 0)}">›</a></dd>
            <dt>IDT</dt><dd>${s.idt ? ui('idtOn') : ui('idtOff')} <a class="muted" href="${href('machine', 'idt', 0)}">›</a></dd>
            ${s.wing ? `<dt>${ui('needle')}</dt><dd>${t('Wing needle (hemstitch) on natural fibres', 'Игла wing (мережка) на натуральных тканях')}</dd>` : ''}
          </dl>
          <p class="muted small" style="margin-top:8px">${ui('machineDefaults')}</p>
        </div>
        ${s.manual ? `<div class="card"><h3>${ui('manualSays')}</h3><p>${esc(T(s.manual))}</p></div>` : `<div class="card"><p class="muted small">${ui('ourName')}</p></div>`}
        <div class="card">
          <h3>${ui('useFor')}</h3>
          <ul class="plain uses" style="padding:0;list-style:none">${s.uses.map((u) => `<li>${esc(T(u))}${u.fabrics.length ? `<div class="fab">${u.fabrics.map((f) => `<span>${esc(fabricLabel(f))}</span>`).join('')}</div>` : ''}</li>`).join('')}</ul>
        </div>
        ${s.tips.length ? `<div class="card"><h3>${ui('tips')}</h3><ul class="plain">${s.tips.map((x) => `<li>${esc(T(x))}</li>`).join('')}</ul></div>` : ''}
        <div class="card"><h3>${t('Related', 'Похожие')}</h3><div class="chips">${STITCHES.filter((x) => x.cat === s.cat && x.no !== no).slice(0, 12).map((x) => `<a class="chip" href="${href('stitches', pad(x.no))}">${pad(x.no)} ${esc(T(x.name))}</a>`).join('')}</div></div>
      </div>
    </div>
  </div>`);
  root.appendChild(page);

  const stage = page.querySelector('#simStage');
  const w = page.querySelector('#w');
  const l = page.querySelector('#l');
  const wo = page.querySelector('#wo');
  const lo = page.querySelector('#lo');
  const draw = () => {
    const width = Number(w.value);
    const length = Number(l.value);
    wo.textContent = isStraight ? `${width.toFixed(1)}` : `${width.toFixed(1)} ${ui('mm')}`;
    lo.textContent = s.countOnly ? '6' : `${length.toFixed(1)} ${ui('mm')}`;
    const simWidth = isStraight ? 0 : width;
    stage.innerHTML = renderStitchSVG(s, { width: simWidth, length, heightMm: 36, pxPerMm: 6, dots: s.geom.kind === 'line' });
    if (isStraight) {
      // show the needle position as an offset of the straight line within the 7 mm field
      const svg = stage.querySelector('svg');
      const offset = (width - 3.5) * 6;
      svg.querySelector('path').setAttribute('transform', `translate(${offset} 0)`);
      svg.querySelectorAll('circle').forEach((c) => c.setAttribute('transform', `translate(${offset} 0)`));
    }
  };
  w.addEventListener('input', draw);
  l.addEventListener('input', draw);
  page.querySelector('#reset').addEventListener('click', () => {
    w.value = s.width.def;
    l.value = s.length.def;
    draw();
  });
  draw();
  askButton(page, ctx);
}
