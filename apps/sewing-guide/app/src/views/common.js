import { T, ui, lang } from '../i18n.js';
import { href } from '../router.js';
import { byNo } from '../data/stitches.js';
import { renderStitchSVG } from '../stitch-render.js';

export const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]);
export const pad = (n) => String(n).padStart(2, '0');
export const el = (html) => {
  const tpl = document.createElement('template');
  tpl.innerHTML = html.trim();
  return tpl.content.firstElementChild;
};

/** Small inline stitch preview linking to the stitch page. */
export function stitchChip(no, { len, wid } = {}) {
  const s = byNo(no);
  if (!s) return '';
  const svg = renderStitchSVG(s, { heightMm: 14, pxPerMm: 2.4, width: wid ?? s.width.def, length: len ?? s.length.def });
  const settings = [len != null ? `${ui('length')} ${len}` : '', wid != null ? `${ui('width')} ${wid}` : ''].filter(Boolean).join(' · ');
  return `<a class="setting" href="${href('stitches', pad(no))}" title="${esc(T(s.name))}"><span class="key">${pad(no)}</span><span class="mini">${svg}</span><span>${esc(T(s.name))}${settings ? ` <span class="muted">(${settings})</span>` : ''}</span></a>`;
}

/** "Ask a question" footer: shares the deep link so Boris can update the guide. */
export function askButton(container, { toast }) {
  const btn = el(`<div class="ask"><button class="btn" type="button"><svg viewBox="0 0 24 24"><path d="M12 3a9 9 0 0 0-7.8 13.5L3 21l4.6-1.2A9 9 0 1 0 12 3zm0 14.2a1.2 1.2 0 1 1 0-2.4 1.2 1.2 0 0 1 0 2.4zm1.3-4.6c-.6.4-.8.7-.8 1.4h-1.6c0-1.3.5-1.9 1.3-2.5.5-.4.8-.7.8-1.2 0-.6-.5-1-1.1-1s-1.2.4-1.3 1.2H8.9c.1-1.8 1.4-2.9 3.1-2.9 1.8 0 3.1 1.1 3.1 2.6 0 1-.5 1.8-1.8 2.4z"/></svg>${ui('ask')}</button></div>`);
  btn.querySelector('button').addEventListener('click', async () => {
    const url = window.location.href;
    const text = `${ui('askBody')}: ${document.title}\n${url}`;
    try {
      if (navigator.share) {
        await navigator.share({ title: document.title, text, url });
        return;
      }
      await navigator.clipboard.writeText(text);
      toast(ui('copied'));
    } catch (err) {
      if (err && err.name === 'AbortError') return;
      toast(ui('shareFail'));
    }
  });
  container.appendChild(btn);
}

export function setTitle(parts) {
  document.title = [...parts, 'passport 3.0'].filter(Boolean).join(' · ');
}

export const fabricLabel = (id) =>
  ({
    cotton: { en: 'cotton', ru: 'хлопок' },
    silk: { en: 'silk', ru: 'шёлк' },
    upholstery: { en: 'upholstery', ru: 'обивка' },
    velvet: { en: 'velvet', ru: 'бархат' },
    knit: { en: 'knit', ru: 'трикотаж' },
    denim: { en: 'denim', ru: 'джинса' },
  })[id]?.[lang] || id;
