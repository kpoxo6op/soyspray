const { test, expect } = require('@playwright/test');

function day(offset) {
  const value = new Date(); value.setDate(value.getDate() + offset);
  return `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, '0')}-${String(value.getDate()).padStart(2, '0')}`;
}
function board() {
  return {
    destination: { name: 'Тестовый берег' },
    dates: { options: [
      { id: 'short', label: 'Три ночи', arrival: day(60), departure: day(63) },
      { id: 'long', label: 'Четыре ночи', arrival: day(60), departure: day(64) },
    ], selected: null },
    budget: { min_cents: null, max_cents: null },
    accommodation: { candidates: [], selected: null, paying_people: null },
    call: { at: null, timezone: null, url: '' },
  };
}
const emptyResponse = () => ({ answers: {}, attendance: null, arrival: null, departure: null, adults: null, children: null, notes: '', budget: { min_cents: null, max_cents: null } });
async function read(page) { return (await page.request.get('/api/trip')).json(); }
async function update(page, change) {
  const current = await read(page);
  const document = current.trip.document; delete document.decisions;
  change(document);
  const result = await page.request.put('/api/trip', { data: { document, expected_revision: current.trip.revision } });
  expect(result.status()).toBe(200);
  return result.json();
}
async function openSection(page, title) {
  await page.locator('#trip-overview .trip-card').filter({ has: page.getByRole('heading', { name: title, exact: true }) }).getByRole('button', { name: 'Изменить', exact: true }).click();
}
async function save(page) {
  await page.locator('#trip-edit-save').click();
  await expect(page.locator('#trip-editor')).not.toBeVisible();
}
let errors;
test.beforeEach(async ({ page }) => {
  errors = []; page.on('pageerror', (error) => errors.push(error.message));
  const crew = await (await page.request.get('/api/crew')).json();
  const claimed = crew.crew.find((item) => item.name === 'Boris K').claimed;
  const auth = await page.request.post(claimed ? '/api/session' : '/api/claim', { data: { name: 'Boris K', pin: '2468', ...(claimed ? {} : { seed_pin: '1357' }) } });
  expect(auth.status()).toBe(200);
  const dates = await (await page.request.get('/api/availability')).json();
  expect((await page.request.put('/api/availability', { data: { dates: [], expected_revision: dates.revision } })).status()).toBe(200);
  await update(page, (document) => Object.assign(document, board()));
  const current = await read(page);
  const mine = current.responses.find((item) => item.name_key === 'boris k');
  const response = await page.request.put('/api/trip/response', { data: { document: emptyResponse(), expected_revision: mine?.revision || 0, expected_trip_revision: current.trip.revision } });
  expect(response.status()).toBe(200);
  if (test.info().title.startsWith('periodic trip')) await page.clock.install();
  await page.goto('/');
  await expect(page.locator('#trip-overview')).toContainText('Тестовый берег');
});
test.afterEach(() => expect(errors).toEqual([]));

test('three views show unknown values and the active trip month', async ({ page }) => {
  await expect(page.locator('#trip-overview')).toContainText('Что ещё нужно решить');
  await expect(page.locator('#trip-overview')).toContainText('AUD на человека, без перелётов');
  await expect(page.locator('#trip-overview')).toContainText('Звонок ещё не назначен');
  await page.locator('[data-view=dates-panel]').click();
  const cards = page.locator('.date-option');
  await expect(cards).toHaveCount(2);
  await expect(cards.nth(0)).toContainText('Ночей: 3 · полных общих дней: 2');
  await expect(cards.nth(1)).toContainText('Ночей: 4 · полных общих дней: 3');
  await expect(cards.nth(0).locator('li').filter({ hasText: 'Boris K' })).toContainText('Нет ответа');
  await expect(page.locator(`[data-date="${day(60)}"]`)).toBeVisible();
  await page.locator('[data-view=members-panel]').click();
  await expect(page.locator('.member-card')).toHaveCount(9);
  await expect(page.locator('.member-card').filter({ hasText: 'Boris K' })).toContainText('Нет ответа об участии');
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
});

