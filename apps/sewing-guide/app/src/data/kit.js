// Everything in the box, what it is for, and where it shows up in the projects. Numbers
// follow the manual's accessory list (35-43); feet carry their printed codes.
const t = (en, ru) => ({ en, ru });

// Small line icons, 64x64 viewBox, stroke only.
const ICONS = {
  foot0A: '<path d="M14 40h30l8-10v-6H26l-6 6h-6z"/><path d="M28 24v-8h8v8"/><path d="M36 30h4"/>',
  foot1A: '<path d="M14 40h30l8-10v-6H26l-6 6h-6z"/><path d="M28 24v-8h8v8"/><path d="M20 36h22" stroke-dasharray="3 2"/>',
  foot2A: '<path d="M14 40h30l8-10v-6H26l-6 6h-6z"/><path d="M28 24v-8h8v8"/><path d="M22 34h18M22 37h18"/>',
  foot3: '<path d="M14 40h30l8-10v-6H26l-6 6h-6z"/><path d="M28 24v-8h8v8"/><path d="M16 28v12" stroke-width="3"/>',
  foot4: '<path d="M30 40h14l8-10v-6H38l-6 6h-2z"/><path d="M36 24v-8h8v8"/><path d="M22 20v22" stroke-dasharray="2 3"/>',
  foot5B: '<rect x="22" y="8" width="20" height="48" rx="4"/><rect x="27" y="14" width="10" height="16"/><circle cx="32" cy="46" r="4"/>',
  bobbin: '<circle cx="32" cy="32" r="16"/><circle cx="32" cy="32" r="5"/><path d="M18 26h28M18 38h28" stroke-dasharray="2 2"/>',
  felt: '<circle cx="32" cy="32" r="18"/><circle cx="32" cy="32" r="2"/>',
  screwdriver: '<path d="M10 54l14-14"/><rect x="22" y="22" width="24" height="12" rx="6" transform="rotate(-45 34 28)"/><path d="M40 10l14 14"/>',
  multitool: '<path d="M14 16h12v12l10 10 12-12v-8"/><path d="M26 28l-12 12v8h8l14-14"/>',
  capLarge: '<ellipse cx="32" cy="40" rx="22" ry="7"/><path d="M24 40v-14a8 4 0 0 1 16 0v14"/>',
  capSmall: '<ellipse cx="32" cy="40" rx="12" ry="4"/><path d="M26 40v-10a6 3 0 0 1 12 0v10"/>',
  ripper: '<path d="M12 52l28-28"/><path d="M40 24l10-10 4 4-8 8"/><circle cx="46" cy="22" r="2"/><path d="M14 12h10M14 16h10M14 20h10" />',
  guide: '<path d="M14 50V14h8v24h28"/><circle cx="18" cy="42" r="2"/>',
  auxpin: '<path d="M32 10v44"/><path d="M26 54h12"/><ellipse cx="32" cy="24" rx="7" ry="3"/>',
  pedal: '<path d="M8 44l8-16h32l8 16z"/><path d="M14 36h36M12 40h40"/><path d="M48 28c8-6 12-10 8-18"/>',
  cord: '<path d="M8 32c8-12 16 12 24 0s16-12 24 0"/><rect x="48" y="26" width="10" height="12" rx="2"/>',
  needles: '<path d="M20 8v48M32 8v48M44 8v48"/><circle cx="20" cy="46" r="1.5"/><circle cx="32" cy="46" r="1.5"/><circle cx="44" cy="46" r="1.5"/>',
  cover: '<path d="M10 52V22a12 12 0 0 1 12-12h20a12 12 0 0 1 12 12v30"/><path d="M24 10v-4h16v4"/>',
  card: '<rect x="18" y="8" width="28" height="48" rx="3"/><path d="M24 16h16M24 22h16M24 28h16M24 34h16M24 40h16"/>',
};

