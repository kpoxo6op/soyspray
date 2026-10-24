// Bundles the guide into dist/app.js + dist/app.css and copies dist/index.html with
// content-revision query strings so returning phones never run a stale bundle.
import { build } from 'esbuild';
import { readFileSync, writeFileSync, mkdirSync, cpSync, existsSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const out = resolve(here, 'dist');
mkdirSync(out, { recursive: true });

await build({
  entryPoints: [resolve(here, 'src/main.js')],
  outfile: resolve(out, 'app.js'),
  bundle: true,
  format: 'iife',
  platform: 'browser',
  target: ['es2020', 'safari15'],
  minify: true,
  charset: 'utf8',
  legalComments: 'eof',
  logLevel: 'info',
});

let html = readFileSync(resolve(here, 'src/index.html'), 'utf8');
for (const asset of ['app.js', 'app.css']) {
  const revision = createHash('sha256').update(readFileSync(resolve(out, asset))).digest('hex').slice(0, 16);
  html = html.replace(`"${asset}"`, `"${asset}?v=${revision}"`);
}
writeFileSync(resolve(out, 'index.html'), html);
if (existsSync(resolve(here, 'public'))) cpSync(resolve(here, 'public'), out, { recursive: true });
console.log('built', out);
