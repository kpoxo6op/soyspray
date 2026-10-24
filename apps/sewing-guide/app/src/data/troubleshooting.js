// Symptom first, then causes in the order to try. The manual's own troubleshooting table is
// included; the rest is what actually goes wrong at a sewing table.
const t = (en, ru) => ({ en, ru });
const fix = (en, ru, link) => ({ en, ru, link });

export const PROBLEMS = [
  {
    id: 'tunneling',
    title: t('Zigzag pulls the fabric into a ridge (silk "chewed up")', 'Зигзаг стягивает ткань в валик (шёлк «сжёвывается»)'),
    looks: t('Inside the zigzag the fabric is bunched into a tunnel; the stitch is not flat; on silk it looks chewed.', 'Внутри зигзага ткань собрана в туннель; строчка не плоская; на шёлке как будто пожёвано.'),
    why: t('Each swing of a wide zigzag pulls the two needle holes towards each other. Thin fabric has nothing to resist with, so it folds up between them. This is called tunnelling. It is not a tension problem first; it is a width, support and needle problem.', 'Каждый размах широкого зигзага стягивает два прокола друг к другу. Тонкой ткани нечем сопротивляться, и она складывается между ними. Это называется туннелинг. В первую очередь это не натяжение, а ширина, поддержка ткани и игла.'),
    fixes: [
      fix('Switch to three-step zigzag 05 (width 4 to 5, length 1.0). Three small stitches per swing cannot pull a ridge.', 'Перейдите на трёхступенчатый зигзаг 05 (ширина 4–5, длина 1,0). Три маленьких стежка на размах не могут стянуть валик.', ['stitches', '5']),
      fix('If you want plain zigzag: width 2.5, length 1.5, and sew it 1 cm INSIDE the raw edge over a strip of tissue paper, then trim the fabric to the stitching and tear the paper away.', 'Если нужен обычный зигзаг: ширина 2,5, длина 1,5, и шейте на 1 см ВНУТРЬ от среза поверх полоски папиросной бумаги, затем срежьте ткань до строчки и оторвите бумагу.', ['stitches', '2']),
      fix('New Microtex 60/8 or 70/10 needle. A universal 80 pushes silk down into the plate.', 'Новая игла Microtex 60/8 или 70/10. Универсальная 80 проталкивает шёлк в пластину.', ['fabrics', 'silk']),
      fix('IDT engaged. Tension down to 3. Presser foot pressure half a turn anticlockwise.', 'IDT включён. Натяжение на 3. Давление лапки на полоборота против часовой.', ['machine', 'idt']),
      fix('Better still for silk seams: a French seam. Two straight seams (00 at 2.0 mm) and the raw edge is sealed inside. No zigzag at all.', 'Ещё лучше для швов на шёлке: французский шов. Два прямых шва (00 на 2,0 мм), и срез запечатан внутри. Никакого зигзага.', ['stitches', '0']),
    ],
  },
  {
    id: 'birdnest',
    title: t('Thread nest under the fabric', 'Клубок ниток под тканью'),
    looks: t('Loops and a tangle on the underside, the fabric may be stuck, the top looks almost normal.', 'Петли и клубок снизу, ткань может застрять, сверху почти нормально.'),
    why: t('Nests under the fabric are a TOP thread problem nine times out of ten: the top thread is not held by the tension discs, so it is pulled down freely by the hook.', 'Клубок снизу в девяти случаях из десяти — проблема ВЕРХНЕЙ нити: она не зажата дисками натяжения, и челнок свободно утягивает её вниз.'),
    fixes: [
      fix('Rethread the top completely with the PRESSER FOOT UP and the needle fully up. The foot opens the discs; threading with it down leaves the thread outside them.', 'Перезаправьте верх полностью с ПОДНЯТОЙ ЛАПКОЙ и иглой вверху. Лапка раскрывает диски; при опущенной лапке нить остаётся снаружи.', ['machine', 'thread']),
      fix('Check the thread is in the take-up lever. Turn the handwheel towards you until the lever is visible in the left slot.', 'Проверьте, что нить в нитепритягивателе. Крутите маховик на себя, пока крючок не покажется в левой прорези.', ['machine', 'thread']),
      fix('Hold both thread tails behind the foot for the first stitches. Lower the foot before you start.', 'Держите оба хвостика нити за лапкой на первых стежках. Опустите лапку перед стартом.', ['machine', 'first-seam']),
      fix('Bobbin in counter-clockwise, thread through the slit and the guide. Clean lint out of the bobbin area.', 'Шпулька против часовой, нить через прорезь и направитель. Вычистите пух из шпульного отсека.', ['machine', 'bobbin']),
    ],
  },
  {
    id: 'loops-top',
    title: t('Bobbin thread shows on top / loops on top', 'Нижняя нить видна сверху / петли сверху'),
    looks: t('Little dots or loops of the bobbin thread on the right side.', 'Точки или петли нижней нити на лицевой стороне.'),
    why: t('Top tension too tight for this thread and fabric, or the bobbin thread is not under the bobbin case tension (not through the slit).', 'Верхнее натяжение слишком сильное для этой нити и ткани, или нижняя нить не под натяжением шпульного колпачка (не прошла через прорезь).'),
    fixes: [
      fix('Lower the top tension one number (4 → 3). Test on a scrap; the threads should meet inside the layers.', 'Уменьшите верхнее натяжение на единицу (4 → 3). Проверьте на лоскуте; нити должны встречаться внутри слоёв.', ['fabrics']),
      fix('Reinsert the bobbin: counter-clockwise, pull the thread firmly through the slit (C) so it clicks under the spring.', 'Переставьте шпульку: против часовой, протяните нить с усилием через прорезь (C), чтобы щёлкнула под пружиной.', ['machine', 'bobbin']),
      fix('Same thread top and bottom. A thick top thread with thin bobbin thread will always show.', 'Одна и та же нить сверху и снизу. Толстая верхняя с тонкой нижней всегда будет видна.'),
    ],
  },
  {
    id: 'loops-bottom',
    title: t('Top thread loops underneath', 'Верхняя нить петляет снизу'),
    looks: t('Small even loops of the top thread on the wrong side, no nest.', 'Небольшие ровные петли верхней нити с изнанки, без клубка.'),
    why: t('Top tension too loose, or thread not in the discs.', 'Верхнее натяжение слишком слабое, или нить не в дисках.'),
    fixes: [
      fix('Raise the top tension one number (4 → 5).', 'Увеличьте верхнее натяжение на единицу (4 → 5).'),
      fix('Rethread with the foot up; tug the thread above the needle: there must be resistance.', 'Перезаправьте с поднятой лапкой; потяните нить над иглой: должно быть сопротивление.', ['machine', 'thread']),
      fix('For decorative stitches and buttonholes this is correct: the manual says the top thread should show a little underneath.', 'Для декоративных строчек и петель это нормально: по инструкции верхняя нить должна немного уходить на изнанку.'),
    ],
  },
  {
    id: 'skipped',
    title: t('Skipped stitches', 'Пропуски стежков'),
    looks: t('Gaps in the seam where a stitch is missing; long floats of thread.', 'Пробелы в шве, где стежка нет; длинные протяжки нити.'),
    why: t('The hook missed the loop: needle bent, blunt, wrong type, not pushed all the way up, or flat side the wrong way.', 'Челнок не поймал петлю: игла погнута, тупая, не того типа, вставлена не до упора или плоской стороной не туда.'),
    fixes: [
      fix('New needle, pushed all the way up, flat side to the back. Right type: stretch for knits, Microtex for silk, jeans for upholstery.', 'Новая игла до упора вверх, плоской стороной назад. Правильный тип: stretch для трикотажа, Microtex для шёлка, джинсовая для обивки.', ['machine', 'needle']),
      fix('Needle too small for the thread: go up one size.', 'Игла мала для нити: возьмите на размер больше.', ['fabrics']),
      fix('Rethread top. Check the right presser foot for the stitch (info button).', 'Перезаправьте верх. Проверьте лапку для строчки (кнопка «i»).', ['machine', 'thread']),
      fix('Do not pull or push the fabric; let IDT feed it.', 'Не тяните и не толкайте ткань; пусть IDT её двигает.', ['machine', 'idt']),
    ],
  },
  {
    id: 'top-breaks',
    title: t('Needle thread breaks', 'Рвётся верхняя нить'),
    looks: t('Thread snaps after a few stitches, sometimes with a click.', 'Нить обрывается через несколько стежков, иногда со щелчком.'),
    why: t('From the manual\'s table: needle, threading, thread quality, spool cap, spool pin position, or a damaged plate hole.', 'Из таблицы инструкции: игла, заправка, качество нити, фиксатор катушки, положение стержня или повреждённое отверстие пластины.'),
    fixes: [
      fix('New needle of the right size; 130/705 H system only.', 'Новая игла нужного размера; только система 130/705 H.', ['machine', 'needle']),
      fix('Rethread from the spool. Check the thread is not caught under the spool or around the spool pin.', 'Перезаправьте от катушки. Проверьте, что нить не зацепилась под катушкой или вокруг стержня.', ['machine', 'thread']),
      fix('Spool cap just larger than the spool, pressed flat. Try the vertical spool pin for cross-wound or slippery thread.', 'Фиксатор чуть больше катушки, прижат плоско. Попробуйте вертикальный стержень для крестовой намотки или скользкой нити.', ['machine', 'spool']),
      fix('Old or cheap thread dries out and snaps. Use good polyester.', 'Старая или дешёвая нить пересыхает и рвётся. Берите хороший полиэстер.'),
      fix('Tension too high for a fine thread: lower it. Run a fingernail round the needle hole in the plate; a burr means a new plate.', 'Натяжение слишком сильное для тонкой нити: уменьшите. Проведите ногтем по отверстию иглы в пластине; заусенец — нужна новая пластина.'),
    ],
  },
  {
    id: 'bobbin-breaks',
    title: t('Bobbin thread breaks', 'Рвётся нижняя нить'),
    looks: t('The seam stops forming; a cut bobbin thread in the case.', 'Шов перестаёт образовываться; оборванная нить в колпачке.'),
    why: t('Bobbin wound unevenly or inserted wrong, lint in the case, or a damaged plate.', 'Шпулька намотана неровно или вставлена неправильно, пух в колпачке или повреждённая пластина.'),
    fixes: [
      fix('Wind a fresh bobbin, thread through the winder tension disc so it winds firm and even.', 'Намотайте новую шпульку, нить через диск натяжения моталки, чтобы намотка была плотной и ровной.', ['machine', 'wind']),
      fix('Reinsert counter-clockwise; clean the bobbin area.', 'Переставьте против часовой; почистите шпульный отсек.', ['machine', 'clean']),
      fix('Only PFAFF bobbins #416475801. Other bobbins look the same and jam.', 'Только шпульки PFAFF #416475801. Другие выглядят так же и заклинивают.'),
    ],
  },
  {
    id: 'puckering',
    title: t('Seam puckers (gathered along the seam)', 'Шов сборит (присобран вдоль)'),
    looks: t('The fabric is drawn up along the seam line, especially on silk and fine cotton.', 'Ткань стянута вдоль линии шва, особенно на шёлке и тонком хлопке.'),
    why: t('Tension too high, stitch too long for a fine fabric, needle too big, or layers fed unevenly.', 'Слишком сильное натяжение, слишком длинный стежок для тонкой ткани, слишком толстая игла или слои подаются неравномерно.'),
    fixes: [
      fix('IDT on. Tension 3. Stitch length 2.0. Microtex 60 to 70 needle.', 'IDT включён. Натяжение 3. Длина стежка 2,0. Игла Microtex 60–70.', ['fabrics', 'silk']),
      fix('Loosen presser foot pressure half a turn anticlockwise for very light fabric.', 'Ослабьте давление лапки на полоборота против часовой для очень лёгкой ткани.'),
      fix('Hold the fabric lightly taut in front and behind the foot without pulling it through.', 'Слегка натягивайте ткань перед лапкой и за ней, не протягивая её.'),
    ],
  },
  {
    id: 'uneven',
    title: t('Uneven stitch length or wavy seam', 'Неровный стежок или волнистый шов'),
    looks: t('Some stitches long, some short; the seam wanders.', 'Одни стежки длинные, другие короткие; шов гуляет.'),
    why: t('From the manual: tension and threading, thick or slubbed thread, uneven bobbin, wrong needle. Also: pulling the fabric.', 'Из инструкции: натяжение и заправка, толстая или неровная нить, неровная шпулька, не та игла. Ещё: вы тянете ткань.'),
    fixes: [
      fix('Hands guide, feed dogs and IDT pull. Let go a little.', 'Руки направляют, транспортёр и IDT тянут. Отпустите чуть.', ['machine', 'idt']),
      fix('Rewind the bobbin; check threading and tension; new needle.', 'Перемотайте шпульку; проверьте заправку и натяжение; новая игла.', ['machine', 'wind']),
      fix('Use the edge guide or the plate lines; keep the speed lever low until the seam is straight by itself.', 'Используйте направитель или линии пластины; держите скорость низкой, пока шов не станет ровным сам.'),
    ],
  },
  {
    id: 'no-feed',
    title: t('Fabric does not move', 'Ткань не двигается'),
    looks: t('The needle goes up and down in the same spot.', 'Игла ходит вверх-вниз на одном месте.'),
    why: t('Feed dogs lowered, presser foot up, stitch length 0, or lint under the plate.', 'Транспортёр опущен, лапка поднята, длина стежка 0 или пух под пластиной.'),
    fixes: [
      fix('Feed dog slide to the RIGHT, then one turn of the handwheel.', 'Ползунок транспортёра ВПРАВО, затем один оборот маховика.', ['machine', 'feed-dogs']),
      fix('Lower the presser foot. Check the stitch length is not 0.', 'Опустите лапку. Проверьте, что длина стежка не 0.'),
      fix('Clean the feed dogs.', 'Почистите транспортёр.', ['machine', 'clean']),
    ],
  },
  {
    id: 'wont-sew',
    title: t('Machine will not sew / beeps', 'Машина не шьёт / пищит'),
    looks: t('Pedal pressed, nothing happens, or a beep.', 'Педаль нажата, ничего не происходит, или писк.'),
    why: t('Bobbin winder lever still to the right (display SP), buttonhole lever not down for a buttonhole, plugs loose, or a jam (display EL).', 'Рычаг моталки остался справа (дисплей SP), рычаг петли не опущен для петли, вилки не до конца, или заклинило (дисплей EL).'),
    fixes: [
      fix('Display SP: push the bobbin winder lever LEFT.', 'На дисплее SP: сдвиньте рычаг моталки ВЛЕВО.', ['machine', 'wind']),
      fix('Display EL (overload): switch off, clear the thread jam under the plate, rethread top and bobbin, switch on.', 'На дисплее EL (перегрузка): выключите, уберите нитяной клубок под пластиной, перезаправьте верх и шпульку, включите.', ['machine', 'clean']),
      fix('Beep at a buttonhole: lower the buttonhole lever all the way and push it back.', 'Писк на петле: опустите рычаг петли до конца и отведите назад.', ['machine', 'buttonhole']),
      fix('Buttons do not respond (static): switch off and on again.', 'Кнопки не реагируют (статика): выключите и включите снова.'),
      fix('Both plugs firmly in, wall socket on, foot control model C-9002.', 'Обе вилки до упора, розетка включена, педаль модели C-9002.', ['machine', 'power']),
    ],
  },
  {
    id: 'needle-breaks',
    title: t('Needle breaks', 'Ломается игла'),
    looks: t('A snap, needle in two pieces. Wear glasses when you sew.', 'Щелчок, игла пополам. Шейте в очках.'),
    why: t('Pulling the fabric so the needle deflects, wrong needle for thick fabric, hitting a pin or a foot, needle not fully up in the clamp.', 'Тянули ткань и игла отклонилась, не та игла для толстой ткани, удар о булавку или лапку, игла не до упора в зажиме.'),
    fixes: [
      fix('Never sew over pins; remove each one before the foot reaches it.', 'Никогда не шейте через булавки; вынимайте каждую, пока лапка до неё не дошла.'),
      fix('Jeans 90/14 or 100/16 for upholstery and many layers; slow down, handwheel over bumps.', 'Джинсовая 90/14 или 100/16 для обивки и многих слоёв; медленнее, маховик на утолщениях.', ['fabrics', 'upholstery']),
      fix('Twin needle or wide stitch with a narrow foot: reduce the width. Foot 4 (zipper) with the needle moved the wrong way hits the foot.', 'Двойная игла или широкая строчка с узкой лапкой: уменьшите ширину. Лапка 4 (молния) с иглой, сдвинутой не в ту сторону, бьёт по лапке.'),
      fix('Reinsert the needle fully up, screw tight.', 'Переставьте иглу до упора, винт затянуть.', ['machine', 'needle']),
    ],
  },
  {
    id: 'decorative-ugly',
    title: t('Decorative stitch looks nothing like the card', 'Декоративная строчка не похожа на карту'),
    looks: t('Gaps in satin stitches, distorted motifs, fabric bunched.', 'Пробелы в гладьевых строчках, искажённые мотивы, ткань собрана.'),
    why: t('Decorative stitches need support under the fabric, the right foot and a slow, even speed.', 'Декоративным строчкам нужна опора под тканью, правильная лапка и медленная ровная скорость.'),
    fixes: [
      fix('Tear-away stabilizer under the fabric. Always. The manual says so too.', 'Отрывной стабилизатор под ткань. Всегда. В инструкции тоже так написано.'),
      fix('Foot 1A for decorative, 2A for satin, IDT OFF for both 2A and 5B. Press the info button to check.', 'Лапка 1A для декоративных, 2A для гладьевых, IDT ВЫКЛ для 2A и 5B. Нажмите кнопку «i», чтобы проверить.', ['machine', 'foot']),
      fix('Speed lever at one third. Tension 3. Embroidery needle 90/14 if the thread shreds.', 'Ползунок скорости на треть. Натяжение 3. Вышивальная игла 90/14, если нить лохматится.'),
      fix('Do not help the fabric; the motif is built from forward and backward feeds and your hands break the rhythm.', 'Не помогайте ткани; мотив строится из движений вперёд и назад, и руки сбивают ритм.'),
    ],
  },
];

export const problemById = (id) => PROBLEMS.find((p) => p.id === id);