test('range selection preserves old dates and gives keyboard day details', async ({ page }) => {
  const old = await (await page.request.get('/api/availability')).json();
  const history = old.participants.find((person) => person.name === 'Boris K').dates.filter((value) => value < day(0));
  await page.locator('[data-view=dates-panel]').click();
  await page.locator('#range-start').fill(day(61)); await page.locator('#range-end').fill(day(63));
  await page.getByRole('button', { name: 'Выбрать дни', exact: true }).click();
  await expect(page.locator(`[data-date="${day(62)}"]`)).toHaveAttribute('aria-pressed', 'true');
  await expect(page.locator('#day-details')).toContainText('Boris K');
  await page.locator('#save-button').click();
  await expect(page.locator('#save-status')).toHaveText('Общая доступность сохранена.');
  const fresh = await (await page.request.get('/api/availability')).json();
  expect(fresh.participants.find((person) => person.name === 'Boris K').dates).toEqual(expect.arrayContaining([...history, day(61), day(62), day(63)]));
  await page.locator('#range-start').fill(day(62)); await page.locator('#range-end').fill(day(62));
  await page.getByRole('button', { name: 'Убрать дни', exact: true }).click();
  await expect(page.locator(`[data-date="${day(62)}"]`)).toHaveAttribute('aria-pressed', 'false');
  await page.locator(`[data-date="${day(62)}"]`).focus(); await page.keyboard.press('Space');
  await expect(page.locator(`[data-date="${day(62)}"]`)).toBeFocused();
});

test('shared changes attribute agreement and reopen edited values', async ({ page }) => {
  const card = page.locator('.trip-card').filter({ has: page.getByRole('heading', { name: 'Направление', exact: true }) });
  await card.getByRole('button', { name: 'Отметить как согласованное' }).click();
  await expect(card).toContainText('Отметил как согласованное: Boris K');
  await openSection(page, 'Направление'); await page.getByLabel('Куда едем').fill('Новый тестовый берег'); await save(page);
  await expect(card.locator('.decision-badge')).toHaveText('Черновик');
  await card.getByRole('button', { name: 'Отметить как согласованное' }).click();
  await card.getByRole('button', { name: 'Вернуть в черновик' }).click();
  await expect(card).toContainText('Вернул в черновик: Boris K');
  await expect(page.locator('#trip-activity-list')).toContainText('Boris K');
});

test('own response keeps unanswered choices and exact cents separate from availability', async ({ page }) => {
  const before = await (await page.request.get('/api/availability')).json();
  await page.getByRole('button', { name: 'Мой ответ и дорога', exact: true }).click();
  await page.locator('[name="answer.short"]').selectOption('maybe');
  await page.getByLabel('Планируете поехать?').selectOption('yes');
  await page.getByLabel('Мой приезд', { exact: true }).fill(day(59));
  await page.getByLabel('Мой отъезд', { exact: true }).fill(day(64));
  await page.getByLabel('Со мной взрослых, не считая меня').fill('0');
  await page.getByLabel('Со мной детей').fill('2');
  await page.getByLabel('Минимум, AUD', { exact: true }).fill('123,45');
  await page.getByLabel('Коротко о дороге. Имена семьи не нужны.').fill('Личная тестовая заметка');
  await save(page);
  const current = await read(page); const mine = current.responses.find((item) => item.name_key === 'boris k').document;
  expect(mine.answers).toEqual({ short: 'maybe' });
  expect(mine.budget).toEqual({ min_cents: 12345, max_cents: null });
  expect(mine.adults).toBe(0); expect(mine.children).toBe(2);
  expect((await (await page.request.get('/api/availability')).json()).revision).toBe(before.revision);
  await update(page, (document) => { document.dates.selected = 'short'; });
  await page.evaluate(() => dispatchEvent(new Event('focus')));
  await page.locator('[data-view=members-panel]').click();
  const card = page.locator('.member-card').filter({ hasText: 'Boris K' });
  await expect(card).toContainText('Приезд отличается от общих дат на 1 дн. (раньше)');
  await expect(card).toContainText('Отъезд отличается от общих дат на 1 дн. (позже)');
});

