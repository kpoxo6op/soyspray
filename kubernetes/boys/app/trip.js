import { dateText, fullDays, dayCount, parseMoney, money, budgetText, perPerson, localInstants, localTime, callTimes, equal } from './trip-utils.mjs';

const $ = (selector) => document.querySelector(selector);
const titles = { destination: 'Направление', dates: 'Даты поездки', budget: 'Общий бюджет', accommodation: 'Жильё', call: 'Следующий звонок' };
const answers = { yes: 'Да', maybe: 'Возможно', no: 'Нет' };
const T = { active: false, me: '', members: [], data: null, refreshing: false, epoch: 0, editor: null, monthOpened: false, pendingDecision: false };
const dialog = $('#trip-editor');
const form = $('#trip-edit-form');

function node(tag, className = '', value = '') {
  const item = document.createElement(tag);
  if (className) item.className = className;
  if (value !== '') item.textContent = value;
  return item;
}
function button(label, action, className = 'button') {
  const item = node('button', className, label);
  item.type = 'button';
  item.addEventListener('click', action);
  return item;
}
function link(label, url) {
  const item = node('a', 'text-button', label);
  item.href = url; item.target = '_blank'; item.rel = 'noopener noreferrer';
  return item;
}
function memberName(key) { return T.members.find((member) => member.name.toLowerCase() === key)?.name || key; }
function myResponse() { return T.data?.responses.find((item) => item.name_key === T.me); }
function emptyResponse() {
  return { answers: {}, attendance: null, arrival: null, departure: null, adults: null, children: null, notes: '', budget: { min_cents: null, max_cents: null } };
}
function sharedValues(document) { return Object.fromEntries(Object.keys(titles).map((key) => [key, structuredClone(document[key])])); }
function selectedDates() { const value = T.data.trip.document.dates; return value.options.find((item) => item.id === value.selected); }
function statusLine(decision) {
  if (!decision.by) return 'Черновик';
  const when = new Date(decision.at).toLocaleString('ru-RU');
  return `${decision.status === 'agreed' ? 'Отметил как согласованное' : 'Вернул в черновик'}: ${memberName(decision.by)} · ${when}`;
}
function rangeText(option) {
  if (!option) return 'Даты ещё не выбраны';
  const days = fullDays(option.arrival, option.departure);
  return `${dateText(option.arrival)} → ${dateText(option.departure)} · ночей: ${days.nights} · полных общих дней: ${days.count}`;
}
function sectionLines(section, document) {
  const value = document[section];
  if (section === 'destination') return [value.name || 'Направление не указано'];
  if (section === 'dates') return [rangeText(value.options.find((option) => option.id === value.selected))];
  if (section === 'budget') return [budgetText(value), 'AUD на человека, без перелётов'];
  if (section === 'call') return value.at ? [...callTimes(value), `Часовой пояс: ${value.timezone}`] : ['Звонок ещё не назначен'];
  const candidate = value.candidates.find((item) => item.id === value.selected);
  if (!candidate) return ['Жильё ещё не выбрано'];
  const estimate = perPerson(candidate.total_cents, value.paying_people);
  return [candidate.title, `Общая котировка: ${money(candidate.total_cents)}`, `На человека: ${estimate == null ? 'неизвестно' : '≈ ' + money(estimate)}`, `Платящих людей: ${value.paying_people ?? 'не указано'}`, `Дата котировки: ${dateText(candidate.quoted_on, false)}`];
}
function sectionCard(section) {
  const document = T.data.trip.document;
  const card = node('article', 'trip-card');
  const heading = node('div', 'card-heading');
  heading.append(node('h2', '', titles[section]), node('span', `decision-badge ${document.decisions[section].status}`, document.decisions[section].status === 'agreed' ? 'Согласовано' : 'Черновик'));
  card.append(heading);
  sectionLines(section, document).forEach((line) => card.append(node('p', '', line)));
  if (section === 'call' && document.call.url) card.append(link('Присоединиться к звонку', document.call.url));
  card.append(node('p', 'attribution', statusLine(document.decisions[section])));
  const actions = node('div', 'card-actions');
  actions.append(button('Изменить', () => editSection(section)));
  const agreed = document.decisions[section].status === 'agreed';
  const mark = button(agreed ? 'Вернуть в черновик' : 'Отметить как согласованное', () => decide(section, !agreed), 'text-button');
  mark.disabled = T.pendingDecision;
  actions.append(mark); card.append(actions);
  return card;
}
function renderOverview() {
  const root = $('#trip-overview'); root.replaceChildren();
  const document = T.data.trip.document;
  const intro = node('section', 'trip-heading');
  intro.append(node('h2', '', document.destination.name || 'Новая поездка'));
  const agreed = Object.values(document.decisions).filter((value) => value.status === 'agreed').length;
  intro.append(node('p', '', agreed === 5 ? 'Согласовано: все разделы' : `Черновик · согласовано разделов: ${agreed} из 5`));
  intro.append(node('p', 'muted', 'Отметка означает решение конкретного участника. Это не голосование от имени всех.'));
  intro.append(button('Текст для Telegram', openSummary));
  root.append(intro);
  const pending = Object.keys(titles).filter((key) => document.decisions[key].status !== 'agreed');
  if (pending.length) {
    const decisions = node('section', 'pending-decisions');
    decisions.append(node('h2', '', 'Что ещё нужно решить'));
    const actions = node('div', 'card-actions');
    pending.forEach((key) => actions.append(button(titles[key], () => editSection(key), 'text-button')));
    decisions.append(actions); root.append(decisions);
  }
  const progress = node('article', 'trip-card attendance-progress');
  const responses = T.data.responses;
  const answered = responses.filter((item) => item.document.attendance != null).length;
  const yes = responses.filter((item) => item.document.attendance === 'yes').length;
  progress.append(node('h2', '', 'Кто едет'), node('p', '', `Ответили: ${answered} из ${T.members.length} · едут: ${yes} · без ответа: ${T.members.length - answered}`), button('Мой ответ и дорога', editResponse));
  root.append(progress);
  const grid = node('div', 'trip-card-grid');
  Object.keys(titles).forEach((section) => grid.append(sectionCard(section)));
  root.append(grid);
  if (document.accommodation.candidates.length) root.append(accommodationList());
  const activity = node('section', 'trip-activity');
  activity.append(node('h2', '', 'Последние изменения'), node('div', '', 'Загружаем историю…'));
  activity.lastChild.id = 'trip-activity-list'; root.append(activity);
  loadActivity();
}
function accommodationList() {
  const root = node('section', 'accommodation-list');
  root.append(node('h2', '', 'Варианты жилья'));
  const grid = node('div', 'comparison-columns');
  const value = T.data.trip.document.accommodation;
  value.candidates.forEach((item) => {
    const card = node('article', 'trip-card');
    card.append(node('h3', '', item.title));
    if (item.id === value.selected) card.append(node('p', 'decision-badge', 'Выбранный вариант'));
    card.append(node('p', '', `${dateText(item.arrival, false)} → ${dateText(item.departure, false)}`), node('p', '', `Общая котировка: ${money(item.total_cents)}`), node('p', '', `Дата котировки: ${dateText(item.quoted_on, false)}`), node('p', '', `Вместимость: ${item.capacity ?? 'неизвестно'}`));
    const cost = perPerson(item.total_cents, value.paying_people);
    card.append(node('p', '', `На человека: ${cost == null ? 'неизвестно' : '≈ ' + money(cost)}`));
    if (item.notes) card.append(node('p', 'multiline', item.notes));
    if (item.url) card.append(link('Открыть ссылку на жильё', item.url));
    grid.append(card);
  });
  root.append(grid, node('p', 'muted', 'Это ручные котировки с указанной датой. Сайт не проверяет цены и не делает бронирования.'));
  return root;
}
function renderOptions() {
  const root = $('#trip-options'); root.replaceChildren();
  const heading = node('div', 'card-heading');
  heading.append(node('h2', '', 'Варианты поездки'), button('Мои ответы на даты', editResponse));
  root.append(heading, node('p', 'muted', 'Дни приезда и отъезда не входят в полные общие дни. Личная дорога может отличаться.'));
  const grid = node('div', 'comparison-columns');
  const document = T.data.trip.document;
  document.dates.options.forEach((option) => {
    const card = node('article', 'trip-card date-option');
    const days = fullDays(option.arrival, option.departure);
    card.append(node('h3', '', option.label), node('p', '', `Приезд: ${dateText(option.arrival)}`), node('p', '', `Отъезд: ${dateText(option.departure)}`), node('p', '', `Ночей: ${days.nights} · полных общих дней: ${days.count}`));
    if (days.count) card.append(node('p', '', `Полные дни: ${dateText(days.first, false)} → ${dateText(days.last, false)}`));
    if (option.id === document.dates.selected) card.append(node('p', 'decision-badge', 'Выбранные общие даты'));
    const list = node('ul', 'answer-list');
    T.members.forEach((member) => {
      const response = T.data.responses.find((item) => item.name_key === member.name.toLowerCase());
      const answer = response && Object.hasOwn(response.document.answers, option.id) ? response.document.answers[option.id] : null;
      const row = node('li', answer ? `answer-${answer}` : 'answer-empty');
      row.append(node('span', '', member.name), node('strong', '', answers[answer] || 'Нет ответа'));
      if (response && Object.hasOwn(response.unanswered_causes, option.id)) row.append(node('small', '', 'Даты изменились — нужен новый ответ'));
      list.append(row);
    });
    card.append(list); grid.append(card);
  });
  if (!document.dates.options.length) root.append(node('p', '', 'Варианты дат ещё не добавлены.'));
  root.append(grid, button('Изменить варианты и общие даты', () => editSection('dates')));
}
function renderMembers() {
  const root = $('#trip-members'); root.replaceChildren();
  root.append(node('h2', '', 'Участники и дорога'), button('Мой ответ, дорога и бюджет', editResponse));
  const grid = node('div', 'trip-card-grid');
  const shared = selectedDates();
  T.members.forEach((member) => {
    const response = T.data.responses.find((item) => item.name_key === member.name.toLowerCase());
    const value = response?.document || emptyResponse();
    const card = node('article', 'trip-card member-card');
    card.append(node('h3', '', member.name), node('p', 'attendance', value.attendance == null ? 'Нет ответа об участии' : `Участие: ${answers[value.attendance]}`));
    if (!member.claimed) card.append(node('p', 'muted', 'Имя ещё не закреплено'));
    card.append(node('p', '', `Приезд: ${dateText(value.arrival, false)}`), node('p', '', `Отъезд: ${dateText(value.departure, false)}`));
    if (shared && value.arrival && value.arrival !== shared.arrival) card.append(node('p', 'travel-difference', `Приезд отличается от общих дат на ${Math.abs(dayCount(shared.arrival, value.arrival))} дн. (${value.arrival < shared.arrival ? 'раньше' : 'позже'})`));
    if (shared && value.departure && value.departure !== shared.departure) card.append(node('p', 'travel-difference', `Отъезд отличается от общих дат на ${Math.abs(dayCount(shared.departure, value.departure))} дн. (${value.departure < shared.departure ? 'раньше' : 'позже'})`));
    card.append(node('p', '', `Со мной: взрослых — ${value.adults ?? 'не указано'}, детей — ${value.children ?? 'не указано'}`), node('p', '', `Личный бюджет: ${budgetText(value.budget)}`), node('p', 'muted', 'AUD на человека, без перелётов'));
    if (value.notes) card.append(node('p', 'multiline', value.notes));
    grid.append(card);
  });
  root.append(grid);
}

