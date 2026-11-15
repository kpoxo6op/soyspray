import './style.css';
import { Color, Matrix4, Vector3 } from 'three';
import { Stage, clamp, mixPose, smooth } from './stage.js';
import { buildScene } from './scene.js';
import { CHAPTERS, SHOTS, buildTimeline } from './story.js';
import { Player } from './player.js';
import { createUI } from './ui.js';
import { createSheets } from './sheets.js';
import { createLoop } from './loop.js';

const root = document.getElementById('app');
const stageEl = document.getElementById('stage');
const loading = document.getElementById('loading');
const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
const phone = window.matchMedia('(max-width: 700px), (pointer: coarse)').matches;

const CAMERA_MOVE = 1.6; // seconds the camera takes to reach a beat's shot
const SPLIT_MOVE = 2.5; // seconds devices take to walk to (or back from) their new streets
const RULER_ORDER = ['ends', 'nodes', 'metallb', 'pool'];
const RULER_SETS = {
  ends: [0, 1, 255],
  nodes: [10, 11, 12, 13],
  metallb: Array.from({ length: 19 }, (_, i) => 20 + i),
  pool: Array.from({ length: 150 }, (_, i) => 100 + i),
};
const COLOR = { dim: new Color(0x4d4842), seen: new Color(0x9c958b), all: new Color(0xb9b1a5), hot: new Color(0xe8ae62), mark: new Color(0xf3efe8) };

function fail(title, text, err) {
  root.classList.add('failed');
  loading.hidden = false;
  loading.innerHTML = `<strong>${title}</strong><span>${text}</span>`;
  if (err) console.error(err);
}

