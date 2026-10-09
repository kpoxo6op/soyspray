// Transport bar: chapter scrubber, playback buttons, keyboard shortcuts and the chapter caption.

import { formatTime } from './player.js';

const ICONS = {
  prev: 'M6 6h2v12H6zm3.5 6 8.5 6V6z',
  rewind: 'M11 18V6l-8.5 6 8.5 6zm.5-6 8.5 6V6l-8.5 6z',
  play: 'M8 5.14v13.72a1 1 0 0 0 1.52.85l10.4-6.86a1 1 0 0 0 0-1.7L9.52 4.29A1 1 0 0 0 8 5.14z',
  pause: 'M7 5h3.2v14H7zm6.8 0H17v14h-3.2z',
  next: 'M6 18l8.5-6L6 6v12zM16 6v12h2V6h-2z',
  view: 'M5 15H3v4a2 2 0 0 0 2 2h4v-2H5v-4zM5 5h4V3H5a2 2 0 0 0-2 2v4h2V5zm14-2h-4v2h4v4h2V5a2 2 0 0 0-2-2zm0 16h-4v2h4a2 2 0 0 0 2-2v-4h-2v4zM12 9a3 3 0 1 0 0 6 3 3 0 0 0 0-6z',
  full: 'M7 14H5v5h5v-2H7v-3zm-2-4h2V7h3V5H5v5zm12 7h-3v2h5v-5h-2v3zM14 5v2h3v3h2V5h-5z',
  unfull: 'M5 16h3v3h2v-5H5v2zm3-8H5v2h5V5H8v3zm6 11h2v-3h3v-2h-5v5zm2-11V5h-2v5h5V8h-3z',
};

const svg = (path) => `<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="${path}"/></svg>`;

const IDLE_MS = 2600;

