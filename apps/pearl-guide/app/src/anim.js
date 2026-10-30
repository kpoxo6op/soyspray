// Small timing helpers. Everything on screen is a pure function of the playhead, so these stay stateless.

export const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
export const lerp = (a, b, t) => a + (b - a) * t;
export const smooth = (t) => {
  const x = clamp(t);
  return x * x * (3 - 2 * x);
};
export const easeOut = (t) => 1 - (1 - clamp(t)) ** 3;
export const easeIn = (t) => clamp(t) ** 3;
export const easeInOut = (t) => {
  const x = clamp(t);
  return x < 0.5 ? 4 * x * x * x : 1 - (-2 * x + 2) ** 3 / 2;
};
/** Progress of u through the window [a, b], clamped to 0..1. */
export const span = (u, a, b) => clamp((u - a) / (b - a));
export const mix3 = (a, b, t) => [lerp(a[0], b[0], t), lerp(a[1], b[1], t), lerp(a[2], b[2], t)];
/** A gentle drop into place: starts `h` metres higher and transparent, lands with an ease-out. */
export const drop = (u, h = 0.05) => ({ dy: h * (1 - easeOut(u)), alpha: smooth(u * 1.6) });