function field(name, label, type, value, settings = {}) {
  const wrapper = node('label', 'edit-field', label);
  const input = node(type === 'textarea' ? 'textarea' : 'input');
  input.name = name; input.id = 'trip-field-' + name;
  if (type !== 'textarea') input.type = type;
  input.value = value == null ? '' : String(value);
  Object.assign(input, settings);
  wrapper.append(input); return wrapper;
}
function selectField(name, label, choices, value) {
  const wrapper = node('label', 'edit-field', label);
  const select = node('select'); select.name = name; select.id = 'trip-field-' + name;
  choices.forEach(([key, label]) => { const option = node('option', '', label); option.value = key; select.append(option); });
  select.value = value ?? ''; wrapper.append(select); return wrapper;
}
function amount(value) { return value == null ? '' : (value / 100).toFixed(2).replace('.', ','); }
function moneyFields(root, value, prefix = 'budget') {
  root.append(node('p', 'muted', 'AUD на человека, без перелётов. Можно оставить пустым.'));
  const row = node('div', 'form-row');
  row.append(field(prefix + '.min', 'Минимум, AUD', 'text', amount(value.min_cents), { inputMode: 'decimal' }), field(prefix + '.max', 'Максимум, AUD', 'text', amount(value.max_cents), { inputMode: 'decimal' })); root.append(row);
}
function refreshChoices() {
  const select = form.elements.namedItem('selected'); if (!select) return;
  const chosen = select.value;
  select.replaceChildren();
  const blank = node('option', '', 'Ещё не выбрано'); blank.value = ''; select.append(blank);
  form.querySelectorAll('[data-record]').forEach((record) => {
    const label = record.querySelector('input[data-record-title]').value;
    const option = node('option', '', label || 'Новый вариант'); option.value = record.dataset.record; select.append(option);
  });
  select.value = [...select.options].some((item) => item.value === chosen) ? chosen : '';
}
function recordFields(root, value, kind) {
  const record = node('fieldset', 'edit-record'); record.dataset.record = value.id;
  const prefix = value.id + '.';
  record.append(node('legend', '', kind === 'dates' ? 'Вариант дат' : 'Вариант жилья'));
  const title = field(prefix + 'title', kind === 'dates' ? 'Название варианта' : 'Название жилья', 'text', kind === 'dates' ? value.label : value.title, { required: true, maxLength: 200 });
  title.querySelector('input').dataset.recordTitle = 'true';
  title.addEventListener('input', refreshChoices); record.append(title);
  const dates = node('div', 'form-row'); dates.append(field(prefix + 'arrival', 'Приезд', 'date', value.arrival, { required: kind === 'dates' }), field(prefix + 'departure', 'Отъезд', 'date', value.departure, { required: kind === 'dates' })); record.append(dates);
  if (kind === 'accommodation') {
    record.append(field(prefix + 'url', 'Ссылка на жильё', 'url', value.url, { maxLength: 2048 }));
    const quote = node('div', 'form-row'); quote.append(field(prefix + 'total', 'Общая котировка за проживание, AUD', 'text', amount(value.total_cents), { inputMode: 'decimal' }), field(prefix + 'quoted', 'Дата котировки', 'date', value.quoted_on)); record.append(quote);
    record.append(field(prefix + 'capacity', 'Вместимость, человек', 'number', value.capacity, { min: '1', max: '100', step: '1' }), field(prefix + 'notes', 'Заметки о жилье', 'textarea', value.notes, { maxLength: 1000, rows: 3 }));
  }
  record.append(button('Удалить вариант', () => { record.remove(); refreshChoices(); changedEditor(); }, 'text-button'));
  root.append(record);
}
function editSection(section, override = null) {
  if (!T.data?.trip || T.editor) return;
  const original = structuredClone(T.data.trip.document[section]);
  const base = override || original;
  T.editor = { kind: 'section', section, base: original, board: sharedValues(T.data.trip.document), revision: T.data.trip.revision, tripRevision: T.data.trip.revision, dirty: false, saving: false, conflict: null };
  $('#trip-edit-title').textContent = titles[section];
  const root = $('#trip-edit-fields'); root.replaceChildren();
  if (section === 'destination') root.append(field('name', 'Куда едем', 'text', base.name, { maxLength: 200 }));
  if (section === 'budget') moneyFields(root, base);
  if (section === 'dates' || section === 'accommodation') {
    const list = node('div', 'edit-record-list'); root.append(list);
    (section === 'dates' ? base.options : base.candidates).forEach((value) => recordFields(list, value, section));
    root.append(button('Добавить вариант', () => {
      if (list.children.length >= 12) { $('#trip-edit-error').textContent = 'Можно добавить до 12 вариантов.'; return; }
      recordFields(list, { id: crypto.randomUUID(), label: '', title: '', arrival: null, departure: null, url: '', total_cents: null, quoted_on: null, capacity: null, notes: '' }, section);
      refreshChoices(); changedEditor(); list.lastChild.querySelector('input').focus();
    }));
    root.append(selectField('selected', section === 'dates' ? 'Общие даты' : 'Выбранное жильё', [['', 'Ещё не выбрано']], base.selected));
    refreshChoices(); form.elements.namedItem('selected').value = base.selected ?? '';
    if (section === 'accommodation') root.append(field('paying', 'Количество платящих людей для расчёта', 'number', base.paying_people, { min: '1', max: '100', step: '1' }), node('p', 'muted', 'Укажите число явно. Оно не вычисляется из ответов участников.'));
  }
  if (section === 'call') {
    root.append(field('call-local', 'Дата и время звонка', 'datetime-local', base.at ? localTime(base.at, base.timezone).slice(0, 16) : ''), selectField('call-zone', 'Часовой пояс', [['Pacific/Auckland', 'Окленд — Pacific/Auckland'], ['Australia/Brisbane', 'Брисбен — Australia/Brisbane'], ['UTC', 'UTC']], base.timezone || 'Pacific/Auckland'));
    if (base.timezone && ![...form.elements.namedItem('call-zone').options].some((item) => item.value === base.timezone)) {
      const option = node('option', '', base.timezone); option.value = base.timezone; form.elements.namedItem('call-zone').append(option); form.elements.namedItem('call-zone').value = base.timezone;
    }
    const occurrence = selectField('call-instant', 'При переводе часов время повторяется. Выберите нужный раз.', [['', 'Выберите время']], ''); occurrence.id = 'call-occurrence'; root.append(occurrence);
    const preview = node('p', 'call-preview'); preview.id = 'call-preview'; root.append(preview);
    root.append(field('call-url', 'Ссылка для подключения', 'url', base.url, { maxLength: 2048 }));
    form.elements.namedItem('call-local').addEventListener('input', () => updateCallChoices());
    form.elements.namedItem('call-zone').addEventListener('change', () => updateCallChoices());
    form.elements.namedItem('call-instant').addEventListener('change', renderCallPreview);
    updateCallChoices(base.at);
  }
  openEditor();
}
function editResponse(override = null) {
  if (!T.data?.trip || T.editor) return;
  const mine = myResponse(); const original = structuredClone(mine?.document || emptyResponse());
  const base = override && Object.hasOwn(override, 'answers') ? override : original;
  T.editor = { kind: 'response', base: original, options: structuredClone(T.data.trip.document.dates.options), revision: mine?.revision || 0, tripRevision: T.data.trip.revision, dirty: false, saving: false, conflict: null };
  $('#trip-edit-title').textContent = 'Мой ответ, дорога и бюджет';
  const root = $('#trip-edit-fields'); root.replaceChildren();
  root.append(node('p', 'muted', 'Вы изменяете только свои ответы. Пустое поле означает, что вы ещё не ответили.'));
  T.data.trip.document.dates.options.forEach((option) => root.append(selectField('answer.' + option.id, `${option.label}: ${dateText(option.arrival, false)} → ${dateText(option.departure, false)}`, [['', 'Нет ответа'], ...Object.entries(answers)], Object.hasOwn(base.answers, option.id) ? base.answers[option.id] : '')));
  root.append(selectField('attendance', 'Планируете поехать?', [['', 'Ещё не ответил'], ...Object.entries(answers)], base.attendance));
  const travel = node('div', 'form-row'); travel.append(field('arrival', 'Мой приезд', 'date', base.arrival), field('departure', 'Мой отъезд', 'date', base.departure)); root.append(travel);
  const companions = node('div', 'form-row'); companions.append(field('adults', 'Со мной взрослых, не считая меня', 'number', base.adults, { min: '0', max: '20', step: '1' }), field('children', 'Со мной детей', 'number', base.children, { min: '0', max: '20', step: '1' })); root.append(companions);
  root.append(field('notes', 'Коротко о дороге. Имена семьи не нужны.', 'textarea', base.notes, { maxLength: 600, rows: 3 }), node('h3', '', 'Личный бюджет'));
  moneyFields(root, base.budget); openEditor();
}
function updateCallChoices(preferred) {
  const select = form.elements.namedItem('call-instant'); const previous = preferred || select.value;
  select.replaceChildren(); $('#call-preview').textContent = '';
  try {
    const value = form.elements.namedItem('call-local').value;
    const instants = value ? localInstants(value, form.elements.namedItem('call-zone').value) : [];
    $('#call-occurrence').hidden = instants.length < 2;
    const blank = node('option', '', 'Выберите время'); blank.value = ''; select.append(blank);
    instants.forEach((instant, index) => { const option = node('option', '', `${index === 0 ? 'Первый' : 'Второй'} раз · UTC ${instant.slice(0, 16).replace('T', ' ')}`); option.value = instant; select.append(option); });
    select.value = instants.length === 1 ? instants[0] : instants.find((instant) => Date.parse(instant) === Date.parse(previous)) || '';
    renderCallPreview();
  } catch (error) { $('#call-preview').textContent = error.message; }
}
function renderCallPreview() {
  const at = form.elements.namedItem('call-instant').value;
  $('#call-preview').textContent = at ? callTimes({ at }).join(' · ') : '';
}
function readEditor() {
  const data = new FormData(form);
  const value = (name) => String(data.get(name) ?? '').trim();
  const integer = (name) => { const raw = value(name); if (!raw) return null; if (!/^\d+$/.test(raw)) throw new Error('Укажите целое неотрицательное число.'); return Number(raw); };
  const budget = () => ({ min_cents: parseMoney(value('budget.min')), max_cents: parseMoney(value('budget.max')) });
  if (T.editor.kind === 'response') return {
    answers: Object.fromEntries(T.editor.options.map((option) => [option.id, value('answer.' + option.id)]).filter(([, answer]) => answer)),
    attendance: value('attendance') || null, arrival: value('arrival') || null, departure: value('departure') || null,
    adults: integer('adults'), children: integer('children'), notes: value('notes'), budget: budget(),
  };
  const section = T.editor.section;
  if (section === 'destination') return { name: value('name') };
  if (section === 'budget') return budget();
  if (section === 'call') {
    if (!value('call-local')) { if (value('call-url')) throw new Error('Сначала укажите время звонка.'); return { at: null, timezone: null, url: '' }; }
    if (!value('call-instant')) throw new Error('Проверьте время звонка и выберите нужный раз при переводе часов.');
    let at = value('call-instant').replace('.000Z', 'Z');
    const previous = T.editor.base;
    if (previous.at && previous.timezone === value('call-zone') && Math.floor(Date.parse(previous.at) / 60000) === Math.floor(Date.parse(at) / 60000)) at = previous.at;
    return { at, timezone: value('call-zone'), url: value('call-url') };
  }
  const records = [...form.querySelectorAll('[data-record]')].map((record) => {
    const id = record.dataset.record; const prefix = id + '.';
    const dates = { id, arrival: value(prefix + 'arrival') || null, departure: value(prefix + 'departure') || null };
    return section === 'dates' ? { ...dates, label: value(prefix + 'title') } : { ...dates, title: value(prefix + 'title'), url: value(prefix + 'url'), total_cents: parseMoney(value(prefix + 'total')), quoted_on: value(prefix + 'quoted') || null, capacity: integer(prefix + 'capacity'), notes: value(prefix + 'notes') };
  });
  return section === 'dates' ? { options: records, selected: value('selected') || null } : { candidates: records, selected: value('selected') || null, paying_people: integer('paying') };
}