test('failed trip saves retry and in-flight edits remain a draft', async ({ page }) => {
  await openSection(page, 'Направление'); await page.getByLabel('Куда едем').fill('Первый черновик');
  await page.route('**/api/trip', (route) => route.request().method() === 'PUT' ? route.abort('failed') : route.continue());
  await page.locator('#trip-edit-save').click();
  await expect(page.locator('#trip-edit-error')).toContainText('Не удалось сохранить');
  await expect(page.getByLabel('Куда едем')).toHaveValue('Первый черновик');
  await expect(page.locator('#trip-edit-save')).toBeEnabled();
  await page.unroute('**/api/trip');
  let release; let started;
  const pending = new Promise((resolve) => { started = resolve; });
  const wait = new Promise((resolve) => { release = resolve; });
  await page.route('**/api/trip', async (route) => { if (route.request().method() === 'PUT') { started(); await wait; } await route.continue(); });
  await page.locator('#trip-edit-save').click(); await pending;
  await page.getByLabel('Куда едем').fill('Более новый черновик');
  await expect(page.locator('#trip-edit-save')).toBeDisabled(); release();
  await expect(page.locator('#trip-edit-status')).toContainText('Новые правки ещё не сохранены');
  await expect(page.getByLabel('Куда едем')).toHaveValue('Более новый черновик');
  expect((await read(page)).trip.document.destination.name).toBe('Первый черновик');
  await save(page); expect((await read(page)).trip.document.destination.name).toBe('Более новый черновик');
});

test('a shared conflict retains local fields and preserves another section', async ({ page }) => {
  await openSection(page, 'Направление'); await page.getByLabel('Куда едем').fill('Мой берег');
  await update(page, (document) => { document.destination.name = 'Их берег'; document.budget.min_cents = 55500; });
  await page.locator('#trip-edit-save').click();
  await expect(page.locator('#trip-edit-conflict')).toContainText('Их берег');
  await expect(page.getByLabel('Куда едем')).toHaveValue('Мой берег');
  await page.getByRole('button', { name: 'Применить мои правки к новым данным' }).click();
  await save(page);
  const current = await read(page); expect(current.trip.document.destination.name).toBe('Мой берег'); expect(current.trip.document.budget.min_cents).toBe(55500);
});

test('changed trip dates require review before an old draft can answer them', async ({ page }) => {
  await page.getByRole('button', { name: 'Мой ответ и дорога', exact: true }).click();
  await page.locator('[name="answer.short"]').selectOption('yes');
  await update(page, (document) => { document.dates.options[0].departure = day(65); });
  await page.evaluate(() => dispatchEvent(new Event('focus')));
  await expect(page.locator('[name="answer.short"]')).toHaveValue('yes');
  await page.locator('#trip-edit-save').click();
  await expect(page.locator('#trip-edit-conflict')).toContainText('Проверьте актуальные даты');
  await page.getByRole('button', { name: 'Применить мои правки к новым данным' }).click(); await save(page);
  expect((await read(page)).responses.find((item) => item.name_key === 'boris k').document.answers.short).toBe('yes');
  await update(page, (document) => { document.dates.options[0].departure = day(66); });
  await page.evaluate(() => dispatchEvent(new Event('focus')));
  await page.locator('[data-view=dates-panel]').click();
  await expect(page.locator('.date-option').first().locator('li').filter({ hasText: 'Boris K' })).toContainText('Даты изменились — нужен новый ответ');
});

