const { test, expect } = require('@playwright/test');

async function signIn(page) {
  const crew = await (await page.request.get('/api/crew')).json();
  if (!crew.crew.find((person) => person.name === 'Boris K').claimed) {
    await page.request.post('/api/claim', { data: { name: 'Boris K', seed_pin: '1357', pin: '2468' } });
  } else {
    await page.request.post('/api/session', { data: { name: 'Boris K', pin: '2468' } });
  }
  const current = await (await page.request.get('/api/availability')).json();
  await page.request.put('/api/availability', { data: { dates: [], expected_revision: current.revision } });
  await page.goto('/');
  await expect(page.locator('#calendar-view')).toBeVisible();
  await page.locator('[data-view=dates-panel]').click();
  await expect(page.locator('#trip-sync-status')).toContainText('Поездка обновлена');
  if (await days(page).count() < 3) await page.locator('#next-month').click();
}

function days(page) {
  return page.locator('.calendar-day[aria-readonly=false]');
}

async function updateElsewhere(page, dates) {
  const current = await (await page.request.get('/api/availability')).json();
  const saved = await page.request.put('/api/availability', { data: { dates, expected_revision: current.revision } });
  expect(saved.status()).toBe(200);
}

function futureDay(offset) {
  const day = new Date();
  day.setDate(day.getDate() + offset);
  return `${day.getFullYear()}-${String(day.getMonth() + 1).padStart(2, '0')}-${String(day.getDate()).padStart(2, '0')}`;
}

test('claim flow and personal PIN login remain separate', async ({ page }) => {
  await page.goto('/');
  const name = test.info().project.name === 'phone' ? 'Max Edin' : 'Sergey Kiktev';
  await page.locator('#name').selectOption(name);
  await page.locator('#name-form button[type=submit]').click();
  await page.locator('#seed-pin').fill('1357');
  await page.locator('#crew-pin-form button[type=submit]').click();
  await page.locator('#new-pin').fill('5678');
  await page.locator('#personal-pin-form button[type=submit]').click();
  await expect(page.locator('#signed-in-label')).toHaveText(name);
  await page.locator('#logout-button').click();
  await page.locator('#name').selectOption(name);
  await page.locator('#name-form button[type=submit]').click();
  await expect(page.locator('#login-form')).toBeVisible();
  await page.locator('#login-pin').fill('1357');
  await page.locator('#login-form button[type=submit]').click();
  await expect(page.locator('#login-error')).toContainText('не подходит');
  await page.locator('#login-pin').fill('5678');
  await page.locator('#login-form button[type=submit]').click();
  await expect(page.locator('#calendar-view')).toBeVisible();
  await expect(page.locator('#signed-in-label')).toHaveText(name);
  await page.reload();
  await expect(page.locator('#signed-in-label')).toHaveText(name);
});

test('failed saves keep the draft and permit a successful retry', async ({ page }) => {
  await signIn(page);
  await days(page).nth(0).click();
  await page.route('**/api/availability', (route) => route.request().method() === 'PUT' ? route.abort('failed') : route.continue());
  await page.locator('#save-button').click();
  await expect(page.locator('#save-status')).toContainText('Не удалось сохранить');
  await expect(page.locator('#save-button')).toBeEnabled();
  await expect(days(page).nth(0)).toHaveAttribute('aria-pressed', 'true');
  await page.unroute('**/api/availability');
  await page.locator('#save-button').click();
  await expect(page.locator('#save-status')).toHaveText('Общая доступность сохранена.');
  await page.reload();
  await page.locator('[data-view=dates-panel]').click();
  await expect(page.locator('#trip-sync-status')).toContainText('Поездка обновлена');
  await expect(days(page).nth(0)).toHaveAttribute('aria-pressed', 'true');
});

test('new edits during a save remain unsaved and no duplicate save starts', async ({ page }) => {
  await signIn(page);
  let release;
  let started;
  const pending = new Promise((resolve) => { started = resolve; });
  const wait = new Promise((resolve) => { release = resolve; });
  let writes = 0;
  await page.route('**/api/availability', async (route) => {
    if (route.request().method() === 'PUT') {
      writes += 1;
      started();
      await wait;
    }
    await route.continue();
  });
  await days(page).nth(0).click();
  await page.locator('#save-button').click();
  await pending;
  await days(page).nth(1).click();
  await expect(page.locator('#save-button')).toBeDisabled();
  release();
  await expect(page.locator('#save-status')).toHaveText('Есть несохранённые изменения.');
  expect(writes).toBe(1);
  await expect(days(page).nth(1)).toHaveAttribute('aria-pressed', 'true');
  await page.locator('#save-button').click();
  await expect(page.locator('#save-status')).toHaveText('Общая доступность сохранена.');
  await page.reload();
  await page.locator('[data-view=dates-panel]').click();
  await expect(page.locator('#trip-sync-status')).toContainText('Поездка обновлена');
  await expect(days(page).nth(0)).toHaveAttribute('aria-pressed', 'true');
  await expect(days(page).nth(1)).toHaveAttribute('aria-pressed', 'true');
});

test('conflicts preserve the draft and reapply its delta after review', async ({ page }) => {
  await signIn(page);
  await days(page).nth(0).click();
  await updateElsewhere(page, [futureDay(45)]);
  await page.locator('#save-button').click();
  await expect(page.locator('#save-conflict')).toBeVisible();
  await expect(days(page).nth(0)).toHaveAttribute('aria-pressed', 'true');
  await expect(page.locator('#save-button')).toBeDisabled();
  await page.locator('#reapply-dates').click();
  await page.locator('#save-button').click();
  await expect(page.locator('#save-status')).toHaveText('Общая доступность сохранена.');
  const saved = await (await page.request.get('/api/availability')).json();
  const mine = saved.participants.find((person) => person.name === 'Boris K');
  expect(mine.dates).toHaveLength(2);
  expect(mine.dates).toContain(futureDay(45));
});

