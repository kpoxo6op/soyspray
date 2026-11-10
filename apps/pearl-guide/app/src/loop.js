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
