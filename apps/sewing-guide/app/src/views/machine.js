// 3D machine: Explore mode (tap parts) and chapter mode (steps drive camera + animation).
import { T, ui, lang } from '../i18n.js';
import { href, navigate } from '../router.js';
import { el, esc, askButton, setTitle, pad } from './common.js';
import { PARTS, partById } from '../data/parts.js';
import { PROCEDURES, procedureById } from '../data/procedures.js';

let scene = null;
let resizeObs = null;
let keyHandler = null;

async function loadScene(stageEl, onPart) {
  const { Machine3D } = await import('../machine3d.js');
  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  return new Machine3D(stageEl, { reducedMotion: reduced, onPart });
}

export function destroy() {
  if (scene) scene.dispose();
  scene = null;
  if (resizeObs) resizeObs.disconnect();
  resizeObs = null;
  if (keyHandler) window.removeEventListener('keydown', keyHandler);
  keyHandler = null;
}

export function render(root, route, ctx) {
  const t = (en, ru) => (lang === 'ru' ? ru : en);
  const chapterId = route.id && route.id !== 'explore' ? route.id : null;
  const proc = chapterId ? procedureById(chapterId) : null;
  const stepIndex = Math.max(0, Math.min((proc ? proc.steps.length : 1) - 1, Number(route.sub || 0)));
  setTitle([proc ? T(proc.title) : ui('tabs.machine')]);

  const page = el(`<div class="page machine">
    <div>
      <h1>${proc ? esc(T(proc.title)) : t('The machine', 'Машина')}</h1>
      <p class="lede">${proc ? esc(T(proc.intro)) : t('Drag to turn it round. Tap a numbered dot for the part. Pick a chapter below to see each step animated.', 'Тяните, чтобы повернуть. Нажмите на точку с номером, чтобы узнать деталь. Выберите главу ниже, чтобы увидеть каждый шаг в анимации.')}</p>
    </div>
    <div class="chapter-bar" role="tablist">
      <a class="chip${!proc ? ' active' : ''}" href="${href('machine', 'explore')}">${ui('explore')}</a>
      ${PROCEDURES.map((p) => `<a class="chip${proc && proc.id === p.id ? ' active' : ''}" href="${href('machine', p.id, 0)}">${esc(T(p.title))}</a>`).join('')}
    </div>
    <div class="stage-wrap" id="stage">
      <div class="stage-tools"><button class="btn" type="button" id="resetView">${ui('resetView')}</button></div>
      <div class="stage-hint">${ui('rotateHint')}</div>
    </div>
    <div id="panel"></div>
  </div>`);
  root.appendChild(page);
  const stage = page.querySelector('#stage');
  const panel = page.querySelector('#panel');

  // ------------------------------------------------------------ panel content
  let activePart = null;
  function showPart(id) {
    activePart = id;
    const p = partById(id);
    if (scene) scene.setActiveHotspot(id);
    const card = panel.querySelector('#partCard');
    if (!p || !card) return;
    card.innerHTML = `<h3>${p.no ? `<span class="tag">${p.no}</span> ` : ''}${esc(T(p.name))}</h3><p>${esc(T(p.what))}</p>${p.id === 'presser-foot' || p.id === 'accessory-tray' ? `<p style="margin-top:8px"><a class="btn" href="${href('kit')}">${ui('tabs.kit')} ›</a></p>` : ''}`;
    panel.querySelectorAll('.part-list button').forEach((b) => b.classList.toggle('active', b.dataset.id === id));
  }

  if (!proc) {
    panel.innerHTML = `<div class="card part-card" id="partCard"><h3>${t('Tap a dot, or a name below', 'Нажмите на точку или на название ниже')}</h3><p class="muted">${t('Numbers match the owner\'s manual.', 'Номера совпадают с инструкцией.')}</p></div>
      <div class="card"><h3>${ui('parts')}</h3><div class="part-list">${PARTS.map((p) => `<button type="button" data-id="${p.id}"><span class="n">${p.no ?? '·'}</span><span>${esc(T(p.name))}</span></button>`).join('')}</div></div>`;
    panel.querySelectorAll('.part-list button').forEach((b) => b.addEventListener('click', () => showPart(b.dataset.id)));
  } else {
    const step = proc.steps[stepIndex];
    panel.innerHTML = `<div class="step-card">
        <div class="step-head"><span class="n">${ui('step')} ${stepIndex + 1} ${ui('of')} ${proc.steps.length}</span><div class="dots">${proc.steps.map((_, i) => `<i class="${i === stepIndex ? 'on' : ''}"></i>`).join('')}</div></div>
        <p class="step-text">${esc(T(step.text))}</p>
        ${step.check ? `<div class="check"><strong>${ui('check')}:</strong> ${esc(T(step.check))}</div>` : ''}
        ${step.parts && step.parts.length ? `<div class="chips" style="margin-top:10px">${step.parts.map((id) => { const p = partById(id); return p ? `<button class="chip" type="button" data-id="${id}">${p.no ? `${p.no} · ` : ''}${esc(T(p.name))}</button>` : ''; }).join('')}</div>` : ''}
        <div class="step-nav">
          <a class="btn" ${stepIndex > 0 ? `href="${href('machine', proc.id, stepIndex - 1)}"` : 'aria-disabled="true" style="visibility:hidden"'}>‹ ${ui('previous')}</a>
          <span></span>
          ${stepIndex < proc.steps.length - 1 ? `<a class="btn primary" href="${href('machine', proc.id, stepIndex + 1)}">${ui('next')} ›</a>` : `<a class="btn" href="${href('machine', 'explore')}">${ui('explore')}</a>`}
        </div>
      </div>
      <div class="card part-card" id="partCard" hidden></div>
      <ol class="steps card" style="margin-top:12px">${proc.steps.map((s, i) => `<li${i === stepIndex ? ' style="font-weight:650"' : ''}><a href="${href('machine', proc.id, i)}" style="text-decoration:none;color:inherit">${esc(T(s.text))}</a></li>`).join('')}</ol>`;
    panel.querySelectorAll('.chips .chip').forEach((b) =>
      b.addEventListener('click', () => {
        const card = panel.querySelector('#partCard');
        card.hidden = false;
        showPart(b.dataset.id);
      }),
    );
    keyHandler = (e) => {
      if (e.target && /input|textarea|select/i.test(e.target.tagName)) return;
      if (e.key === 'ArrowRight' && stepIndex < proc.steps.length - 1) navigate('machine', proc.id, stepIndex + 1);
      if (e.key === 'ArrowLeft' && stepIndex > 0) navigate('machine', proc.id, stepIndex - 1);
    };
    window.addEventListener('keydown', keyHandler);
  }

  // ------------------------------------------------------------ 3D
  const applyStep = () => {
    if (!scene) return;
    if (proc) {
      // Accumulate anim state from the start of the chapter so a deep link lands in the right pose.
      const st = {};
      for (let i = 0; i <= stepIndex; i++) Object.assign(st, proc.steps[i].anim || {});
      scene.resetState();
      scene.setState(st, stepIndex === 0);
      scene.goCamera(proc.steps[stepIndex].cam, false);
      const ids = proc.steps[stepIndex].parts || [];
      scene.setHotspots(PARTS.filter((p) => ids.includes(p.id)));
    } else {
      scene.resetState();
      scene.setHotspots(PARTS, activePart);
    }
  };

  const start = async () => {
    try {
      if (scene) scene.dispose();
      scene = await loadScene(stage, (id) => {
        const card = panel.querySelector('#partCard');
        if (card) card.hidden = false;
        showPart(id);
      });
      window.__machine = scene;
      if (!proc) scene.goCamera('front', true);
      applyStep();
      resizeObs = new ResizeObserver(() => scene && scene.resize());
      resizeObs.observe(stage);
    } catch (err) {
      console.error(err);
      page.classList.add('no-webgl');
      stage.insertAdjacentHTML('afterend', `<p class="card">${ui('noWebgl')}</p>`);
    }
  };
  start();
  page.querySelector('#resetView').addEventListener('click', () => scene && scene.goCamera(proc ? proc.steps[stepIndex].cam : 'front'));

  askButton(page, ctx);
}
