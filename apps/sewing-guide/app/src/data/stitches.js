// The 100 stitches of the passport 3.0. Names 00-21 and the "manual" lines are the
// owner's manual's words. Names 22-99 are ours: the manual shows those only as pictures.
// Length/width defaults are starting points for Irina's fabrics; the machine shows its own
// default on the display when a stitch is selected. Max width 7 mm, max length 4.5 mm.
import { GEOMETRY } from './stitch-geometry.js';

const t = (en, ru) => ({ en, ru });
const L = (def, min = 0.3, max = 4.5) => ({ def, min, max });
const W = (def, min = 0, max = 7) => ({ def, min, max });
const SATIN_L = L(0.4, 0.2, 1.5);

// uses: [{ en, ru, fabrics: ['cotton','silk','upholstery','velvet','knit','denim'] }]
const u = (en, ru, fabrics = []) => ({ en, ru, fabrics });

const S = [];
const add = (rec) => S.push(rec);

// ---------------------------------------------------------------- utility
add({
  no: 0, cat: 'utility', official: true,
  name: t('Straight stitch', 'Прямая строчка'),
  manual: t('For seaming and topstitching. Select from 29 different needle positions.', 'Для стачивания и отстрочки. 29 положений иглы.'),
  foot: '0A', idt: true, length: L(2.5), width: W(3.5, 0, 7), positionOnly: true,
  uses: [
    u('Every seam on cotton, upholstery and velvet. 2.5 mm is the all-round length; 3.0 to 3.5 mm on thick upholstery and velvet so the thread sits flat.', 'Все швы на хлопке, обивочной ткани и бархате. 2,5 мм — универсальная длина; 3,0–3,5 мм на толстой обивке и бархате, чтобы нить лежала ровно.', ['cotton', 'upholstery', 'velvet']),
    u('Silk: 2.0 mm, new 60/8 or 70/10 Microtex needle, tension one notch lower, IDT engaged. A short stitch and a fresh fine needle are what stop silk from puckering.', 'Шёлк: 2,0 мм, новая игла Microtex 60/8 или 70/10, натяжение на деление ниже, IDT включён. Короткий стежок и свежая тонкая игла — вот что спасает шёлк от сборок.', ['silk']),
    u('Topstitching and piping: 3.0 to 3.5 mm, move the needle with the width buttons so it runs exactly where you want (3.5 on the display is centre).', 'Отстрочка и кант: 3,0–3,5 мм, сдвигайте иглу кнопками ширины, чтобы строчка шла ровно там, где нужно (3.5 на дисплее — центр).', ['cotton', 'upholstery']),
    u('Basting: 4.5 mm, tension lowered to 2, easy to pull out later.', 'Намётка: 4,5 мм, натяжение 2, потом легко выдёргивается.'),
  ],
  tips: [t('The width buttons move the needle for this stitch. Use that for the zipper foot and for piping: put the needle right against the cord.', 'Кнопки ширины у этой строчки сдвигают иглу. Это нужно для лапки для молнии и для канта: поставьте иглу вплотную к шнуру.')],
});
add({
  no: 1, cat: 'utility', official: true,
  name: t('Stretch triple straight stitch', 'Тройная усиленная прямая строчка'),
  manual: t('Reinforced seam. Topstitching.', 'Усиленный шов. Отстрочка.'),
  foot: '0A', idt: true, length: L(2.5), width: W(3.5, 0, 7), positionOnly: true,
  uses: [
    u('Seams that take strain: cushion seams that get sat on, bag handles, crotch seams, blanket edges that get pulled.', 'Швы под нагрузкой: швы подушек, на которых сидят, ручки сумок, швы-сидения, края пледа, за которые тянут.', ['cotton', 'upholstery', 'denim']),
    u('Bold topstitching: the thread goes over each stitch three times, so it looks like heavy topstitching thread with ordinary thread.', 'Выразительная отстрочка: нить проходит по каждому стежку трижды, обычная нитка выглядит как толстая отстрочечная.', ['denim', 'upholstery']),
    u('Seams on knits that must stretch without breaking.', 'Швы на трикотаже, которые должны тянуться и не рваться.', ['knit']),
  ],
  tips: [t('Slow. It sews forward, back, forward. Do not pull the fabric or the stitches bunch.', 'Медленная: вперёд-назад-вперёд. Не тяните ткань, иначе стежки собьются в кучу.')],
});
add({
  no: 2, cat: 'utility', official: true,
  name: t('Zigzag stitch', 'Зигзаг'),
  manual: t('Reinforce seams, clean finish, stretch sewing, lace insertion.', 'Усиление швов, чистая обработка, эластичные швы, вшивание кружева.'),
  foot: '0A', idt: true, length: L(2.0), width: W(5.0),
  uses: [
    u('Finishing a raw edge on cotton, upholstery and velvet: width 4 to 5, length 2 to 2.5, right swing just off the edge.', 'Обмётка среза на хлопке, обивке и бархате: ширина 4–5, длина 2–2,5, правый укол чуть за краем ткани.', ['cotton', 'upholstery', 'velvet']),
    u('Silk: this is the stitch that chewed your silk. A wide zigzag pulls the fine fabric into a ridge (tunnelling). Fix: width 2 to 3, length 1.5, sew 1 cm inside the edge over tissue paper, then trim. Or use three-step zigzag 05, or a French seam instead.', 'Шёлк: именно эта строчка «сжёвывала» ваш шёлк. Широкий зигзаг стягивает тонкую ткань в валик (туннелинг). Решение: ширина 2–3, длина 1,5, шить на 1 см от среза поверх папиросной бумаги, потом срезать. Или трёхступенчатый зигзаг 05, или французский шов.', ['silk']),
    u('Sewing elastic, appliqué with a narrow zigzag (width 2, length 1), attaching lace.', 'Пришивание резинки, аппликация узким зигзагом (ширина 2, длина 1), пришивание кружева.'),
  ],
  tips: [t('Under 1.0 mm length switch to foot 2A and disengage IDT: the groove under 2A lets the dense stitching pass.', 'При длине меньше 1,0 мм поставьте лапку 2A и отключите IDT: канавка под 2A пропускает плотную строчку.')],
});
add({
  no: 3, cat: 'utility', official: true,
  name: t('Z-zigzag stitch', 'Z-зигзаг (плотный узкий)'),
  manual: t('Appliqué, couching, eyelets.', 'Аппликация, вшивание шнура, глазки.'),
  foot: '2A', idt: false, length: L(0.6, 0.2, 2), width: W(3.0),
  uses: [
    u('Appliqué edges: a tight zigzag that covers the raw edge of a shape stitched onto a cushion or table runner.', 'Края аппликации: плотный зигзаг закрывает срез фигуры, нашитой на подушку или дорожку.', ['cotton']),
    u('Couching: laying a cord or thick yarn on the fabric and zigzagging over it without piercing it. Set the width a little wider than the cord.', 'Кушинг: кладёте шнур или толстую пряжу на ткань и зигзагом пришиваете поверх, не прокалывая. Ширина чуть больше шнура.', ['cotton', 'upholstery']),
  ],
  tips: [t('Always stabilizer or interfacing under appliqué, otherwise the fabric gathers inside the stitch.', 'Под аппликацию всегда стабилизатор или флизелин, иначе ткань соберётся внутри строчки.')],
});
add({
  no: 4, cat: 'utility', official: true,
  name: t('Stretch triple zigzag stitch', 'Тройной эластичный зигзаг'),
  manual: t('Elastic stitch for decorative hems or topstitching.', 'Эластичная строчка для декоративных подгибов и отстрочки.'),
  foot: '0A', idt: true, length: L(2.5), width: W(5.0),
  uses: [
    u('A hem on a stretchy blanket or fleece that must stretch and still look bold.', 'Подгиб тянущегося пледа или флиса, который должен тянуться и выглядеть выразительно.', ['knit']),
    u('Decorative topstitching along a cushion edge with a contrast thread.', 'Декоративная отстрочка по краю подушки контрастной нитью.', ['cotton', 'upholstery']),
  ],
  tips: [],
});
add({
  no: 5, cat: 'utility', official: true,
  name: t('Three-step zigzag stitch', 'Трёхступенчатый зигзаг'),
  manual: t('Sewing elastic, darning, patching.', 'Пришивание резинки, штопка, заплаты.'),
  foot: '0A', idt: true, length: L(1.0, 0.3, 2.5), width: W(5.0),
  uses: [
    u('Edge finish on silk and anything thin. The needle lands three times across each swing, so the fabric cannot gather into a ridge. Width 4 to 5, length 1.0.', 'Обмётка среза на шёлке и всём тонком. Игла делает три укола на каждом размахе, ткань не может собраться в валик. Ширина 4–5, длина 1,0.', ['silk', 'cotton']),
    u('Sewing flat elastic to a cushion cover or fitted sheet: stretch the elastic as you sew.', 'Пришивание плоской резинки к чехлу подушки или простыне: растягивайте резинку во время шитья.'),
    u('Darning a worn spot or holding a patch on, with a scrap underneath.', 'Штопка протёртого места или заплата, с лоскутом снизу.'),
  ],
  tips: [t('This is the answer to "the zigzag chews my silk". Try it before anything else.', 'Это ответ на «зигзаг сжёвывает шёлк». Попробуйте его первым.')],
});
add({
  no: 6, cat: 'utility', official: true,
  name: t('Honeycomb stitch', 'Сотовая строчка'),
  manual: t('Decorative stitch for stretch fabrics and hems. Also used with elastic thread in the bobbin.', 'Декоративная строчка для эластичных тканей и подгибов. Также с эластичной нитью в шпульке.'),
  foot: '1A', idt: true, length: L(2.5), width: W(6.0),
  uses: [
    u('Shirring: wind elastic thread on the bobbin by hand and sew rows; the fabric gathers into smocking. Lovely on a cotton cushion front.', 'Сборка-буфы: намотайте эластичную нить на шпульку вручную и прошейте ряды; ткань соберётся в «вафли». Красиво на лицевой стороне хлопковой подушки.', ['cotton']),
    u('A decorative hem on a knit blanket that stretches.', 'Декоративный подгиб на трикотажном пледе, который тянется.', ['knit']),
  ],
  tips: [],
});
add({
  no: 7, cat: 'utility', official: true,
  name: t('Bridging stitch', 'Соединительная строчка (бриджинг)'),
  manual: t('Joining fabrics and quilt batting, decorative stitch for quilting, hemstitching.', 'Соединение тканей и ватина, декоративная строчка для квилтинга, мережка.'),
  foot: '1A', idt: true, length: L(2.5), width: W(6.0),
  uses: [
    u('Joining two pieces of batting or thick fabric edge to edge without overlap: no bulk in a blanket.', 'Соединение двух кусков ватина или толстой ткани встык, без нахлёста: в пледе не будет утолщения.', ['upholstery', 'velvet']),
    u('Fagoting: two folded edges 3 mm apart, stitch bridges the gap. Decorative on a table runner.', 'Фаготинг: два подогнутых края на расстоянии 3 мм, строчка перекидывается через зазор. Декоративно на дорожке.', ['cotton']),
  ],
  tips: [],
});
add({
  no: 8, cat: 'utility', official: true,
  name: t('Foundation elastic stitch', 'Эластичная соединительная строчка'),
  manual: t('Joining stitch for undergarments, terry cloth, leather, bulky fabrics where overlapping the seams.', 'Соединительная строчка для белья, махры, кожи, объёмных тканей при соединении внахлёст.'),
  foot: '0A', idt: true, length: L(2.5), width: W(5.0),
  uses: [
    u('Overlapped seams in thick velvet or towelling: lay one edge 1 cm over the other and sew flat, no seam allowance ridge.', 'Швы внахлёст на толстом бархате или махре: положите один край на другой на 1 см и прошейте плоско, без валика припуска.', ['velvet', 'upholstery']),
    u('Attaching elastic to lingerie-weight fabrics.', 'Пришивание резинки к тонким бельевым тканям.', ['knit']),
  ],
  tips: [],
});
add({
  no: 9, cat: 'utility', official: true,
  name: t('Crosshem stitch', 'Крестообразная подрубочная строчка'),
  manual: t('Elastic decorative hem for stretch fabrics.', 'Эластичный декоративный подгиб для эластичных тканей.'),
  foot: '1A', idt: true, length: L(3.0), width: W(6.0),
  uses: [
    u('Visible hem on a knit blanket or T-shirt that stretches and looks like hand cross stitch.', 'Видимый подгиб на трикотажном пледе или футболке: тянется и похож на ручной крестик.', ['knit']),
    u('A decorative border row on a cotton table runner.', 'Декоративный ряд-бордюр на хлопковой дорожке.', ['cotton']),
  ],
  tips: [],
});
add({
  no: 10, cat: 'utility', official: true,
  name: t('Blindhem stitch', 'Потайная подшивочная строчка'),
  manual: t('Sewing blindhems on woven fabrics.', 'Потайной подгиб на тканых материалах.'),
  foot: '3', idt: true, length: L(2.5), width: W(2.0, 0, 7),
  uses: [
    u('Invisible hem on curtains, trousers, a table runner or a woven blanket. The needle swings left once every four stitches and catches one or two threads of the fold.', 'Невидимый подгиб на шторах, брюках, дорожке или тканом пледе. Игла раз в четыре стежка уходит влево и захватывает одну-две нити сгиба.', ['cotton', 'upholstery']),
    u('Velvet: works, but test. If the bite shows on the right side, reduce width to 1.5.', 'Бархат: работает, но пробуйте. Если укол виден с лица, уменьшите ширину до 1,5.', ['velvet']),
  ],
  tips: [t('Fold the hem back on itself so 6 mm of the finished edge sticks out, wrong side up. The red guide on foot 3 rides along the fold. Turn the screw on the foot until the stitch just barely catches.', 'Сложите подгиб обратно на себя так, чтобы 6 мм обработанного края выступали, изнанкой вверх. Красный ограничитель лапки 3 идёт по сгибу. Крутите винт на лапке, пока стежок не станет едва цеплять сгиб.')],
});
add({
  no: 11, cat: 'utility', official: true,
  name: t('Elastic blindhem stitch', 'Эластичная потайная подшивочная'),
  manual: t('Sewing blindhems on stretch fabrics.', 'Потайной подгиб на эластичных тканях.'),
  foot: '3', idt: true, length: L(2.5), width: W(2.5, 0, 7),
  uses: [u('Blind hem on knits and fleece; the small zigzags let the hem stretch. No need to finish the raw edge first on most knits.', 'Потайной подгиб на трикотаже и флисе; маленькие зигзаги дают подгибу тянуться. На большинстве трикотажа срез можно не обмётывать.', ['knit'])],
  tips: [],
});
add({
  no: 12, cat: 'utility', official: true,
  name: t('Stretch tricot stitch', 'Трикотажная строчка'),
  manual: t('Sewing seams on stretch fabrics.', 'Швы на эластичных тканях.'),
  foot: '0A', idt: true, length: L(2.5), width: W(1.5, 0, 7),
  uses: [u('The seam stitch for knits and jersey: a very narrow slanted zigzag that stretches with the fabric and still looks like a straight seam from the outside. Stretch needle 75/11.', 'Основной шов для трикотажа и джерси: очень узкий косой зигзаг тянется вместе с тканью и снаружи выглядит как прямая строчка. Игла stretch 75/11.', ['knit'])],
  tips: [],
});
add({
  no: 13, cat: 'utility', official: true,
  name: t('Closed overlock', 'Закрытый оверлок'),
  manual: t('Seam and overcast stretch fabrics in one step.', 'Стачивание и обмётка эластичных тканей за один проход.'),
  foot: '0A', idt: true, length: L(2.5), width: W(5.0),
  uses: [
    u('Seam and finish in one pass, the closest this machine gets to your overlocker. Sew with the right swing just off the raw edge, 6 mm from the cut edge, then trim nothing.', 'Шов и обмётка за один проход — ближе всего к вашему оверлоку. Правый укол чуть за срезом, 6 мм от края, потом ничего не срезать.', ['knit', 'cotton']),
    u('Seams inside a cushion cover that will not be seen: fast and tidy.', 'Внутренние швы чехла подушки, которые не видны: быстро и аккуратно.', ['cotton', 'upholstery']),
  ],
  tips: [t('Use the edge guide from the accessory box or the lines on the stitch plate to keep the edge in the same place.', 'Используйте направитель из коробки с аксессуарами или линии на игольной пластине, чтобы край шёл по одной линии.')],
});
add({
  no: 14, cat: 'utility', official: true,
  name: t('Standard overcast', 'Стандартная обмёточная строчка'),
  manual: t('Seam and overcast stretch fabrics in one step with reinforced edge.', 'Стачивание и обмётка эластичных тканей за один проход с усиленным краем.'),
  foot: '0A', idt: true, length: L(2.5), width: W(5.0),
  uses: [
    u('Overcasting the raw edge of upholstery fabric and thick velvet that fray badly: the straight part holds, the diagonal wraps the edge.', 'Обмётка среза обивочной ткани и толстого бархата, которые сильно осыпаются: прямая часть держит, диагональ оборачивает край.', ['upholstery', 'velvet']),
    u('Cotton edges before washing a table runner.', 'Края хлопка перед стиркой дорожки.', ['cotton']),
  ],
  tips: [],
});
add({
  no: 15, cat: 'utility', official: true,
  name: t('Closed overlock (reinforced)', 'Закрытый оверлок (усиленный)'),
  manual: t('Seam and overcast stretch fabrics in one step.', 'Стачивание и обмётка эластичных тканей за один проход.'),
  foot: '0A', idt: true, length: L(2.5), width: W(5.0),
  uses: [u('Like 13 with a second straight line: heavier knits, fleece, towelling, a blanket from stretchy fabric.', 'Как 13, но с второй прямой линией: плотный трикотаж, флис, махра, плед из тянущейся ткани.', ['knit', 'upholstery'])],
  tips: [],
});
add({
  no: 16, cat: 'buttonhole', official: true,
  name: t('Standard buttonhole', 'Стандартная петля'),
  manual: t('Basic buttonhole for blouses, shirts and jackets. Also for pillowcases.', 'Базовая петля для блуз, рубашек и жакетов. Также для наволочек.'),
  foot: '5B', idt: false, length: L(0.4, 0.2, 1.0), width: W(5.0, 2, 7),
  uses: [u('Cushion back closure with buttons, pillowcases, shirts. Put the button in the back of foot 5B and the machine sews the right size by itself.', 'Застёжка на пуговицах на спинке подушки, наволочки, рубашки. Вставьте пуговицу в заднюю часть лапки 5B, и машина сама сошьёт петлю нужного размера.', ['cotton', 'upholstery'])],
  tips: [t('Interfacing under every buttonhole. Lower the buttonhole lever all the way and push it away from you. Always a test buttonhole on a scrap first.', 'Под каждую петлю флизелин. Опустите рычаг петли до конца и отведите от себя. Сначала всегда пробная петля на лоскуте.')],
});
add({
  no: 17, cat: 'buttonhole', official: true,
  name: t('Rounded buttonhole', 'Петля с закруглённым концом'),
  manual: t('Buttonhole for garments.', 'Петля для одежды.'),
  foot: '5B', idt: false, length: L(0.4, 0.2, 1.0), width: W(5.0, 2, 7),
  uses: [u('Fine fabrics and blouses, where a rounded end looks softer.', 'Тонкие ткани и блузы, где закруглённый конец выглядит мягче.', ['cotton', 'silk'])],
  tips: [],
});
add({
  no: 18, cat: 'buttonhole', official: true,
  name: t('Eyelet buttonhole', 'Петля с глазком'),
  manual: t('Tailors buttonhole for jackets and trousers.', 'Портновская петля для жакетов и брюк.'),
  foot: '5B', idt: false, length: L(0.4, 0.2, 1.0), width: W(5.0, 2, 7),
  uses: [u('Thick fabric and buttons with a shank: coats, upholstery-weight cushion fronts, bags.', 'Толстые ткани и пуговицы на ножке: пальто, подушки из обивочной ткани, сумки.', ['upholstery', 'denim', 'velvet'])],
  tips: [],
});
add({
  no: 19, cat: 'buttonhole', official: true,
  name: t('Stretch buttonhole', 'Эластичная петля'),
  manual: t('Buttonhole for stretch fabrics.', 'Петля для эластичных тканей.'),
  foot: '5B', idt: false, length: L(1.0, 0.5, 2.0), width: W(5.0, 2, 7),
  uses: [u('Knits and jersey. Cord it (loop a thick thread over the finger at the back of foot 5B) so it does not stretch out.', 'Трикотаж и джерси. Прокладывайте шнур (петлёй через выступ сзади лапки 5B), чтобы петля не растягивалась.', ['knit'])],
  tips: [],
});
add({
  no: 20, cat: 'buttonhole', official: true,
  name: t('Button sewing', 'Пришивание пуговицы'),
  manual: t('Sew on buttons or tacking.', 'Пришивание пуговиц или закрепки.'),
  foot: 'none', idt: false, length: L(0, 0, 0), width: W(3.0, 2, 7), countOnly: true,
  uses: [u('Remove the presser foot, lower the feed dogs, hold the button under the holder, turn the handwheel to check the swing hits both holes, then sew. The length buttons set the number of stitches (6 by default).', 'Снимите лапку, опустите транспортёр, держите пуговицу под держателем, прокрутите маховик и проверьте, что игла попадает в оба отверстия, затем шейте. Кнопки длины задают число стежков (по умолчанию 6).')],
  tips: [t('Slide the multi-purpose tool under the button to make a thread shank on thick fabric.', 'Подложите под пуговицу универсальный инструмент, чтобы сделать ножку из нити на толстой ткани.')],
});
add({
  no: 21, cat: 'buttonhole', official: true,
  name: t('Programmable darning stitch', 'Программируемая штопка'),
  manual: t('Darning holes or damaged fabric.', 'Штопка дыр и повреждённой ткани.'),
  foot: '0A', idt: false, length: L(0.4, 0.2, 1.0), width: W(6.0, 2, 7),
  uses: [u('Mending a hole: scrap underneath, sew over the hole, press reverse to set the length, the machine finishes the square and repeats that size.', 'Ремонт дыры: лоскут снизу, прошейте поверх дыры, нажмите реверс, чтобы задать длину, машина сама закончит квадрат и повторит этот размер.')],
  tips: [],
});

