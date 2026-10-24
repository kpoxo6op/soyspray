// Two languages, switchable at any time. Content records carry {en, ru}; UI strings live here.
const STORAGE_KEY = 'sewing-guide-lang';
const listeners = new Set();

export let lang = 'en';

export function initLang() {
  const url = new URL(window.location.href);
  const fromUrl = url.searchParams.get('lang');
  let stored = null;
  try {
    stored = localStorage.getItem(STORAGE_KEY);
  } catch {
    /* private mode */
  }
  const nav = (navigator.language || '').toLowerCase().startsWith('ru') ? 'ru' : 'en';
  lang = ['en', 'ru'].includes(fromUrl) ? fromUrl : stored || nav;
  document.documentElement.lang = lang;
  return lang;
}

export function setLang(next) {
  if (next === lang) return;
  lang = next;
  document.documentElement.lang = lang;
  try {
    localStorage.setItem(STORAGE_KEY, lang);
  } catch {
    /* ignore */
  }
  for (const fn of listeners) fn(lang);
}

export const onLang = (fn) => {
  listeners.add(fn);
  return () => listeners.delete(fn);
};

/** Pick the current language from a {en, ru} record (strings pass through). */
export const T = (rec) => (rec == null ? '' : typeof rec === 'string' ? rec : rec[lang] ?? rec.en ?? '');

const UI = {
  guide: { en: 'guide', ru: 'гид' },
  tabs: {
    home: { en: 'Home', ru: 'Главная' },
    machine: { en: 'Machine', ru: 'Машина' },
    start: { en: 'Start', ru: 'Старт' },
    stitches: { en: 'Stitches', ru: 'Строчки' },
    kit: { en: 'Kit', ru: 'Набор' },
    fabrics: { en: 'Fabrics', ru: 'Ткани' },
    projects: { en: 'Projects', ru: 'Проекты' },
    fix: { en: 'Fix', ru: 'Проблемы' },
  },
  search: { en: 'Search stitches, problems, parts…', ru: 'Поиск по строчкам, проблемам, деталям…' },
  all: { en: 'All', ru: 'Все' },
  byTask: { en: 'By task', ru: 'По задаче' },
  byCategory: { en: 'By category', ru: 'По категории' },
  width: { en: 'Width', ru: 'Ширина' },
  length: { en: 'Length', ru: 'Длина' },
  position: { en: 'Needle position', ru: 'Положение иглы' },
  stitches: { en: 'Stitches', ru: 'Стежков' },
  foot: { en: 'Presser foot', ru: 'Лапка' },
  idtOn: { en: 'IDT on', ru: 'IDT включён' },
  idtOff: { en: 'IDT off', ru: 'IDT выключен' },
  wing: { en: 'Wing needle', ru: 'Игла wing' },
  manualSays: { en: 'The manual says', ru: 'В инструкции' },
  ourName: { en: 'Our name for it. The manual shows this stitch only as a picture.', ru: 'Название наше: в инструкции эта строчка показана только картинкой.' },
  approx: { en: 'Drawing matched to the pull-out stitch card on the right of the machine; the sewn result is denser.', ru: 'Рисунок по выдвижной карте строчек справа на машине; на ткани строчка плотнее.' },
  useFor: { en: 'Use it for', ru: 'Для чего' },
  tips: { en: 'Tips', ru: 'Советы' },
  reset: { en: 'Reset', ru: 'Сброс' },
  selectOnMachine: { en: 'On the machine: press', ru: 'На машине: нажмите' },
  thenAdjust: { en: 'then adjust with the + and − buttons', ru: 'затем настройте кнопками + и −' },
  recommended: { en: 'Recommended start', ru: 'Рекомендуемый старт' },
  mm: { en: 'mm', ru: 'мм' },
  fabricsLabel: { en: 'Fabrics', ru: 'Ткани' },
  previous: { en: 'Previous', ru: 'Назад' },
  next: { en: 'Next', ru: 'Дальше' },
  play: { en: 'Play', ru: 'Играть' },
  pause: { en: 'Pause', ru: 'Пауза' },
  step: { en: 'Step', ru: 'Шаг' },
  of: { en: 'of', ru: 'из' },
  parts: { en: 'Parts', ru: 'Детали' },
  chapters: { en: 'How to', ru: 'Как сделать' },
  explore: { en: 'Explore', ru: 'Обзор' },
  rotateHint: { en: 'Drag to rotate · pinch or scroll to zoom · tap a dot for the part name', ru: 'Тяните, чтобы вращать · щипок или колесо — масштаб · точка — название детали' },
  resetView: { en: 'Reset view', ru: 'Сбросить вид' },
  check: { en: 'Check', ru: 'Проверьте' },
  ask: { en: 'Ask a question about this page', ru: 'Задать вопрос по этой странице' },
  askBody: { en: 'Question about the passport 3.0 guide', ru: 'Вопрос по гиду passport 3.0' },
  copied: { en: 'Link copied. Send it with your question.', ru: 'Ссылка скопирована. Отправьте её с вопросом.' },
  shareFail: { en: 'Could not share; the link is in the address bar.', ru: 'Не удалось поделиться; ссылка в адресной строке.' },
  noWebgl: { en: 'This browser cannot show the 3D machine. The steps below still work.', ru: 'Этот браузер не показывает 3D-модель. Шаги ниже работают.' },
  symptom: { en: 'What do you see?', ru: 'Что вы видите?' },
  causes: { en: 'Try in this order', ru: 'Пробуйте по порядку' },
  needle: { en: 'Needle', ru: 'Игла' },
  thread: { en: 'Thread', ru: 'Нитка' },
  tension: { en: 'Tension', ru: 'Натяжение' },
  pressure: { en: 'Foot pressure', ru: 'Давление лапки' },
  seam: { en: 'Seam stitch', ru: 'Шов' },
  edgeFinish: { en: 'Edge finish', ru: 'Обработка среза' },
  hem: { en: 'Hem', ru: 'Подгиб' },
  notes: { en: 'Notes', ru: 'Заметки' },
  youNeed: { en: 'You need', ru: 'Понадобится' },
  settings: { en: 'Machine settings', ru: 'Настройки машины' },
  steps: { en: 'Steps', ru: 'Шаги' },
  openStitch: { en: 'Open stitch', ru: 'Открыть строчку' },
  machineDefaults: { en: 'The machine shows its own default on the display when you select a stitch; these are starting points for the fabrics in this guide.', ru: 'Машина показывает свои значения на дисплее при выборе строчки; здесь — стартовые значения для тканей из этого гида.' },
  source: { en: 'Source', ru: 'Источник' },
  backTo: { en: 'Back to', ru: 'Назад к' },
};

export function ui(path) {
  const rec = path.split('.').reduce((o, k) => (o ? o[k] : undefined), UI);
  return rec ? T(rec) : path;
}
