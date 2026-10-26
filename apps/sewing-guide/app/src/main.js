import './style.css';
import { initLang, setLang, onLang, lang, ui } from './i18n.js';
import { startRouter, onRoute, href, parseRoute } from './router.js';
import * as home from './views/home.js';
import * as machine from './views/machine.js';
import * as start from './views/start.js';
import * as stitches from './views/stitches.js';
import * as fabrics from './views/fabrics.js';
import * as projects from './views/projects.js';
import * as fix from './views/fix.js';
import * as kit from './views/kit.js';

const VIEWS = { home, machine, start, stitches, fabrics, projects, fix, kit };
const TAB_ORDER = ['machine', 'start', 'stitches', 'kit', 'fabrics', 'projects', 'fix'];
const ICONS = {
  machine: '<path d="M4 17V9a2 2 0 0 1 2-2h9l4 4v6"/><path d="M4 17h17"/><path d="M8 7v10"/><path d="M15 7v4h4"/><circle cx="18" cy="14" r="1.2"/>',
  start: '<circle cx="12" cy="12" r="9"/><path d="M10 8.5v7l5.5-3.5z"/>',
  stitches: '<path d="M3 12c2-6 4-6 6 0s4 6 6 0 4-6 6 0"/>',
  kit: '<path d="M4 8h16v12H4z"/><path d="M9 8V5h6v3"/><path d="M4 13h16"/>',
  fabrics: '<path d="M4 6h16v12H4z"/><path d="M4 10h16M4 14h16M8 6v12M12 6v12M16 6v12"/>',
  projects: '<path d="M12 3l9 5-9 5-9-5z"/><path d="M3 13l9 5 9-5"/>',
  fix: '<path d="M14.7 6.3a4 4 0 0 0-5.2 5.2L4 17v3h3l5.5-5.5a4 4 0 0 0 5.2-5.2l-2.4 2.4-2.2-2.2z"/>',
};

const main = document.getElementById('main');
const tabs = document.getElementById('tabs');
const toastEl = document.getElementById('toast');
const langBtn = document.getElementById('langBtn');
const brandSub = document.getElementById('brandSub');

let current = null;
let currentRoute = null;
let toastTimer = 0;

export function toast(msg) {
  toastEl.textContent = msg;
  toastEl.classList.add('show');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toastEl.classList.remove('show'), 2600);
}

function renderTabs(route) {
  tabs.innerHTML = TAB_ORDER.map(
    (id) =>
      `<a class="tab${route.section === id ? ' active' : ''}" href="${href(id)}"><svg viewBox="0 0 24 24" aria-hidden="true">${ICONS[id]}</svg><span>${ui(`tabs.${id}`)}</span></a>`,
  ).join('');
}

function render(route) {
  if (current && current.destroy) current.destroy();
  const view = VIEWS[route.section] || VIEWS.home;
  main.innerHTML = '';
  main.className = `main view-${route.section}`;
  current = view;
  view.render(main, route, { toast });
  renderTabs(route);
  brandSub.textContent = ui('guide');
  langBtn.textContent = lang === 'en' ? 'RU' : 'EN';
  langBtn.setAttribute('aria-label', lang === 'en' ? 'Переключить на русский' : 'Switch to English');
  if (currentRoute && (currentRoute.section !== route.section || currentRoute.id !== route.id)) window.scrollTo(0, 0);
  currentRoute = route;
}

initLang();
langBtn.addEventListener('click', () => setLang(lang === 'en' ? 'ru' : 'en'));
onLang(() => render(parseRoute()));
onRoute(render);
startRouter();

// Offline and instant repeat opens: the service worker precaches this exact build.
if ('serviceWorker' in navigator && location.protocol !== 'file:') {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('sw.js').catch(() => {});
  });
}

// Warm the 3D engine chunk once the first screen is idle, so the Machine tab opens at once.
const warm = () => import('./machine3d.js').catch(() => {});
if (parseRoute().section !== 'machine') {
  if ('requestIdleCallback' in window) requestIdleCallback(warm, { timeout: 4000 });
  else setTimeout(warm, 2500);
}
