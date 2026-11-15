// One chapter of a guide as a UI SDK primitive: a link into the guide and a Done toggle. The agent bridge lists
// each one with its title, link and done state, and an agent can tick it or open it without clicking.
import { createChange, definePrimitive } from '@ui-sdk/core';
import { createParts, wrappedButton } from '@ui-sdk/web';

export const chapter = definePrimitive({
  name: 'chapter',
  options: { href: 'string', done: 'boolean', defaultDone: 'boolean', onDoneChange: 'callback' },
  controlled: ['done', 'href'],
  state: (options) => ({ done: options.done ?? options.defaultDone ?? false, href: options.href ?? '' }),
  sync: (options) => ({
    ...(options.done === undefined ? {} : { done: options.done }),
    ...(options.href === undefined ? {} : { href: options.href }),
  }),
  api: (context) => {
    const change = createChange(context);
    return {
      isDone: () => context.store.get().done,
      setDone: (done, event) => change('done', done === true || done === 'true', { reason: 'press', event }),
      toggleDone: (event) => change('done', !context.store.get().done, { reason: 'press', event }),
      open: () => window.location.assign(context.store.get().href),
    };
  },
  slots: (slot) => ({
    root: slot({ attrs: (state) => ({ 'data-done': state.done ? '' : undefined }) }),
    done: slot({
      attrs: (state) => ({ type: 'button', 'aria-pressed': String(state.done) }),
      press: ({ api }, event) => api.toggleDone(event),
    }),
  }),
  agent: { actions: ['setDone', 'open'] },
});

export function defineChapterElements() {
  createParts(chapter, {
    root: { tag: 'soy-chapter', api: ['isDone', 'setDone', 'toggleDone', 'open'] },
    done: { tag: 'soy-chapter-done', target: wrappedButton, display: 'contents' },
  });
}
