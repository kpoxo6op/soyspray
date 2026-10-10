import { CABLES } from './wiring.js';
import { clamp } from './math.js';

const smooth = (t) => { const x = clamp(t, 0, 1); return x * x * (3 - 2 * x); };
export function wireState(timeline, cable, time) {
  const chapter = timeline.chapters.find(c => c.wire === cable.id);
  const dt = time - chapter.start;
  const ties = timeline.chapters.find(c => c.id === 'zip-ties');
  return {
    alpha: smooth((dt - 0.1) / 0.45),
    sA: (cable.plugs.a?.hover || 0) * (1 - smooth((dt - 0.6) / 1.0)),
    sB: cable.routeCum.at(-1) * smooth((dt - 1.8) / 4.0),
    dress: smooth((time - ties.start - 0.6) / 3.6),
    active: dt >= 0 && time < chapter.end,
  };
}
export function installationState(timeline, time) {
  const room = timeline.chapters.find(c => c.id === 'power-bricks');
  const ties = timeline.chapters.find(c => c.id === 'zip-ties');
  return { room: smooth((time - room.start) / 1.4), ties: smooth((time - ties.start - 0.2) / 4.2),
    wires: Object.fromEntries(CABLES.map(c => [c.id, wireState(timeline, c, time)])) };
}