// ---------------------------------------------------------------- quilt 22-55
const Q = (no, name, uses, opts = {}) => add({
  no, cat: 'quilt', official: false, name, manual: null,
  foot: opts.foot || '1A', idt: opts.idt ?? true, length: opts.length || L(2.5), width: opts.width || W(opts.w ?? 5),
  uses, tips: opts.tips || [],
});
Q(22, t('Hand-look quilting stitch', 'Строчка «под ручную стёжку»'), [
  u('The manual: thread the needle with clear monofilament, cotton in the bobbin, tension 7 to 9. Only the bobbin thread shows, in little dashes, like hand quilting. Beautiful on a blanket or table runner.', 'По инструкции: в иглу прозрачную мононить, в шпульку хлопок, натяжение 7–9. Видна только нижняя нить, пунктиром, как ручная стёжка. Красиво на пледе и дорожке.', ['cotton']),
], { foot: '0A', width: W(3.5, 0, 7), tips: [t('Reset the tension to 4 afterwards or the next seam will be wrong.', 'После верните натяжение на 4, иначе следующий шов будет неправильным.')] });
Q(23, t('Hand-look appliqué stitch (left)', 'Аппликационная «ручная» строчка (влево)'), [u('Stitching appliqué shapes on with a hand-sewn look; the bite goes to the left.', 'Пришивание аппликации «вручную»; укол уходит влево.', ['cotton'])], { w: 3 });
Q(24, t('Hand-look appliqué stitch (right)', 'Аппликационная «ручная» строчка (вправо)'), [u('Same as 23 mirrored, for the other side of a shape.', 'То же, что 23, зеркально, для другой стороны фигуры.', ['cotton'])], { w: 3 });
Q(25, t('Cross-bar quilting stitch', 'Стёжка с перекладиной'), [u('Decorative quilting line on a blanket: straight with a small bar every stitch.', 'Декоративная линия стёжки на пледе: прямая с маленькой перекладиной.', ['cotton', 'upholstery'])], { w: 4 });
Q(26, t('Stepped quilting stitch', 'Ступенчатая стёжка'), [u('Decorative line for crazy quilting and borders.', 'Декоративная линия для «крейзи» квилта и бордюров.', ['cotton'])], { w: 5 });
Q(27, t('Blanket stitch', 'Обмёточная «одеяльная» строчка'), [
  u('The classic blanket edge. Fold the edge once, sew with the straight part just inside the fold and the bar swinging onto the blanket. Width 5 to 6, length 3. Fleece, wool, felt, velvet.', 'Классический край одеяла. Подогните край один раз, прямая часть идёт вдоль сгиба, перекладина ложится на плед. Ширина 5–6, длина 3. Флис, шерсть, фетр, бархат.', ['velvet', 'knit', 'upholstery']),
  u('Appliqué on a cushion with a folk look, contrast thread.', 'Аппликация на подушке в народном стиле, контрастная нить.', ['cotton']),
], { w: 6, length: L(3.0) });
Q(28, t('Dense blanket stitch', 'Плотная одеяльная строчка'), [u('Blanket stitch with three bars per step: for thick edges and a bolder look.', 'Одеяльная строчка с тремя перекладинами на шаг: для толстых краёв и более плотного вида.', ['velvet', 'upholstery'])], { w: 6, length: L(3.0) });
Q(29, t('Cross quilting stitch', 'Стёжка «крестик»'), [u('Straight line with a cross bar: a plus-sign border on a table runner.', 'Прямая с перекладиной: бордюр из плюсиков на дорожке.', ['cotton'])], { w: 4 });
Q(30, t('Double cross quilting stitch', 'Стёжка «двойной крестик»'), [u('Like 29 with two bars; good with thick thread.', 'Как 29 с двумя перекладинами; хорошо толстой нитью.', ['cotton'])], { w: 4 });
Q(31, t('Square wave stitch', 'Прямоугольная волна'), [u('Geometric border; align it with a stripe in the fabric.', 'Геометрический бордюр; выровняйте по полоске ткани.', ['cotton', 'upholstery'])], { w: 5 });
Q(32, t('Star stitch', 'Звёздочка'), [u('A row of stars: a child-blanket border or cushion stripe. Stabilizer underneath.', 'Ряд звёздочек: бордюр детского пледа или полоса на подушке. Снизу стабилизатор.', ['cotton'])], { w: 6 });
Q(33, t('Comb stitch', 'Гребёнка'), [u('Edge decoration that also holds a folded edge down.', 'Отделка края, которая заодно держит подогнутый край.', ['cotton'])], { w: 5 });
Q(34, t('Open zigzag quilting stitch', 'Открытый зигзаг для стёжки'), [u('Loose zigzag with ticks, for quilting lines on a blanket.', 'Свободный зигзаг с насечками, для линий стёжки на пледе.', ['cotton', 'upholstery'])], { w: 6 });
Q(35, t('Appliqué pin stitch', 'Аппликационная строчка «пин-стич»'), [u('PFAFF\'s appliqué pin stitch: a straight line with a short double bar into the shape. Invisible-looking appliqué, raw-edge or turned-edge. Width 2 to 3, length 2.', 'Фирменная строчка PFAFF для аппликации: прямая линия с короткой двойной перекладиной внутрь фигуры. Аппликация с почти невидимым швом. Ширина 2–3, длина 2.', ['cotton', 'silk'])], { w: 3, length: L(2.0) });
Q(36, t('Feather stitch', 'Ёлочка (фезер-стич)'), [u('The crazy-quilt classic: over a seam line, both sides. Lovely in a contrast cotton thread on a table runner.', 'Классика «крейзи» квилта: по линии шва, в обе стороны. Красиво контрастной хлопковой нитью на дорожке.', ['cotton', 'upholstery'])], { w: 6 });
Q(37, t('Serpentine stitch', 'Серпантин'), [u('A wavy line with small ticks: quilting a blanket without marking, border rows.', 'Волнистая линия с насечками: стёжка пледа без разметки, ряды бордюра.', ['cotton'])], { w: 6 });
Q(38, t('Arrowhead stitch', 'Стрелочки'), [u('Decorative row of arrowheads, or hold a folded edge flat.', 'Декоративный ряд стрелок, или держит подогнутый край плоско.', ['cotton'])], { w: 5 });
Q(39, t('Loop stitch', 'Петельки'), [u('A row of loops like chain embroidery; border on a cushion.', 'Ряд петель как тамбурная вышивка; бордюр на подушке.', ['cotton'])], { w: 5 });
Q(40, t('Double loop stitch', 'Двойные петельки'), [u('Looser loops; use thicker thread (30 wt cotton) and foot 1A.', 'Более свободные петли; возьмите толстую нить (хлопок 30) и лапку 1A.', ['cotton'])], { w: 6 });
Q(41, t('Wave stitch (left)', 'Волна (влево)'), [u('A smooth wave for quilting a blanket in parallel rows; rows 5 cm apart look like water.', 'Плавная волна для стёжки пледа параллельными рядами; ряды через 5 см похожи на воду.', ['cotton', 'upholstery'])], { w: 7 });
Q(42, t('Wave stitch (right)', 'Волна (вправо)'), [u('Mirror of 41 so rows can alternate direction.', 'Зеркало 41, чтобы ряды чередовали направление.', ['cotton', 'upholstery'])], { w: 7 });
Q(43, t('Greek key stitch', 'Меандр'), [u('Border on a table runner or along a cushion edge. Needs stabilizer and foot 1A.', 'Бордюр на дорожке или по краю подушки. Нужен стабилизатор и лапка 1A.', ['cotton', 'upholstery'])], { w: 7 });
Q(44, t('Lattice chain stitch', 'Решётка'), [u('Chain of crossed diamonds; a strong band pattern.', 'Цепочка перекрещённых ромбов; выразительная полоса.', ['cotton'])], { w: 6 });
Q(45, t('Leaf chain stitch', 'Листики'), [u('Row of leaves; vine-like border.', 'Ряд листьев; бордюр-лоза.', ['cotton'])], { w: 6 });
Q(46, t('Cross-stitch chain', 'Цепочка крестиков'), [u('Looks like counted cross stitch; border on a cotton runner.', 'Похоже на вышивку крестом; бордюр на хлопковой дорожке.', ['cotton'])], { w: 5 });
Q(47, t('Diamond chain stitch', 'Цепочка ромбов'), [u('Open diamonds, quilting or border.', 'Открытые ромбы, стёжка или бордюр.', ['cotton'])], { w: 6 });
Q(48, t('Zigzag with knots', 'Зигзаг с узелками'), [u('Textured zigzag line for crazy quilting.', 'Фактурный зигзаг для «крейзи» квилта.', ['cotton'])], { w: 5 });
Q(49, t('Long serpentine stitch', 'Длинный серпантин'), [u('A long gentle wave: fast all-over quilting on a blanket.', 'Длинная мягкая волна: быстрая сплошная стёжка пледа.', ['cotton', 'upholstery'])], { w: 7 });
Q(50, t('Ladder stitch', 'Лесенка'), [u('Bars off a straight line; hem decoration.', 'Перекладины от прямой линии; отделка подгиба.', ['cotton'])], { w: 5 });
Q(51, t('Triple chevron stitch', 'Тройной шеврон'), [u('Rows of chevrons; good along a striped upholstery fabric.', 'Ряды шевронов; хорошо вдоль полосатой обивки.', ['cotton', 'upholstery'])], { w: 6 });
Q(52, t('Feathered arrow stitch', 'Стрела с оперением'), [u('Decorative row; cushion centre stripe.', 'Декоративный ряд; центральная полоса подушки.', ['cotton'])], { w: 6 });
Q(53, t('Fern stitch', 'Папоротник'), [u('Branching line; vine borders, folk style.', 'Ветвистая линия; бордюры-лоза, народный стиль.', ['cotton'])], { w: 6 });
Q(54, t('Dense cross stitch', 'Плотный крестик'), [u('Thick crosses; looks hand-embroidered in 30 wt thread.', 'Плотные крестики; как ручная вышивка нитью 30.', ['cotton'])], { w: 5 });
Q(55, t('Brick stitch', 'Кирпичики'), [u('Geometric bricks; good on linen and cotton.', 'Геометрические кирпичики; хорошо на льне и хлопке.', ['cotton'])], { w: 6 });

