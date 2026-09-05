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
  if (test.info().title.startsWith('periodic refresh')) await page.clock.install();
  await page.goto('/');
  await expect(page.locator('#trip-caption')).toHaveText('Тестовый берег');
});
test.afterEach(() => expect(errors).toEqual([]));

test('range selection preserves old dates and gives keyboard day details', async ({ page }) => {
  const old = await (await page.request.get('/api/availability')).json();
  const history = old.participants.find((person) => person.name === 'Boris K').dates.filter((value) => value < day(0));
  await page.getByText('Выбрать диапазон', { exact: true }).click();
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

async function openLinks(page) {
  await page.locator('[data-view=links-panel]').click();
  await expect(page.locator('#calendar-grid')).toBeHidden();
  await expect(page.locator('#save-button')).toBeHidden();
}
async function addLink(page, title = 'Дом у воды', url = 'https://example.com/stay') {
  await openLinks(page);
  await page.locator('#add-link').click();
  await expect(page.locator('#link-title')).toBeFocused();
  await page.locator('#link-title').fill(title);
  await page.locator('#link-url').fill(url);
}
async function saveLink(page) {
  await page.locator('#link-save').click();
  await expect(page.locator('#link-editor')).toBeHidden();
}
function candidate(id, title) {
  return { id, title, url: 'https://example.com/' + id, arrival: day(60), departure: day(63), total_cents: 120000, quoted_on: day(0), capacity: 8, notes: 'Старая сохранённая заметка' };
}

test('calendar is the first screen and links have a separate two-field editor', async ({ page }) => {
  await expect(page.locator('#calendar-grid')).toBeVisible();
  await expect(page.locator(`[data-date="${day(60)}"]`)).toBeVisible();
  const remote = [];
  page.on('request', (request) => { if (new URL(request.url()).origin !== 'http://127.0.0.1:18183') remote.push(request.url()); });
  await addLink(page);
  await expect(page.locator('#link-editor input')).toHaveCount(2);
  await saveLink(page);
  await expect(page.getByRole('link', { name: 'Дом у воды' })).toHaveAttribute('href', 'https://example.com/stay');
  expect(remote).toEqual([]);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.reload();
  await expect(page.locator('#calendar-grid')).toBeVisible();
  await openLinks(page);
  await expect(page.getByRole('link', { name: 'Дом у воды' })).toBeVisible();
});

test('editing a link preserves saved quotes, hidden board fields, and responses', async ({ page }) => {
  await update(page, (document) => {
    document.accommodation = { candidates: [candidate('house', 'Старое название')], selected: 'house', paying_people: 6 };
    document.budget = { min_cents: 30000, max_cents: 70000 };
    document.call = { at: '2027-01-02T07:00:00Z', timezone: 'Pacific/Auckland', url: 'https://example.com/call' };
  });
  const before = await read(page);
  await page.reload(); await expect(page.locator('#trip-caption')).not.toBeEmpty(); await openLinks(page);
  await page.getByRole('button', { name: 'Изменить: Старое название', exact: true }).click();
  await page.locator('#link-title').fill('Новое название');
  await saveLink(page);
  const after = await read(page);
  const expected = before.trip.document; expected.accommodation.candidates[0].title = 'Новое название';
  delete expected.decisions;
  const actual = after.trip.document; delete actual.decisions;
  expect(actual).toEqual(expected);
  expect(after.responses).toEqual(before.responses);
});

test('failed link save retains the draft and retries', async ({ page }) => {
  await addLink(page);
  await page.route('**/api/trip', (route) => route.request().method() === 'PUT' ? route.abort('failed') : route.continue());
  await page.locator('#link-save').click();
  await expect(page.locator('#link-error')).toContainText('Не удалось сохранить');
  await expect(page.locator('#link-title')).toHaveValue('Дом у воды');
  await expect(page.locator('#link-save')).toBeEnabled();
  await page.unroute('**/api/trip'); await saveLink(page);
  await expect(page.getByRole('link', { name: 'Дом у воды' })).toBeVisible();
});

test('edits during a link save need a second save', async ({ page }) => {
  await addLink(page);
  let release, started;
  const pending = new Promise((resolve) => { started = resolve; });
  const wait = new Promise((resolve) => { release = resolve; });
  await page.route('**/api/trip', async (route) => {
    if (route.request().method() === 'PUT') { started(); await wait; }
    await route.continue();
  });
  await page.locator('#link-save').click(); await pending;
  await page.locator('#link-title').fill('Дом у озера');
  await expect(page.locator('#link-save')).toBeDisabled(); release();
  await expect(page.locator('#link-save')).toBeEnabled();
  await expect(page.locator('#link-editor')).toBeVisible();
  expect((await read(page)).trip.document.accommodation.candidates[0].title).toBe('Дом у воды');
  await saveLink(page);
  expect((await read(page)).trip.document.accommodation.candidates[0].title).toBe('Дом у озера');
});

test('conflicting additions retain the draft and preserve remote changes', async ({ page }) => {
  await addLink(page);
  await update(page, (document) => { document.accommodation.candidates.push(candidate('remote', 'Добавили в другом окне')); document.budget.max_cents = 85000; });
  await page.locator('#link-save').click();
  await expect(page.locator('#link-conflict')).toBeVisible();
  await expect(page.locator('#link-title')).toHaveValue('Дом у воды');
  await page.locator('#link-reapply').click(); await saveLink(page);
  const saved = (await read(page)).trip.document;
  expect(saved.accommodation.candidates.map((item) => item.title)).toEqual(['Добавили в другом окне', 'Дом у воды']);
  expect(saved.budget.max_cents).toBe(85000);
});

test('remote deletion requires review before restoring a link draft', async ({ page }) => {
  await update(page, (document) => document.accommodation.candidates.push(candidate('old', 'Дом')));
  await page.reload(); await expect(page.locator('#trip-caption')).not.toBeEmpty(); await openLinks(page);
  await page.getByRole('button', { name: 'Изменить: Дом', exact: true }).click();
  await page.locator('#link-title').fill('Исправленное название');
  await update(page, (document) => { document.accommodation.candidates = []; });
  await page.locator('#link-save').click();
  await expect(page.locator('#link-conflict')).toContainText('удалили в другом окне');
  expect((await read(page)).trip.document.accommodation.candidates).toEqual([]);
  await page.locator('#link-reapply').click(); await saveLink(page);
  expect((await read(page)).trip.document.accommodation.candidates[0].title).toBe('Исправленное название');
});

test('periodic refresh retains the link draft and reports failures', async ({ page }) => {
  await addLink(page);
  await update(page, (document) => document.accommodation.candidates.push(candidate('remote', 'Новая ссылка')));
  await page.clock.fastForward(30000);
  await expect(page.locator('#links-list')).toContainText('Новая ссылка');
  await expect(page.locator('#link-title')).toHaveValue('Дом у воды');
  await page.route('**/api/trip', (route) => route.abort('failed'));
  await page.evaluate(() => window.dispatchEvent(new Event('focus')));
  await expect(page.locator('#links-status')).toContainText('Не удалось обновить');
  await expect(page.locator('#link-title')).toHaveValue('Дом у воды');
});

test('keyboard close and unsaved navigation keep a link draft', async ({ page }) => {
  await addLink(page);
  let warning = page.waitForEvent('dialog');
  const closing = page.keyboard.press('Escape');
  await (await warning).dismiss(); await closing;
  await expect(page.locator('#link-title')).toHaveValue('Дом у воды');
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  warning = page.waitForEvent('dialog'); const loading = page.reload();
  const unload = await warning; expect(unload.type()).toBe('beforeunload');
  await unload.accept(); await loading;
});

test('deleting a selected link preserves unrelated data', async ({ page }) => {
  await update(page, (document) => { document.accommodation.candidates = [candidate('one', 'Удаляемая ссылка'), candidate('two', 'Остаётся')]; document.accommodation.selected = 'one'; document.accommodation.paying_people = 5; });
  await page.reload(); await expect(page.locator('#trip-caption')).not.toBeEmpty(); await openLinks(page);
  await page.getByRole('button', { name: 'Изменить: Удаляемая ссылка', exact: true }).click();
  page.once('dialog', (dialog) => dialog.accept());
  await page.locator('#link-delete').click();
  await expect(page.locator('#link-editor')).toBeHidden();
  const saved = (await read(page)).trip.document.accommodation;
  expect(saved.candidates).toEqual([candidate('two', 'Остаётся')]);
  expect(saved.selected).toBe(null); expect(saved.paying_people).toBe(5);
});