test('focus refresh keeps local edits when this member changed elsewhere', async ({ page }) => {
  await signIn(page);
  await days(page).nth(0).click();
  await updateElsewhere(page, [futureDay(45)]);
  await page.evaluate(() => window.dispatchEvent(new Event('focus')));
  await expect(page.locator('#save-conflict')).toBeVisible();
  await expect(days(page).nth(0)).toHaveAttribute('aria-pressed', 'true');
  await page.locator('#use-remote-dates').click();
  await expect(page.locator('#save-conflict')).toBeHidden();
  await expect(days(page).nth(0)).toHaveAttribute('aria-pressed', 'false');
});

test('keyboard selection, layout, and unsaved navigation protection', async ({ page }) => {
  await signIn(page);
  await days(page).nth(0).focus();
  await page.keyboard.press('Space');
  await expect(days(page).nth(0)).toHaveAttribute('aria-pressed', 'true');
  await expect(days(page).nth(0)).toBeFocused();
  const dialogPromise = page.waitForEvent('dialog');
  const navigation = page.locator('a[href="/events.html"]').click();
  const dialog = await dialogPromise;
  expect(dialog.type()).toBe('confirm');
  await dialog.dismiss();
  await navigation;
  await expect(page.locator('#calendar-view')).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  if (test.info().project.name === 'phone') {
    const save = await page.locator('#save-button').boundingBox();
    expect(save.y + save.height).toBeLessThanOrEqual(844);
  }
  const unload = page.waitForEvent('dialog');
  const reloading = page.reload();
  const warning = await unload;
  expect(warning.type()).toBe('beforeunload');
  await warning.accept();
  await reloading;
});


test('a lost acknowledgement is confirmed by conflict recovery', async ({ page }) => {
  await signIn(page);
  await days(page).nth(0).click();
  await page.route('**/api/availability', async (route) => {
    if (route.request().method() === 'PUT') {
      await route.fetch();
      await route.abort('failed');
    } else await route.continue();
  });
  await page.locator('#save-button').click();
  await expect(page.locator('#save-status')).toContainText('Не удалось сохранить');
  await page.unroute('**/api/availability');
  await page.locator('#save-button').click();
  await expect(page.locator('#save-status')).toHaveText('Общая доступность сохранена.');
  await expect(page.locator('#save-conflict')).toBeHidden();
});

test('a delayed refresh cannot overwrite a later save acknowledgement', async ({ page }) => {
  await signIn(page);
  let release;
  let fetched;
  const pending = new Promise((resolve) => { fetched = resolve; });
  const wait = new Promise((resolve) => { release = resolve; });
  await page.route('**/api/availability', async (route) => {
    if (route.request().method() === 'GET') {
      const response = await route.fetch();
      fetched();
      await wait;
      await route.fulfill({ response });
    } else await route.continue();
  });
  await page.evaluate(() => window.dispatchEvent(new Event('focus')));
  await pending;
  await days(page).nth(0).click();
  await page.locator('#save-button').click();
  await expect(page.locator('#save-status')).toHaveText('Общая доступность сохранена.');
  const refreshed = page.waitForResponse((response) => response.url().endsWith('/api/availability') && response.request().method() === 'GET');
  release();
  await refreshed;
  await expect(days(page).nth(0)).toHaveAttribute('aria-pressed', 'true');
  await expect(page.locator('#save-status')).toHaveText('Общая доступность сохранена.');
});

test('periodic refresh updates another member without losing the local draft', async ({ page, playwright }) => {
  await page.clock.install();
  await signIn(page);
  await days(page).nth(0).click();
  const other = await playwright.request.newContext({ baseURL: 'http://127.0.0.1:18183' });
  try {
    const crew = await (await other.get('/api/crew')).json();
    const name = 'Bronislav';
    if (crew.crew.find((person) => person.name === name).claimed) {
      await other.post('/api/session', { data: { name, pin: '5678' } });
    } else {
      await other.post('/api/claim', { data: { name, seed_pin: '1357', pin: '5678' } });
    }
    const current = await (await other.get('/api/availability')).json();
    await other.put('/api/availability', { data: { dates: [futureDay(20)], expected_revision: current.revision } });
    await page.clock.fastForward(30000);
    await expect(page.locator('#legend')).toContainText('Bronislav · дней: 1');
    await expect(days(page).nth(0)).toHaveAttribute('aria-pressed', 'true');
    await expect(page.locator('#save-status')).toHaveText('Есть несохранённые изменения.');
  } finally {
    await other.dispose();
  }
});


test('crew patterns remain distinct and runtime assets stay local', async ({ page }) => {
  const remote = [];
  page.on('request', (request) => {
    if (new URL(request.url()).origin !== 'http://127.0.0.1:18183') remote.push(request.url());
  });
  await signIn(page);
  const patterns = await page.locator('.legend-mark').evaluateAll((marks) => marks.map((mark) => {
    const style = getComputedStyle(mark);
    return [style.backgroundColor, style.backgroundImage];
  }));
  expect(patterns).toHaveLength(9);
  expect(new Set(patterns.map((pattern) => JSON.stringify(pattern))).size).toBe(9);
  expect(remote).toEqual([]);
});