// ---------------------------------------------------------------- needle art 56-66
const N = (no, name, uses, opts = {}) => add({
  no, cat: 'needleart', official: false, name, manual: null,
  foot: opts.foot || '1A', idt: opts.idt ?? false, length: opts.length || L(2.5), width: opts.width || W(opts.w ?? 5),
  uses, tips: opts.tips || [], wing: opts.wing || false,
});
N(56, t('Cross-stitch band', 'Полоса крестиков'), [u('Embroidery-look band; table runner ends.', 'Полоса под вышивку; концы дорожки.', ['cotton'])], { w: 5 });
N(57, t('Cross stitch', 'Крестик'), [u('Single row of crosses.', 'Один ряд крестиков.', ['cotton'])], { w: 5 });
N(58, t('Staggered cross stitch', 'Крестик вразбежку'), [u('Alternating crosses, lighter look.', 'Крестики в шахматном порядке, легче по виду.', ['cotton'])], { w: 5 });
N(59, t('Hemstitch ladder (wing needle)', 'Мережка-лесенка (игла wing)'), [u('Heirloom hemstitching on linen and cotton: the wing needle punches holes and the stitch pulls them open. Table runner hems, napkins. Spray starch first.', 'Мережка на льне и хлопке: игла wing пробивает отверстия, строчка их раскрывает. Подгибы дорожек, салфетки. Сначала накрахмальте.', ['cotton'])], { w: 3, wing: true });
N(60, t('Hemstitch squares (wing needle)', 'Мережка-квадратики (игла wing)'), [u('Square holes in a row; natural-fibre fabric only.', 'Квадратные отверстия в ряд; только натуральные ткани.', ['cotton'])], { w: 3, wing: true });
N(61, t('Hemstitch diamonds (wing needle)', 'Мережка-ромбики (игла wing)'), [u('Diamond hemstitch for a runner border.', 'Ромбовидная мережка для бордюра дорожки.', ['cotton'])], { w: 3, wing: true });
N(62, t('Running stitch', 'Намёточный стежок'), [u('Looks like hand running stitch: sashiko-style lines on a cotton cushion in thick thread.', 'Как ручной стежок «вперёд иголку»: линии в стиле сашико на хлопковой подушке толстой нитью.', ['cotton', 'denim'])], { foot: '0A', idt: true, w: 0, width: W(3.5, 0, 7), length: L(4.0) });
N(63, t('Wavy running stitch', 'Волнистый намёточный'), [u('Hand-look wavy line; quilting without marking.', 'Волнистая линия «под ручную»; стёжка без разметки.', ['cotton'])], { w: 5 });
N(64, t('Double zigzag', 'Двойной зигзаг'), [u('Two offset zigzags; textured border.', 'Два смещённых зигзага; фактурный бордюр.', ['cotton'])], { w: 6 });
N(65, t('Scalloped satin edge (narrow)', 'Узкий гладьевой фестон'), [u('Narrow satin scallop; edging a napkin.', 'Узкий гладьевой фестон; край салфетки.', ['cotton'])], { w: 4, length: SATIN_L });
N(66, t('Flower chain', 'Цепочка цветов'), [u('Small flowers in a row; child blanket border.', 'Маленькие цветы в ряд; бордюр детского пледа.', ['cotton'])], { w: 6 });

