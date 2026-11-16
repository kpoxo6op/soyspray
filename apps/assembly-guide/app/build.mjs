// Bundles the viewer into dist/app.js + dist/app.css with dist/index.html, and the crimping explainer into dist/crimping/.
// Everything (three.js, meshes, layout data) ends up in local files loaded with relative paths.
import { build } from 'esbuild';
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const out = resolve(here, 'dist');
mkdirSync(out, { recursive: true });

// Two pages share the player: the Soyrack guide at the root and the crimping explainer in crimping/.
const pages = [
  { entry: 'src/main.js', html: 'src/index.html', dir: out },
  { entry: 'src/crimping-main.js', html: 'src/crimping.html', dir: resolve(out, 'crimping') },
];
for (const page of pages) {
  mkdirSync(page.dir, { recursive: true });
  await build({
    entryPoints: [resolve(here, page.entry)],
    outfile: resolve(page.dir, 'app.js'),
    bundle: true,
    format: 'iife',
    platform: 'browser',
    target: ['es2020', 'safari15'],
    minify: true,
    legalComments: 'eof',
    loader: { '.bin': 'binary', '.json': 'json' },
    logLevel: 'info',
  });
  let html = readFileSync(resolve(here, page.html), 'utf8');
  for (const asset of ['app.js', 'app.css']) {
    const revision = createHash('sha256').update(readFileSync(resolve(page.dir, asset))).digest('hex').slice(0, 16);
    html = html.replace(`"${asset}"`, `"${asset}?v=${revision}"`);
  }
  writeFileSync(resolve(page.dir, 'index.html'), html);
}
console.log('built', out);
