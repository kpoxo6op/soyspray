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