/** Everything on screen is a function of the playhead: direct(t) sets the camera, streets, labels and packets. */
function makeDirector(stage, S, timeline) {
  const { chapters } = timeline;
  const beats = chapters.flatMap((c) => c.beats);
  const M = S.materials;
  const tmp = new Vector3();
  const mat = new Matrix4();
  let shown = null;
  let splitShown = -1;
  let flows = [];
  let linesFor = -1;
  let linesSplit = -1;
  const count = { ok: 0, no: 0 };
  const pose = { p: [0, 0, 0], t: [0, 0, 0] };

  const chapterAt = (t) => {
    let i = 0;
    while (i + 1 < chapters.length && chapters[i + 1].start <= t) i++;
    return i;
  };
  const beatAt = (t) => {
    const c = chapters[chapterAt(t)];
    return c.beats.find((b) => t < b.end) || c.beats[c.beats.length - 1];
  };
  function splitAt(t) {
    const ci = chapterAt(t);
    const c = chapters[ci];
    if (c.split) {
      let s = ci;
      while (s > 0 && chapters[s - 1].split) s--;
      return smooth((t - chapters[s].start) / SPLIT_MOVE);
    }
    if (ci > 0 && chapters[ci - 1].split) return 1 - smooth((t - c.start) / SPLIT_MOVE);
    return 0;
  }
  const point = (id, out) => {
    if (id.startsWith('ruler')) return out.copy(S.rulerAnchor(Number(id.slice(5))));
    return S.actors.get(id).anchor.getWorldPosition(out);
  };

  function applySplit(k) {
    for (const a of S.actors.values()) {
      const s = a.place?.split;
      if (!s) continue;
      const f = a.place.flat;
      a.obj.position.set(f[0] + (s[0] - f[0]) * k, f[1] + (s[1] - f[1]) * k, f[2] + (s[2] - f[2]) * k);
    }
    for (const [id, a] of Object.entries(S.plates)) {
      const vis = id === 'lanPlate' ? 1 - k : k;
      a.obj.visible = vis > 0.01;
      a.plate.opacity = (a.lit ? 0.18 : 0.09) * vis;
    }
    S.actors.get('router').obj.parent.updateMatrixWorld();
  }

  function applyBeat(b) {
    const focus = new Set(b.focus);
    for (const a of S.actors.values()) {
      const lit = focus.has(a.id);
      if (a.plate) {
        a.lit = lit;
        a.plate.color.setHex(lit ? 0xe8ae62 : 0xe6e0d6);
        continue;
      }
      a.meshes.forEach((m, i) => (m.material = lit ? a.focusMat || M.focus : a.base[i]));
    }
    for (const [name, objs] of Object.entries(S.layers)) objs.forEach((o) => (o.visible = b.layers.includes(name)));
    S.chips.visible = b.chips;
    S.actors.get('guestphone').obj.visible = !!b.guest;
    stage.setLabels(
      b.labels.map(([id, text, side]) => ({ id, text, side, at: id.startsWith('ruler') ? S.rulerAnchor(Number(id.slice(5))) : S.actors.get(id).anchor })),
    );
    if (b.ruler) {
      const upto = RULER_ORDER.indexOf(b.ruler);
      for (let i = 0; i < 256; i++) S.ruler.setColorAt(i, b.ruler === 'all' ? COLOR.all : COLOR.dim);
      RULER_ORDER.forEach((name, j) => {
        if (j > upto) return;
        for (const i of RULER_SETS[name]) S.ruler.setColorAt(i, j === upto ? COLOR.hot : COLOR.seen);
      });
      if (b.ruler === 'pool') for (const i of [146, 232]) S.ruler.setColorAt(i, COLOR.mark);
      S.ruler.instanceColor.needsUpdate = true;
    }
    splitShown = -1; // plate brightness depends on focus too
    flows = b.flows.map(([path, kind]) => ({ path, kind, pts: path.map(() => new Vector3()), lens: [], total: 0 }));
    linesFor = -1;
  }

  function measure(f) {
    f.path.forEach((id, i) => point(id, f.pts[i]));
    let total = 0;
    f.lens.length = 0;
    f.lens.push(0);
    for (let i = 1; i < f.pts.length; i++) {
      total += f.pts[i].distanceTo(f.pts[i - 1]);
      f.lens.push(total);
    }
    f.total = total;
  }
  function along(f, d, out) {
    for (let i = 1; i < f.pts.length; i++) {
      if (d <= f.lens[i] || i === f.pts.length - 1) {
        const seg = f.lens[i] - f.lens[i - 1] || 1;
        return out.lerpVectors(f.pts[i - 1], f.pts[i], clamp((d - f.lens[i - 1]) / seg));
      }
    }
    return out.copy(f.pts[0]);
  }

  // The paths only move with the beat or while devices walk to their streets; measure and draw them then.
  function updatePaths(b, split) {
    if (b.n === linesFor && split === linesSplit) return;
    linesFor = b.n;
    linesSplit = split;
    for (const f of flows) measure(f);
    const arr = S.flowLines.geometry.attributes.position;
    let v = 0;
    for (const f of flows) {
      for (let i = 1; i < f.pts.length && v + 2 <= arr.count; i++) {
        arr.setXYZ(v++, f.pts[i - 1].x, f.pts[i - 1].y + 0.05, f.pts[i - 1].z);
        arr.setXYZ(v++, f.pts[i].x, f.pts[i].y + 0.05, f.pts[i].z);
      }
    }
    arr.needsUpdate = true;
    S.flowLines.geometry.setDrawRange(0, v);
  }

  function drawPackets(b, t) {
    const n = count;
    n.ok = n.no = 0;
    for (const f of flows) {
      const period = clamp(f.total / 2.4, 1.4, 3.6);
      for (let k = 0; k < 3; k++) {
        const u = ((t - b.start) / period + k / 3) % 1;
        let s;
        let d;
        if (f.kind === 'no') {
          d = f.total * Math.min(1, u / 0.7);
          s = u < 0.7 ? Math.min(1, u * 10) : 1 - (u - 0.7) / 0.3;
        } else {
          d = f.total * u;
          s = Math.min(1, u * 10, (1 - u) * 10);
        }
        const mesh = S.packets[f.kind];
        if (n[f.kind] >= mesh.instanceMatrix.count) continue;
        along(f, d, tmp);
        mat.makeScale(s, s, s).setPosition(tmp.x, tmp.y + 0.05, tmp.z);
        mesh.setMatrixAt(n[f.kind]++, mat);
      }
    }
    S.packets.ok.count = n.ok;
    S.packets.ok.instanceMatrix.needsUpdate = true;
    S.packets.no.count = n.no;
    S.packets.no.instanceMatrix.needsUpdate = true;
  }

  return function direct(t) {
    const b = beatAt(t);
    if (b !== shown) {
      shown = b;
      applyBeat(b);
    }
    const split = splitAt(t);
    if (split !== splitShown) {
      splitShown = split;
      applySplit(split);
    }
    const prev = beats[Math.max(0, b.n - 1)];
    stage.setPose(mixPose(SHOTS[prev.shot], SHOTS[b.shot], (t - b.start) / CAMERA_MOVE, pose));
    updatePaths(b, split);
    drawPackets(b, t);
  };
}