function openEditor() {
  $('#trip-edit-error').textContent = ''; $('#trip-edit-conflict').hidden = true;
  syncEditor(); if (!dialog.open) dialog.showModal();
  form.querySelector('input,select,textarea')?.focus();
}
function syncEditor() {
  const editor = T.editor; if (!editor) return;
  try { editor.dirty = !equal(editor.base, readEditor()); } catch { editor.dirty = true; }
  $('#trip-edit-save').disabled = editor.saving || !editor.dirty || !!editor.conflict;
  $('#trip-edit-close').disabled = editor.saving;
  $('#trip-edit-status').textContent = editor.saving ? 'Сохраняем отправленный вариант. Новые правки останутся в черновике.' : editor.dirty ? 'Есть несохранённые изменения' : 'Изменений нет';
}
function changedEditor() { if (T.editor) { syncEditor(); } }
function closeEditor() {
  if (!T.editor) return true;
  if (T.editor.saving) return false;
  if (T.editor.dirty && !window.confirm('Закрыть без сохранения изменений?')) return false;
  T.editor = null; dialog.close(); return true;
}
function mergeEdits(base, draft, remote) {
  if (equal(base, draft)) return structuredClone(remote);
  if (Array.isArray(base) && Array.isArray(draft) && Array.isArray(remote) && [...base, ...draft, ...remote].every((value) => value && typeof value.id === 'string')) {
    const old = new Map(base.map((value) => [value.id, value]));
    const mine = new Map(draft.map((value) => [value.id, value]));
    const merged = remote.filter((value) => !old.has(value.id) || mine.has(value.id)).map((value) => old.has(value.id) && mine.has(value.id) ? mergeEdits(old.get(value.id), mine.get(value.id), value) : value);
    const ids = new Set(merged.map((value) => value.id));
    draft.forEach((value) => { if (!ids.has(value.id) && (!old.has(value.id) || !equal(old.get(value.id), value))) merged.push(value); });
    return merged;
  }
  if (base && draft && remote && typeof base === 'object' && typeof draft === 'object' && typeof remote === 'object' && !Array.isArray(base) && !Array.isArray(draft) && !Array.isArray(remote)) {
    let merged = structuredClone(remote);
    for (const key of new Set([...Object.keys(base), ...Object.keys(draft)])) {
      if (equal(base[key], draft[key])) continue;
      if (!Object.hasOwn(draft, key)) delete merged[key];
      else merged = { ...merged, [key]: mergeEdits(base[key], draft[key], remote[key]) };
    }
    return merged;
  }
  return structuredClone(draft);
}
function responseLines(value) {
  return [`Участие: ${answers[value.attendance] || 'нет ответа'}`, `Приезд: ${dateText(value.arrival, false)}`, `Отъезд: ${dateText(value.departure, false)}`, `Взрослых со мной: ${value.adults ?? 'не указано'}; детей: ${value.children ?? 'не указано'}`, `Бюджет: ${budgetText(value.budget)}`, `Заметки: ${value.notes || 'нет'}`, ...Object.entries(value.answers).map(([id, answer]) => `${T.data.trip.document.dates.options.find((option) => option.id === id)?.label || 'Старый вариант'}: ${answers[answer]}`)];
}
function describe(section, value) {
  if (!section) return responseLines(value);
  const lines = sectionLines(section, { [section]: value });
  if (section === 'dates') lines.push(...value.options.map((option) => `${option.label}: ${rangeText(option)}`));
  if (section === 'accommodation') lines.push(...value.candidates.map((item) => `${item.title}: ${dateText(item.arrival, false)} → ${dateText(item.departure, false)}; ${money(item.total_cents)}; котировка ${dateText(item.quoted_on, false)}; мест ${item.capacity ?? 'неизвестно'}; ${item.url}; ${item.notes}`));
  return lines;
}
function showConflict() {
  const editor = T.editor; const fresh = editor.conflict;
  const panel = $('#trip-edit-conflict'); panel.replaceChildren(); panel.hidden = false;
  panel.append(node('h3', '', 'Данные изменились. Ваш черновик остаётся в форме.'));
  const remote = editor.kind === 'section' ? fresh.trip.document[editor.section] : fresh.responses.find((item) => item.name_key === T.me)?.document || emptyResponse();
  let draft; try { draft = readEditor(); } catch { draft = editor.base; }
  const columns = node('div', 'comparison-columns');
  for (const [title, value] of [['Сейчас сохранено', remote], ['Ваш черновик', draft]]) {
    const column = node('div'); column.append(node('h4', '', title));
    describe(editor.section, value).forEach((line) => column.append(node('p', '', line))); columns.append(column);
  }
  panel.append(columns);
  if (editor.kind === 'response') fresh.trip.document.dates.options.forEach((option) => panel.append(node('p', 'muted', `Проверьте актуальные даты: ${option.label} · ${rangeText(option)}`)));
  panel.append(button('Применить мои правки к новым данным', () => {
    let local; try { local = readEditor(); } catch (error) { $('#trip-edit-error').textContent = error.message; return; }
    const merged = mergeEdits(editor.base, local, remote);
    T.data = fresh;
    if (editor.kind === 'response') {
      T.editor = null; editResponse(merged);
    } else {
      T.editor = null; editSection(editor.section, merged);
    }
    renderTrip();
  }), button('Отменить мой черновик', () => { T.data = fresh; T.editor = null; dialog.close(); renderTrip(); }, 'text-button'));
  syncEditor();
}
async function saveEditor(event) {
  event.preventDefault(); const editor = T.editor;
  if (!editor || editor.saving || editor.conflict || !form.reportValidity()) return;
  let sent; try { sent = readEditor(); } catch (error) { $('#trip-edit-error').textContent = error.message; return; }
  T.epoch += 1; T.refreshing = false;
  editor.saving = true; $('#trip-edit-error').textContent = ''; syncEditor();
  try {
    const response = editor.kind === 'section'
      ? await api('/api/trip', { method: 'PUT', body: JSON.stringify({ expected_revision: editor.revision, document: { ...editor.board, [editor.section]: sent } }) })
      : await api('/api/trip/response', { method: 'PUT', body: JSON.stringify({ expected_revision: editor.revision, expected_trip_revision: editor.tripRevision, document: sent }) });
    if (T.editor !== editor) return;
    if (editor.kind === 'section') {
      T.data.trip = response.trip; editor.base = structuredClone(response.trip.document[editor.section]); editor.board = sharedValues(response.trip.document); editor.revision = response.trip.revision;
    } else {
      T.data.responses = T.data.responses.filter((item) => item.name_key !== T.me).concat(response.response);
      editor.base = structuredClone(response.response.document); editor.revision = response.response.revision;
    }
    editor.saving = false; syncEditor(); renderTrip();
    if (!editor.dirty) { T.editor = null; dialog.close(); showToast('Изменения сохранены.'); }
    else $('#trip-edit-status').textContent = 'Отправленный вариант сохранён. Новые правки ещё не сохранены.';
    await refreshTrip();
  } catch (error) {
    if (T.editor !== editor) return;
    editor.saving = false;
    $('#trip-edit-error').textContent = `Не удалось сохранить. Черновик остаётся в этом окне. ${window.boysError ? window.boysError(error) : error.message}`;
    if (error.status === 409) {
      try {
        const fresh = await api('/api/trip');
        if (T.editor === editor && fresh.trip) { editor.conflict = fresh; showConflict(); }
      } catch { $('#trip-edit-error').textContent += ' Не удалось получить новые данные. Повторите попытку.'; }
    }
    syncEditor();
  }
}
async function decide(section, agreed) {
  if (T.pendingDecision || !T.data?.trip) return;
  T.epoch += 1; T.refreshing = false;
  T.pendingDecision = true; renderTrip();
  try {
    const result = await api('/api/trip/decision', { method: 'POST', body: JSON.stringify({ section, agreed, expected_revision: T.data.trip.revision }) });
    T.data.trip = result.trip; $('#trip-sync-status').textContent = 'Решение сохранено.';
  } catch (error) {
    $('#trip-sync-status').textContent = error.status === 409 ? 'Поездка изменилась. Проверьте новые значения и повторите действие.' : 'Не удалось сохранить решение. Повторите попытку.';
    if (error.status === 409) { T.pendingDecision = false; await refreshTrip(false); }
  } finally { T.pendingDecision = false; renderTrip(); }
}
async function loadActivity() {
  const epoch = T.epoch;
  const version = T.activityVersion = (T.activityVersion || 0) + 1;
  try {
    const result = await api('/api/trip/activity');
    const root = $('#trip-activity-list'); if (epoch !== T.epoch || version !== T.activityVersion || !root) return;
    root.replaceChildren();
    const labels = { seed: 'Создан черновик поездки', edit: 'Изменил общий план', response: 'Обновил свой ответ', agree: 'Отметил раздел как согласованный', reopen: 'Вернул раздел в черновик' };
    result.activity.slice(0, 12).forEach((event) => root.append(node('p', '', `${new Date(event.at).toLocaleString('ru-RU')} · ${event.by ? memberName(event.by) + ': ' : ''}${labels[event.action] || event.action}${event.detail.section ? ' — ' + titles[event.detail.section] : ''}`)));
  } catch { const root = $('#trip-activity-list'); if (epoch === T.epoch && version === T.activityVersion && root) root.textContent = 'История сейчас недоступна.'; }
}
function renderTrip() {
  if (!T.active) return;
  if (!T.data?.trip) {
    for (const id of ['#trip-overview', '#trip-options', '#trip-members']) $(id).replaceChildren(node('p', 'empty-state', 'Поездка ещё не настроена. Общая доступность остаётся в разделе «Даты».'));
    return;
  }
  renderOverview(); renderOptions(); renderMembers();
}
async function refreshTrip(showStatus = true) {
  if (!T.active || T.refreshing || T.editor?.saving || T.pendingDecision) return false;
  const epoch = T.epoch; T.refreshing = true;
  try {
    const payload = await api('/api/trip');
    if (epoch !== T.epoch || !T.active) return false;
    T.data = payload; T.me = payload.me;
    if (showStatus) $('#trip-sync-status').textContent = `Поездка обновлена: ${new Date().toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })}`;
    if (!T.monthOpened && payload.trip?.document.dates.options.length) { window.boysCalendar?.setMonth(payload.trip.document.dates.options[0].arrival); T.monthOpened = true; }
    renderTrip(); return true;
  } catch (error) {
    if (epoch === T.epoch) $('#trip-sync-status').textContent = error.status === 401 ? 'Сессия закончилась. Войдите в другом окне; черновик останется здесь.' : 'Не удалось обновить поездку. Показаны последние полученные данные.';
    return false;
  } finally { if (epoch === T.epoch) T.refreshing = false; }
}