test('accommodation uses manual quotes and an explicit paying count', async ({ page }) => {
  const external = []; page.on('request', (request) => { if (new URL(request.url()).origin !== 'http://127.0.0.1:18183') external.push(request.url()); });
  await openSection(page, 'Жильё'); await page.getByRole('button', { name: 'Добавить вариант', exact: true }).click();
  await page.getByLabel('Название жилья', { exact: true }).fill('Тестовый дом');
  await page.getByLabel('Ссылка на жильё', { exact: true }).fill('https://example.com/stay');
  await page.getByLabel('Общая котировка за проживание, AUD').fill('1234,56');
  await page.getByLabel('Дата котировки', { exact: true }).fill(day(0));
  await page.getByLabel('Вместимость, человек').fill('8');
  await page.getByLabel('Выбранное жильё').selectOption({ label: 'Тестовый дом' }); await save(page);
  const card = page.locator('.accommodation-list .trip-card');
  await expect(card).toContainText('На человека: неизвестно');
  await openSection(page, 'Жильё'); await page.getByLabel('Количество платящих людей для расчёта').fill('3'); await save(page);
  await expect(card).toContainText('411,52');
  expect((await read(page)).trip.document.accommodation.paying_people).toBe(3);
  expect(external).toEqual([]);
});

test('call editor handles summer winter and ambiguous local times', async ({ page }) => {
  await openSection(page, 'Следующий звонок');
  await page.getByLabel('Дата и время звонка', { exact: true }).fill('2030-01-15T19:00');
  await expect(page.locator('#call-preview')).toContainText('16:00');
  await page.getByLabel('Ссылка для подключения').fill('https://example.com/call'); await save(page);
  expect((await read(page)).trip.document.call).toEqual({ at: '2030-01-15T06:00:00Z', timezone: 'Pacific/Auckland', url: 'https://example.com/call' });
  await openSection(page, 'Следующий звонок'); await page.getByLabel('Дата и время звонка', { exact: true }).fill('2030-07-15T19:00');
  await expect(page.locator('#call-preview')).toContainText('17:00'); await save(page);
  expect((await read(page)).trip.document.call.at).toBe('2030-07-15T07:00:00Z');
  await openSection(page, 'Следующий звонок'); await page.getByLabel('Дата и время звонка', { exact: true }).fill('2030-09-29T02:30');
  await expect(page.locator('#call-preview')).toContainText('Такого времени нет');
  await page.getByLabel('Дата и время звонка', { exact: true }).fill('2030-04-07T02:30');
  await expect(page.locator('#call-occurrence')).toBeVisible();
  await page.locator('[name=call-instant]').selectOption('2030-04-06T14:30:00.000Z'); await save(page);
  expect((await read(page)).trip.document.call.at).toBe('2030-04-06T14:30:00Z');
});

test('manual summary excludes personal details and navigation warns about drafts', async ({ page }) => {
  await page.getByRole('button', { name: 'Мой ответ и дорога', exact: true }).click();
  await page.getByLabel('Коротко о дороге. Имена семьи не нужны.').fill('Секретная тестовая дорога');
  await page.getByLabel('Минимум, AUD', { exact: true }).fill('987,65'); await save(page);
  await page.getByRole('button', { name: 'Текст для Telegram', exact: true }).click();
  await expect(page.locator('#trip-summary-text')).not.toHaveValue(/Секретная тестовая дорога|987,65/);
  await page.locator('#summary-private').check();
  await expect(page.locator('#trip-summary-text')).toHaveValue(/Секретная тестовая дорога/);
  await expect(page.locator('#trip-copy-status')).not.toContainText('Скопировано');
  await page.locator('#trip-summary-close').click();
  await openSection(page, 'Направление'); await page.getByLabel('Куда едем').fill('Несохранённый берег');
  const closed = page.waitForEvent('dialog'); const escape = page.keyboard.press('Escape');
  const confirmation = await closed; expect(confirmation.type()).toBe('confirm'); await confirmation.dismiss(); await escape;
  await expect(page.getByLabel('Куда едем')).toHaveValue('Несохранённый берег');
  const unload = page.waitForEvent('dialog'); const reload = page.reload();
  const warning = await unload; expect(warning.type()).toBe('beforeunload'); await warning.accept(); await reload;
  await expect(page.locator('#trip-overview')).toContainText('Тестовый берег');
});

