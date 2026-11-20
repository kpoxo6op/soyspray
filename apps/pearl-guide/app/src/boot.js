import './style.css';
import { Stage } from './stage.js';
import { loadAssets } from './assets.js';
import { buildTimeline, makeDirector } from './director.js';
import { Player } from './player.js';
import { createUI } from './ui.js';
import { createSheets } from './sheets.js';
import { autoLoop, createLoop } from './loop.js';
import { loopWanted, parseHash } from './nav.js';

export function startGuide({ chapters, buildScene, canvasLabel, loop: loopDefault = false, sheets: sheetOptions }) {
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
      stage = new Stage({ container: stageEl, labelLayer: document.getElementById('labels'), reducedMotion: reducedMotion.matches, phone, canvasLabel });
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
    const timeline = buildTimeline(chapters);
    const direct = makeDirector(stage, S, timeline);
    const player = new Player(timeline);
    const cancelLoop = autoLoop(player, loopWanted(window.location.search, loopDefault), reducedMotion);
    let sheets = null;
    const ui = createUI({ root, player, timeline, stage, reducedMotion, onActivity: () => schedule(), dialogsOpen: () => sheets?.anyOpen() });
    sheets = createSheets({
      ...sheetOptions,
      root,
      timeline,
      player,
      onOpen: (open) => {
        if (open) {
          cancelLoop();
          player.pause();
        }
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

    let last = 0;
    let idleFrames = 0;
    const loop = createLoop((now) => {
      const dt = last ? Math.min(0.1, (now - last) / 1000) : 0;
      last = now;
      player.tick(dt);
      if (player.playing && dt > 0) stage.adapt(dt * 1000);
      direct(player.time);
      stage.controls.update();
      stage.render();
      // Damping keeps the camera gliding after a drag: allow it 90 quiet frames, then rest.
      const more = player.playing || (stage.controls.enableDamping && idleFrames++ <= 90);
      if (!more) last = 0;
      return more;
    });
    function schedule() {
      idleFrames = 0;
      loop.schedule();
    }
    stage.controls.addEventListener('change', schedule);
    stage.controls.addEventListener('start', schedule);

    // A tap toggles playback; drags, pinches and the second click of a double click do not.
    let tap = null;
    const pointers = new Set();
    stage.canvas.addEventListener('pointerdown', (e) => {
      pointers.add(e.pointerId);
      tap = pointers.size === 1 && e.button === 0 ? { id: e.pointerId, x: e.clientX, y: e.clientY } : null;
    });
    stage.canvas.addEventListener('pointermove', (e) => {
      if (tap?.id === e.pointerId && Math.hypot(e.clientX - tap.x, e.clientY - tap.y) >= 6) tap = null;
    });
    stage.canvas.addEventListener('pointerup', (e) => {
      pointers.delete(e.pointerId);
      if (tap?.id === e.pointerId && Math.hypot(e.clientX - tap.x, e.clientY - tap.y) >= 6) tap = null;
    });
    stage.canvas.addEventListener('pointercancel', (e) => {
      pointers.delete(e.pointerId);
      tap = null;
    });
    stage.canvas.addEventListener('click', (e) => {
      if (e.detail < 2 && (tap || e.detail === 0)) player.toggle();
      tap = null;
    });

    let hashTimer = 0;
    let navigating = false;
    player.on((reason) => {
      schedule();
      if (navigating || sheets.anyOpen() || reason === 'play' || reason === 'scrub') return;
      // While playing, write at most once a second without postponing forever on each tick.
      if (reason === 'tick' && hashTimer) return;
      clearTimeout(hashTimer);
      hashTimer = setTimeout(() => {
        hashTimer = 0;
        if (sheets.anyOpen()) return;
        try {
          history.replaceState(null, '', `#t=${player.time.toFixed(1)}`);
        } catch {
          /* some browsers refuse replaceState on file:// */
        }
      }, reason === 'tick' ? 1000 : 250);
    });
    reducedMotion.addEventListener?.('change', () => {
      stage.controls.enableDamping = !reducedMotion.matches;
      if (reducedMotion.matches) {
        cancelLoop();
        player.pause();
      }
    });

    function navigate() {
      clearTimeout(hashTimer);
      hashTimer = 0;
      cancelLoop();
      const target = parseHash(window.location.hash, timeline.chapters);
      navigating = true;
      try {
        if (target.time !== null) {
          sheets.close();
          player.seek(target.time, 'restore');
        }
        if (target.panel) sheets.open(target.panel);
      } finally {
        navigating = false;
      }
      return target;
    }
    const target = navigate();
    window.addEventListener('hashchange', navigate);
    syncInsets();
    ui.update();
    schedule();
    loading.hidden = true;
    root.classList.add('ready');
    window.__pearl = { player, timeline, stage, S, sheets };
    if (target.time === null && !reducedMotion.matches) {
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

  return start();
}
