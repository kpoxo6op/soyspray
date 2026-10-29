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
  'top_cap', 'drive_tray', 'switch_shelf', 'router_shelf', 'keystone_panel', 'foot', 'zigbee_mast',
  'coupon_post', 'coupon_corner', 'coupon_nut', 'coupon_keystone'];

async function main() {
  if (!existsSync(FONT)) throw new Error(`missing ${FONT}: install fonts-liberation or set FONT_TTF`);
  const all = partNames();
  const chosen = process.argv.slice(2);
  for (const p of chosen) if (!all.includes(p)) throw new Error(`unknown part ${p}`);
  const parts = chosen.length ? chosen : all;
  const jobs = parts.map((part) => ({ part, orient: 'print', web: false }));
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

  mkdirSync(resolve(here, 'stl'), { recursive: true });
  const manifest = existsSync(resolve(here, 'stl/parts.json')) ? JSON.parse(readFileSync(resolve(here, 'stl/parts.json'), 'utf8')) : {};
  for (const part of parts) {
    const bytes = toBed(results.get(`${part}:print`));
    writeFileSync(resolve(here, `stl/${part}.stl`), bytes);
    const tris = readStl(bytes);
    manifest[part] = { triangles: tris.length / 9, ...measure(tris) };
  }
  writeFileSync(resolve(here, 'stl/parts.json'), JSON.stringify(sortKeys(manifest), null, 2) + '\n');

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
