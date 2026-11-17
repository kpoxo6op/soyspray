// Renders the ESP32 case with the OpenSCAD WebAssembly build (Manifold backend).
//
//   npm ci && node render.mjs     base.stl and lid.stl into stl/, turned for printing
//
// The lid labels need Liberation Sans Bold; set FONT_TTF if it is not in the usual place.

import { createOpenSCAD } from 'openscad-wasm-prebuilt';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const FONT = process.env.FONT_TTF || '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf';

async function render(part, orient) {
  const log = [];
  const scad = await createOpenSCAD({ noInitialRun: true, print: (t) => log.push(t), printErr: (t) => log.push(t) });
  const inst = scad.getInstance();
  inst.FS.mkdir('/src');
  inst.FS.writeFile('/src/esp32-case.scad', readFileSync(resolve(here, 'esp32-case.scad'), 'utf8'));
  inst.FS.writeFile('/src/LiberationSans-Bold.ttf', readFileSync(FONT));
  const code = inst.callMain(['/src/esp32-case.scad', '-o', '/out.stl', '--backend=manifold', '--export-format=binstl',
    '-D', `part="${part}"`, '-D', `orient="${orient}"`]);
  if (code !== 0 || log.some((l) => /WARNING|ERROR/.test(l))) throw new Error(`${part} failed:\n${log.join('\n')}`);
  return inst.FS.readFile('/out.stl');
}

const out = process.argv[2] ? resolve(process.argv[2]) : resolve(here, 'stl');
const orient = process.env.ORIENT || 'print';
mkdirSync(out, { recursive: true });
for (const part of ['base', 'lid']) {
  const bytes = await render(part, orient);
  writeFileSync(resolve(out, `${part}.stl`), bytes);
  console.log(`${part}.stl  ${bytes.length} bytes`);
}
