// Each page is self-contained: relative assets, decoder copies and content revisions.
import { build } from 'esbuild';
import { copyFileSync, mkdirSync, readFileSync, readdirSync, rmSync, writeFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { KIT as SOLDER_KIT } from './src/soldering/kit.js';

const here = dirname(fileURLToPath(import.meta.url));
const dist = resolve(here, 'dist');
const rev = (file) => createHash('sha256').update(readFileSync(file)).digest('hex').slice(0, 16);
const pages = [
  { entry: 'main.js', html: 'index.html', path: '', assets: ['pearl', 'prints', 'bench'], kit: true, files: true },
  { entry: 'soldering-main.js', html: 'soldering.html', path: 'soldering', assets: ['bench'], photos: ['table.jpg'], films: 'films', kit: !!SOLDER_KIT, files: false },
];

rmSync(dist, { recursive: true, force: true });
for (const page of pages) {
  const out = resolve(dist, page.path);
  for (const d of ['data', 'draco']) mkdirSync(resolve(out, d), { recursive: true });
  const assets = {};
  for (const name of page.assets) {
    const f = `${name}.glb`;
    copyFileSync(resolve(here, 'data', f), resolve(out, 'data', f));
    assets[name] = `data/${f}?v=${rev(resolve(here, 'data', f))}`;
  }
  const photos = {};
  for (const f of page.photos || []) {
    copyFileSync(resolve(here, 'data', f), resolve(out, 'data', f));
    photos[f.replace(/\.\w+$/, '')] = `data/${f}?v=${rev(resolve(here, 'data', f))}`;
  }
  if (page.films) {
    // rendered clips (Blender, ~/code/pearl-solder-film), referenced by beats as films/NAME.mp4
    mkdirSync(resolve(out, 'films'), { recursive: true });
    for (const f of readdirSync(resolve(here, page.films))) copyFileSync(resolve(here, page.films, f), resolve(out, 'films', f));
  }
  const draco = resolve(here, 'node_modules/three/examples/jsm/libs/draco/gltf');
  for (const f of ['draco_decoder.wasm', 'draco_wasm_wrapper.js']) copyFileSync(resolve(draco, f), resolve(out, 'draco', f));
  if (page.files) {
    mkdirSync(resolve(out, 'files'));
    for (const f of readdirSync(resolve(here, 'files'))) copyFileSync(resolve(here, 'files', f), resolve(out, 'files', f));
    for (const f of readdirSync(resolve(here, 'public'))) copyFileSync(resolve(here, 'public', f), resolve(out, f));
  }
  await build({
    entryPoints: [resolve(here, 'src', page.entry)],
    outfile: resolve(out, 'app.js'),
    bundle: true,
    format: 'iife',
    platform: 'browser',
    target: ['es2020', 'safari15'],
    minify: !process.env.PEARL_DEBUG,
    legalComments: 'eof',
    // DRACOLoader's default import.meta.url is unavailable in an IIFE bundle.
    define: { __PEARL_BUNDLED__: 'true', __PEARL_ASSETS__: JSON.stringify(assets), __PEARL_PHOTOS__: JSON.stringify(photos), 'import.meta.url': 'document.baseURI' },
    logLevel: 'info',
  });
  let html = readFileSync(resolve(here, 'src', page.html), 'utf8');
  if (!page.kit) html = html.split('\n').filter((line) => !/id="(?:btnKit|kitSheet)"/.test(line)).join('\n');
  for (const asset of ['app.js', 'app.css', ...(page.files ? ['pearl.svg'] : [])]) {
    html = html.replace(`"${asset}"`, `"${asset}?v=${rev(resolve(out, asset))}"`);
  }
  writeFileSync(resolve(out, 'index.html'), html);
  console.log('built', out, assets);
}