// ---------------------------------------------------------------- satin 67-79
const SA = (no, name, uses, opts = {}) => add({
  no, cat: 'satin', official: false, name, manual: null,
  foot: '2A', idt: false, length: SATIN_L, width: W(opts.w ?? 7),
  uses, tips: opts.tips || [],
});
const satinTip = t('Satin stitches are dense: foot 2A, IDT off, stabilizer or tissue paper under the fabric, tension lowered to 3 so the top thread wraps slightly to the back. Sew slowly with the speed slider halfway.', 'Гладьевые строчки плотные: лапка 2A, IDT выключен, стабилизатор или папиросная бумага под ткань, натяжение 3, чтобы верхняя нить чуть уходила на изнанку. Шейте медленно, ползунок скорости посередине.');
SA(67, t('Scallop satin stitch', 'Гладьевой фестон'), [
  u('The classic scalloped edge: sew along a hem or a pillowcase edge, then trim the fabric close to the outer curve with small scissors. A shirt collar, a cuff, a runner end.', 'Классический фестончатый край: прошейте вдоль подгиба или края наволочки, затем срежьте ткань близко к внешней дуге маленькими ножницами. Воротник рубашки, манжета, конец дорожки.', ['cotton']),
  u('On silk only with tear-away stabilizer and width 4, otherwise it tunnels.', 'На шёлке только с отрывным стабилизатором и шириной 4, иначе стянет.', ['silk']),
], { tips: [satinTip] });
SA(68, t('Scallop satin stitch (mirrored)', 'Гладьевой фестон (зеркальный)'), [u('Same as 67 facing the other way: the second side of a symmetrical border.', 'То же, что 67, в другую сторону: вторая сторона симметричного бордюра.', ['cotton'])], { tips: [satinTip] });
SA(69, t('Shell edge satin stitch', 'Гладьевой «ракушка»'), [u('A shallow scallop with a straight inner edge; napkin and pillowcase edging.', 'Неглубокий фестон с прямым внутренним краем; окантовка салфеток и наволочек.', ['cotton'])], { tips: [satinTip] });
SA(70, t('Crescent satin stitch', 'Гладьевой полумесяц'), [u('Crescent moons; a border row on a cushion in a contrast thread.', 'Полумесяцы; ряд-бордюр на подушке контрастной нитью.', ['cotton', 'upholstery'])], { tips: [satinTip] });
SA(71, t('Dense scallop', 'Плотный фестон'), [u('Tight small scallops; edge finish on felt and thick cotton.', 'Мелкие плотные фестоны; обработка края на фетре и плотном хлопке.', ['cotton', 'upholstery'])], { tips: [satinTip] });
SA(72, t('Sawtooth satin stitch', 'Гладьевая пила'), [u('Triangles; a graphic border for a modern table runner.', 'Треугольники; графичный бордюр для современной дорожки.', ['cotton'])], { tips: [satinTip] });
SA(73, t('Hourglass satin stitch', 'Гладьевые песочные часы'), [u('Narrow-wide-narrow blocks; good over a seam to hide it.', 'Блоки узкий-широкий-узкий; хорошо поверх шва, чтобы спрятать его.', ['cotton'])], { tips: [satinTip] });
SA(74, t('Diamond satin stitch', 'Гладьевые ромбы'), [u('A row of filled diamonds; bold border.', 'Ряд заполненных ромбов; выразительный бордюр.', ['cotton', 'upholstery'])], { tips: [satinTip] });
SA(75, t('Bead satin stitch', 'Гладьевые бусины'), [u('Oval beads; looks like a string of pearls in rayon thread.', 'Овальные бусины; как нитка жемчуга вискозной нитью.', ['cotton'])], { tips: [satinTip] });
SA(76, t('Block satin stitch', 'Гладьевые блоки'), [u('Alternating wide and narrow bars; a tape-like band.', 'Чередование широких и узких полос; похоже на тесьму.', ['cotton', 'upholstery'])], { tips: [satinTip] });
SA(77, t('Leaf satin stitch', 'Гладьевые листья'), [u('Pointed leaves; vine borders.', 'Остроконечные листья; бордюры-лоза.', ['cotton'])], { tips: [satinTip] });
SA(78, t('Satin stitch (bar)', 'Гладь (ровная полоса)'), [u('Plain satin: covering a raw edge of appliqué, making a solid line, bar tacks. Width 3 to 5 for appliqué.', 'Ровная гладь: закрыть срез аппликации, сплошная линия, закрепки. Ширина 3–5 для аппликации.', ['cotton', 'upholstery'])], { tips: [satinTip] });
SA(79, t('Satin ladder stitch', 'Гладьевая лесенка'), [u('Satin blocks with a narrow link; a decorative band.', 'Гладьевые блоки с узкой перемычкой; декоративная полоса.', ['cotton'])], { tips: [satinTip] });