test('conflict reapply keeps a remote deletion and a remote addition', async ({ page }) => {
  await openSection(page, 'Даты поездки');
  await page.locator('[name="short.title"]').fill('Мой вариант');
  await update(page, (document) => {
    document.dates.options = [document.dates.options[0], { id: 'remote', label: 'Новый чужой вариант', arrival: day(70), departure: day(73) }];
  });
  await page.locator('#trip-edit-save').click();
  await expect(page.locator('#trip-edit-conflict')).toBeVisible();
  await page.getByRole('button', { name: 'Применить мои правки к новым данным' }).click();
  await expect(page.locator('[name="long.title"]')).toHaveCount(0);
  await expect(page.locator('[name="remote.title"]')).toHaveValue('Новый чужой вариант');
  await save(page);
  expect((await read(page)).trip.document.dates.options.map((item) => item.id)).toEqual(['short', 'remote']);
});

test('lost trip acknowledgement can be reviewed without a duplicate audit entry', async ({ page }) => {
  await openSection(page, 'Направление'); await page.getByLabel('Куда едем').fill('Сохранено без ответа');
  await page.route('**/api/trip', async (route) => {
    if (route.request().method() === 'PUT') { await route.fetch(); await route.abort('failed'); }
    else await route.continue();
  });
  await page.locator('#trip-edit-save').click();
  await expect(page.locator('#trip-edit-error')).toContainText('Не удалось сохранить');
  await page.unroute('**/api/trip');
  const revision = (await read(page)).trip.revision;
  await page.locator('#trip-edit-save').click();
  await expect(page.locator('#trip-edit-conflict')).toBeVisible();
  await page.getByRole('button', { name: 'Применить мои правки к новым данным' }).click();
  await expect(page.locator('#trip-edit-save')).toBeDisabled();
  await page.locator('#trip-edit-close').click();
  expect((await read(page)).trip.revision).toBe(revision);
});

test('periodic trip refresh updates responses while keeping an open draft', async ({ page, playwright }) => {
  await openSection(page, 'Направление'); await page.getByLabel('Куда едем').fill('Мой локальный берег');
  const other = await playwright.request.newContext({ baseURL: 'http://127.0.0.1:18183' });
  try {
    const crew = await (await other.get('/api/crew')).json(); const name = 'Vitaly Borisov';
    const claimed = crew.crew.find((item) => item.name === name).claimed;
    expect((await other.post(claimed ? '/api/session' : '/api/claim', { data: { name, pin: '5678', ...(claimed ? {} : { seed_pin: '1357' }) } })).status()).toBe(200);
    const current = await (await other.get('/api/trip')).json();
    const mine = current.responses.find((item) => item.name_key === name.toLowerCase());
    const attendance = mine?.document.attendance === 'maybe' ? 'yes' : 'maybe';
    const response = { ...emptyResponse(), attendance, answers: { long: 'maybe' } };
    expect((await other.put('/api/trip/response', { data: { document: response, expected_revision: mine?.revision || 0, expected_trip_revision: current.trip.revision } })).status()).toBe(200);
    await page.clock.fastForward(30000);
    await expect(page.locator('.member-card').filter({ hasText: name })).toContainText(attendance === 'maybe' ? 'Участие: Возможно' : 'Участие: Да');
    await expect(page.locator('.member-card').filter({ hasText: name })).not.toContainText('Имя ещё не закреплено');
    await expect(page.getByLabel('Куда едем')).toHaveValue('Мой локальный берег');
    await expect(page.locator('#trip-edit-save')).toBeEnabled();
  } finally { await other.dispose(); }
});
