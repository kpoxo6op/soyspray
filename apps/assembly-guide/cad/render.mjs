// Renders the Soyrack parts with the OpenSCAD WebAssembly build (Manifold backend).
//
//   npm ci && node render.mjs          print STLs into stl/, browser meshes and the print list into ../app/data/v3/
//   node render.mjs base_tub top_cap   only these parts (browser meshes are left alone)
//
// Text engraving needs Liberation Sans Bold; set FONT_TTF if it is not in the usual place.

import { createOpenSCAD } from 'openscad-wasm-prebuilt';
import { Worker, isMainThread, parentPort, workerData } from 'node:worker_threads';
import { availableParallelism } from 'node:os';
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const SCAD = resolve(here, 'soyrack.scad');
const FONT = process.env.FONT_TTF || '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf';

async function render({ part, orient, web }) {
  const log = [];
  const scad = await createOpenSCAD({ noInitialRun: true, print: (t) => log.push(t), printErr: (t) => log.push(t) });
  const inst = scad.getInstance();
  inst.FS.mkdir('/src');
  inst.FS.writeFile('/src/soyrack.scad', readFileSync(SCAD, 'utf8'));
  inst.FS.writeFile('/src/LiberationSans-Bold.ttf', readFileSync(FONT));
  const args = ['/src/soyrack.scad', '-o', '/out.stl', '--backend=manifold', '--export-format=binstl',
    '-D', `part="${part}"`, '-D', `orient="${orient}"`, '-D', `web=${web}`];
  let code;
  try {
    code = inst.callMain(args);
  } catch (e) {
    throw new Error(`${part}: ${e}\n${log.join('\n')}`);
  }
  const warnings = log.filter((l) => /WARNING|ERROR/.test(l));
  if (code !== 0 || warnings.length) throw new Error(`${part} (${orient}${web ? ', web' : ''}) failed:\n${log.join('\n')}`);
  return inst.FS.readFile('/out.stl');
}

function partNames() {
  const src = readFileSync(SCAD, 'utf8');
  const m = src.match(/PARTS = \[([^\]]*)\]/);
  return [...m[1].matchAll(/"([^"]+)"/g)].map((x) => x[1]);
}

// Browser meshes: everything that appears in the guide, at its rack position.
const WEB = ['base_tub', 'base_deck', 'post_lower_a', 'post_lower_b', 'mid_deck', 'post_upper_a', 'post_upper_b',
  'top_cap', 'drive_tray', 'switch_shelf', 'keystone_panel', 'zigbee_mast',
  'coupon_post', 'coupon_corner', 'coupon_base', 'coupon_keystone'];

// Manufacturing presets use the same freshly rendered parts as the guide. They are explicit
// requests, not extra rack components or browser meshes. One lower A has already been printed.
const PRINT_BATCHES = {
  lower_posts_remaining: [
    { part: 'post_lower_a', at: [0, 0] },
    { part: 'post_lower_b', at: [0, 30] },
    { part: 'post_lower_b', at: [0, 60] },
  ],
  // All four upper posts: two A (front-left, rear-right) and two B, as the rack uses them.
  upper_posts_remaining: [
    { part: 'post_upper_a', at: [0, 0] },
    { part: 'post_upper_b', at: [0, 30] },
    { part: 'post_upper_a', at: [0, 60] },
    { part: 'post_upper_b', at: [0, 90] },
  ],
  // The last two parts that fit the bed after the top cap: the mast, and the mid deck standing
  // on its rear edge behind it. The mast stops at 140 mm; the deck carries on alone to 209 mm.
  mid_deck_and_mast: [
    { part: 'zigbee_mast', at: [0, 0] },
    { part: 'mid_deck', at: [0, 94] },
  ],
};
const BATCH_GAP_MM = 10;

