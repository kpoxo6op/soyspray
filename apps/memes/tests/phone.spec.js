const {test,expect} = require('@playwright/test');
const fs = require('node:fs');
test('private phone feed preloads two and commits clicks, with results matching the API', async ({page,request}, testInfo) => {
  // Infrastructure tests do not own authenticated image rendering or touch targets.
  expect((await request.get('/api/feed')).status()).toBe(401);
  await page.goto(JSON.parse(fs.readFileSync('test-results/invite','utf8'))[testInfo.project.name]);
  await expect(page.getByRole('button',{name:'👍 Like'})).toBeEnabled();
  await expect(page.locator('#meme')).toBeVisible();
  const feed = await page.evaluate(async () => (await fetch('/api/feed')).json());
  expect(feed.items).toHaveLength(3);
  expect(JSON.stringify(feed)).not.toMatch(/"(arm|score|assignment_prob)"/);
  await expect.poll(() => page.evaluate(() => performance.getEntriesByType('resource').filter(r => r.name.includes('/images/')).length)).toBeGreaterThanOrEqual(3);
  const box = await page.getByRole('button',{name:'👍 Like'}).boundingBox();
  expect(box.height).toBeGreaterThanOrEqual(60);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  for (const action of ['👍 Like','👎 Dislike','Skip']) {
    const before = await page.locator('#meme').getAttribute('src');
    await page.getByRole('button',{name:action,exact:true}).click();
    await expect(page.locator('#meme')).not.toHaveAttribute('src',before);
    await expect(page.getByRole('button',{name:'👍 Like'})).toBeEnabled();
  }
  await page.getByRole('link',{name:'Results',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Your results'})).toBeVisible();
  await expect(page.locator('#stats')).toContainText('Warm-up: 1 likes, 1 dislikes, 1 skips.');
  await expect(page.locator('#verdict')).toContainText('Not enough data');
  const results = await page.evaluate(async () => (await fetch('/api/results')).json());
  expect(results.warmup.likes).toBe(1);expect(results.warmup.dislikes).toBe(1);expect(results.warmup.skips).toBe(1);
});
