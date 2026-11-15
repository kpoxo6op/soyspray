// Renders the catalog page from data/guides.json, bundles its script and stylesheet, and stamps both with a
// content revision. `node build.mjs` writes dist/ (the shipped page, with UI SDK); `--plain` writes dist-plain/,
// the same page with native controls only, for the agent comparison.
import { build } from 'esbuild';
import { mkdirSync, readFileSync, renameSync, rmSync, writeFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { renderPage } from './src/page.js';

const here = dirname(fileURLToPath(import.meta.url));
const plain = process.argv.includes('--plain');
const out = resolve(here, plain ? 'dist-plain' : 'dist');
const rev = (file) => createHash('sha256').update(readFileSync(file)).digest('hex').slice(0, 16);
const guides = JSON.parse(readFileSync(resolve(here, 'data/guides.json'), 'utf8'));

rmSync(out, { recursive: true, force: true });
mkdirSync(out, { recursive: true });
await build({
  entryPoints: [resolve(here, plain ? 'src/plain.js' : 'src/main.js')],
  outfile: resolve(out, 'app.js'),
  bundle: true,
  format: 'iife',
  platform: 'browser',
  target: ['es2022', 'safari16'],
  minify: !process.env.EXPLAIN_DEBUG,
  legalComments: 'eof',
  define: { 'process.env.NODE_ENV': '"production"' },
  logLevel: 'warning',
});
const html = renderPage(guides, {
  bridge: !plain,
  css: `app.css?v=${rev(resolve(out, 'app.css'))}`,
  js: `app.js?v=${rev(resolve(out, 'app.js'))}`,
});
writeFileSync(resolve(out, 'index.html'), html);
console.log('built', out);
