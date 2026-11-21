// Address parsing is shared by initial navigation and hash changes.
const PANELS = new Set(['chapters', 'kit', 'files']);

export function parseHash(hash, chapters) {
  const parts = hash.replace(/^#/, '').split('&');
  const panel = parts.find((part) => PANELS.has(part)) || null;
  const timestamp = parts.find((part) => /^t=\d+(?:\.\d+)?$/.test(part));
  const seconds = timestamp === undefined ? NaN : Number(timestamp.slice(2));
  const chapter = chapters.find((c) => !PANELS.has(c.id) && parts.includes(c.id));
  return { time: Number.isFinite(seconds) ? seconds : chapter?.start ?? null, panel };
}

export function loopWanted(search, byDefault = false) {
  const params = new URLSearchParams(search);
  return params.has('loop') ? params.get('loop') !== '0' : byDefault;
}

// Keep tap eligibility separate from active pointers: normal capture release precedes click.
export function createTapTracker(toggle) {
  let tap = null;
  const pointers = new Set();
  const moved = (e) => {
    if (tap?.id === e.pointerId && Math.hypot(e.clientX - tap.x, e.clientY - tap.y) >= 6) tap = null;
  };
  return {
    pointerdown(e) {
      pointers.add(e.pointerId);
      tap = pointers.size === 1 && e.button === 0 ? { id: e.pointerId, x: e.clientX, y: e.clientY } : null;
    },
    pointermove: moved,
    pointerup(e) {
      pointers.delete(e.pointerId);
      moved(e);
    },
    pointercancel(e) {
      pointers.delete(e.pointerId);
      tap = null;
    },
    lostpointercapture(e) {
      if (pointers.delete(e.pointerId)) tap = null;
    },
    click(e) {
      if (e.detail < 2 && (tap || e.detail === 0)) toggle();
      tap = null;
    },
  };
}
