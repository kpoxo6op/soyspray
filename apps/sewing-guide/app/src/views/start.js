// First hour: checklist, the button panel decoded, display codes, the accessory box.
import { T, ui, lang } from '../i18n.js';
import { href } from '../router.js';
import { el, esc, askButton, setTitle, stitchChip } from './common.js';

const KEY = 'sewing-guide-checklist';

export function render(root, route, ctx) {
  const t = (en, ru) => (lang === 'ru' ? ru : en);
  setTitle([ui('tabs.start')]);
  const checklist = [
    [t('Machine on a steady table, handwheel on the right, 30 cm free to the left for fabric', 'Машина на устойчивом столе, маховик справа, 30 см свободно слева для ткани'), href('machine', 'power')],
    [t('Foot control in the front socket, power in the rear, switch on: light and 00', 'Педаль в передний разъём, питание в задний, включить: подсветка и 00'), href('machine', 'power')],
    [t('Speed slider halfway', 'Ползунок скорости посередине'), href('machine', 'power')],
    [t('Spool on, cap tight', 'Катушка надета, фиксатор прижат'), href('machine', 'spool')],
    [t('A bobbin wound firm and even', 'Шпулька намотана плотно и ровно'), href('machine', 'wind')],
    [t('Bobbin in, counter-clockwise, thread cut at E', 'Шпулька вставлена против часовой, нить отрезана у E'), href('machine', 'bobbin')],
    [t('Top thread: foot up, needle up, through the take-up lever', 'Верхняя нить: лапка вверх, игла вверх, через нитепритягиватель'), href('machine', 'thread')],
    [t('Needle 80/12 universal, new, flat side back', 'Игла 80/12 универсальная, новая, плоской стороной назад'), href('machine', 'needle')],
    [t('IDT engaged, foot 0A', 'IDT включён, лапка 0A'), href('machine', 'idt')],
    [t('First seam on two layers of cotton scrap; both sides look the same', 'Первый шов на двух слоях хлопкового лоскута; обе стороны одинаковые'), href('machine', 'first-seam')],
    [t('Try: zigzag 02, three-step zigzag 05, overlock 13, blind hem 10', 'Попробовать: зигзаг 02, трёхступенчатый 05, оверлок 13, потайной 10'), href('stitches')],
    [t('Pack away: cords, tray, cover', 'Убрать: провода, лоток, чехол'), href('machine', 'pack')],
  ];
  let done = [];
  try {
    done = JSON.parse(localStorage.getItem(KEY) || '[]');
  } catch {
    /* ignore */
  }

  const buttons = [
    ['0–9', t('Stitch number', 'Номер строчки'), t('Two digits. 0 then 2 gives zigzag. The display shows the number; the card on the right shows the picture.', 'Две цифры. 0, потом 2 — зигзаг. Дисплей показывает номер; карта справа — картинку.')],
    ['i', t('Info', 'Инфо'), t('Shows which foot the stitch wants: 0A, 1A, 2A, 3, 5B. A dot bottom right means engage IDT.', 'Показывает, какая лапка нужна: 0A, 1A, 2A, 3, 5B. Точка справа внизу — включить IDT.')],
    ['− ⟷ +', t('Width / needle position', 'Ширина / положение иглы'), t('Top row. For straight stitches it moves the needle: 3.5 is centre, 29 positions. For everything else it is the width, up to 7 mm.', 'Верхний ряд. Для прямых строчек сдвигает иглу: 3.5 — центр, 29 положений. Для остальных — ширина, до 7 мм.')],
    ['− ⇅ +', t('Length', 'Длина'), t('Second row. Up to 4.5 mm. Satin stitches use 0.3 to 0.5. The default flashes when you scroll past it.', 'Второй ряд. До 4,5 мм. Гладьевые строчки 0,3–0,5. Значение по умолчанию мигает, когда проходите мимо.')],
    ['⤓', t('Needle up / down', 'Игла вверх / вниз'), t('Also sets where the needle stops: down for pivoting at corners, up for pulling fabric out. A tap on the foot control does the same.', 'Также задаёт, где игла останавливается: внизу — для поворотов на углах, вверху — чтобы вынуть ткань. Короткое нажатие педали делает то же.')],
    ['⊣', t('Tie-off', 'Закрепка'), t('While sewing: ties off immediately and stops. Before sewing: lights the LED, then press reverse at the end and it ties off and stops. Not for stitches 16 to 21.', 'Во время шитья: закрепка сразу и стоп. До шитья: загорается светодиод, в конце нажмите реверс — закрепка и стоп. Не для строчек 16–21.')],
    ['✂', t('Thread snips', 'Обрезка нити'), t('Cuts top and bobbin threads. Pressed while sewing: finishes the stitch, ties off, cuts.', 'Режет верхнюю и нижнюю нить. Нажата во время шитья: заканчивает стежок, закрепка, обрезка.')],
    ['⟲', t('Reverse', 'Реверс'), t('Sews backwards while held. Three stitches at each end of a seam locks it. Also ends the darning stitch.', 'Шьёт назад, пока нажата. Три стежка в начале и конце шва закрепляют его. Также заканчивает штопку.')],
    ['▶ ∎', t('Start / stop', 'Старт / стоп'), t('Sews without the foot control at the speed set by the slider. Press again to stop.', 'Шьёт без педали на скорости ползунка. Нажмите ещё раз, чтобы остановить.')],
    ['⫿', t('Speed slider', 'Ползунок скорости'), t('Maximum speed. Low for buttonholes, satin, corners and silk.', 'Максимальная скорость. Низко для петель, глади, углов и шёлка.')],
  ];
  const codes = [
    ['SP', t('Bobbin winder lever is to the right. Push it left to sew.', 'Рычаг моталки справа. Сдвиньте влево, чтобы шить.')],
    ['EL', t('Motor overloaded: thread jammed under the plate or in the hook. Off, clear, rethread, on.', 'Перегрузка мотора: нить застряла под пластиной или в челноке. Выключить, убрать, перезаправить, включить.')],
    ['0A 1A 2A 3 5B', t('After the info button: the foot this stitch wants.', 'После кнопки инфо: лапка для этой строчки.')],
    [t('beep', 'писк'), t('Minimum or maximum reached, or the buttonhole lever is up, or a button pressed in SP mode.', 'Достигнут минимум или максимум, или рычаг петли поднят, или кнопка нажата в режиме SP.')],
  ];
  const kit = [
    [t('Feet 0A, 1A, 2A, 3, 4, 5B', 'Лапки 0A, 1A, 2A, 3, 4, 5B'), t('Standard, two fancy-stitch feet, blind hem, zipper, one-step buttonhole.', 'Стандартная, две для декоративных строчек, потайная, для молнии, петельная.')],
    [t('5 bobbins #416475801', '5 шпулек #416475801'), t('Only these fit. Buy spares with that number.', 'Подходят только эти. Запасные с этим номером.')],
    [t('Spool caps large ×2, small ×1; felt pad; auxiliary spool pin', 'Фиксаторы катушки большие ×2, малый ×1; фетр; дополнительный стержень'), t('Caps hold the spool; the pin and felt are for a second spool or vertical use.', 'Фиксаторы держат катушку; стержень и фетр — для второй катушки или вертикальной установки.')],
    [t('Screwdriver, multi-purpose tool, seam ripper with brush, edge guide', 'Отвёртка, универсальный инструмент, вспарыватель с кисточкой, направитель'), t('Screwdriver for the plate; the tool holds needles, levels the foot over thick seams and makes button shanks; the guide screws onto the foot holder to keep seams parallel.', 'Отвёртка для пластины; инструмент держит иглы, выравнивает лапку на толстых швах и делает ножку пуговицы; направитель крепится к держателю лапки для параллельных швов.')],
  ];

  const page = el(`<div class="page">
    <h1>${t('The first hour', 'Первый час')}</h1>
    <p class="lede">${t('Tick as you go. Each line opens the chapter with the animation.', 'Отмечайте по ходу. Каждая строка открывает главу с анимацией.')}</p>
    <ul class="checklist">${checklist.map(([text, link], i) => `<li class="${done.includes(i) ? 'done' : ''}"><input type="checkbox" id="c${i}" ${done.includes(i) ? 'checked' : ''}><label for="c${i}" style="flex:1">${esc(text)}</label><a class="muted" href="${link}">›</a></li>`).join('')}</ul>
    <section>
      <h2>${t('The buttons', 'Кнопки')}</h2>
      <div class="panel" style="margin-top:10px">${buttons.map(([sym, name, what]) => `<div class="card"><div class="sym">${esc(sym)}</div><h3>${esc(name)}</h3><p class="small">${esc(what)}</p></div>`).join('')}</div>
    </section>
    <section class="card">
      <h2>${t('What the display is telling you', 'Что говорит дисплей')}</h2>
      <dl class="kv" style="margin-top:8px">${codes.map(([c, w]) => `<dt><span class="display">${esc(c)}</span></dt><dd>${esc(w)}</dd>`).join('')}</dl>
    </section>
    <section class="card">
      <h2>${t('Which stitch for the first evening', 'Какие строчки в первый вечер')}</h2>
      <div class="row" style="margin-top:8px;gap:14px">${[0, 2, 5, 13, 10, 16].map((n) => stitchChip(n)).join('')}</div>
      <p class="muted" style="margin-top:8px">${t('Sew each on a folded cotton scrap. Then the same on a silk scrap with 05 to see why 05 beats 02 there.', 'Прошейте каждую на сложенном хлопковом лоскуте. Потом то же на шёлковом лоскуте с 05, чтобы увидеть, почему там 05 лучше 02.')}</p>
    </section>
    <section class="card">
      <h2>${t('What is in the box', 'Что в коробке')}</h2>
      <dl class="kv" style="margin-top:8px">${kit.map(([k, w]) => `<dt>${esc(k)}</dt><dd>${esc(w)}</dd>`).join('')}</dl>
    </section>
    <section class="card">
      <h2>${t('Three habits from day one', 'Три привычки с первого дня')}</h2>
      <ul class="plain">
        <li>${t('Foot up when threading, foot down before sewing. Check both every time.', 'Лапка вверх при заправке, лапка вниз перед шитьём. Проверяйте обе каждый раз.')}</li>
        <li>${t('New needle per project; the right needle per fabric.', 'Новая игла на проект; правильная игла для ткани.')}</li>
        <li>${t('Test on a scrap of the same fabric, both sides, before touching the real thing.', 'Проба на лоскуте той же ткани, с обеих сторон, прежде чем трогать изделие.')}</li>
      </ul>
    </section>
  </div>`);
  root.appendChild(page);
  page.querySelectorAll('.checklist input').forEach((cb, i) =>
    cb.addEventListener('change', () => {
      cb.closest('li').classList.toggle('done', cb.checked);
      done = cb.checked ? [...new Set([...done, i])] : done.filter((x) => x !== i);
      try {
        localStorage.setItem(KEY, JSON.stringify(done));
      } catch {
        /* ignore */
      }
    }),
  );
  askButton(page, ctx);
}
