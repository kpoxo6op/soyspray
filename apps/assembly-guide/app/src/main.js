import './style.css';
import placements from '../data/placements.json';
import meshBytes from '../data/meshes.bin';
import { buildTimeline } from './timeline.js';
import { decodeMeshes } from './meshes.js';
import { Player } from './player.js';
import { createUI } from './ui.js';
import { Viewer } from './scene.js';

const root = document.getElementById('app');
const stage = document.getElementById('stage');
const hud = document.getElementById('hud');
const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
const phone = window.matchMedia('(max-width: 700px), (pointer: coarse)').matches;

const timeline = buildTimeline(placements);
const player = new Player(timeline);

function readHashTime() {
  const m = /(?:^|[#&])t=(\d+(?:\.\d+)?)/.exec(window.location.hash);
  return m ? Number(m[1]) : null;
}

let viewer;
try {
  viewer = new Viewer({ container: stage, timeline, meshes: decodeMeshes(meshBytes), reducedMotion: reducedMotion.matches, phone });
} catch (err) {
  root.classList.add('no-webgl');
  document.getElementById('chapterTitle').textContent = 'This browser cannot show the 3D view';
  document.getElementById('chapterText').textContent = 'WebGL is turned off or unavailable here. Try a current Chrome, Firefox or Safari.';
  console.error(err);
  throw err;
}

const ui = createUI({ root, player, timeline, viewer, reducedMotion, onUserActivity: () => schedule() });

// Keep the 3D content centred in the area above the caption and transport bar.
const caption = document.getElementById('caption');
function syncInset() {
  const h = stage.clientHeight || window.innerHeight;
  viewer.setBottomInset(Math.max(0, h - caption.getBoundingClientRect().top + 12));
  schedule();
}
new ResizeObserver(syncInset).observe(hud);
window.addEventListener('resize', () => {
  viewer.resize();
  syncInset();
});

// ---------------------------------------------------------------- render loop (on demand)
let raf = 0;
let last = 0;
function frame(now) {
  raf = 0;
  const dt = last ? Math.min(0.1, (now - last) / 1000) : 0;
  last = now;
  if (player.tick(dt)) viewer.setTime(player.time);
  const cameraMoving = viewer.update(dt);
  if (viewer.dirty) viewer.render();
  if (player.playing || cameraMoving || viewer.tween) {
    raf = requestAnimationFrame(frame);
  } else {
    last = 0;
  }
}
function schedule() {
  if (!raf) raf = requestAnimationFrame(frame);
}
viewer.controls.addEventListener('change', schedule);
viewer.controls.addEventListener('start', schedule);
viewer.onRequestFrame = schedule;

let hashTimer = 0;
player.on((reason) => {
  if (reason !== 'tick') viewer.setTime(player.time);
  schedule();
  if (reason !== 'tick' && reason !== 'play' && reason !== 'scrub') {
    clearTimeout(hashTimer);
    hashTimer = setTimeout(() => {
      try {
        history.replaceState(null, '', `#t=${player.time.toFixed(1)}`);
      } catch {
        /* file:// in some browsers */
      }
    }, 250);
  }
});

reducedMotion.addEventListener?.('change', () => {
  viewer.reducedMotion = reducedMotion.matches;
  viewer.controls.enableDamping = !reducedMotion.matches;
  if (reducedMotion.matches) player.pause();
});

// ---------------------------------------------------------------- start
const startAt = readHashTime();
if (startAt !== null) player.seek(startAt, 'restore');
syncInset();
viewer.setTime(player.time);
ui.update();
schedule();
root.classList.add('ready');

if (startAt === null && !reducedMotion.matches) {
  setTimeout(() => {
    if (!player.playing && player.time === 0 && !player.scrubbing) player.play();
  }, 900);
}