function batchMesh(name, results) {
  const placed = PRINT_BATCHES[name].map(({ part, at }) => {
    const bytes = toBed(results.get(`${part}:print`));
    const { size } = measure(readStl(bytes));
    if (at.length !== 2 || !at.every(Number.isFinite) || at.some((v) => v < 0)
      || at[0] + size[0] > 256 || at[1] + size[1] > 256)
      throw new Error(`${name}: batch placement outside the bed`);
    return { part, at, size, bytes };
  });
  for (let i = 0; i < placed.length; i++) for (let j = 0; j < i; j++) {
    const a = placed[i], b = placed[j];
    const gap = Math.max(a.at[0] - b.at[0] - b.size[0], b.at[0] - a.at[0] - a.size[0],
      a.at[1] - b.at[1] - b.size[1], b.at[1] - a.at[1] - a.size[1]);
    if (gap < BATCH_GAP_MM) throw new Error(`${name}: batch clearance below ${BATCH_GAP_MM} mm`);
  }
  // A single STL keeps this fixed layout through the slicer and the independent layer checker.
  // Copy the source triangles; only XY translation changes. No source CAD or orientation changes.
  const triangles = placed.reduce((n, p) => n + p.bytes.readUInt32LE(80), 0);
  const out = Buffer.alloc(84 + 50 * triangles);
  out.writeUInt32LE(triangles, 80);
  let offset = 84;
  for (const { bytes, at } of placed) {
    bytes.copy(out, offset, 84);
    for (let i = 0; i < bytes.readUInt32LE(80); i++) for (let vertex = 0; vertex < 3; vertex++) {
      const p = offset + i * 50 + 12 + vertex * 12;
      for (let axis = 0; axis < 2; axis++) out.writeFloatLE(out.readFloatLE(p + axis * 4) + at[axis], p + axis * 4);
    }
    offset += bytes.length - 84;
  }
  return { bytes: out, batch: placed.map(({ part, at, size }) => ({ part, at, size })) };
}

async function main() {
  if (!existsSync(FONT)) throw new Error(`missing ${FONT}: install fonts-liberation or set FONT_TTF`);
  const all = partNames();
  const chosen = process.argv.slice(2);
  const outputFlag = chosen.indexOf('--output-dir');
  let printDir = resolve(here, 'stl');
  if (outputFlag !== -1) {
    if (!chosen[outputFlag + 1]) throw new Error('--output-dir requires a directory');
    printDir = resolve(chosen[outputFlag + 1], 'stl');
    chosen.splice(outputFlag, 2);
    if (!chosen.length) throw new Error('--output-dir requires explicit part names');
  }
  for (const p of chosen) if (!all.includes(p) && !Object.hasOwn(PRINT_BATCHES, p)) throw new Error(`unknown part ${p}`);
  // Batches are print jobs, not guide parts: keep them out of the linked stl/ folder.
  if (outputFlag === -1 && chosen.some((p) => Object.hasOwn(PRINT_BATCHES, p)))
    throw new Error('print batches need --output-dir (or use preflight.mjs)');
  const parts = chosen.length ? chosen : all;
  const sources = [...new Set(parts.flatMap((part) => PRINT_BATCHES[part]?.map((p) => p.part) ?? [part]))];
  const jobs = sources.map((part) => ({ part, orient: 'print', web: false }));
  if (!chosen.length) jobs.push(...WEB.map((part) => ({ part, orient: 'world', web: true })));

  const results = new Map();
  const queue = [...jobs];
  const workers = Math.min(availableParallelism(), queue.length);
  const t0 = Date.now();
  await Promise.all(Array.from({ length: workers }, () => new Promise((done, fail) => {
    const w = new Worker(fileURLToPath(import.meta.url));
    const next = () => {
      const job = queue.shift();
      if (!job) { w.terminate(); done(); return; }
      w.postMessage(job);
    };
    w.on('message', ({ job, bytes, error }) => {
      if (error) { w.terminate(); fail(new Error(error)); return; }
      results.set(`${job.part}:${job.orient}`, Buffer.from(bytes));
      console.log(`  ${job.orient === 'print' ? 'stl ' : 'web '} ${job.part}`);
      next();
    });
    w.on('error', fail);
    next();
  })));

  mkdirSync(printDir, { recursive: true });
  // A full render rewrites the manifest; a partial one updates its entries.
  const manifest = chosen.length && existsSync(resolve(printDir, 'parts.json')) ? JSON.parse(readFileSync(resolve(printDir, 'parts.json'), 'utf8')) : {};
  for (const part of parts) {
    const composed = Object.hasOwn(PRINT_BATCHES, part) ? batchMesh(part, results) : null;
    const bytes = composed?.bytes ?? toBed(results.get(`${part}:print`));
    writeFileSync(resolve(printDir, `${part}.stl`), bytes);
    const tris = readStl(bytes);
    manifest[part] = { triangles: tris.length / 9, ...measure(tris) };
    if (composed) manifest[part].batch = composed.batch;
  }
  writeFileSync(resolve(printDir, 'parts.json'), JSON.stringify(sortKeys(manifest), null, 2) + '\n');

  if (!chosen.length) {
    const out = resolve(here, '../app/data/v3');
    mkdirSync(out, { recursive: true });
    const printList = Object.fromEntries(all.map((p) => [p, { size: manifest[p].size, grams: manifest[p].grams }]));
    writeFileSync(resolve(out, 'parts.json'), JSON.stringify(printList, null, 2) + '\n');
    const meshes = WEB.map((part) => [part, readStl(results.get(`${part}:world`))]);
    const size = pack(meshes, resolve(out, 'meshes.bin'));
    console.log(`wrote app/data/v3/meshes.bin: ${size} bytes`);
  }
  console.log(`rendered ${jobs.length} meshes in ${((Date.now() - t0) / 1000).toFixed(1)} s`);
}

