/* Read-only live checks. No PINs, browser profiles, traces, or private responses are saved. */
const { chromium, expect } = require('@playwright/test');
const { execFileSync } = require('node:child_process');

class SmokeFailure extends Error {}

async function checkPublicJourney(page, baseURL) {
  const origin = new URL(baseURL).origin;
  const blockedWrites = [];
  let scriptErrors = 0;
  page.on('pageerror', () => { scriptErrors += 1; });
  await page.route('**/*', (route) => {
    const request = route.request();
    if (!['GET', 'HEAD'].includes(request.method())) {
      blockedWrites.push(request.method());
      return route.abort();
    }
    if (new URL(request.url()).origin !== origin) return route.abort();
    return route.continue();
  });
  async function get(path, status) {
    const response = await page.request.get(new URL(path, origin).href, { maxRedirects: 0, timeout: 10000 });
    if (response.status() !== status) throw new SmokeFailure(`${path}: expected HTTP ${status}, received ${response.status()}`);
    return response;
  }
  async function json(path) {
    const response = await get(path, 200);
    try { return await response.json(); } catch { throw new SmokeFailure(`${path}: invalid JSON`); }
  }
  if ((await json('/healthz')).ok !== true) throw new SmokeFailure('Health check did not confirm service health.');
  if ((await json('/ready')).ready !== true) throw new SmokeFailure('Readiness check did not confirm database access.');
  if ((await json('/api/session')).authenticated !== false) throw new SmokeFailure('The smoke context must be anonymous.');
  for (const path of ['/api/availability', '/api/events', '/api/trip', '/api/trip/activity']) await get(path, 401);
  await get('/seed.json', 404);
  const crew = (await json('/api/crew')).crew;
  if (!Array.isArray(crew) || crew.length !== 9 || new Set(crew.map((member) => member.name)).size !== 9 ||
      crew.some((member) => typeof member.name !== 'string' || typeof member.claimed !== 'boolean')) {
    throw new SmokeFailure('The public crew list must contain nine distinct identities and claim states.');
  }
  const response = await page.goto(origin, { waitUntil: 'networkidle', timeout: 15000 });
  if (response.status() !== 200 || new URL(page.url()).origin !== origin) throw new SmokeFailure('The public page did not load at its declared origin.');
  await expect(page.locator('#name option')).toHaveCount(10);
  await expect(page.locator('#access-view')).toBeVisible();
  await expect(page.locator('#calendar-view')).toBeHidden();
  const forms = {};
  for (const [key, claimed, form, input] of [
    ['personal_pin_screen', true, '#login-form', '#login-pin'],
    ['crew_pin_screen', false, '#crew-pin-form', '#seed-pin'],
  ]) {
    const member = crew.find((item) => item.claimed === claimed);
    if (!member) {
      forms[key] = { status: 'unknown', cause: `No ${claimed ? 'claimed' : 'unclaimed'} identity is available; the check does not change identities.` };
      continue;
    }
    await page.locator('#name').selectOption(member.name);
    await page.locator('#name-form button[type=submit]').focus();
    await page.keyboard.press('Enter');
    await expect(page.locator(form)).toBeVisible();
    await expect(page.locator(input)).toHaveAttribute('type', 'password');
    const box = await page.locator(input).boundingBox();
    if (!box || box.x < 0 || box.x + box.width > page.viewportSize().width) throw new SmokeFailure('The PIN control does not fit the viewport.');
    await page.locator(`${form} .choose-name-button`).click();
    await expect(page.locator('#name-form')).toBeVisible();
    forms[key] = { status: 'passed' };
  }
  if (scriptErrors) throw new SmokeFailure(`The page raised ${scriptErrors} JavaScript error(s).`);
  if (blockedWrites.length) throw new SmokeFailure('The public journey attempted a write; the browser blocked it.');
  return { status: 'passed', readiness: 'passed', private_routes: 'protected', ...forms };
}

async function main() {
  const report = {
    app: 'boys', status: 'partial', checked_at: new Date().toISOString(),
    authenticated_journey: { status: 'unknown', cause: 'No personal PIN or existing session is used. Sign-in, claim completion, calendar saves, and links require separate authenticated verification.' },
    layouts: {},
  };
  let browser;
  try {
    const app = JSON.parse(execFileSync('kubectl', ['--request-timeout=10s', '-n', 'argocd', 'get', 'application', 'boys', '-o', 'json'], { timeout: 20000, stdio: ['ignore', 'pipe', 'pipe'] }));
    const url = new URL(app.metadata.annotations['soyspray.vip/access-url']);
    if (url.protocol !== 'https:' || url.username || url.password || url.search || url.hash || url.pathname !== '/') throw new SmokeFailure('Application metadata must declare an HTTPS origin without credentials.');
    report.url = url.origin;
    browser = await chromium.launch({ timeout: 20000 });
    for (const [name, viewport] of [['desktop', { width: 1440, height: 1000 }], ['phone', { width: 390, height: 844 }]]) {
      const context = await browser.newContext({ viewport, serviceWorkers: 'block' });
      try {
        const page = await context.newPage();
        page.setDefaultTimeout(10000);
        report.layouts[name] = await checkPublicJourney(page, url.href);
      } finally { await context.close(); }
    }
  } catch (error) {
    report.status = 'failed';
    // Request failures and locator diagnostics can include response content. Keep it private.
    report.cause = error instanceof SmokeFailure ? error.message : `The read-only live check did not complete (${error.name || 'Error'}). Check application access, readiness, browser tools, and the public sign-in screen.`;
    process.exitCode = 1;
  } finally {
    if (browser) await browser.close();
    console.log(JSON.stringify(report, null, 2));
  }
}

module.exports = { checkPublicJourney };
if (require.main === module) main();
