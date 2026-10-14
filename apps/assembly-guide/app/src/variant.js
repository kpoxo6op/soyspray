// The URL selects one complete, deterministic installation on each page load.
export function parseLayout(search = '') {
  return new URLSearchParams(search).get('layout') === 'v1' ? 'v1' : 'v2';
}
export const VARIANT = parseLayout(globalThis.location?.search);
export const DRILLED = VARIANT === 'v1';
export const VARIANT_LABEL = DRILLED ? 'v1 · Drilled hole' : 'v2 · No holes';