// ---------------------------------------------------------------- decorative 80-99
const D = (no, name, uses, opts = {}) => add({
  no, cat: 'decorative', official: false, name, manual: null,
  foot: '1A', idt: false, length: opts.length || L(2.5), width: W(opts.w ?? 7),
  uses, tips: opts.tips || [],
});
const decoTip = t('The manual: place stabilizer under the fabric for decorative stitches. Foot 1A, IDT off, tension 3, test on a scrap of the same fabric first.', 'По инструкции: под ткань для декоративных строчек кладите стабилизатор. Лапка 1A, IDT выключен, натяжение 3, сначала проба на лоскуте той же ткани.');
D(80, t('Vine with leaves', 'Лоза с листьями'), [u('A leafy vine: the border of a cotton table runner, 2 cm from the hem. Variegated thread looks great.', 'Лоза с листьями: бордюр хлопковой дорожки, 2 см от подгиба. Меланжевая нить смотрится отлично.', ['cotton'])], { tips: [decoTip] });
D(81, t('Scroll stitch', 'Завитки'), [u('Curly scroll; a cushion front stripe.', 'Кудрявые завитки; полоса на лицевой стороне подушки.', ['cotton', 'upholstery'])], { tips: [decoTip] });
D(82, t('Leaf vine', 'Листья на стебле'), [u('Symmetric leaves on a stem; runner border.', 'Симметричные листья на стебле; бордюр дорожки.', ['cotton'])], { tips: [decoTip] });
D(83, t('Branch stitch', 'Ветка'), [u('Fine branch; delicate border on silk with stabilizer.', 'Тонкая ветка; нежный бордюр на шёлке со стабилизатором.', ['cotton', 'silk'])], { tips: [decoTip] });
D(84, t('Stars', 'Звёзды'), [u('Five-point stars; child blanket or Christmas runner.', 'Пятиконечные звёзды; детский плед или новогодняя дорожка.', ['cotton'])], { tips: [decoTip] });
D(85, t('Leaf pairs', 'Парные листья'), [u('Filled leaves alternating sides.', 'Заполненные листья по очереди с двух сторон.', ['cotton'])], { tips: [decoTip] });
D(86, t('Daisy stitch', 'Ромашки'), [u('Daisies in a row; pincushion top, cushion border.', 'Ромашки в ряд; верх игольницы, бордюр подушки.', ['cotton'])], { tips: [decoTip] });
D(87, t('Circles', 'Кружочки'), [u('Bubbles; modern border on linen.', 'Пузырьки; современный бордюр на льне.', ['cotton'])], { tips: [decoTip] });
D(88, t('Double zigzag band', 'Двойная зигзаг-полоса'), [u('Layered zigzag; strong texture on upholstery fabric.', 'Слоистый зигзаг; выраженная фактура на обивочной ткани.', ['upholstery', 'cotton'])], { tips: [decoTip] });
D(89, t('Snowflake stitch', 'Снежинки'), [u('Snowflakes; winter table runner.', 'Снежинки; зимняя дорожка.', ['cotton'])], { tips: [decoTip] });
D(90, t('Flower and bud', 'Цветок с бутоном'), [u('Alternating flower and bud.', 'Чередование цветка и бутона.', ['cotton'])], { tips: [decoTip] });
D(91, t('Candlewick loops', 'Петли «кэндлвик»'), [u('Looped knots like candlewicking; use thick thread.', 'Петельные узелки как в кэндлвике; толстая нить.', ['cotton'])], { tips: [decoTip] });
D(92, t('Chevron band', 'Полоса шевронов'), [u('Repeating chevrons; a bold stripe on a cushion.', 'Повторяющиеся шевроны; яркая полоса на подушке.', ['cotton', 'upholstery'])], { tips: [decoTip] });
D(93, t('Spiral stitch', 'Спираль'), [u('Spirals in a row; playful border.', 'Спирали в ряд; игривый бордюр.', ['cotton'])], { tips: [decoTip] });
D(94, t('Lightning stitch', 'Молния'), [u('Jagged line; modern graphic border.', 'Ломаная линия; современный графичный бордюр.', ['cotton'])], { tips: [decoTip] });
D(95, t('Wave line', 'Волнистая линия'), [u('A single smooth wave; quilting a blanket or a soft border. Also fine on silk with stabilizer.', 'Одна плавная волна; стёжка пледа или мягкий бордюр. Подходит и для шёлка со стабилизатором.', ['cotton', 'silk'])], { tips: [decoTip] });
D(96, t('Wave with ticks', 'Волна с насечками'), [u('Wave with small side ticks; border row.', 'Волна с маленькими боковыми насечками; ряд бордюра.', ['cotton'])], { tips: [decoTip] });
D(97, t('Fringe stitch', 'Бахрома'), [u('Bars off one side, like a fringe; hem decoration on a runner.', 'Перекладины с одной стороны, как бахрома; отделка подгиба дорожки.', ['cotton'])], { tips: [decoTip] });
D(98, t('Hearts', 'Сердечки'), [u('Hearts in a row; a gift cushion or child blanket.', 'Сердечки в ряд; подушка в подарок или детский плед.', ['cotton'])], { tips: [decoTip] });
D(99, t('Bow stitch', 'Бантики'), [u('Bows; whimsical border for a pincushion or runner end.', 'Бантики; игривый бордюр для игольницы или конца дорожки.', ['cotton'])], { tips: [decoTip] });

