// Bundles the viewer into dist/app.js + dist/app.css and copies dist/index.html.
// Everything (three.js, meshes, layout data) ends up in local files loaded with relative paths.
import { build } from 'esbuild';
import { copyFileSync, mkdirSync } from 'node:fs';
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
  legalComments: 'eof',
  loader: { '.bin': 'binary', '.json': 'json' },
  logLevel: 'info',
});
copyFileSync(resolve(here, 'src/index.html'), resolve(out, 'index.html'));
console.log('built', out);
