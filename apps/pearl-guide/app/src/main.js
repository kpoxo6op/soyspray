import './style.css';
import { Stage } from './stage.js';
import { loadAssets } from './assets.js';
import { buildScene } from './scene.js';
import { CHAPTERS, buildTimeline, makeDirector } from './story.js';
import { Player } from './player.js';
import { createUI } from './ui.js';
import { createSheets } from './sheets.js';

const root = document.getElementById('app');
const stageEl = document.getElementById('stage');
const loading = document.getElementById('loading');
const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
const phone = window.matchMedia('(max-width: 700px), (pointer: coarse)').matches;

function fail(title, text, err) {
  root.classList.add('failed');
  loading.hidden = false;
  loading.innerHTML = `<strong>${title}</strong><span>${text}</span>`;
  if (err) console.error(err);
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
  let assets;
  try {
    assets = await loadAssets((f) => bar && (bar.style.transform = `scaleX(${0.85 * f})`), { light: phone });
  } catch (err) {
    fail('The 3D models did not load.', 'Reload the page. If it keeps happening, the site needs a look.', err);
    return;
  }

  let S;
  try {
    S = buildScene(stage, assets);
  } catch (err) {
    fail('The 3D scene did not build.', 'Reload the page. If it keeps happening, the site needs a look.', err);
    return;
  }
  await warmUp(stage, S);
  if (bar) bar.style.transform = 'scaleX(1)';
  const timeline = buildTimeline(CHAPTERS);
  const direct = makeDirector(stage, S, timeline);
  const player = new Player(timeline);
  let sheets = null;
  const ui = createUI({ root, player, timeline, stage, reducedMotion, onActivity: () => schedule(), dialogsOpen: () => sheets?.anyOpen() });
  sheets = createSheets({
    root,
    timeline,
    player,
    onOpen: (open) => {
      if (open) player.pause();
    },
  });

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

  let raf = 0;
  let last = 0;
  function frame(now) {
    raf = 0;
    const dt = last ? Math.min(0.1, (now - last) / 1000) : 0;
    last = now;
    player.tick(dt);
    if (player.playing && dt > 0) stage.adapt(dt * 1000);
    direct(player.time);
    stage.controls.update();
    stage.render();
    if (player.playing || stage.controls.enableDamping) {
      raf = requestAnimationFrame(frame);
      if (!player.playing && idleFrames++ > 90) {
        cancelAnimationFrame(raf);
        raf = 0;
        last = 0;
      }
    } else last = 0;
  }
  let idleFrames = 0;
  function schedule() {
    idleFrames = 0;
    if (!raf) raf = requestAnimationFrame(frame);
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

  const m = /(?:^|[#&])t=(\d+(?:\.\d+)?)/.exec(window.location.hash);
  if (m) player.seek(Number(m[1]), 'restore');
  syncInsets();
  ui.update();
  schedule();
  loading.hidden = true;
  root.classList.add('ready');
  window.__pearl = { player, timeline, stage, S, sheets };
  if (!m && !reducedMotion.matches) {
    setTimeout(() => {
      if (!player.playing && player.time === 0 && !player.scrubbing && !sheets.anyOpen()) player.play();
    }, 900);
  }
}

// Compile every shader before playback. Without this each new object compiles its shaders the first time it
// appears, and the player stalls for a few hundred milliseconds at almost every new beat.
async function warmUp(stage, S) {
  const actors = [...S.cast.map.values()];
  const shown = actors.map((a) => a.obj.visible);
  const mats = actors.flatMap((a) => a.mats);
  const was = mats.map((m) => [m.transparent, m.depthWrite]);
  actors.forEach((a) => (a.obj.visible = true));
  stage.setBench(true);
  const pass = async () => {
    try {
      await stage.renderer.compileAsync(stage.scene, stage.camera);
    } catch {
      /* older browsers: the render below compiles them instead */
    }
    stage.renderer.shadowMap.needsUpdate = true;
    stage.renderer.render(stage.scene, stage.camera);
  };
  await pass(); // as drawn normally
  mats.forEach((m) => {
    m.transparent = true;
    m.needsUpdate = true;
  });
  await pass(); // while fading in or out
  mats.forEach((m) => (m.depthWrite = false));
  await pass(); // nearly faded out (Actor.fade stops depth writes below 0.6)
  mats.forEach((m, i) => {
    [m.transparent, m.depthWrite] = was[i];
    m.needsUpdate = true;
  });
  actors.forEach((a, i) => (a.obj.visible = shown[i]));
}

start();