export function createUI({ root, player, timeline, viewer, reducedMotion, onUserActivity }) {
  const $ = (id) => root.querySelector(`#${id}`);
  const hud = $('hud');
  const scrubber = $('scrubber');
  const track = $('track');
  const thumb = $('thumb');
  const tip = $('hoverTip');
  const tipTitle = tip.querySelector('.tip-title');
  const tipTime = tip.querySelector('.tip-time');
  const chapterNo = $('chapterNo');
  const chapterTitle = $('chapterTitle');
  const chapterText = $('chapterText');
  const caption = $('caption');
  const live = $('live');
  const timeNow = $('timeNow');
  const timeTotal = $('timeTotal');
  const btn = {
    prev: $('btnPrev'),
    rewind: $('btnRewind'),
    play: $('btnPlay'),
    next: $('btnNext'),
    speed: $('btnSpeed'),
    view: $('btnView'),
    full: $('btnFull'),
  };
  btn.prev.innerHTML = svg(ICONS.prev);
  btn.rewind.innerHTML = svg(ICONS.rewind);
  btn.next.innerHTML = svg(ICONS.next);
  btn.view.innerHTML = svg(ICONS.view);

  const { chapters, duration } = timeline;
  const pad = (n) => String(n).padStart(2, '0');
  timeTotal.textContent = formatTime(duration);
  scrubber.setAttribute('aria-valuemax', duration.toFixed(1));

  // ---------------------------------------------------------- chapter segments
  const segs = chapters.map((c) => {
    const el = document.createElement('div');
    el.className = 'seg';
    el.style.flexGrow = String(c.end - c.start);
    el.innerHTML = '<div class="buf"></div><div class="fill"></div>';
    track.appendChild(el);
    return { el, fill: el.lastChild, buf: el.firstChild, c };
  });

  // Map between scrubber x and timeline time, honouring the gaps between segments.
  // Segment boxes are cached (offset* values ignore the hover scale) and refreshed on resize.
  let geoCache = null;
  function geometry() {
    if (geoCache) {
      const left = track.getBoundingClientRect().left;
      return geoCache.map((g) => ({ left: left + g.x0, right: left + g.x1, c: g.c }));
    }
    geoCache = segs.map((s) => ({ x0: s.el.offsetLeft, x1: s.el.offsetLeft + s.el.offsetWidth, c: s.c }));
    return geometry();
  }

  function timeAtX(x) {
    const g = geometry();
    if (x <= g[0].left) return 0;
    for (let i = 0; i < g.length; i++) {
      const s = g[i];
      if (x <= s.right) {
        if (x < s.left) return s.c.start; // inside a gap: snap to the chapter start
        const f = (x - s.left) / Math.max(1, s.right - s.left);
        return s.c.start + f * (s.c.end - s.c.start);
      }
    }
    return duration;
  }

  function xAtTime(t) {
    if (!geoCache) geometry();
    const g = geoCache;
    for (const s of g) {
      if (t <= s.c.end || s === g[g.length - 1]) {
        const f = Math.min(1, Math.max(0, (t - s.c.start) / (s.c.end - s.c.start)));
        return track.offsetLeft + s.x0 + f * (s.x1 - s.x0);
      }
    }
    return track.offsetLeft + track.offsetWidth;
  }

  function chapterIndexAt(t) {
    let i = 0;
    while (i + 1 < chapters.length && chapters[i + 1].start <= t) i++;
    return i;
  }

  // ---------------------------------------------------------- caption height
  // Reserve the height of the longest chapter text so the bar (and the camera framing that
  // depends on it) never shifts while playback moves between chapters.
  function reserveCaptionHeight() {
    const probe = caption.cloneNode(true);
    probe.removeAttribute('id');
    probe.querySelectorAll('[id]').forEach((el) => el.removeAttribute('id'));
    probe.style.cssText = `position:absolute;visibility:hidden;pointer-events:none;left:0;top:0;width:${caption.clientWidth}px;min-height:0`;
    caption.parentNode.appendChild(probe);
    let max = 0;
    const [no, title] = probe.querySelectorAll('.chapter span');
    const text = probe.querySelector('.chapter-text');
    chapters.forEach((c, i) => {
      no.textContent = pad(i + 1);
      title.textContent = c.title;
      text.textContent = c.text;
      max = Math.max(max, probe.offsetHeight);
    });
    probe.remove();
    caption.style.minHeight = `${Math.ceil(max)}px`;
  }

  // ---------------------------------------------------------- rendering of state
  let shownChapter = -1;
  let liveTimer = 0;
  let swapTimer = 0;
  let pendingCaption = 0;

  function applyCaption(i) {
    const c = chapters[i];
    chapterNo.textContent = pad(i + 1);
    chapterTitle.textContent = c.title;
    chapterText.textContent = c.text;
  }

  function renderCaption(i, animate) {
    const c = chapters[i];
    pendingCaption = i;
    if (animate && !reducedMotion.matches) {
      caption.classList.add('swap');
      if (!swapTimer) {
        swapTimer = setTimeout(() => {
          swapTimer = 0;
          applyCaption(pendingCaption);
          caption.classList.remove('swap');
        }, 140);
      }
    } else {
      clearTimeout(swapTimer);
      swapTimer = 0;
      caption.classList.remove('swap');
      applyCaption(i);
    }
    clearTimeout(liveTimer);
    liveTimer = setTimeout(() => {
      live.textContent = `Chapter ${i + 1} of ${chapters.length}: ${c.title}. ${c.text}`;
    }, player.playing || player.scrubbing ? 900 : 250);
  }

  function update() {
    const t = player.time;
    const i = player.chapterIndex;
    if (i !== shownChapter) {
      renderCaption(i, shownChapter !== -1);
      shownChapter = i;
    }
    for (const s of segs) {
      const f = Math.min(1, Math.max(0, (t - s.c.start) / (s.c.end - s.c.start)));
      s.fill.style.transform = `scaleX(${f})`;
    }
    thumb.style.left = `${xAtTime(t)}px`;
    timeNow.textContent = formatTime(t);
    scrubber.setAttribute('aria-valuenow', t.toFixed(1));
    scrubber.setAttribute('aria-valuetext', `${formatTime(t)} of ${formatTime(duration)}, chapter ${i + 1}: ${chapters[i].title}`);

    const key = `${player.direction}|${player.speed}`;
    if (key !== buttonState) {
      buttonState = key;
      const playingFwd = player.direction > 0;
      btn.play.innerHTML = svg(playingFwd ? ICONS.pause : ICONS.play);
      btn.play.setAttribute('aria-label', playingFwd ? 'Pause' : 'Play');
      btn.play.title = playingFwd ? 'Pause (Space)' : 'Play (Space)';
      btn.rewind.setAttribute('aria-pressed', String(player.reversing));
      btn.rewind.setAttribute('aria-label', player.reversing ? 'Stop rewinding' : 'Rewind');
      btn.rewind.title = player.reversing ? 'Stop rewinding (R)' : 'Rewind (R)';
      btn.speed.textContent = `${player.speed}×`;
      btn.speed.setAttribute('aria-label', `Playback speed ${player.speed}×`);
      hud.classList.toggle('playing', player.playing);
      if (!player.playing) setIdle(false);
    }
  }
  let buttonState = '';

  // ---------------------------------------------------------- scrubbing
  let hotSeg = null;
  function hover(x) {
    const t = timeAtX(x);
    const i = chapterIndexAt(t);
    const rect = scrubber.getBoundingClientRect();
    const half = Math.max(60, tip.offsetWidth / 2);
    const left = Math.min(rect.width - half, Math.max(half, x - rect.left));
    tip.style.left = `${left}px`;
    tipTitle.textContent = chapters[i].title;
    tipTime.textContent = formatTime(t);
    const seg = segs[i];
    if (hotSeg !== seg) {
      hotSeg?.el.classList.remove('hot');
      seg.el.classList.add('hot');
      hotSeg = seg;
    }
    for (const s of segs) {
      const f = Math.min(1, Math.max(0, (t - s.c.start) / (s.c.end - s.c.start)));
      s.buf.style.transform = `scaleX(${f})`;
    }
  }

  function clearHover() {
    hotSeg?.el.classList.remove('hot');
    hotSeg = null;
    for (const s of segs) s.buf.style.transform = 'scaleX(0)';
  }

  let dragging = null;
  scrubber.addEventListener('pointerdown', (e) => {
    if (e.button !== 0 && e.pointerType === 'mouse') return;
    e.preventDefault();
    scrubber.setPointerCapture(e.pointerId);
    dragging = e.pointerId;
    scrubber.classList.add('active');
    player.beginScrub();
    player.seek(timeAtX(e.clientX), 'scrub');
    hover(e.clientX);
    activity();
  });
  scrubber.addEventListener('pointermove', (e) => {
    if (dragging === e.pointerId) player.seek(timeAtX(e.clientX), 'scrub');
    if (e.pointerType === 'mouse' || dragging === e.pointerId) hover(e.clientX);
  });
  const endDrag = (e) => {
    if (dragging !== e.pointerId) return;
    dragging = null;
    scrubber.classList.remove('active');
    player.endScrub();
    if (e.pointerType !== 'mouse') clearHover();
    scrubber.focus({ preventScroll: true });
  };
  scrubber.addEventListener('pointerup', endDrag);
  scrubber.addEventListener('pointercancel', endDrag);
  scrubber.addEventListener('pointerleave', (e) => {
    if (dragging === null && e.pointerType === 'mouse') clearHover();
  });

  // ---------------------------------------------------------- buttons
  btn.play.addEventListener('click', () => (player.direction > 0 ? player.pause() : player.play()));
  btn.rewind.addEventListener('click', () => player.toggleReverse());
  btn.prev.addEventListener('click', () => player.prevChapter());
  btn.next.addEventListener('click', () => player.nextChapter());
  btn.speed.addEventListener('click', () => player.cycleSpeed());
  btn.view.addEventListener('click', () => viewer.resetView());

  const fsTarget = document.documentElement;
  if (document.fullscreenEnabled && fsTarget.requestFullscreen) {
    const syncFs = () => {
      const on = !!document.fullscreenElement;
      btn.full.innerHTML = svg(on ? ICONS.unfull : ICONS.full);
      btn.full.setAttribute('aria-label', on ? 'Exit full screen' : 'Full screen');
      btn.full.title = on ? 'Exit full screen (F)' : 'Full screen (F)';
    };
    btn.full.addEventListener('click', () => toggleFullscreen());
    document.addEventListener('fullscreenchange', syncFs);
    syncFs();
  } else {
    btn.full.remove();
    btn.full = null;
  }

  function toggleFullscreen() {
    if (!btn.full) return;
    if (document.fullscreenElement) document.exitFullscreen();
    else fsTarget.requestFullscreen().catch(() => {});
  }

  function syncViewButton() {
    btn.view.classList.toggle('is-hidden', viewer.pristine);
    btn.view.tabIndex = viewer.pristine ? -1 : 0;
  }
  viewer.controls.addEventListener('start', syncViewButton);
  btn.view.addEventListener('click', () => requestAnimationFrame(syncViewButton));
  syncViewButton();
  viewer.onPristineChange = syncViewButton;

  // ---------------------------------------------------------- keyboard
  window.addEventListener('keydown', (e) => {
    if (e.defaultPrevented) return;
    // Leave browser shortcuts alone (Ctrl/Cmd+R, Ctrl+F, Alt+letters ...); modifiers only combine with arrows.
    if ((e.ctrlKey || e.metaKey || e.altKey) && !e.key.startsWith('Arrow')) return;
    const tag = e.target?.tagName;
    const onButton = tag === 'BUTTON';
    const k = e.key;
    let handled = true;
    const chapterJump = e.shiftKey || e.ctrlKey || e.metaKey || e.altKey;
    switch (k) {
      case ' ':
      case 'Spacebar':
        if (onButton) return; // the focused button handles its own activation
        if (player.playing) player.pause();
        else player.play();
        break;
      case 'k':
      case 'K':
        if (player.playing) player.pause();
        else player.play();
        break;
      case 'ArrowLeft':
        if (chapterJump) player.prevChapter();
        else player.seekBy(-5);
        break;
      case 'ArrowRight':
        if (chapterJump) player.nextChapter();
        else player.seekBy(5);
        break;
      case 'ArrowUp':
      case 'PageUp':
        player.nextChapter();
        break;
      case 'ArrowDown':
      case 'PageDown':
        player.prevChapter();
        break;
      case 'j':
      case 'J':
        player.seekBy(-10);
        break;
      case 'l':
      case 'L':
        player.seekBy(10);
        break;
      case ',':
        player.pause();
        player.seekBy(-0.2);
        break;
      case '.':
        player.pause();
        player.seekBy(0.2);
        break;
      case 'Home':
        player.seek(0);
        break;
      case 'End':
        player.seek(duration);
        break;
      case 'r':
      case 'R':
        player.toggleReverse();
        break;
      case 'f':
      case 'F':
        toggleFullscreen();
        break;
      case 'v':
      case 'V':
        viewer.resetView();
        syncViewButton();
        break;
      default:
        if (/^[0-9]$/.test(k) && !e.ctrlKey && !e.metaKey) player.seek((Number(k) / 10) * duration);
        else handled = false;
    }
    if (handled) {
      e.preventDefault();
      activity();
    }
  });

  // ---------------------------------------------------------- idle dimming while playing
  let idleTimer = 0;
  function setIdle(on) {
    hud.classList.toggle('idle', on);
  }
  function activity() {
    setIdle(false);
    clearTimeout(idleTimer);
    if (player.playing) idleTimer = setTimeout(() => player.playing && !hud.matches(':hover, :focus-within') && setIdle(true), IDLE_MS);
    onUserActivity?.();
  }
  for (const ev of ['pointermove', 'pointerdown', 'wheel', 'touchstart']) {
    window.addEventListener(ev, activity, { passive: true });
  }
  hud.addEventListener('focusin', () => setIdle(false));

  player.on((reason) => {
    if (reason === 'play') activity();
    update();
  });
  let resizeTimer = 0;
  window.addEventListener('resize', () => {
    geoCache = null;
    update();
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(reserveCaptionHeight, 120);
  });
  reserveCaptionHeight();
  update();

  return { update, activity };
}
