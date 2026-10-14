import { spawnSync } from 'node:child_process';
import { readdirSync } from 'node:fs';
const files = readdirSync('test').filter(f => f.endsWith('.test.mjs')).map(f => `test/${f}`);
for (const layout of ['v2', 'v1']) {
  console.log(`Installation variant: ${layout}`);
  const browserURL = `globalThis.location = new URL("https://assembly.invalid/?layout=${layout}");`;
  const result = spawnSync(process.execPath, [`--import=data:text/javascript,${encodeURIComponent(browserURL)}`, '--test', ...files], { stdio: 'inherit' });
  if (result.status !== 0) process.exit(result.status ?? 1);
}
