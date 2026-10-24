// Bundles the guide as ES modules with code splitting: dist/app.js is the small shell
// (views, data, stitch renderer); the 3D engine (three.js) lives in its own chunk loaded
// only when the Machine tab opens. Entry assets get content-revision query strings, chunks
// carry content hashes in their names, and a service worker precaches the exact build.
import { build } from 'esbuild';
import { readFileSync, writeFileSync, mkdirSync, cpSync, existsSync, rmSync, readdirSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const out = resolve(here, 'dist');
rmSync(out, { recursive: true, force: true });
mkdirSync(resolve(out, 'chunks'), { recursive: true });

const result = await build({
  entryPoints: [resolve(here, 'src/main.js')],
  outdir: out,
  entryNames: 'app',
  chunkNames: 'chunks/[name]-[hash]',
  bundle: true,
  splitting: true,
  format: 'esm',
  platform: 'browser',
  target: ['es2020', 'safari15'],
  minify: true,
  charset: 'utf8',
  legalComments: 'eof',
  metafile: true,
  logLevel: 'info',
});

const rev = (file) => createHash('sha256').update(readFileSync(resolve(out, file))).digest('hex').slice(0, 16);
let html = readFileSync(resolve(here, 'src/index.html'), 'utf8');
for (const asset of ['app.js', 'app.css']) html = html.replace(`"${asset}"`, `"${asset}?v=${rev(asset)}"`);
writeFileSync(resolve(out, 'index.html'), html);
if (existsSync(resolve(here, 'public'))) cpSync(resolve(here, 'public'), out, { recursive: true });

// Service worker: precache list = every file in dist with the same revision scheme as index.html.
const files = [];
const walk = (dir, prefix = '') => {
  for (const name of readdirSync(dir, { withFileTypes: true })) {
    if (name.isDirectory()) walk(resolve(dir, name.name), `${prefix}${name.name}/`);
    else if (name.name !== 'sw.js') files.push(`${prefix}${name.name}`);
  }
};
walk(out);
const precache = files.map((f) => (f === 'app.js' || f === 'app.css' ? `${f}?v=${rev(f)}` : f === 'index.html' ? './' : f));
const version = createHash('sha256').update(precache.join('\n') + files.map(rev).join('\n')).digest('hex').slice(0, 12);
const sw = readFileSync(resolve(here, 'src/sw.js'), 'utf8')
  .replace('__VERSION__', version)
  .replace('__PRECACHE__', JSON.stringify(precache));
writeFileSync(resolve(out, 'sw.js'), sw);

const outputs = Object.entries(result.metafile.outputs).map(([f, o]) => `${f.replace(/^.*dist\//, '')} ${(o.bytes / 1024).toFixed(1)}kb`);
console.log('built', out, '\n ', outputs.join('\n  '), `\n  sw ${version} precaches ${precache.length} files`);
