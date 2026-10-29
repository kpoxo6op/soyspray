// The URL selects one complete, deterministic installation on each page load.
const LAYOUTS = ['v1', 'v2', 'v3'];
export function parseLayout(search = '') {
  const v = new URLSearchParams(search).get('layout');
  return LAYOUTS.includes(v) ? v : 'v2';
}
export const VARIANT = parseLayout(globalThis.location?.search);
export const DRILLED = VARIANT === 'v1';
export const SOYRACK = VARIANT === 'v3';
export const VARIANT_LABEL = { v1: 'v1 · Drilled hole', v2: 'v2 · No holes', v3: 'v3 · Soyrack' }[VARIANT];
