// Step-by-step chapters for the 3D machine. Each step moves the camera (cam preset) and
// sets animation targets (anim: 0..1 values the scene tweens to). Text follows the owner's
// manual; "check" lines are what you should see before moving on.
const t = (en, ru) => ({ en, ru });

export const PROCEDURES = [
  {
    id: 'power',
    title: t('Plug in and switch on', 'Подключить и включить'),
    intro: t('Two cords, one switch. The foot control is the front socket; the power cord is the rear socket.', 'Два провода, один выключатель. Педаль — в передний разъём, питание — в задний.'),
    steps: [
      { cam: 'right-low', anim: { pedalPlugged: 0, cordPlugged: 0, power: 0 }, parts: ['power'], text: t('Put the machine on a steady table with the handwheel on your right. Find the two sockets and the switch at the bottom of the right side.', 'Поставьте машину на устойчивый стол маховиком справа. Найдите два разъёма и выключатель внизу справа.') },
      { cam: 'right-low', anim: { pedalPlugged: 1 }, parts: ['power', 'foot-control'], text: t('Plug the foot control into the FRONT socket (A).', 'Вставьте педаль в ПЕРЕДНИЙ разъём (A).') },
      { cam: 'right-low', anim: { cordPlugged: 1 }, parts: ['power'], text: t('Plug the power cord into the REAR socket (B), then into the wall.', 'Вставьте шнур питания в ЗАДНИЙ разъём (B), затем в розетку.') },
      { cam: 'front', anim: { power: 1 }, parts: ['buttons'], text: t('Press the switch (C) to ON.', 'Нажмите выключатель (C) в положение ON.'), check: t('The light under the head comes on and the display shows 00: the straight stitch.', 'Загорается подсветка под головкой, на дисплее 00 — прямая строчка.') },
      { cam: 'front', anim: {}, parts: ['speed-lever'], text: t('Slide the speed lever to the middle. Half speed is plenty for the first week.', 'Сдвиньте ползунок скорости на середину. Половинной скорости хватит на первую неделю.') },
    ],
  },
  {
    id: 'spool',
    title: t('Put the thread spool on', 'Поставить катушку'),
    intro: t('Horizontal pin for normal thread. The cap must press flat against the spool with no gap.', 'Горизонтальный стержень для обычной нити. Фиксатор прижат к катушке плоской стороной без зазора.'),
    steps: [
      { cam: 'top', anim: { spoolOn: 0, spoolVertical: 0 }, parts: ['spool-pin', 'spool-caps'], text: t('The main spool pin lies in the recess on top. Slide a spool cap on first, flat side facing where the spool will be.', 'Основной стержень лежит в углублении сверху. Сначала наденьте фиксатор плоской стороной к катушке.') },
      { cam: 'top', anim: { spoolOn: 1 }, parts: ['spool-pin'], text: t('Push the spool on so the thread comes off OVER the top, towards the front. Then the second cap: the one just larger than the spool, pressed firmly against it.', 'Наденьте катушку так, чтобы нить сходила ЧЕРЕЗ верх, вперёд. Затем второй фиксатор: тот, что чуть больше катушки, плотно к ней.'), check: t('No gap between cap and spool. A small spool gets the small cap in front.', 'Между фиксатором и катушкой нет зазора. Маленькой катушке — маленький фиксатор спереди.') },
      { cam: 'top', anim: { spoolVertical: 1 }, parts: ['spool-pin'], text: t('For slippery or specialty thread (metallic, silk thread, big cones) lift the pin upright, put the felt pad under the spool, large cap on. Nothing on top.', 'Для скользкой или специальной нити (металлик, шёлковая нить, большие бобины) поднимите стержень вертикально, фетр под катушку, большой фиксатор. Сверху ничего.') },
      { cam: 'top', anim: { spoolVertical: 0 }, parts: ['aux-hole'], text: t('The auxiliary spool pin goes into the hole at the top right for a second spool.', 'Дополнительный стержень вставляется в отверстие справа сверху для второй катушки.') },
    ],
  },
  {
    id: 'wind',
    title: t('Wind a bobbin', 'Намотать шпульку'),
    intro: t('Use the same thread top and bottom for ordinary seams. Only the five PFAFF bobbins (#416475801) fit.', 'Для обычных швов одна и та же нить сверху и снизу. Подходят только пять шпулек PFAFF (#416475801).'),
    steps: [
      { cam: 'top', anim: { spoolOn: 1, winder: 0, winderLever: 0, bobbinOnSpindle: 0, bobbinSpin: 0 }, parts: ['spool-pin'], text: t('Spool on the horizontal pin, cap tight against it.', 'Катушка на горизонтальном стержне, фиксатор прижат.') },
      { cam: 'top-left', anim: { winder: 0.35 }, parts: ['thread-guides'], text: t('Take the thread into the thread guide (A) from front to back.', 'Заведите нить в нитенаправитель (A) спереди назад.') },
      { cam: 'top-left', anim: { winder: 0.55 }, parts: ['winder-tension'], text: t('Pull it CLOCKWISE around the bobbin winder tension disc (B), the small disc just below the guide.', 'Оберните ПО ЧАСОВОЙ вокруг диска натяжения моталки (B), маленький диск чуть ниже направителя.') },
      { cam: 'top-right', anim: { winder: 0.85, bobbinOnSpindle: 1 }, parts: ['bobbin-winder'], text: t('Thread through the hole in the bobbin from the INSIDE to the outside, and put the bobbin on the spindle.', 'Проденьте нить в отверстие шпульки ИЗНУТРИ наружу и наденьте шпульку на стержень.') },
      { cam: 'top-right', anim: { winder: 1, winderLever: 1 }, parts: ['bobbin-winder', 'buttons'], text: t('Push the bobbin lever to the right.', 'Сдвиньте рычаг моталки вправо.'), check: t('The display flashes SP. The needle will not move now.', 'На дисплее мигает SP. Игла теперь не двигается.') },
      { cam: 'top-right', anim: { bobbinSpin: 1 }, parts: ['bobbin-winder'], text: t('Hold the thread tail, press the foot control. After a few turns stop, snip the tail close to the bobbin, then wind until it stops filling.', 'Держите хвостик нити, нажмите педаль. После нескольких оборотов остановитесь, отрежьте хвостик у шпульки, затем мотайте, пока шпулька не перестанет заполняться.') },
      { cam: 'top-right', anim: { bobbinSpin: 0, winderLever: 0, bobbinOnSpindle: 0, winder: 0 }, parts: ['bobbin-winder'], text: t('Push the lever back LEFT, take the bobbin off, cut the thread.', 'Верните рычаг ВЛЕВО, снимите шпульку, обрежьте нить.'), check: t('Even, firm winding. Loose or lumpy means the thread missed the tension disc: unwind and redo.', 'Ровная плотная намотка. Рыхлая или бугристая — нить не прошла через диск натяжения: размотайте и повторите.') },
    ],
  },
  {
    id: 'bobbin',
    title: t('Insert the bobbin', 'Вставить шпульку'),
    intro: t('Machine OFF, needle up. The bobbin drops in from the top; the thread must run counter-clockwise.', 'Машина ВЫКЛЮЧЕНА, игла вверху. Шпулька вставляется сверху; нить должна идти против часовой стрелки.'),
    steps: [
      { cam: 'bobbin', anim: { cover: 0, bobbinIn: 0, bobbinThread: 0, power: 0 }, parts: ['bobbin-cover'], text: t('Switch off. Needle fully up (handwheel towards you). Push the release button to the right (A) and lift the clear cover off (B).', 'Выключите. Игла полностью вверху (маховик на себя). Сдвиньте кнопку вправо (A) и снимите прозрачную крышку (B).') },
      { cam: 'bobbin', anim: { cover: 1, bobbinIn: 1 }, parts: ['bobbin-cover'], text: t('Drop the bobbin in with the thread coming off COUNTER-CLOCKWISE (the tail leaves on the left and goes to the front).', 'Опустите шпульку так, чтобы нить сходила ПРОТИВ ЧАСОВОЙ (хвостик уходит слева и идёт вперёд).'), check: t('Looking down, the thread makes a backwards C on the left side of the bobbin.', 'Если смотреть сверху, нить образует обратную C слева от шпульки.') },
      { cam: 'bobbin', anim: { bobbinThread: 0.4 }, parts: ['bobbin-cover'], text: t('Pull the thread through the slit (C) at the front.', 'Протяните нить через прорезь (C) спереди.') },
      { cam: 'bobbin', anim: { bobbinThread: 0.75 }, parts: ['bobbin-cover'], text: t('A finger lightly on the bobbin: draw the thread along the arrows into the guide from (C) to (D), on the left.', 'Палец слегка на шпульке: ведите нить по стрелкам в направитель от (C) к (D), налево.') },
      { cam: 'bobbin', anim: { bobbinThread: 1 }, parts: ['bobbin-cover'], text: t('Then along the arrows from (D) to (E) and back over the blade at (E) to cut it. No need to bring the bobbin thread up.', 'Затем по стрелкам от (D) к (E) и назад через лезвие в (E), чтобы отрезать. Поднимать нижнюю нить не нужно.') },
      { cam: 'bobbin', anim: { cover: 0 }, parts: ['bobbin-cover'], text: t('Put the cover back: left edge first, press the right side down until it clicks.', 'Верните крышку: сначала левый край, затем прижмите правую сторону до щелчка.') },
    ],
  },
  {
    id: 'thread',
    title: t('Thread the top thread', 'Заправить верхнюю нить'),
    intro: t('Presser foot UP (opens the tension discs) and needle at its highest. Those two things fix most "it was threaded but it will not sew" problems.', 'Лапка ВВЕРХ (раскрывает диски натяжения), игла в верхнем положении. Эти две вещи решают большинство проблем «заправила, но не шьёт».'),
    steps: [
      { cam: 'head', anim: { footLift: 1, thread: 0, spoolOn: 1 }, parts: ['presser-foot-lift', 'take-up-lever'], text: t('Raise the presser foot. Press needle up/down until the needle is fully up and the take-up lever shows in the left slot.', 'Поднимите лапку. Нажимайте «игла вверх/вниз», пока игла не окажется вверху, а нитепритягиватель не покажется в левой прорези.') },
      { cam: 'top-left', anim: { thread: 0.18 }, parts: ['thread-guides'], text: t('Thread into the RIGHT thread guide (B) from front to back, then into the LEFT guide (C) from back to front.', 'Нить в ПРАВЫЙ нитенаправитель (B) спереди назад, затем в ЛЕВЫЙ направитель (C) сзади вперёд.') },
      { cam: 'top-left', anim: { thread: 0.3 }, parts: ['tension-discs'], text: t('Pull the thread down between the tension discs (D). You feel a light click as it seats.', 'Протяните нить вниз между дисками натяжения (D). Почувствуете лёгкий щелчок, когда нить сядет.'), check: t('Tug the thread: slight resistance means it is in the discs. None means it is not. Start over with the foot up.', 'Потяните нить: лёгкое сопротивление — она в дисках. Нет сопротивления — не в дисках. Начните заново с поднятой лапкой.') },
      { cam: 'head', anim: { thread: 0.52 }, parts: ['threading-slots'], text: t('Down the RIGHT slot to the bottom, then UP the LEFT slot.', 'Вниз по ПРАВОЙ прорези до низа, затем ВВЕРХ по ЛЕВОЙ.') },
      { cam: 'head', anim: { thread: 0.66 }, parts: ['take-up-lever'], text: t('From the right into the take-up lever (E), then down the left slot again.', 'Справа в нитепритягиватель (E), затем снова вниз по левой прорези.'), check: t('The thread sits in the hook of the lever. If the lever is hidden, the needle is not up.', 'Нить лежит в крючке нитепритягивателя. Если крючок не виден — игла не вверху.') },
      { cam: 'needle', anim: { thread: 0.86 }, parts: ['lower-thread-guide', 'needle-thread-guide'], text: t('Into the lower thread guide (F), then the needle thread guide (G) just above the needle.', 'В нижний нитенаправитель (F), затем в нитенаправитель иглы (G) над самой иглой.') },
      { cam: 'needle', anim: { thread: 1 }, parts: ['needle-threader'], text: t('Thread the needle FRONT to back, by hand or with the threader (next chapter). Leave a 10 cm tail behind the foot.', 'Вденьте нить в иглу СПЕРЕДИ назад, вручную или нитевдевателем (следующая глава). Оставьте хвост 10 см за лапкой.') },
    ],
  },
  {
    id: 'threader',
    title: t('Use the needle threader', 'Нитевдеватель'),
    intro: t('Needle fully up, foot down. Works for needle sizes 70 to 120.', 'Игла полностью вверху, лапка опущена. Для игл 70–120.'),
    steps: [
      { cam: 'needle', anim: { thread: 1, threaderDown: 0, footLift: 0 }, parts: ['needle-threader'], text: t('Needle at its highest (needle up/down button). Lower the presser foot so the needle cannot move.', 'Игла в верхнем положении (кнопка «игла вверх/вниз»). Опустите лапку, чтобы игла не сдвинулась.') },
      { cam: 'needle', anim: { threaderDown: 1 }, parts: ['needle-threader'], text: t('Pull the threader handle all the way down. A tiny hook swings through the needle eye.', 'Опустите рычажок нитевдевателя до упора. Крошечный крючок проходит через ушко иглы.') },
      { cam: 'needle', anim: { threaderDown: 1 }, parts: ['needle-threader'], text: t('Lay the thread from the back over the guide hook (G) and under the small hook (F) in the eye.', 'Положите нить сзади через направляющий крючок (G) и под маленький крючок (F) в ушке.') },
      { cam: 'needle', anim: { threaderDown: 0 }, parts: ['needle-threader'], text: t('Let the handle swing back gently. It pulls a loop through the eye; pull the loop out behind the needle.', 'Мягко отпустите рычажок. Он протянет петлю через ушко; вытяните петлю за иглой.'), check: t('Thread through the eye, tail to the back. If it did not catch, the needle was not fully up.', 'Нить в ушке, хвост назад. Если не зацепило — игла была не полностью вверху.') },
    ],
  },
  {
    id: 'first-seam',
    title: t('Sew the first seam', 'Первый шов'),
    intro: t('Two layers of cotton scrap, stitch 00. This is where you learn what a correct stitch looks like on both sides.', 'Два слоя хлопкового лоскута, строчка 00. Здесь вы увидите, как выглядит правильный стежок с обеих сторон.'),
    steps: [
      { cam: 'needle', anim: { footLift: 1, idt: 1, thread: 1 }, parts: ['idt', 'presser-foot-lift'], text: t('Foot up. Engage IDT (press the black arm down until it clicks onto the foot). Slide the fabric under, edge on the 15 mm line of the plate.', 'Лапка вверх. Включите IDT (нажмите чёрный рычаг вниз до щелчка на лапке). Положите ткань под лапку, край по линии 15 мм на пластине.') },
      { cam: 'needle', anim: { footLift: 0 }, parts: ['presser-foot'], text: t('Lower the foot. Hold both thread tails lightly behind the foot for the first three stitches.', 'Опустите лапку. Придержите оба хвостика нити за лапкой на первые три стежка.') },
      { cam: 'front', anim: {}, parts: ['buttons'], text: t('Press reverse for three stitches, release, then sew forward slowly. Guide the fabric; never push or pull it.', 'Нажмите реверс на три стежка, отпустите, затем шейте вперёд медленно. Направляйте ткань; никогда не толкайте и не тяните.') },
      { cam: 'front', anim: {}, parts: ['buttons'], text: t('At the end press reverse for three stitches, or press the tie-off button. Then the scissors button: it cuts both threads.', 'В конце нажмите реверс на три стежка или кнопку закрепки. Затем кнопку с ножницами: она отрежет обе нити.'), check: t('Both sides look the same: a line of equal dashes, no loops, no bobbin thread dots on top. If not, go to Fix.', 'Обе стороны одинаковые: линия ровных штрихов, без петель, без точек нижней нити сверху. Если нет — в раздел «Проблемы».') },
    ],
  },
  {
    id: 'idt',
    title: t('IDT: the walking feed', 'IDT: верхний транспортёр'),
    intro: t('This is what makes a PFAFF feel like your industrial machine: top and bottom feed together, so silk does not pucker and layers do not creep.', 'Это то, что делает PFAFF похожей на промышленную машину: ткань двигается сверху и снизу одновременно, шёлк не собирается, слои не ползут.'),
    steps: [
      { cam: 'foot-side', anim: { footLift: 1, idt: 0 }, parts: ['idt'], text: t('Raise the presser foot. The IDT arm is the black lever behind the foot bar.', 'Поднимите лапку. Рычаг IDT — чёрный рычаг за стержнем лапки.') },
      { cam: 'foot-side', anim: { idt: 1 }, parts: ['idt'], text: t('Press the arm down until it clicks into the cut-out at the back of the foot. Engaged.', 'Нажмите рычаг вниз, пока он не защёлкнется в вырезе сзади лапки. Включено.'), check: t('The arm sits in the notch behind the foot and moves with it when you lower the lift.', 'Рычаг сидит в вырезе за лапкой и двигается вместе с ней, когда вы опускаете рычаг подъёма.') },
      { cam: 'foot-side', anim: { idt: 0 }, parts: ['idt'], text: t('To release: foot up, hold the ribbed ankle with two fingers, pull it down, then pull it towards you and let it rise slowly.', 'Чтобы отключить: лапка вверх, возьмите ребристую «лодыжку» двумя пальцами, потяните вниз, затем на себя и дайте медленно подняться.') },
      { cam: 'foot-side', anim: {}, parts: ['idt'], text: t('ON for seams, hems, piping, quilting, silk, velvet, stripes. OFF for foot 2A and 5B (satin stitches, buttonholes) and for sewing on buttons.', 'ВКЛЮЧИТЬ для швов, подгибов, канта, стёжки, шёлка, бархата, полоски. ВЫКЛЮЧИТЬ для лапок 2A и 5B (гладьевые строчки, петли) и для пришивания пуговиц.') },
    ],
  },
  {
    id: 'foot',
    title: t('Change the presser foot', 'Сменить лапку'),
    intro: t('No screwdriver. The feet snap on and off the holder.', 'Без отвёртки. Лапки защёлкиваются на держателе.'),
    steps: [
      { cam: 'foot-side', anim: { footLift: 1, idt: 0, footOn: 1 }, parts: ['foot-holder'], text: t('Switch off. Raise the foot. Release IDT if it is engaged.', 'Выключите. Поднимите лапку. Отключите IDT, если включён.') },
      { cam: 'foot-side', anim: { footOn: 0 }, parts: ['foot-holder'], text: t('Press the foot DOWN with a finger until it pops off the holder.', 'Нажмите на лапку ВНИЗ пальцем, пока она не отщёлкнется от держателя.') },
      { cam: 'foot-side', anim: { footOn: 0 }, parts: ['presser-foot'], text: t('Place the new foot under the holder, its pin in line with the notch.', 'Положите новую лапку под держатель, штифт напротив выемки.') },
      { cam: 'foot-side', anim: { footOn: 1, footLift: 0 }, parts: ['presser-foot-lift'], text: t('Lower the presser foot lift: the holder snaps onto the pin.', 'Опустите рычаг лапки: держатель защёлкнется на штифте.'), check: t('Raise the lift: the foot comes up with it and does not wobble. Press the info button: the display shows the foot the stitch wants (0A, 1A, 2A, 3, 5B).', 'Поднимите рычаг: лапка поднимается вместе с ним и не болтается. Нажмите кнопку «i»: дисплей покажет, какая лапка нужна строчке (0A, 1A, 2A, 3, 5B).') },
    ],
  },
  {
    id: 'needle',
    title: t('Change the needle', 'Сменить иглу'),
    intro: t('A new needle every project or every 8 hours. A dull needle causes skipped stitches, pulls on silk and snapped thread.', 'Новая игла на каждый проект или каждые 8 часов. Тупая игла даёт пропуски, затяжки на шёлке и обрыв нити.'),
    steps: [
      { cam: 'needle', anim: { needleIn: 1, footLift: 1 }, parts: ['needle-screw'], text: t('Switch off. Put the needle through the hole in the multi-purpose tool so it cannot fall. Loosen the needle screw (screwdriver if stiff).', 'Выключите. Вставьте иглу в отверстие универсального инструмента, чтобы не упала. Ослабьте винт иглы (отвёрткой, если туго).') },
      { cam: 'needle', anim: { needleIn: 0 }, parts: ['needle-bar'], text: t('Pull the old needle down and out.', 'Вытяните старую иглу вниз.') },
      { cam: 'needle', anim: { needleIn: 1 }, parts: ['needle-bar'], text: t('Push the new needle UP as far as it goes, FLAT side of the shank facing AWAY from you (to the back).', 'Вставьте новую иглу ВВЕРХ до упора, ПЛОСКОЙ стороной колбы ОТ себя (назад).'), check: t('Flat side back, needle all the way up. Tighten the screw as tight as it will go.', 'Плоская сторона назад, игла до упора вверх. Затяните винт до конца.') },
      { cam: 'needle', anim: {}, parts: ['needle-bar'], text: t('Only system 130/705 H needles. Universal 80/12 for cotton, Microtex 60 to 70 for silk, 90/14 or 100/16 denim/jeans for upholstery, 90/14 for velvet, stretch 75/11 for knits.', 'Только иглы системы 130/705 H. Универсальная 80/12 для хлопка, Microtex 60–70 для шёлка, 90/14 или 100/16 джинсовая для обивки, 90/14 для бархата, stretch 75/11 для трикотажа.') },
    ],
  },
  {
    id: 'feed-dogs',
    title: t('Lower and raise the feed dogs', 'Опустить и поднять транспортёр'),
    intro: t('Needed for sewing on buttons and free-motion quilting.', 'Нужно для пришивания пуговиц и свободной стёжки.'),
    steps: [
      { cam: 'back-low', anim: { feedDogs: 1 }, parts: ['feed-dog-slide'], text: t('The slide is at the back of the free arm, under the needle.', 'Ползунок сзади свободного рукава, под иглой.') },
      { cam: 'back-low', anim: { feedDogs: 0 }, parts: ['feed-dog-slide'], text: t('Push it LEFT: feed dogs down. The fabric no longer moves by itself.', 'Сдвиньте ВЛЕВО: транспортёр опущен. Ткань больше не двигается сама.') },
      { cam: 'back-low', anim: { feedDogs: 1 }, parts: ['feed-dog-slide'], text: t('Push it RIGHT to raise them, then turn the handwheel one full turn: they only come up after a stitch cycle.', 'Сдвиньте ВПРАВО, чтобы поднять, затем один полный оборот маховика: они поднимаются только после цикла стежка.'), check: t('"Fabric does not move" almost always means this slide was left to the left.', '«Ткань не двигается» почти всегда значит, что ползунок остался слева.') },
    ],
  },
  {
    id: 'buttonhole',
    title: t('Sew a buttonhole', 'Сделать петлю'),
    intro: t('Foot 5B measures the button and the machine does the rest. IDT off. Interfacing under the fabric. Test on a scrap first.', 'Лапка 5B измеряет пуговицу, остальное делает машина. IDT выключен. Под ткань флизелин. Сначала проба на лоскуте.'),
    steps: [
      { cam: 'foot-side', anim: { footLift: 1, idt: 0, footOn: 1, buttonholeFoot: 1 }, parts: ['presser-foot'], text: t('Mark the buttonhole on the fabric. Snap on foot 5B.', 'Разметьте петлю на ткани. Наденьте лапку 5B.') },
      { cam: 'foot-side', anim: { buttonPlate: 1 }, parts: ['presser-foot'], text: t('Pull the button holder plate out at the back of the foot and put the button in. The button sets the length.', 'Выдвиньте пластину для пуговицы сзади лапки и вставьте пуговицу. Пуговица задаёт длину.') },
      { cam: 'needle', anim: {}, parts: ['presser-foot'], text: t('Pass the top thread through the hole in the foot and under it to the back.', 'Проведите верхнюю нить через отверстие в лапке и под неё назад.') },
      { cam: 'front', anim: {}, parts: ['buttons'], text: t('Select 16 (standard), 17 (rounded), 18 (eyelet) or 19 (stretch).', 'Выберите 16 (стандарт), 17 (закруглённая), 18 (с глазком) или 19 (эластичная).') },
      { cam: 'foot-side', anim: { footLift: 0, bhLever: 1 }, parts: ['buttonhole-lever'], text: t('Line the mark up with the centre of the foot, lower the foot. Pull the buttonhole lever ALL the way down and push it AWAY from you.', 'Совместите разметку с центром лапки, опустите лапку. Опустите рычаг петли ДО КОНЦА и отведите ОТ себя.'), check: t('If the machine beeps when you start, the lever is not fully down.', 'Если машина пищит при старте — рычаг опущен не до конца.') },
      { cam: 'foot-side', anim: {}, parts: ['presser-foot'], text: t('Hold the thread tail and sew. It sews front to back and stops by itself. Raise the foot, cut threads, open the hole with the seam ripper with a pin across the end so you do not cut the bartack.', 'Придержите хвостик нити и шейте. Петля шьётся спереди назад и останавливается сама. Поднимите лапку, обрежьте нити, прорежьте петлю вспарывателем, поставив булавку поперёк конца, чтобы не разрезать закрепку.') },
    ],
  },
  {
    id: 'clean',
    title: t('Clean the bobbin area', 'Почистить шпульный отсек'),
    intro: t('Lint builds up under the plate after a few projects, especially with velvet and fleece. No oiling needed.', 'Пух скапливается под пластиной через несколько проектов, особенно от бархата и флиса. Смазка не нужна.'),
    steps: [
      { cam: 'bobbin', anim: { power: 0, footOn: 0, cover: 1, bobbinIn: 0, feedDogs: 0 }, parts: ['stitch-plate'], text: t('Off, needle up, feed dogs down. Remove the foot, the bobbin cover and the bobbin.', 'Выключить, игла вверху, транспортёр опущен. Снимите лапку, крышку шпульки и шпульку.') },
      { cam: 'bobbin', anim: { plateOff: 1 }, parts: ['stitch-plate'], text: t('Undo the two screws with the screwdriver from the box. Lift the plate.', 'Открутите два винта отвёрткой из набора. Снимите пластину.') },
      { cam: 'bobbin', anim: {}, parts: ['stitch-plate'], text: t('Brush out the feed dogs and the bobbin case with the brush. Lift the bobbin case up and to the right to clean under it. Do not blow in: that pushes lint deeper.', 'Вычистите транспортёр и шпульный колпачок кисточкой. Поднимите колпачок вверх и вправо, чтобы почистить под ним. Не дуйте внутрь: пух уйдёт глубже.') },
      { cam: 'bobbin', anim: { plateOff: 0, cover: 0, feedDogs: 1 }, parts: ['stitch-plate'], text: t('Put the case back with its tip in the stopper, plate on with feed dogs still down, screws tight, cover on, feed dogs up.', 'Верните колпачок носиком в упор, пластину при опущенном транспортёре, винты затянуть, крышку на место, транспортёр поднять.') },
    ],
  },
  {
    id: 'pack',
    title: t('Pack away: cords and cover', 'Убрать: провода и чехол'),
    intro: t('The manual\'s order, plus where the power cord goes.', 'Порядок из инструкции, плюс куда девать шнур питания.'),
    steps: [
      { cam: 'right-low', anim: { power: 0 }, parts: ['power'], text: t('Switch off first. The light may glow a few seconds more; that is normal.', 'Сначала выключите. Подсветка может гореть ещё пару секунд; это нормально.') },
      { cam: 'right-low', anim: { cordPlugged: 0 }, parts: ['power'], text: t('Unplug the power cord from the WALL first, then from the machine. Pull the plug, never the cord.', 'Выньте шнур питания сначала из РОЗЕТКИ, затем из машины. Тяните за вилку, не за шнур.') },
      { cam: 'right-low', anim: { pedalPlugged: 0 }, parts: ['foot-control'], text: t('Unplug the foot control. Wind its cord around the foot control itself.', 'Отключите педаль. Намотайте её провод вокруг самой педали.') },
      { cam: 'front', anim: { cordCoiled: 1 }, parts: ['free-arm'], text: t('Power cord: coil it in loose loops the size of your hand, no tight bend at either plug, and close the loop with its tie or a velcro strip. Lay it next to the foot control.', 'Шнур питания: смотайте свободными кольцами размером с ладонь, без резких изгибов у вилок, и стяните его завязкой или липучкой. Положите рядом с педалью.') },
      { cam: 'front', anim: { trayOn: 1 }, parts: ['accessory-tray'], text: t('All accessories into the tray, tray onto the free arm. Foot control and the coiled cord go in the space above the free arm, under the head.', 'Все аксессуары в лоток, лоток на свободный рукав. Педаль и смотанный шнур — в пространство над свободным рукавом, под головкой.') },
      { cam: 'front', anim: { hardCover: 1 }, parts: ['handle'], text: t('Hard cover on. Carry it by the handle.', 'Наденьте жёсткий чехол. Переносите за ручку.'), check: t('Nothing left plugged in; the needle is up and the foot is down on a scrap so the feed dogs are protected.', 'Ничего не подключено; игла вверху, лапка опущена на лоскут, чтобы защитить транспортёр.') },
    ],
  },
];

export const procedureById = (id) => PROCEDURES.find((p) => p.id === id);