// Compile every shader before playback: everything visible once, lit and unlit, packets and lines drawn.
async function warmUp(stage, S) {
  const hidden = [];
  stage.scene.traverse((o) => {
    if (!o.visible) {
      hidden.push(o);
      o.visible = true;
    }
  });
  for (const p of Object.values(S.packets)) p.count = 1;
  S.flowLines.geometry.setDrawRange(0, 2);
  const pass = async () => {
    try {
      await stage.renderer.compileAsync(stage.scene, stage.camera);
    } catch {
      /* older browsers: the render below compiles them instead */
    }
    stage.renderer.render(stage.scene, stage.camera);
  };
  await pass();
  const swapped = [];
  for (const a of S.actors.values()) {
    if (a.plate) continue;
    a.meshes.forEach((m) => {
      swapped.push([m, m.material]);
      m.material = a.focusMat || S.materials.focus;
    });
  }
  await pass();
  swapped.forEach(([m, material]) => (m.material = material));
  hidden.forEach((o) => (o.visible = false));
  stage.renderer.clear(); // the warm-up frames are not for the reader
}

async function start() {
  let stage;
  try {
    stage = new Stage({ container: stageEl, labelLayer: document.getElementById('labels'), reducedMotion: reducedMotion.matches, phone });
  } catch (err) {
    fail('This browser cannot show the 3D view.', 'WebGL is off or missing here. Try a current Chrome, Firefox or Safari.', err);
    return;
  }
  const bar = loading.querySelector('i');
  let S;
  try {
    S = buildScene(stage);
  } catch (err) {
    fail('The 3D scene did not build.', 'Reload the page. If it keeps happening, the site needs a look.', err);
    return;
  }
  if (bar) bar.style.transform = 'scaleX(0.6)';
  const timeline = buildTimeline(CHAPTERS);
  stage.applyPose(SHOTS.wide);
  await warmUp(stage, S);
  if (bar) bar.style.transform = 'scaleX(1)';
  const direct = makeDirector(stage, S, timeline);
  const player = new Player(timeline);
  let sheets = null;
  const ui = createUI({ root, player, timeline, stage, reducedMotion, onActivity: () => schedule(), dialogsOpen: () => sheets?.anyOpen() });
  sheets = createSheets({ root, timeline, player, onOpen: (open) => open && player.pause() });

  // keep the picture centred between the top bar and the caption block
  const top = document.getElementById('top');
  const caption = document.getElementById('caption');
  function syncInsets() {
    const h = stageEl.clientHeight || window.innerHeight;
    stage.setInsets(top.getBoundingClientRect().bottom, Math.max(0, h - caption.getBoundingClientRect().top + 8));
    schedule();
  }
  new ResizeObserver(syncInsets).observe(document.getElementById('hud'));
  window.addEventListener('resize', () => {
    stage.resize();
    syncInsets();
  });

  let last = 0;
  const loop = createLoop((now) => {
    const dt = last ? Math.min(0.1, (now - last) / 1000) : 0;
    last = now;
    player.tick(dt);
    if (player.playing && dt > 0) stage.adapt(dt * 1000);
    direct(player.time);
    // update() reports whether damping is still gliding the camera after a drag; when it stops, so does the loop
    const gliding = stage.controls.update();
    stage.render();
    const more = player.playing || gliding;
    if (!more) last = 0;
    return more;
  });
  function schedule() {
    loop.schedule();
  }
  stage.controls.addEventListener('change', schedule);
  stage.controls.addEventListener('start', schedule);

  let hashTimer = 0;
  player.on((reason) => {
    schedule();
    if (reason === 'tick' || reason === 'play' || reason === 'scrub') return;
    clearTimeout(hashTimer);
    hashTimer = setTimeout(() => {
      try {
        history.replaceState(null, '', `#t=${player.time.toFixed(1)}`);
      } catch {
        /* some browsers refuse replaceState on file:// */
      }
    }, 250);
  });
  reducedMotion.addEventListener?.('change', () => {
    stage.controls.enableDamping = !reducedMotion.matches;
    if (reducedMotion.matches) player.pause();
  });

  // #t=123.4 restores a moment; #<chapter id> (the catalog's links) opens a chapter; #chapters or #words a panel
  const hash = window.location.hash.slice(1);
  const m = /(?:^|&)t=(\d+(?:\.\d+)?)/.exec(hash);
  const byId = timeline.chapters.find((c) => c.id === hash);
  if (m) player.seek(Number(m[1]), 'restore');
  else if (byId) player.seek(byId.start, 'restore');
  syncInsets();
  ui.update();
  schedule();
  loading.hidden = true;
  root.classList.add('ready');
  if (hash === 'chapters' || hash === 'words') sheets.open(hash);
  window.__network = { player, timeline, stage, S, sheets };
  if (!m && !byId && !reducedMotion.matches) {
    setTimeout(() => {
      if (!player.playing && player.time === 0 && !player.scrubbing && !sheets.anyOpen()) player.play();
    }, 900);
  }
}

start();
