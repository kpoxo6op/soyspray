// One browser page for one agent run, driven over local HTTP so an agent can call it from a shell.
//   node server.mjs --mode browser|bridge --url <page> --port <n> --log <run.jsonl>
// browser: Playwright's AI snapshot with refs, click, type, press and screenshot, each action answering with a
//          fresh snapshot, as the Playwright MCP browser tools do.
// bridge:  the page's UI SDK agent bridge, window.agent.snapshot(), act() and query(), and nothing else.
// Every call is logged with its time and the characters it returned. GET /state is for the scorer, not the agent.
import { createServer } from 'node:http';
import { appendFileSync } from 'node:fs';
import { chromium } from 'playwright';

const arg = (name) => process.argv[process.argv.indexOf(`--${name}`) + 1];
const mode = arg('mode');
const port = Number(arg('port'));
const log = arg('log');
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
await page.goto(arg('url'));
await page.waitForLoadState('networkidle');

const snapshot = () => page.ariaSnapshot({ mode: 'ai' });
const ref = (r) => page.locator(`aria-ref=${String(r).replace(/^ref=/, '')}`);
let shots = 0;

const commands = {
  browser: {
    snapshot: async () => snapshot(),
    click: async ([r]) => (await ref(r).click({ timeout: 5000 }), snapshot()),
    type: async ([r, ...text]) => (await ref(r).fill(text.join(' '), { timeout: 5000 }), snapshot()),
    press: async ([key]) => (await page.keyboard.press(key), snapshot()),
    screenshot: async () => {
      const path = `${log}.shot${++shots}.png`;
      await page.screenshot({ path });
      return `Saved ${path}. Read the file to see it.`;
    },
  },
  bridge: {
    snapshot: async () => JSON.stringify(await page.evaluate(() => window.agent.snapshot())),
    act: async ([json]) => JSON.stringify(await page.evaluate((steps) => window.agent.act(steps), JSON.parse(json))),
    query: async ([json]) => JSON.stringify(await page.evaluate((q) => window.agent.query(q), JSON.parse(json))),
  },
}[mode];

createServer(async (req, res) => {
  if (req.method === 'GET' && req.url === '/state') {
    const state = await page.evaluate(() => ({
      url: location.href,
      count: document.querySelector('[data-count]')?.textContent,
      search: document.querySelector('input[type=search]')?.value,
      visible: [...document.querySelectorAll('li[data-id]:not([hidden])')].map((li) => li.dataset.id),
      storage: Object.fromEntries(Object.keys(localStorage).map((k) => [k, JSON.parse(localStorage.getItem(k))])),
    }));
    res.end(JSON.stringify(state));
    return;
  }
  let body = '';
  for await (const chunk of req) body += chunk;
  const { cmd, args = [] } = JSON.parse(body || '{}');
  const t0 = Date.now();
  let out;
  try {
    if (!commands[cmd]) throw new Error(`Unknown command ${cmd}. Commands: ${Object.keys(commands).join(', ')}`);
    out = await commands[cmd](args);
  } catch (e) {
    out = `Error: ${e.message.split('\n')[0]}`;
  }
  appendFileSync(log, JSON.stringify({ at: t0, ms: Date.now() - t0, cmd, args, chars: out.length, screenshot: cmd === 'screenshot' }) + '\n');
  res.end(out);
}).listen(port, '127.0.0.1', () => console.log(`ready ${mode} ${port}`));