function summaryText(includePrivate = false) {
  if (!T.data?.trip) return 'Поездка ещё не настроена.';
  const document = T.data.trip.document;
  const lines = [`Поездка: ${document.destination.name || 'направление не указано'}`, ...sectionLines('dates', document), `Бюджет: ${budgetText(document.budget)} · AUD на человека, без перелётов`, ...sectionLines('accommodation', document), ...sectionLines('call', document)];
  if (!document.dates.selected) lines.push(...document.dates.options.map((option) => `${option.label}: ${rangeText(option)}`));
  if (document.call.url) lines.push(document.call.url);
  lines.push('', 'Участники:');
  T.members.forEach((member) => {
    const value = T.data.responses.find((item) => item.name_key === member.name.toLowerCase())?.document;
    lines.push(`${member.name}: ${value?.attendance == null ? 'нет ответа' : answers[value.attendance]}`);
    if (includePrivate && value) {
      lines.push(`  Личный бюджет: ${budgetText(value.budget)}`);
      if (value.notes) lines.push(`  Дорога: ${value.notes}`);
    }
  });
  lines.push('', 'Решения:');
  Object.keys(titles).forEach((section) => lines.push(`${titles[section]}: ${statusLine(document.decisions[section])}`));
  lines.push('Отметка о согласовании принадлежит указанному участнику и не означает голосование всех.');
  return lines.join('\n');
}
async function openSummary() {
  if (!await refreshTrip()) return;
  $('#summary-private').checked = false;
  $('#trip-summary-text').value = summaryText(false);
  $('#trip-copy-status').textContent = 'В тексте только сохранённые данные.';
  $('#trip-summary-dialog').showModal();
}
$('#summary-private').addEventListener('change', () => {
  $('#trip-summary-text').value = summaryText($('#summary-private').checked);
  $('#trip-copy-status').textContent = 'Текст обновлён. Он ещё не скопирован.';
});
$('#trip-copy-button').addEventListener('click', async () => {
  try {
    await navigator.clipboard.writeText($('#trip-summary-text').value);
    $('#trip-copy-status').textContent = 'Скопировано. Вставьте текст в Telegram сами.';
  } catch {
    $('#trip-summary-text').focus(); $('#trip-summary-text').select();
    $('#trip-copy-status').textContent = 'Автоматическое копирование недоступно. Скопируйте выделенный текст вручную.';
  }
});
$('#trip-summary-close').addEventListener('click', () => $('#trip-summary-dialog').close());
$('#trip-edit-close').addEventListener('click', closeEditor);
dialog.addEventListener('cancel', (event) => { event.preventDefault(); closeEditor(); });
form.addEventListener('input', changedEditor);
form.addEventListener('change', changedEditor);
form.addEventListener('submit', saveEditor);

function openTrip(payload) {
  T.active = true; T.epoch += 1; T.refreshing = false; T.monthOpened = false;
  T.members = payload.participants; T.me = payload.me.toLowerCase(); T.data = null;
  $('#trip-sync-status').textContent = 'Загружаем поездку…';
  refreshTrip();
}
function resetTrip() {
  T.active = false; T.epoch += 1; T.refreshing = false; T.editor = null; T.data = null; T.pendingDecision = false;
  dialog.close(); $('#trip-summary-dialog').close();
  ['#trip-overview', '#trip-options', '#trip-members', '#trip-edit-fields'].forEach((id) => $(id).replaceChildren());
  $('#trip-summary-text').value = '';
}
window.boysTrip = { dirty: () => !!T.editor?.dirty, saving: () => !!T.editor?.saving || T.pendingDecision };
document.addEventListener('boys:open', (event) => openTrip(event.detail));
document.addEventListener('boys:close', resetTrip);
document.addEventListener('boys:members', (event) => { T.members = event.detail; if (T.data?.trip) renderTrip(); });
window.addEventListener('focus', () => refreshTrip());
setInterval(() => { if (!document.hidden) refreshTrip(); }, 30000);
if (window.boysCalendar?.session()) openTrip(window.boysCalendar.session());
