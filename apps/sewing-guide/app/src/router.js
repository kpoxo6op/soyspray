// Hash router: #/section/id. Keeps the app a single static file set that works from any path.
const listeners = new Set();

export function parseRoute(hash = window.location.hash) {
  const clean = hash.replace(/^#\/?/, '');
  const [path, query = ''] = clean.split('?');
  const parts = path.split('/').filter(Boolean).map(decodeURIComponent);
  return { section: parts[0] || 'home', id: parts[1] || null, sub: parts[2] || null, params: new URLSearchParams(query) };
}

export function href(section, id, sub, params) {
  let h = `#/${section}`;
  if (id != null) h += `/${encodeURIComponent(id)}`;
  if (sub != null) h += `/${encodeURIComponent(sub)}`;
  if (params) {
    const q = new URLSearchParams(params).toString();
    if (q) h += `?${q}`;
  }
  return h;
}

export function navigate(section, id, sub, params) {
  window.location.hash = href(section, id, sub, params);
}

export function onRoute(fn) {
  listeners.add(fn);
  return () => listeners.delete(fn);
}

export function startRouter() {
  const fire = () => {
    const r = parseRoute();
    for (const fn of listeners) fn(r);
  };
  window.addEventListener('hashchange', fire);
  fire();
}
