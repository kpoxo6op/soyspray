// Settings per fabric. Needle sizes follow the manual's needle types; everything else is
// standard sewing practice for this class of machine, written as starting points to test on a scrap.
const t = (en, ru) => ({ en, ru });

export const FABRIC_LIST = [
  {
    id: 'cotton',
    name: t('Cotton & linen', 'Хлопок и лён'),
    examples: t('Quilting cotton, poplin, linen, chambray, pincushion and table-runner fabric', 'Хлопок для квилта, поплин, лён, шамбре, ткань для игольницы и дорожки'),
    needle: t('Universal 80/12 (70/10 for fine lawn, 90/14 for heavy linen)', 'Универсальная 80/12 (70/10 для батиста, 90/14 для плотного льна)'),
    thread: t('All-purpose polyester or cotton 50', 'Универсальный полиэстер или хлопок 50'),
    tension: '4', pressure: t('N', 'N'), idt: true, foot: '0A',
    seam: { no: 0, len: 2.5, wid: null },
    edge: { no: 5, len: 1.0, wid: 5 }, edgeAlt: [2, 14, 13],
    hem: { no: 10, len: 2.5, wid: 2 },
    notes: [
      t('Pre-wash fabric for anything that will be washed. Press seams open as you go.', 'Стирайте ткань заранее, если изделие будут стирать. Разутюживайте швы по ходу.'),
      t('Decorative stitches sit beautifully on cotton: this is the fabric to play with the stitch library on.', 'Декоративные строчки отлично ложатся на хлопок: на этой ткани и стоит играть с библиотекой строчек.'),
    ],
  },
  {
    id: 'silk',
    name: t('Silk & fine fabrics', 'Шёлк и тонкие ткани'),
    examples: t('Silk, satin, chiffon, viscose, lining', 'Шёлк, атлас, шифон, вискоза, подкладка'),
    needle: t('Microtex (sharp) 60/8 or 70/10, brand new', 'Microtex (острая) 60/8 или 70/10, новая'),
    thread: t('Fine polyester or silk thread, 60 to 80 weight', 'Тонкий полиэстер или шёлковая нить, 60–80'),
    tension: '3 – 3.5', pressure: t('Half a turn anticlockwise from N', 'Полоборота против часовой от N'), idt: true, foot: '0A',
    seam: { no: 0, len: 2.0, wid: null },
    edge: { no: 5, len: 1.0, wid: 4 }, edgeAlt: [2, 13],
    hem: { no: 0, len: 2.0, wid: null },
    notes: [
      t('Zigzag chews silk because the swing pulls the thin fabric into a ridge. Use three-step zigzag 05, or a narrow zigzag (width 2.5, length 1.5) sewn 1 cm from the edge over tissue paper, then trim. Best of all: a French seam, two straight seams and no raw edge.', 'Зигзаг «сжёвывает» шёлк, потому что размах стягивает тонкую ткань в валик. Берите трёхступенчатый зигзаг 05, или узкий зигзаг (ширина 2,5, длина 1,5) на 1 см от среза поверх папиросной бумаги, потом срезать. Лучше всего — французский шов: два прямых шва и никакого открытого среза.'),
      t('IDT on, always. Fine pins inside the seam allowance only. Hold the thread tails when starting so the fabric is not pulled into the plate.', 'IDT всегда включён. Тонкие булавки только внутри припуска. В начале держите хвостики нитей, чтобы ткань не затянуло в пластину.'),
      t('Hem: a narrow double-fold hem with stitch 00 at 2.0 mm, or the blind hem 10 at width 1.5 on heavier silk.', 'Подгиб: узкий двойной подгиб строчкой 00 на 2,0 мм, или потайной 10 с шириной 1,5 на плотном шёлке.'),
    ],
  },
  {
    id: 'upholstery',
    name: t('Upholstery & canvas', 'Обивочная ткань и канвас'),
    examples: t('Cushion-weight cotton, jacquard, canvas, furnishing linen', 'Плотный хлопок для подушек, жаккард, канвас, мебельный лён'),
    needle: t('Jeans/denim 90/14 or 100/16', 'Джинсовая 90/14 или 100/16'),
    thread: t('Polyester 40 or upholstery thread; same in the bobbin', 'Полиэстер 40 или обивочная нить; в шпульке та же'),
    tension: '4 – 5', pressure: t('Half a turn clockwise from N for thick, stiff cloth', 'Полоборота по часовой от N для толстой жёсткой ткани'), idt: true, foot: '0A',
    seam: { no: 0, len: 3.0, wid: null }, seamAlt: [1],
    edge: { no: 14, len: 2.5, wid: 5 }, edgeAlt: [2, 13],
    hem: { no: 0, len: 3.0, wid: null },
    notes: [
      t('Piping: zipper foot 4 on the side away from the cord, needle moved towards the cord with the width buttons, length 3.0. Second pass closer than the first.', 'Кант: лапка для молнии 4 со стороны, противоположной шнуру, игла сдвинута к шнуру кнопками ширины, длина 3,0. Второй проход ближе первого.'),
      t('Thick corners: stop with the needle down, raise the foot, pivot. Use the multi-purpose tool under the back of the foot to climb over a bulky seam.', 'Толстые углы: остановитесь с иглой внизу, поднимите лапку, поверните. Подложите универсальный инструмент под заднюю часть лапки, чтобы переехать толстый шов.'),
      t('The motor can report EL (overload) on many layers. Slow down, use the handwheel over the thickest spot.', 'На многих слоях мотор может показать EL (перегрузка). Замедлитесь, самое толстое место пройдите маховиком.'),
    ],
  },
  {
    id: 'velvet',
    name: t('Thick velvet & pile', 'Толстый бархат и ворс'),
    examples: t('Cotton velvet, velveteen, corduroy, fleece, towelling', 'Хлопковый бархат, вельвет, флис, махра'),
    needle: t('Universal 90/14 (stretch 90/14 for stretch velvet)', 'Универсальная 90/14 (stretch 90/14 для стрейч-бархата)'),
    thread: t('Polyester 40 to 50', 'Полиэстер 40–50'),
    tension: '3.5 – 4', pressure: t('A little LESS than N so the pile is not crushed', 'Чуть МЕНЬШЕ N, чтобы не примять ворс'), idt: true, foot: '0A',
    seam: { no: 0, len: 3.0, wid: null },
    edge: { no: 14, len: 3.0, wid: 5 }, edgeAlt: [2, 27],
    hem: { no: 27, len: 3.0, wid: 6 }, hemAlt: [10],
    notes: [
      t('IDT is the whole point here: without it the top layer creeps and the pile shifts. Pin every 5 cm, pins across the seam, sew with the nap (stroke the fabric: sew in the smooth direction).', 'Здесь IDT — главное: без него верхний слой ползёт и ворс смещается. Булавки каждые 5 см поперёк шва, шейте по ворсу (погладьте ткань: шейте в гладкую сторону).'),
      t('Never press velvet flat. Steam from the back over a towel. Blanket stitch 27 along a folded edge makes a beautiful throw edge.', 'Никогда не утюжьте бархат плоско. Отпаривайте с изнанки на полотенце. Одеяльная строчка 27 по подогнутому краю — красивый край пледа.'),
      t('Clean the bobbin area after every velvet project; the lint is enormous.', 'Чистите шпульный отсек после каждого проекта с бархатом; пуха очень много.'),
    ],
  },
  {
    id: 'knit',
    name: t('Knits & stretch', 'Трикотаж и стрейч'),
    examples: t('Jersey, T-shirt knit, fleece, stretch velvet, ribbing', 'Джерси, футболочный трикотаж, флис, стрейч-бархат, рибана'),
    needle: t('Stretch 75/11 (ballpoint) — yellow band', 'Stretch 75/11 (шариковая) — жёлтая полоса'),
    thread: t('Polyester', 'Полиэстер'),
    tension: '3.5 – 4', pressure: t('Slightly less than N', 'Чуть меньше N'), idt: true, foot: '0A',
    seam: { no: 12, len: 2.5, wid: 1.5 }, seamAlt: [13, 15, 1],
    edge: { no: 13, len: 2.5, wid: 5 }, edgeAlt: [5],
    hem: { no: 11, len: 2.5, wid: 2.5 }, hemAlt: [4, 9],
    notes: [
      t('Never stretch the fabric as you sew unless you want ruffles. Let IDT do the feeding.', 'Не растягивайте ткань во время шитья, если не хотите волн. Пусть IDT двигает ткань.'),
      t('Skipped stitches on knits: wrong needle. Stretch 75/11, fresh.', 'Пропуски на трикотаже — не та игла. Stretch 75/11, новая.'),
    ],
  },
  {
    id: 'denim',
    name: t('Denim & heavy layers', 'Джинса и толстые слои'),
    examples: t('Denim, canvas bags, several layers of cotton', 'Джинса, сумки из канваса, несколько слоёв хлопка'),
    needle: t('Jeans 100/16 — blue band', 'Джинсовая 100/16 — синяя полоса'),
    thread: t('Polyester 40, topstitching thread 30 in the needle only', 'Полиэстер 40, нить для отстрочки 30 только в игле'),
    tension: '4 – 5', pressure: t('Clockwise from N', 'По часовой от N'), idt: true, foot: '0A',
    seam: { no: 0, len: 3.0, wid: null }, seamAlt: [1],
    edge: { no: 14, len: 3.0, wid: 5 },
    hem: { no: 0, len: 3.5, wid: null },
    notes: [t('Jeans hem over the side seam: multi-purpose tool under the back of the foot, handwheel over the thickest spot.', 'Подгиб джинсов через боковой шов: универсальный инструмент под заднюю часть лапки, маховик на самом толстом месте.')],
  },
];

export const fabricById = (id) => FABRIC_LIST.find((f) => f.id === id);
