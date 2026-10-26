import { T, ui, lang } from '../i18n.js';
import { href } from '../router.js';
import { el, esc, askButton, setTitle, pad } from './common.js';
import { PROJECTS } from '../data/projects.js';
import { PROBLEMS } from '../data/troubleshooting.js';

const t = (en, ru) => (lang === 'ru' ? ru : en);
const ICON = {
  kit: '<path d="M4 8h16v12H4z"/><path d="M9 8V5h6v3"/><path d="M4 13h16"/>',
  machine: '<path d="M4 17V9a2 2 0 0 1 2-2h9l4 4v6"/><path d="M4 17h17"/><path d="M8 7v10"/><path d="M15 7v4h4"/>',
  start: '<circle cx="12" cy="12" r="9"/><path d="M10 8.5v7l5.5-3.5z"/>',
  stitches: '<path d="M3 12c2-6 4-6 6 0s4 6 6 0 4-6 6 0"/>',
  fabrics: '<path d="M4 6h16v12H4z"/><path d="M4 10h16M4 14h16M8 6v12M12 6v12M16 6v12"/>',
  projects: '<path d="M12 3l9 5-9 5-9-5z"/><path d="M3 13l9 5 9-5"/>',
  fix: '<path d="M14.7 6.3a4 4 0 0 0-5.2 5.2L4 17v3h3l5.5-5.5a4 4 0 0 0 5.2-5.2l-2.4 2.4-2.2-2.2z"/>',
};

export function render(root, route, ctx) {
  setTitle([]);
  const tiles = [
    ['machine', t('The machine in 3D', 'Машина в 3D'), t('Every part explained, threading and bobbin animated, chapter by chapter.', 'Каждая деталь, заправка и шпулька в анимации, глава за главой.')],
    ['start', t('First hour', 'Первый час'), t('Plug in, thread, first seam, what every button does.', 'Подключить, заправить, первый шов, что делает каждая кнопка.')],
    ['stitches', t('All 100 stitches', 'Все 100 строчек'), t('Drawn live at your width and length, with what each is for.', 'Рисуются вживую с вашей шириной и длиной, и для чего каждая.')],
    ['kit', t('What is in the box', 'Что в коробке'), t('Every foot, bobbin and tool: what it is for, with examples.', 'Каждая лапка, шпулька и инструмент: для чего, с примерами.')],
    ['fabrics', t('Fabric settings', 'Настройки по ткани'), t('Needle, thread, tension, foot, IDT for cotton, silk, upholstery, velvet.', 'Игла, нить, натяжение, лапка, IDT для хлопка, шёлка, обивки, бархата.')],
    ['projects', t('First projects', 'Первые проекты'), t('Pincushion, piped cushion, blanket, table runner.', 'Игольница, подушка с кантом, плед, дорожка.')],
    ['fix', t('Something is wrong', 'Что-то не так'), t('Find it by what you see on the fabric.', 'Найдите по тому, что видно на ткани.')],
  ];
  const page = el(`<div class="page">
    <div class="hero">
      <span class="tag">PFAFF passport 3.0 · IDT</span>
      <h1>${t('Everything this machine can do, in the order you will need it.', 'Всё, что умеет эта машина, в том порядке, в котором понадобится.')}</h1>
      <p class="lede">${t('Built from the owner\'s manual and the stitch card, for someone who sews on an industrial straight-stitch machine and an overlocker and now has a hundred stitches, a walking feed and a drop-in bobbin to get used to. Phone next to the machine, laptop on the table: both work. Tap RU/EN at the top at any time.', 'Собрано по инструкции и карте строчек для того, кто шьёт на промышленной прямострочной машине и оверлоке, а теперь получил сто строчек, верхний транспортёр и горизонтальную шпульку. Телефон рядом с машиной или ноутбук на столе — работает и так, и так. RU/EN вверху переключается в любой момент.')}</p>
    </div>
    <div class="home-grid">${tiles
      .map(([id, title, desc]) => `<a class="home-tile" href="${href(id)}"><svg viewBox="0 0 24 24" aria-hidden="true">${ICON[id]}</svg><span class="t">${esc(title)}</span><span class="d">${esc(desc)}</span></a>`)
      .join('')}</div>
    <section class="card">
      <h2>${t('Start here tonight', 'Начните сегодня с этого')}</h2>
      <div class="quick">
        <a href="${href('machine', 'power')}"><span class="n">1</span><span>${t('Plug in and switch on', 'Подключить и включить')}</span></a>
        <a href="${href('machine', 'wind')}"><span class="n">2</span><span>${t('Wind a bobbin', 'Намотать шпульку')}</span></a>
        <a href="${href('machine', 'bobbin')}"><span class="n">3</span><span>${t('Insert the bobbin', 'Вставить шпульку')}</span></a>
        <a href="${href('machine', 'thread')}"><span class="n">4</span><span>${t('Thread the top thread', 'Заправить верхнюю нить')}</span></a>
        <a href="${href('machine', 'first-seam')}"><span class="n">5</span><span>${t('First seam on a cotton scrap', 'Первый шов на хлопковом лоскуте')}</span></a>
        <a href="${href('machine', 'pack')}"><span class="n">6</span><span>${t('Pack away: cords and cover', 'Убрать: провода и чехол')}</span></a>
      </div>
    </section>
    <section class="card">
      <h2>${t('The silk question', 'Вопрос про шёлк')}</h2>
      <p>${t('Zigzag on silk that gets chewed into a ridge has a name (tunnelling) and three fixes. It is the first page in', 'Зигзаг на шёлке, который «сжёвывается» в валик, имеет название (туннелинг) и три решения. Это первая страница в разделе')} <a href="${href('fix', 'tunneling')}">${t('Fix', 'Проблемы')}</a>.</p>
    </section>
    <section class="card">
      <h2>${t('First projects', 'Первые проекты')}</h2>
      <div class="quick">${PROJECTS.map((p) => `<a href="${href('projects', p.id)}"><span class="n">${p.order}</span><span>${esc(T(p.title))} <span class="muted">· ${esc(T(p.teaches))}</span></span></a>`).join('')}</div>
    </section>
    <p class="muted">${t('Source: PFAFF passport 2.0/3.0 owner\'s manual 471 01 87-26B and the machine\'s stitch card. Stitch names 22 to 99 and all settings for specific fabrics are this guide\'s recommendations, not PFAFF\'s. Test on a scrap.', 'Источник: инструкция PFAFF passport 2.0/3.0 471 01 87-26B и карта строчек машины. Названия строчек 22–99 и все настройки для конкретных тканей — рекомендации этого гида, а не PFAFF. Проверяйте на лоскуте.')} ${PROBLEMS.length} ${t('problems covered.', 'проблем разобрано.')}</p>
  </div>`);
  root.appendChild(page);
  askButton(page, ctx);
}