function sortKeys(o) {
  return Object.fromEntries(Object.keys(o).sort().map((k) => [k, o[k]]));
}

// Print files start at the bed origin: the lowest corner of each part at 0, 0, 0.
function toBed(buf) {
  const out = Buffer.from(buf);
  const view = new DataView(out.buffer, out.byteOffset, out.byteLength);
  const n = view.getUint32(80, true);
  const at = (i, k) => 84 + Math.floor(i / 3) * 50 + 12 + (i % 3) * 12 + k * 4;
  const lo = [Infinity, Infinity, Infinity];
  for (let i = 0; i < n * 3; i++) for (let k = 0; k < 3; k++) lo[k] = Math.min(lo[k], view.getFloat32(at(i, k), true));
  for (let i = 0; i < n * 3; i++) for (let k = 0; k < 3; k++) view.setFloat32(at(i, k), view.getFloat32(at(i, k), true) - lo[k], true);
  return out;
}

// Binary STL -> flat Float32Array of triangle corners.
function readStl(buf) {
  const view = new DataView(buf.buffer, buf.byteOffset, buf.byteLength);
  const n = view.getUint32(80, true);
  if (84 + n * 50 !== buf.byteLength) throw new Error('expected a binary STL');
  const out = new Float32Array(n * 9);
  for (let i = 0; i < n; i++) {
    const o = 84 + i * 50 + 12;
    for (let k = 0; k < 9; k++) out[i * 9 + k] = view.getFloat32(o + k * 4, true);
  }
  return out;
}

// PETG estimate for 4 walls and 5 top/bottom layers (about 1.2 mm of solid under every
// surface) with 15 % infill inside, at 1.27 g/cm3.
const SHELL_MM = 1.2;
const INFILL = 0.15;
const PETG = 1.27;

