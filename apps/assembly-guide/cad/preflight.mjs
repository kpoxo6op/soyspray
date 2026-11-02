// Render committed CAD into an exclusive job directory, slice those fresh bytes and check
// every deposition layer independently of slicer warnings. Cached repository STLs are not
// print inputs. Any unknown mapping, warning, failed process or changed input rejects the run
// and removes its exported jobs. The configured MCP preparer invokes this command itself;
// a manually supplied PASS report is never a print permission.
//
//   node preflight.mjs ~/prints/soyrack-job drive_tray switch_shelf
//
// Use a NEW output directory under $HOME, where the Flatpak slicer can write.

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

function check(part) {
  const stl = resolve(out, 'stl', `${part}.stl`);
  const dir = resolve(out, part);
  const res = { stl: sha256(stl), triangles: readFileSync(stl).readUInt32LE(80), problems: [] };
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
  const geometryFile = resolve(dir, 'geometry.json');
  const geometryRun = run(process.env.UV || 'uv', ['run', '--locked', '--script', resolve(here, 'check-support.py'),
    gcode, stl, resultFile, geometryFile]);
  if (!existsSync(geometryFile)) {
    res.problems.push(`support checker failed: ${geometryRun.error?.message ?? geometryRun.stderr}`);
  } else {
    const geometry = JSON.parse(readFileSync(geometryFile, 'utf8'));
    res.geometry = { ...geometry, failures: (geometry.failures ?? []).slice(0, 20),
      bridges: (geometry.bridges ?? []).slice(0, 20), failures_count: geometry.failures?.length ?? 0,
      bridges_count: geometry.bridges?.length ?? 0, evidence_sha256: sha256(geometryFile) };
    if (geometryRun.status !== 0 || geometry.pass !== true || geometry.policy_version !== 1)
      res.problems.push(`layer support check failed: ${geometry.error ?? `${geometry.failures.length} unsupported paths; see geometry.json`}`);
  }
  const machine = JSON.parse(readFileSync(resolve(PROFILES, 'machine.json'), 'utf8'));
  const processProfile = JSON.parse(readFileSync(resolve(PROFILES, 'process.json'), 'utf8'));
  res.target = { printer_model: machine.printer_model, nozzle_diameter: machine.nozzle_diameter,
    plate_type: processProfile.curr_bed_type };
  res.slicer = readFileSync(gcode, 'utf8').slice(0, 200).match(/; (BambuStudio [\d.]+)/)?.[1];
  if (res.slicer !== 'BambuStudio 02.08.02.61') res.problems.push(`unqualified slicer version: ${res.slicer}`);
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
const report = { schema_version: 2, geometry_policy_version: 1,
  pass: false, state: 'running', checkedAt: new Date().toISOString(), profiles: {}, parts: {} };
function saveReport() {
  const tmp = resolve(out, 'preflight.json.tmp');
  writeFileSync(tmp, JSON.stringify(report, null, 2) + '\n');
  renameSync(tmp, resolve(out, 'preflight.json'));
}
saveReport();   // interruption or a renderer crash cannot leave a successful result
try {
  const inputs = ['soyrack.scad', 'render.mjs', 'preflight.mjs',
    'check-support.py', 'check-support.py.lock', 'package.json', 'package-lock.json',
    'print/machine.json', 'print/process.json', 'print/filament.json'];
  const status = git('status', '--porcelain', '--', ...inputs);
  if (status) throw new Error(`uncommitted manufacturing inputs: ${status}`);
  const inputHashes = Object.fromEntries(inputs.map((f) => [f, sha256(resolve(here, f))]));
  report.commit = git('rev-parse', 'HEAD');
  const rendered = run(process.execPath, ['render.mjs', '--output-dir', out, ...parts]);
  if (rendered.error || rendered.status !== 0) throw new Error(`render failed: ${rendered.error?.message ?? rendered.stderr}`);
  report.source = sha256(resolve(here, 'soyrack.scad'));
  report.preflight = sha256(fileURLToPath(import.meta.url));
  report.renderer = sha256(resolve(here, 'render.mjs'));
  report.dependencies = sha256(resolve(here, 'package-lock.json'));
  report.support_checker = sha256(resolve(here, 'check-support.py'));
  report.support_dependencies = sha256(resolve(here, 'check-support.py.lock'));
  for (const f of ['machine', 'process', 'filament']) report.profiles[`${f}.json`] = sha256(resolve(PROFILES, `${f}.json`));
  for (const part of parts) {
    let r;
    try { r = check(part); }
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
  if (git('rev-parse', 'HEAD') !== report.commit || git('status', '--porcelain', '--', ...inputs)
    || inputs.some((f) => sha256(resolve(here, f)) !== inputHashes[f]))
    throw new Error('manufacturing inputs changed during preparation; no job admitted');
  report.pass = Object.values(report.parts).every((r) => !r.problems.length);
} catch (error) {
  report.error = error.message;
  console.error(error.message);
}
report.state = 'complete';
if (!report.pass) {
  // Even an unrelated part failure or a late input change invalidates the whole run.
  for (const part of parts) {
    if (!/^[a-z0-9][a-z0-9_-]{0,63}$/.test(part)) continue;
    rmSync(resolve(out, part, `${part}.gcode.3mf`), { force: true });
    if (report.parts[part]) delete report.parts[part].job;
  }
}
saveReport();
console.log(`${report.pass ? 'PASS' : 'FAIL'}: ${resolve(out, 'preflight.json')}`);
process.exit(report.pass ? 0 : 1);