export const KIT = [
  {
    id: 'foot-0a', group: 'feet', icon: ICONS.foot0A, code: '0A', idt: true,
    name: t('Standard presser foot 0A', 'Стандартная лапка 0A'),
    what: t('The foot that is on the machine when it arrives. Flat, wide, with the cut-out at the back that lets IDT clip on. For straight stitch and any zigzag longer than 1.0 mm.', 'Лапка, которая стоит на машине с завода. Плоская, широкая, с вырезом сзади, за который цепляется IDT. Для прямой строчки и любого зигзага длиннее 1,0 мм.'),
    examples: [
      t('Every seam of the pincushion and the cushion cover.', 'Все швы игольницы и чехла подушки.'),
      t('Overcasting with 05, 13 or 14 along a raw edge.', 'Обмётка строчкой 05, 13 или 14 по срезу.'),
      t('Topstitching 3 mm from a folded edge, using the plate lines.', 'Отстрочка в 3 мм от сгиба по линиям на пластине.'),
    ],
    link: ['stitches', '00'],
  },
  {
    id: 'foot-1a', group: 'feet', icon: ICONS.foot1A, code: '1A', idt: true,
    name: t('Fancy stitch foot 1A', 'Лапка для декоративных строчек 1A'),
    what: t('Looks like 0A but has a shallow groove underneath, so a raised decorative row slides under it instead of being flattened or caught. Still has the IDT cut-out.', 'Похожа на 0A, но снизу есть неглубокая канавка: выпуклая декоративная строчка проходит под ней, а не сплющивается и не цепляется. Вырез под IDT есть.'),
    examples: [
      t('The vine 80 or feather 36 along the table runner, with stabilizer.', 'Лоза 80 или ёлочка 36 вдоль дорожки, со стабилизатором.'),
      t('Blanket stitch 27 around the throw edge.', 'Одеяльная строчка 27 по краю пледа.'),
      t('Stitch-in-the-ditch quilting: the centre mark follows the seam.', 'Стёжка «в шов»: центральная метка идёт по шву.'),
    ],
    link: ['stitches', '80'],
  },
  {
    id: 'foot-2a', group: 'feet', icon: ICONS.foot2A, code: '2A', idt: false,
    name: t('Fancy stitch foot 2A', 'Лапка для декоративных строчек 2A'),
    what: t('A deeper groove for dense satin stitching under 1.0 mm long. No IDT cut-out: release IDT before snapping it on.', 'Более глубокая канавка для плотной глади с длиной меньше 1,0 мм. Выреза под IDT нет: отключите IDT, прежде чем надевать.'),
    examples: [
      t('Scalloped edge 67 on the runner ends, then trim outside the scallops.', 'Фестончатый край 67 на концах дорожки, потом срезать за фестонами.'),
      t('Appliqué with the Z-zigzag 03 or satin bar 78 over a raw edge.', 'Аппликация Z-зигзагом 03 или гладьевой полосой 78 по срезу.'),
      t('Any stitch where the info button shows 2A.', 'Любая строчка, для которой кнопка «i» показывает 2A.'),
    ],
    link: ['stitches', '67'],
  },
  {
    id: 'foot-3', group: 'feet', icon: ICONS.foot3, code: '3', idt: true,
    name: t('Blindhem foot 3', 'Лапка для потайного шва 3'),
    what: t('A metal toe and a red adjustable guide that rides along the fold of a hem; the needle swings over it to bite one or two threads. Turn the screw to set how deep the bite is.', 'Металлический носок и красный регулируемый ограничитель, который идёт по сгибу подгиба; игла перепрыгивает через него и цепляет одну-две нити. Винт задаёт глубину захвата.'),
    examples: [
      t('Invisible hem on the table runner with stitch 10.', 'Невидимый подгиб дорожки строчкой 10.'),
      t('Trousers and curtains: hem without a visible line.', 'Брюки и шторы: подгиб без видимой строчки.'),
      t('Elastic blind hem 11 on a fleece blanket.', 'Эластичный потайной подгиб 11 на флисовом пледе.'),
    ],
    link: ['stitches', '10'],
  },
  {
    id: 'foot-4', group: 'feet', icon: ICONS.foot4, code: '4', idt: true,
    name: t('Zipper foot 4', 'Лапка для молнии 4'),
    what: t('A narrow foot that snaps on to the LEFT or RIGHT of the needle, so the foot sits beside the zip teeth or the piping cord while the needle sews right next to them. Move the needle with the width buttons, only towards the foot\'s open side. This is your "one-sided foot" from class.', 'Узкая лапка, которая пристёгивается СЛЕВА или СПРАВА от иглы: лапка идёт рядом с зубцами молнии или шнуром канта, а игла шьёт вплотную. Сдвигайте иглу кнопками ширины, только в открытую сторону лапки. Это ваша «односторонняя лапка» из класса.'),
    examples: [
      t('Making and inserting the piping on the cushion cover.', 'Изготовление и вшивание канта на чехле подушки.'),
      t('An invisible or centred zip in a cushion back.', 'Потайная или центральная молния на спинке подушки.'),
      t('Sewing next to any thick cord or edge the standard foot cannot straddle.', 'Шитьё рядом с любым толстым шнуром или краем, который стандартная лапка не может оседлать.'),
    ],
    link: ['projects', 'piped-cushion'],
  },
  {
    id: 'foot-5b', group: 'feet', icon: ICONS.foot5B, code: '5B', idt: false,
    name: t('One-step buttonhole foot 5B', 'Лапка для петли 5B'),
    what: t('Long foot with a sliding plate at the back: put the button in it and the machine sews a buttonhole exactly that size. Needs the buttonhole lever pulled down. IDT off.', 'Длинная лапка с выдвижной пластиной сзади: вставьте пуговицу, и машина сошьёт петлю ровно такого размера. Нужно опустить рычаг петли. IDT выключен.'),
    examples: [
      t('Buttons on a cushion back instead of a zip.', 'Пуговицы на спинке подушки вместо молнии.'),
      t('A pillowcase with a buttoned end (stitch 16).', 'Наволочка с застёжкой на пуговицах (строчка 16).'),
      t('Darning with stitch 21 can also use this foot.', 'Штопка строчкой 21 тоже может использовать эту лапку.'),
    ],
    link: ['machine', 'buttonhole'],
  },
  {
    id: 'bobbins', group: 'thread', icon: ICONS.bobbin, no: 35,
    name: t('Bobbins, 5 (#416475801)', 'Шпульки, 5 шт. (#416475801)'),
    what: t('Clear plastic bobbins for the drop-in bobbin case. Only this exact part fits; a bobbin from another machine looks the same and jams.', 'Прозрачные пластиковые шпульки для горизонтального челнока. Подходит только эта деталь; шпулька от другой машины выглядит так же и заклинивает.'),
    examples: [
      t('Wind one per thread colour before a project; keep the wound ones in the tray.', 'Намотайте по одной на каждый цвет нити перед проектом; храните намотанные в лотке.'),
      t('Hand-wind elastic thread for honeycomb shirring with stitch 06.', 'Намотайте вручную эластичную нить для сборки-буфов строчкой 06.'),
    ],
    link: ['machine', 'wind'],
  },
  {
    id: 'felt', group: 'thread', icon: ICONS.felt, no: 36,
    name: t('Felt pad', 'Фетровая прокладка'),
    what: t('A felt disc that goes under the spool when the spool pin is upright, so the spool turns smoothly and does not rattle or unwind too fast.', 'Фетровый кружок под катушку при вертикальном стержне: катушка вращается плавно, не дребезжит и не разматывается слишком быстро.'),
    examples: [
      t('Vertical spool pin for metallic or silk thread on the runner decoration.', 'Вертикальный стержень для металлика или шёлковой нити в декоре дорожки.'),
      t('Under the second spool on the auxiliary pin for twin-needle hems.', 'Под второй катушкой на дополнительном стержне для подгиба двойной иглой.'),
    ],
    link: ['machine', 'spool'],
  },
  {
    id: 'screwdriver', group: 'tools', icon: ICONS.screwdriver, no: 37,
    name: t('Screwdriver for the needle plate', 'Отвёртка для игольной пластины'),
    what: t('Fits the two plate screws and the needle screw when it is stiff.', 'Подходит к двум винтам пластины и к винту иглы, если он тугой.'),
    examples: [
      t('Cleaning lint from the feed dogs after velvet or fleece.', 'Чистка пуха с транспортёра после бархата или флиса.'),
      t('Tightening the needle screw properly after a needle change.', 'Затяжка винта иглы после замены иглы.'),
    ],
    link: ['machine', 'clean'],
  },
  {
    id: 'multitool', group: 'tools', icon: ICONS.multitool, no: 38,
    name: t('Multi-purpose tool', 'Универсальный инструмент'),
    what: t('A grey plastic wedge with a hole. Three jobs: holds the needle while you change it, levels the presser foot when it climbs a thick seam, and makes a thread shank under a button.', 'Серый пластиковый клин с отверстием. Три задачи: держит иглу при замене, выравнивает лапку при переезде толстого шва, делает ножку из нити под пуговицей.'),
    examples: [
      t('Jeans hem: slide the thick side under the back of the foot before the side seam.', 'Подгиб джинсов: подложите толстую сторону под заднюю часть лапки перед боковым швом.'),
      t('Cushion corners where the piping doubles up.', 'Углы подушки, где кант идёт в два слоя.'),
      t('Sewing on a coat button with stitch 20: the tool under the button leaves room for the fabric.', 'Пришивание пуговицы пальто строчкой 20: инструмент под пуговицей оставляет место для ткани.'),
    ],
    link: ['machine', 'needle'],
  },
  {
    id: 'cap-large', group: 'thread', icon: ICONS.capLarge, no: 39,
    name: t('Spool caps, large (2)', 'Фиксаторы катушки, большие (2)'),
    what: t('Discs that slide onto the spool pin on either side of the spool. The flat side presses against the spool; choose the cap just bigger than the spool so the thread cannot slip under it.', 'Диски, которые надеваются на стержень с обеих сторон катушки. Плоская сторона к катушке; берите фиксатор чуть больше катушки, чтобы нить не проскальзывала под него.'),
    examples: [
      t('Normal 1000 m polyester spools: large cap both sides.', 'Обычные катушки полиэстера 1000 м: большой фиксатор с обеих сторон.'),
      t('Thread breaking at the spool: the cap is the wrong size or has a gap.', 'Нить рвётся у катушки: фиксатор не того размера или с зазором.'),
    ],
    link: ['machine', 'spool'],
  },
  {
    id: 'cap-small', group: 'thread', icon: ICONS.capSmall, no: 40,
    name: t('Spool cap, small', 'Фиксатор катушки, малый'),
    what: t('For narrow spools: small cap in front, large cap behind.', 'Для узких катушек: малый фиксатор спереди, большой сзади.'),
    examples: [t('Small 200 m spools of hand-sewing or silk thread.', 'Маленькие катушки 200 м для ручного шитья или шёлковой нити.')],
    link: ['machine', 'spool'],
  },
  {
    id: 'ripper', group: 'tools', icon: ICONS.ripper, no: 41,
    name: t('Seam ripper and brush', 'Вспарыватель с кисточкой'),
    what: t('One handle, two ends: the hooked blade cuts stitches, the brush sweeps lint. The little red ball goes down into the seam so you do not cut the fabric.', 'Одна ручка, два конца: крючок-лезвие режет стежки, кисточка сметает пух. Красный шарик идёт внутрь шва, чтобы не порезать ткань.'),
    examples: [
      t('Opening a buttonhole: pin across the bartack, cut from the middle to the pin.', 'Прорезать петлю: булавка поперёк закрепки, резать от середины к булавке.'),
      t('Unpicking a wandering seam on the pincushion.', 'Распороть кривой шов на игольнице.'),
      t('Brushing the bobbin area every few projects.', 'Чистить шпульный отсек каждые несколько проектов.'),
    ],
    link: ['machine', 'clean'],
  },
  {
    id: 'guide', group: 'tools', icon: ICONS.guide, no: 42,
    name: t('Edge guide', 'Направитель (линейка)'),
    what: t('The L-shaped metal bar. It slides into the hole in the presser foot holder and is tightened with the holder screw; its foot rides on the fabric at a set distance from the needle.', 'Г-образная металлическая планка. Вставляется в отверстие держателя лапки и зажимается винтом держателя; её ножка идёт по ткани на заданном расстоянии от иглы.'),
    examples: [
      t('Parallel quilting rows 8 cm apart on the blanket without marking.', 'Параллельные ряды стёжки через 8 см на пледе без разметки.'),
      t('A second decorative row exactly 1 cm inside the first on the runner.', 'Второй декоративный ряд ровно на 1 см внутрь от первого на дорожке.'),
      t('Wide seam allowances beyond the plate lines.', 'Широкие припуски за пределами линий пластины.'),
    ],
    link: ['projects', 'blanket'],
  },
  {
    id: 'auxpin', group: 'thread', icon: ICONS.auxpin, no: 43,
    name: t('Auxiliary spool pin', 'Дополнительный стержень катушки'),
    what: t('A loose pin that plugs into the hole at the top right. It carries a second spool.', 'Отдельный стержень, который вставляется в отверстие справа сверху. Несёт вторую катушку.'),
    examples: [
      t('Wind a bobbin from a second spool without unthreading the machine.', 'Намотать шпульку со второй катушки, не распуская заправку машины.'),
      t('Twin-needle topstitching on a knit hem: two threads, one each pin.', 'Отстрочка двойной иглой на трикотажном подгибе: две нити, по одной на стержень.'),
    ],
    link: ['machine', 'spool'],
  },
  {
    id: 'pedal', group: 'power', icon: ICONS.pedal,
    name: t('Foot control (model C-9002)', 'Педаль (модель C-9002)'),
    what: t('Plugs into the FRONT socket. Light pressure sews slowly; the speed slider caps the maximum. A tap without sewing moves the needle up or down.', 'Вставляется в ПЕРЕДНИЙ разъём. Лёгкое нажатие — медленно; ползунок скорости ограничивает максимум. Короткое нажатие без шитья поднимает или опускает иглу.'),
    examples: [
      t('Corners: tap once to put the needle down, lift the foot, pivot.', 'Углы: одно нажатие — игла вниз, поднять лапку, повернуть.'),
      t('Buttonholes and satin rows: slider at one third, pedal fully down for a steady speed.', 'Петли и гладьевые ряды: ползунок на треть, педаль до упора для ровной скорости.'),
    ],
    link: ['machine', 'power'],
  },
  {
    id: 'cord', group: 'power', icon: ICONS.cord,
    name: t('Power cord', 'Шнур питания'),
    what: t('Plugs into the REAR socket. Unplug from the wall first, then from the machine; coil loosely for storage.', 'Вставляется в ЗАДНИЙ разъём. Выключать сначала из розетки, потом из машины; хранить смотанным свободными кольцами.'),
    examples: [t('Packing away: see the chapter.', 'Уборка: смотрите главу.')],
    link: ['machine', 'pack'],
  },
  {
    id: 'needles', group: 'thread', icon: ICONS.needles,
    name: t('Needles (system 130/705 H)', 'Иглы (система 130/705 H)'),
    what: t('A starter pack of universal needles in common sizes. Only this system fits. Buy the types your fabrics need: Microtex for silk, jeans for upholstery, stretch for knits, embroidery for rayon thread, wing for hemstitching.', 'Стартовый набор универсальных игл ходовых размеров. Подходит только эта система. Докупите типы под свои ткани: Microtex для шёлка, джинсовая для обивки, stretch для трикотажа, вышивальная для вискозной нити, wing для мережки.'),
    examples: [
      t('80/12 universal for the pincushion and runner.', '80/12 универсальная для игольницы и дорожки.'),
      t('90/14 jeans for the piped cushion in upholstery fabric.', '90/14 джинсовая для подушки с кантом из обивочной ткани.'),
      t('A new needle every project.', 'Новая игла на каждый проект.'),
    ],
    link: ['fabrics'],
  },
  {
    id: 'cover', group: 'power', icon: ICONS.cover,
    name: t('Hard cover', 'Жёсткий чехол'),
    what: t('Lifts straight off the top. Keeps dust out of the bobbin area and protects the machine when carried by the handle.', 'Снимается вверх. Защищает от пыли шпульный отсек и машину при переноске за ручку.'),
    examples: [t('On whenever the machine is not in use; the foot control and cord fit underneath in the space above the free arm.', 'Надевать всегда, когда машина не используется; педаль и шнур помещаются под ним в пространстве над свободным рукавом.')],
    link: ['machine', 'pack'],
  },
  {
    id: 'card', group: 'power', icon: ICONS.card,
    name: t('Pull-out stitch card', 'Выдвижная карта строчек'),
    what: t('Built into the right side of the machine. All 100 stitches with their numbers; pull it out to the right. The same pictures are in the Stitches section, drawn live.', 'Встроена в правую сторону машины. Все 100 строчек с номерами; выдвигается вправо. Те же картинки есть в разделе «Строчки», нарисованные вживую.'),
    examples: [t('Find the number, press the two digits, press the info button to see the foot.', 'Найдите номер, нажмите две цифры, нажмите «i», чтобы увидеть лапку.')],
    link: ['stitches'],
  },
];

export const KIT_GROUPS = [
  { id: 'feet', name: t('Presser feet', 'Лапки') },
  { id: 'thread', name: t('Thread and bobbin', 'Нить и шпулька') },
  { id: 'tools', name: t('Tools', 'Инструменты') },
  { id: 'power', name: t('Power, cover and card', 'Питание, чехол и карта') },
];

export const kitById = (id) => KIT.find((k) => k.id === id);
