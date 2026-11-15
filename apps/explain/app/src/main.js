// The catalog with UI SDK: web components for the search, guide picker, switch, meters and buttons, a custom
// chapter primitive, and the agent bridge at window.agent so an agent can read and use the page without clicks.
import './style.css';
import '@ui-sdk/web/field';
import '@ui-sdk/web/input';
import '@ui-sdk/web/segmented-control';
import '@ui-sdk/web/switch';
import '@ui-sdk/web/meter';
import '@ui-sdk/web/button';
import { createAgent } from '@ui-sdk/web/agent';
import { defineChapterElements } from './chapter.js';
import { createCatalog } from './catalog.js';

const root = document.getElementById('app');
const catalog = createCatalog(root, {
  showMeter(slug, done, total) {
    const meter = root.querySelector(`ui-meter[data-meter="${slug}"]`);
    meter.format = (n) => `${n} of ${total}`;
    meter.setAttribute('value', String(done));
  },
});

// Ticks from earlier visits go in as each chapter's starting state, before its element upgrades.
for (const row of root.querySelectorAll('li[data-id]')) {
  if (catalog.isDone(row)) row.querySelector('soy-chapter').setAttribute('default-done', '');
}

window.agent = createAgent();
defineChapterElements();

root.querySelector('ui-input').addEventListener('valuechange', (e) => catalog.setFilter({ text: e.detail.value || '' }));
root.querySelector('ui-segmented-control').addEventListener('valuechange', (e) => catalog.setFilter({ guide: e.detail.value || 'all' }));
root.querySelector('ui-switch').addEventListener('checkedchange', (e) => catalog.setFilter({ hideDone: e.detail.value === true }));
// UI SDK change events fire on the element that changed and do not bubble.
for (const el of root.querySelectorAll('soy-chapter')) {
  const row = el.closest('li[data-id]');
  el.addEventListener('donechange', (e) => catalog.setDone(row.dataset.guide, row.dataset.id, e.detail.value === true));
}

catalog.start();
