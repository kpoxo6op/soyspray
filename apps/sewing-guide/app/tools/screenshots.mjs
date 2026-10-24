// Visual check: phone and desktop screenshots of every section against a running server.
// node tools/screenshots.mjs http://127.0.0.1:4174 out-dir
import { chromium } from 'playwright-core';
import { mkdirSync } from 'node:fs';
import { join } from 'node:path';

const base = process.argv[2] || 'http://127.0.0.1:4174';
const out = process.argv[3] || '/tmp/sewing-shots';
mkdirSync(out, { recursive: true });

const routes = [
  ['home', '#/'],
  ['machine', '#/machine/explore'],
  ['thread-3', '#/machine/thread/3'],
  ['bobbin-1', '#/machine/bobbin/1'],
  ['wind-4', '#/machine/wind/4'],
  ['idt-1', '#/machine/idt/1'],
  ['pack-4', '#/machine/pack/4'],
  ['start', '#/start'],
  ['stitches', '#/stitches'],
  ['stitch-02', '#/stitches/02'],
  ['stitch-67', '#/stitches/67'],
  ['stitch-16', '#/stitches/16'],
  ['fabrics', '#/fabrics'],
  ['fabric-silk', '#/fabrics/silk'],
  ['projects', '#/projects'],
  ['project-piped', '#/projects/piped-cushion'],
  ['fix', '#/fix'],
  ['fix-tunneling', '#/fix/tunneling'],
];

const browser = await chromium.launch({ executablePath: process.env.CHROME_PATH || undefined, args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
const errors = [];
for (const [name, viewport, lang] of [
  ['phone', { width: 390, height: 844 }, 'en'],
  ['desktop', { width: 1280, height: 800 }, 'ru'],
]) {
  const ctx = await browser.newContext({ viewport, deviceScaleFactor: 1, locale: lang === 'ru' ? 'ru-RU' : 'en-NZ' });
  const page = await ctx.newPage();
  page.on('pageerror', (e) => errors.push(`${name}: ${e.message}`));
  page.on('console', (m) => {
    if (m.type() === 'error') errors.push(`${name} console: ${m.text()}`);
  });
  for (const [id, hash] of routes) {
    await page.goto(`${base}/?lang=${lang}${hash}`, { waitUntil: 'load' });
    await page.waitForTimeout(hash.includes('machine') ? 1800 : 400);
    await page.screenshot({ path: join(out, `${name}-${id}.png`), fullPage: !hash.includes('machine') });
  }
  await ctx.close();
}
await browser.close();
if (errors.length) {
  console.error('ERRORS:\n' + errors.join('\n'));
  process.exit(1);
}
console.log('screenshots in', out);
