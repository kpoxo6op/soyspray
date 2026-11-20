// The render loop: at most one animation-frame callback is ever pending. `step(now)` draws one frame and
// returns true while it needs another. `schedule()` asks for a frame from outside; called from inside a
// running step (the player announces every tick to its listeners) it only notes that one more is wanted,
// so a frame can never queue two follow-up frames.
export function createLoop(step, { request = (cb) => requestAnimationFrame(cb), cancel = (id) => cancelAnimationFrame(id) } = {}) {
  let id = 0;
  let running = false;
  let again = false;
  function run(now) {
    id = 0;
    running = true;
    again = false;
    let more = false;
    try {
      more = step(now);
    } finally {
      running = false;
    }
    if (more || again) id = request(run);
  }
  return {
    schedule() {
      if (running) again = true;
      else if (!id) id = request(run);
    },
    stop() {
      if (id) cancel(id);
      id = 0;
      again = false;
    },
    get pending() {
      return id !== 0;
    },
  };
}

// A looping page resumes bookmarks too; explicit panels and reduced motion stay paused.
export function autoplay(player, target, looping, reducedMotion, anyOpen) {
  if ((target.time !== null && !looping) || target.panel || reducedMotion.matches) return;
  const restoredTime = player.time;
  setTimeout(() => {
    if (!reducedMotion.matches && !player.playing && player.time === restoredTime && !player.scrubbing && !anyOpen()) player.play();
  }, 900);
}

// Restart only a completed forward playthrough. Player activity cancels it; a view gesture defers it.
export function autoLoop(player, enabled, reducedMotion, controls) {
  let timer;
  let waiting = false;
  let interacting = false;
  const clear = () => {
    clearTimeout(timer);
    timer = undefined;
  };
  const cancel = () => {
    clear();
    waiting = false;
  };
  const schedule = () => {
    clear();
    if (!waiting || interacting || reducedMotion.matches) return;
    timer = setTimeout(() => {
      cancel();
      if (reducedMotion.matches) return;
      player.seek(0, 'loop');
      player.play();
    }, 2500);
  };
  controls?.addEventListener('start', () => {
    interacting = true;
    clear();
  });
  controls?.addEventListener('end', () => {
    interacting = false;
    schedule();
  });
  player.on((reason) => {
    cancel();
    if (!enabled || reducedMotion.matches || reason !== 'ended' || player.time !== player.duration) return;
    waiting = true;
    schedule();
  });
  return cancel;
}
