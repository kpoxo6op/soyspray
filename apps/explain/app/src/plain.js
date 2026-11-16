// The same catalog with native controls and no UI SDK: the baseline for tools/agent-bench. Not shipped.
import './style.css';
import { createCatalog } from './catalog.js';

const root = document.getElementById('app');
const catalog = createCatalog(root, {
  showMeter(slug, done, total) {
    root.querySelector(`meter[data-meter="${slug}"]`).value = done;
    root.querySelector(`output[data-meter-text="${slug}"]`).value = `${done} of ${total}`;
  },
});

for (const row of root.querySelectorAll('li[data-id]')) {
  row.querySelector('button.done').setAttribute('aria-pressed', String(catalog.isDone(row)));
}
root.querySelector('input[type=search]').addEventListener('input', (e) => catalog.setFilter({ text: e.target.value }));
root.querySelector('.segments').addEventListener('change', (e) => catalog.setFilter({ guide: e.target.value }));
root.querySelector('input[role=switch]').addEventListener('change', (e) => catalog.setFilter({ hideDone: e.target.checked }));
root.addEventListener('click', (e) => {
  const button = e.target.closest('button.done');
  if (!button) return;
  const done = button.getAttribute('aria-pressed') !== 'true';
  button.setAttribute('aria-pressed', String(done));
  const row = button.closest('li[data-id]');
  catalog.setDone(row.dataset.guide, row.dataset.id, done);
});

catalog.start();
