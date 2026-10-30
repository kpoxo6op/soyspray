// Bundles the player into dist/app.js and dist/app.css, copies the models, the Draco decoder and the printable
// files, and stamps every runtime reference with a content revision so returning browsers fetch new bytes.
import { build } from 'esbuild';
import { copyFileSync, mkdirSync, readFileSync, readdirSync, rmSync, writeFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const out = resolve(here, 'dist');
const rev = (file) => createHash('sha256').update(readFileSync(file)).digest('hex').slice(0, 16);

rmSync(out, { recursive: true, force: true });
for (const d of ['data', 'draco', 'files']) mkdirSync(resolve(out, d), { recursive: true });

const assets = {};
for (const f of readdirSync(resolve(here, 'data')).filter((f) => f.endsWith('.glb'))) {
  copyFileSync(resolve(here, 'data', f), resolve(out, 'data', f));
  assets[f.replace(/\.glb$/, '')] = `data/${f}?v=${rev(resolve(here, 'data', f))}`;
}
const draco = resolve(here, 'node_modules/three/examples/jsm/libs/draco/gltf');
for (const f of ['draco_decoder.wasm', 'draco_wasm_wrapper.js']) copyFileSync(resolve(draco, f), resolve(out, 'draco', f));
for (const f of readdirSync(resolve(here, 'files'))) copyFileSync(resolve(here, 'files', f), resolve(out, 'files', f));
for (const f of readdirSync(resolve(here, 'public'))) copyFileSync(resolve(here, 'public', f), resolve(out, f));

await build({
  entryPoints: [resolve(here, 'src/main.js')],
  outfile: resolve(out, 'app.js'),
  bundle: true,
  format: 'iife',
  platform: 'browser',
  target: ['es2020', 'safari15'],
  minify: !process.env.PEARL_DEBUG,
  legalComments: 'eof',
  // DRACOLoader resolves its default decoder path from import.meta.url, which an IIFE bundle does not have.
  define: { __PEARL_ASSETS__: JSON.stringify(assets), 'import.meta.url': 'document.baseURI' },
  logLevel: 'info',
});

let html = readFileSync(resolve(here, 'src/index.html'), 'utf8');
for (const asset of ['app.js', 'app.css', 'pearl.svg']) html = html.replace(`"${asset}"`, `"${asset}?v=${rev(resolve(out, asset))}"`);
writeFileSync(resolve(out, 'index.html'), html);
console.log('built', out, assets);
