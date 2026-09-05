const { test, expect } = require('@playwright/test');
const http = require('node:http');
const { checkPublicJourney } = require('../smoke');

test('live smoke checks the public journey without any write or session', async ({ page, baseURL }) => {
  const writes = [];
  page.on('request', (request) => {
    if (!['GET', 'HEAD'].includes(request.method())) writes.push(request.method());
  });
  const before = await (await page.request.get('/api/crew')).json();
  const report = await checkPublicJourney(page, baseURL);
  expect(report.status).toBe('passed');
  expect(report.private_routes).toBe('protected');
  expect(writes).toEqual([]);
  expect(await (await page.request.get('/api/crew')).json()).toEqual(before);
  expect(await (await page.request.get('/api/session')).json()).toEqual({ authenticated: false });
});

for (const failure of ['private route exposed', 'false readiness', 'redirect to sign-in']) {
  test(`live smoke rejects ${failure}`, async ({ page }) => {
    const server = http.createServer((request, response) => {
      if (failure === 'redirect to sign-in' && request.url === '/healthz') {
        response.writeHead(302, { Location: '/sign-in' }); response.end(); return;
      }
      const data = { '/healthz': { ok: true }, '/ready': { ready: failure !== 'false readiness' }, '/api/session': { authenticated: false } };
      response.writeHead(200, { 'Content-Type': 'application/json' });
      response.end(JSON.stringify(data[request.url] || { private: 'This must not appear in output.' }));
    });
    await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
    try {
      const result = checkPublicJourney(page, `http://127.0.0.1:${server.address().port}`);
      await expect(result).rejects.toThrow(failure === 'false readiness' ? 'Readiness' : 'expected HTTP');
    } finally { await new Promise((resolve) => server.close(resolve)); }
  });
}
