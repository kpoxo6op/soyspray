const image = document.querySelector('#meme');
const message = document.querySelector('#message');
const buttons = [...document.querySelectorAll('[data-action]')];
let feed, busy = true, hidden = 0, hiddenStart = null, sequence = 0;
const cache = new Map();
async function api(path, body) {
  const response = await fetch(path, body ? {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)} : {});
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || 'Please try again.');
  return data;
}
function preload(url) {
  if (!cache.has(url)) {
    const img = new Image();
    cache.set(url, new Promise((resolve, reject) => {img.onload = () => resolve(img); img.onerror = () => {cache.delete(url); reject(new Error('Image could not load. Reload to try again.'));}; img.src = url;}));
  }
  return cache.get(url);
}
async function show(next) {
  busy = true; buttons.forEach(b => b.disabled = true); feed = next;
  if (!feed.items.length) { image.hidden = true; message.hidden = false; message.textContent = 'You’ve seen this catalog. Check your results.'; return; }
  const [head] = feed.items;
  feed.items.slice(1).forEach(item => preload(item.image).catch(() => {}));
  const ready = await preload(head.image);
  image.src = ready.src; image.hidden = false; message.hidden = true;
  await image.decode();
  await new Promise(requestAnimationFrame);
  await api('/api/render', {impression_id:head.impression_id});
  hidden = 0; hiddenStart = document.hidden ? performance.now() : null;
  busy = false; buttons.forEach(b => b.disabled = false);
  for (const url of cache.keys()) if (!feed.items.some(i => i.image === url)) cache.delete(url);
}
function fail(error) { message.hidden = false; message.textContent = error.message; }
buttons.forEach(button => button.addEventListener('click', async () => {
  if (busy) return;
  busy = true; buttons.forEach(b => b.disabled = true);
  try {
    const next = await api('/api/action', {impression_id:feed.items[0].impression_id, action:button.dataset.action, hidden_ms:Math.round(hidden), client_seq:++sequence});
    await show(next);
  } catch (error) {
    fail(error);
    // The server might have committed despite a dropped response. Fetch its head.
    try { await show(await api('/api/feed')); } catch (refreshError) { fail(refreshError); }
  }
}));
document.addEventListener('visibilitychange', () => {
  if (document.hidden) hiddenStart = performance.now();
  else if (hiddenStart !== null) {hidden += performance.now()-hiddenStart; hiddenStart = null;}
});
api('/api/feed').then(show).catch(fail);