function measure(t) {
  const lo = [Infinity, Infinity, Infinity];
  const hi = [-Infinity, -Infinity, -Infinity];
  let vol = 0;
  let area = 0;
  for (let i = 0; i < t.length; i += 9) {
    for (let k = 0; k < 9; k++) {
      const a = k % 3;
      lo[a] = Math.min(lo[a], t[i + k]);
      hi[a] = Math.max(hi[a], t[i + k]);
    }
    const [ax, ay, az, bx, by, bz, cx, cy, cz] = t.subarray(i, i + 9);
    vol += (ax * (by * cz - bz * cy) - ay * (bx * cz - bz * cx) + az * (bx * cy - by * cx)) / 6;
    const [ux, uy, uz, vx, vy, vz] = [bx - ax, by - ay, bz - az, cx - ax, cy - ay, cz - az];
    area += Math.hypot(uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx) / 2;
  }
  const shell = Math.min(vol, area * SHELL_MM);
  const grams = ((shell + INFILL * (vol - shell)) / 1000) * PETG;
  const r = (v) => Math.round(v * 100) / 100;
  return { size: hi.map((h, a) => r(h - lo[a])), volumeCm3: r(vol / 1000), grams: Math.round(grams) };
}

// Same layout as tools/pack_meshes.py: uint32 header length, JSON header, then per part
// float32 positions centred on the bounding-box centre and u16/u32 triangle indices.
function pack(meshes, path) {
  const header = {};
  const blobs = [];
  let offset = 0;
  for (const [name, tris] of meshes) {
    const index = new Map();
    const verts = [];
    const idx = [];
    for (let i = 0; i < tris.length; i += 3) {
      const key = `${tris[i].toFixed(3)},${tris[i + 1].toFixed(3)},${tris[i + 2].toFixed(3)}`;
      let j = index.get(key);
      if (j === undefined) { j = verts.length / 3; index.set(key, j); verts.push(tris[i], tris[i + 1], tris[i + 2]); }
      idx.push(j);
    }
    const kept = [];
    for (let i = 0; i < idx.length; i += 3) {
      const [a, b, c] = [idx[i], idx[i + 1], idx[i + 2]];
      if (a !== b && b !== c && a !== c) kept.push(a, b, c);
    }
    const lo = [Infinity, Infinity, Infinity];
    const hi = [-Infinity, -Infinity, -Infinity];
    for (let i = 0; i < verts.length; i++) {
      lo[i % 3] = Math.min(lo[i % 3], verts[i]);
      hi[i % 3] = Math.max(hi[i % 3], verts[i]);
    }
    const centre = lo.map((l, a) => (l + hi[a]) / 2);
    const pos = new Float32Array(verts.length);
    for (let i = 0; i < verts.length; i++) pos[i] = verts[i] - centre[i % 3];
    const wide = verts.length / 3 >= 65536;
    const ind = wide ? new Uint32Array(kept) : new Uint16Array(kept);
    const pb = Buffer.from(pos.buffer);
    const ib = Buffer.from(ind.buffer);
    const pad = (4 - (ib.length % 4)) % 4;
    const r4 = (v) => Math.round(v * 1e4) / 1e4;
    header[name] = {
      file: `${name}.stl`, centre: centre.map(r4), size: hi.map((h, a) => r4(h - lo[a])),
      vertices: verts.length / 3, triangles: kept.length / 3, sourceTriangles: tris.length / 9,
      positions: [offset, pb.length], indices: [offset + pb.length, ib.length], indexType: wide ? 'u32' : 'u16',
    };
    blobs.push(pb, ib, Buffer.alloc(pad));
    offset += pb.length + ib.length + pad;
  }
  let hjson = Buffer.from(JSON.stringify(header));
  hjson = Buffer.concat([hjson, Buffer.alloc((4 - ((4 + hjson.length) % 4)) % 4, ' ')]);
  const len = Buffer.alloc(4);
  len.writeUInt32LE(hjson.length);
  const file = Buffer.concat([len, hjson, ...blobs]);
  writeFileSync(path, file);
  return file.length;
}

if (!isMainThread) {
  parentPort.on('message', async (job) => {
    try {
      const bytes = await render(job);
      parentPort.postMessage({ job, bytes });
    } catch (error) {
      parentPort.postMessage({ job, error: String(error.message || error) });
    }
  });
} else {
  await main();
}
