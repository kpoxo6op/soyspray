// Print preflight. For each part it re-renders the print STL and requires the committed one to
// match, then slices that STL with the installed Bambu Studio and the profiles in print/. It
// fails on a stale or uncommitted STL, on a slicing error (a part outside the usable plate is
// one) and on any slicer warning, such as a floating cantilever. Print only a .gcode.3mf from a
// passing run: preflight.json records its hash with the commit and the STL and profile hashes,
// and lists the layers where walls cross open air, which a camera check should cover.
//
//   node preflight.mjs ~/prints/soyrack-job drive_tray switch_shelf
//
// The output directory must be new and under $HOME, where the Flatpak slicer can write. BAMBU_STUDIO
// replaces the slicer command.

import { spawnSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { closeSync, existsSync, mkdirSync, openSync, readFileSync, renameSync, rmSync, writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const PROFILES = resolve(here, 'print');
const STUDIO = (process.env.BAMBU_STUDIO || 'flatpak run com.bambulab.BambuStudio').split(' ');
const WATCH_MM = 5;            // report walls that cross at least this much open air

const sha256 = (path) => createHash('sha256').update(readFileSync(path)).digest('hex');
const run = (cmd, args, opts) => spawnSync(cmd, args, { cwd: here, encoding: 'utf8', ...opts });
function git(...args) {
  const r = run('git', args);
  if (r.status !== 0) throw new Error(`git ${args.join(' ')}: ${r.stderr}`);
  return r.stdout.trimEnd();   // status lines start with a space
}

// Height of a binary STL whose lowest point is on the bed, as render.mjs writes them.
function heightOf(stl) {
  const b = readFileSync(stl);
  const corners = b.readUInt32LE(80) * 3;
  let top = 0;
  for (let i = 0; i < corners; i++) top = Math.max(top, b.readFloatLE(84 + Math.floor(i / 3) * 50 + 12 + (i % 3) * 12 + 8));
  return top;
}

function slice(part, stl, dir) {
  mkdirSync(dir);   // a new run never replaces an earlier job or its evidence
  const log = openSync(resolve(dir, 'slicing.log'), 'w');
  try {
    const r = run(STUDIO[0], [...STUDIO.slice(1), '--debug', '2',
      '--load-settings', `${PROFILES}/machine.json;${PROFILES}/process.json`,
      '--load-filaments', `${PROFILES}/filament.json`,
      '--arrange', '1', '--orient', '0', '--slice', '0',
      '--export-3mf', `${part}.gcode.3mf`, '--outputdir', dir, stl], { stdio: ['ignore', log, log] });
    if (r.error || r.status !== 0) throw new Error(`slicer failed (${r.error?.message ?? r.signal ?? r.status}); see ${dir}/slicing.log`);
  } finally { closeSync(log); }
}

// Layers where the slicer lays walls over open air ("Overhang wall"), with the longest such line.
function watch(gcode) {
  const layers = new Map();
  let layer = 0, z = 0, pct = 0, kind = '', x = 0, y = 0;
  for (const line of readFileSync(gcode, 'utf8').split('\n')) {
    if (line.startsWith('; CHANGE_LAYER')) layer++;
    else if (line.startsWith('; Z_HEIGHT:')) z = Number(line.slice(11));
    else if (line.startsWith('; FEATURE:')) kind = line.slice(10).trim();
    else if (line.startsWith('M73 P')) pct = Number(line.split(' ')[1].slice(1));
    if (!/^G[0-3] /.test(line)) continue;
    const cmd = line.split(';')[0];
    const at = (k, v) => { const m = new RegExp(` ${k}(-?[\\d.]+)`).exec(cmd); return m ? Number(m[1]) : v; };
    const [nx, ny, e] = [at('X', x), at('Y', y), at('E', 0)];
    if (kind === 'Overhang wall' && e > 0) {
      const L = layers.get(layer) ?? { layer, z, percent: pct, mm: 0, longestMm: 0 };
      const d = Math.hypot(nx - x, ny - y);
      L.mm += d;
      L.longestMm = Math.max(L.longestMm, d);
      layers.set(layer, L);
    }
    [x, y] = [nx, ny];
  }
  return [...layers.values()].filter((L) => L.longestMm >= WATCH_MM)
    .map((L) => ({ ...L, mm: Math.round(L.mm), longestMm: Math.round(L.longestMm * 10) / 10 }));
}

function check(part, uncommitted) {
  const stl = resolve(here, 'stl', `${part}.stl`);
  const dir = resolve(out, part);
  const res = { stl: sha256(stl), triangles: readFileSync(stl).readUInt32LE(80), problems: [] };
  for (const f of uncommitted) if (f.endsWith('cad/soyrack.scad') || f.endsWith(`stl/${part}.stl`) || f.endsWith('stl/parts.json'))
    res.problems.push(`${f} differs from the commit: a fresh render changed it or it is uncommitted`);
  slice(part, stl, dir);
  const resultFile = resolve(dir, 'result.json');
  if (!existsSync(resultFile)) return { ...res, problems: [...res.problems, `no slicer result in ${dir} (it must be under $HOME)`] };
  const result = JSON.parse(readFileSync(resultFile, 'utf8'));
  const plate = result.sliced_plates?.[0];
  if (result.return_code !== 0 || !plate) return { ...res, problems: [...res.problems, `slicing failed: ${result.error_string}`] };
  // The slicer may drop degenerate triangles, so compare the object and its height: --orient 0
  // must keep the supplied orientation.
  const [object, ...more] = plate.objects ?? [];
  if (!object || more.length || object.name !== `${part}.stl` || Math.abs(object.bbox.height - heightOf(stl)) > 0.01)
    res.problems.push('the slicer did not keep this STL as supplied');
  if (plate.warning_message) res.problems.push(`slicer warning: ${plate.warning_message}`);
  const job = resolve(dir, `${part}.gcode.3mf`);
  const gcode = resolve(dir, 'plate_1.gcode');
  if (!existsSync(job) || !existsSync(gcode)) return { ...res, problems: [...res.problems, 'the slicer wrote no job'] };
  res.slicer = readFileSync(gcode, 'utf8').slice(0, 200).match(/; (BambuStudio [\d.]+)/)?.[1];
  return { ...res, job: sha256(job), minutes: Math.round(plate.total_predication / 60),
    grams: Math.round(plate.filaments[0].total_used_g), watch: watch(gcode) };
}

const [outArg, ...parts] = process.argv.slice(2);
if (!outArg || !parts.length) {
  console.error('usage: node preflight.mjs <out-dir> <part> [<part> ...]');
  process.exit(2);
}
const out = resolve(outArg);
try {
  mkdirSync(dirname(out), { recursive: true });
  mkdirSync(out);
} catch (error) {
  console.error(`Use a NEW job directory; existing jobs are never overwritten: ${error.message}`);
  process.exit(2);
}
const report = { pass: false, state: 'running', checkedAt: new Date().toISOString(), profiles: {}, parts: {} };
function saveReport() {
  const tmp = resolve(out, 'preflight.json.tmp');
  writeFileSync(tmp, JSON.stringify(report, null, 2) + '\n');
  renameSync(tmp, resolve(out, 'preflight.json'));
}
saveReport();   // interruption or a renderer crash cannot leave a successful result
try {
  const rendered = run(process.execPath, ['render.mjs', ...parts]);
  if (rendered.error || rendered.status !== 0) throw new Error(`render failed: ${rendered.error?.message ?? rendered.stderr}`);
  const status = git('status', '--porcelain', '--', 'soyrack.scad', 'stl/parts.json', ...parts.map((p) => `stl/${p}.stl`));
  const uncommitted = status ? status.split('\n').map((l) => l.slice(3)) : [];
  report.commit = git('rev-parse', 'HEAD');
  report.source = sha256(resolve(here, 'soyrack.scad'));
  report.preflight = sha256(fileURLToPath(import.meta.url));
  report.renderer = sha256(resolve(here, 'render.mjs'));
  report.dependencies = sha256(resolve(here, 'package-lock.json'));
  for (const f of ['machine', 'process', 'filament']) report.profiles[`${f}.json`] = sha256(resolve(PROFILES, `${f}.json`));
  for (const part of parts) {
    let r;
    try { r = check(part, uncommitted); }
    catch (error) { r = { problems: [error.message] }; }
    if (r.problems.length) {
      rmSync(resolve(out, part, `${part}.gcode.3mf`), { force: true });
      delete r.job;
    }
    report.parts[part] = r;
    const notes = [...(r.problems.length ? r.problems : [`${r.minutes} min, ${r.grams} g`]),
      ...(r.watch ?? []).map((w) => `layer ${w.layer} (z ${w.z}, ${w.percent} %): ${w.mm} mm of wall over air, longest ${w.longestMm} mm`)];
    console.log(`${r.problems.length ? 'FAIL' : 'pass'}  ${part}: ${notes.join('; ')}`);
  }
  report.pass = Object.values(report.parts).every((r) => !r.problems.length);
} catch (error) {
  report.error = error.message;
  console.error(error.message);
}
report.state = 'complete';
saveReport();
console.log(`${report.pass ? 'PASS' : 'FAIL'}: ${resolve(out, 'preflight.json')}`);
process.exit(report.pass ? 0 : 1);