for (const s of S) s.geom = GEOMETRY[s.no];
S.sort((a, b) => a.no - b.no);

export const STITCHES = S;
export const byNo = (no) => S[no];
export const CATEGORIES = [
  { id: 'utility', name: t('Utility', 'Рабочие'), range: '00–15' },
  { id: 'buttonhole', name: t('Buttonholes & buttons', 'Петли и пуговицы'), range: '16–21' },
  { id: 'quilt', name: t('Quilt', 'Квилт'), range: '22–55' },
  { id: 'needleart', name: t('Needle art', 'Игольное кружево'), range: '56–66' },
  { id: 'satin', name: t('Satin', 'Гладьевые'), range: '67–79' },
  { id: 'decorative', name: t('Decorative', 'Декоративные'), range: '80–99' },
];
export const TASKS = [
  { id: 'seam', name: t('Join two pieces', 'Соединить детали'), nos: [0, 1, 12, 13, 14, 15, 8] },
  { id: 'edge', name: t('Finish a raw edge', 'Обработать срез'), nos: [5, 2, 14, 13, 15, 27, 67] },
  { id: 'hem', name: t('Hem', 'Подогнуть'), nos: [10, 11, 0, 4, 9, 27] },
  { id: 'piping', name: t('Piping & topstitch', 'Кант и отстрочка'), nos: [0, 1] },
  { id: 'button', name: t('Buttons', 'Пуговицы и петли'), nos: [16, 17, 18, 19, 20] },
  { id: 'quilt', name: t('Quilt a blanket', 'Простегать плед'), nos: [22, 41, 42, 49, 37, 0] },
  { id: 'decorate', name: t('Decorate', 'Украсить'), nos: [67, 80, 36, 86, 43, 35, 78] },
  { id: 'stretch', name: t('Stretch fabric', 'Трикотаж'), nos: [12, 13, 15, 11, 19, 6] },
  { id: 'mend', name: t('Mend', 'Починить'), nos: [21, 5, 20] },
];
export const FABRICS = ['cotton', 'silk', 'upholstery', 'velvet', 'knit', 'denim'];
