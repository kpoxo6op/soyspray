(() => {
  const $ = (selector) => document.querySelector(selector);
  const dialog = $('#link-editor');
  const form = $('#link-form');
  const state = { active: false, trip: null, editor: null, epoch: 0, refreshing: false, monthSet: false };
  const fields = () => ({ title: $('#link-title').value.trim(), url: $('#link-url').value.trim() });
  const same = (a, b) => a.title === b.title && a.url === b.url;
  const dirty = () => !!state.editor && !same(state.editor.base, fields());
  const candidates = (trip) => trip?.document.accommodation.candidates || [];

  function element(tag, text, className = '') {
    const node = document.createElement(tag);
    node.textContent = text;
    node.className = className;
    return node;
  }

  function render() {
    const list = $('#links-list');
    list.replaceChildren();
    $('#add-link').disabled = !state.trip || candidates(state.trip).length >= 12;
    if (!candidates(state.trip).length) list.append(element('li', 'Ссылок пока нет.', 'empty-state'));
    for (const item of candidates(state.trip)) {
      const row = element('li', '', 'saved-link');
      const content = element('div', '');
      const link = element('a', item.title);
      link.href = item.url || '#';
      link.target = '_blank'; link.rel = 'noopener noreferrer';
      content.append(link);
      if (item.url) content.append(element('p', new URL(item.url).hostname, 'muted'));
      const edit = element('button', 'Изменить', 'text-button');
      edit.type = 'button'; edit.setAttribute('aria-label', `Изменить: ${item.title}`);
      edit.addEventListener('click', () => openEditor(item));
      row.append(content, edit); list.append(row);
    }
  }

  function syncEditor() {
    const editor = state.editor;
    if (!editor) return;
    $('#link-save').disabled = editor.saving || !!editor.conflict || !dirty();
    $('#link-delete').disabled = editor.saving || !!editor.conflict;
    $('#link-close').disabled = editor.saving;
    for (const input of form.querySelectorAll('input')) input.disabled = editor.saving && editor.removing;
    $('#link-save-status').textContent = editor.saving ? 'Сохраняем…' : dirty() ? 'Есть несохранённые изменения' : '';
  }

  function openEditor(item) {
    if (!state.trip || state.editor) return;
    state.editor = {
      id: item?.id || crypto.randomUUID(),
      base: item ? { title: item.title, url: item.url } : { title: '', url: '' },
      trip: structuredClone(state.trip), saving: false, conflict: null,
    };
    $('#link-title').value = item?.title || '';
    $('#link-url').value = item?.url || '';
    $('#link-edit-title').textContent = item ? 'Изменить ссылку' : 'Добавить ссылку';
    $('#link-delete').hidden = !item;
    $('#link-error').textContent = ''; $('#link-conflict').hidden = true;
    syncEditor(); dialog.showModal(); $('#link-title').focus();
  }

  function closeEditor(discard = false) {
    if (state.editor?.saving) return;
    if (!discard && dirty() && !window.confirm('Закрыть без сохранения изменений?')) return;
    state.editor = null; form.reset(); dialog.close();
  }

  function showConflict(fresh) {
    const editor = state.editor;
    editor.conflict = fresh;
    const saved = candidates(fresh).find((item) => item.id === editor.id);
    const existed = candidates(editor.trip).some((item) => item.id === editor.id);
    $('#link-conflict-message').textContent = saved
      ? `Сейчас сохранено: ${saved.title} — ${saved.url}. Ваш черновик остаётся в форме.`
      : existed ? 'Эту ссылку удалили в другом окне. Ваш черновик остаётся в форме.'
        : 'Список изменился. Ваша ссылка ещё не добавлена.';
    $('#link-reapply').textContent = existed && !saved ? 'Добавить мою ссылку заново' : 'Оставить мой вариант';
    $('#link-conflict').hidden = false;
  }

  async function saveLink(remove = false) {
    const editor = state.editor;
    if (!editor || editor.saving || editor.conflict || (!remove && !form.reportValidity())) return;
    if (remove && !window.confirm('Удалить эту ссылку из общего списка?')) return;
    const sent = fields();
    if (!remove) {
      const url = new URL(sent.url);
      if (!['https:', 'http:'].includes(url.protocol) || url.username || url.password) {
        $('#link-error').textContent = 'Укажите ссылку http или https без пароля.'; return;
      }
    }
    const document = structuredClone(editor.trip.document); delete document.decisions;
    const list = document.accommodation.candidates;
    const index = list.findIndex((item) => item.id === editor.id);
    if (remove) {
      if (index >= 0) list.splice(index, 1);
      if (document.accommodation.selected === editor.id) document.accommodation.selected = null;
    } else if (index >= 0) Object.assign(list[index], sent);
    else list.push({ id: editor.id, ...sent, arrival: null, departure: null, total_cents: null, quoted_on: null, capacity: null, notes: '' });
    state.epoch += 1; state.refreshing = false;
    editor.removing = remove; editor.saving = true; $('#link-error').textContent = ''; syncEditor();
    try {
      const result = await api('/api/trip', { method: 'PUT', body: JSON.stringify({ expected_revision: editor.trip.revision, document }) });
      if (state.editor !== editor) return;
      state.trip = result.trip; editor.trip = structuredClone(result.trip); editor.base = sent;
      editor.saving = false; render(); syncEditor();
      if (remove || !dirty()) { closeEditor(true); $('#links-status').textContent = remove ? 'Ссылка удалена.' : 'Ссылка сохранена.'; }
      else $('#link-save-status').textContent = 'Сохранено. Новые правки ещё не сохранены.';
    } catch (error) {
      if (state.editor !== editor) return;
      $('#link-error').textContent = error.status === 401 ? 'Сессия закончилась. Войдите в другом окне; черновик останется здесь.' : 'Не удалось сохранить. Черновик остаётся здесь. Повторите попытку.';
      if (error.status === 409) {
        try {
          const fresh = await api('/api/trip');
          if (state.editor === editor && fresh.trip) { state.trip = fresh.trip; showConflict(fresh.trip); render(); }
        } catch { $('#link-error').textContent += ' Обновление тоже не удалось.'; }
      }
    } finally {
      if (state.editor === editor) { editor.saving = false; syncEditor(); }
    }
  }

  async function refresh() {
    if (!state.active || state.refreshing || state.editor?.saving) return;
    const epoch = state.epoch; state.refreshing = true;
    try {
      const result = await api('/api/trip');
      if (epoch !== state.epoch || !state.active) return;
      state.trip = result.trip; render();
      $('#links-status').textContent = result.trip ? '' : 'Поездка ещё не настроена. Календарь работает.';
      $('#trip-caption').textContent = result.trip?.document.destination.name || '';
      const first = result.trip?.document.dates.options[0];
      if (!state.monthSet && first) { window.boysCalendar.setMonth(first.arrival); state.monthSet = true; }
    } catch {
      if (epoch === state.epoch) $('#links-status').textContent = 'Не удалось обновить ссылки. Показан последний сохранённый список.';
    } finally { if (epoch === state.epoch) state.refreshing = false; }
  }

  $('#add-link').addEventListener('click', () => openEditor());
  $('#link-close').addEventListener('click', () => closeEditor());
  $('#link-delete').addEventListener('click', () => saveLink(true));
  $('#link-discard').addEventListener('click', () => closeEditor(true));
  $('#link-reapply').addEventListener('click', () => {
    const editor = state.editor;
    const saved = candidates(editor.conflict).find((item) => item.id === editor.id);
    editor.trip = structuredClone(editor.conflict);
    editor.base = saved ? { title: saved.title, url: saved.url } : { title: '', url: '' };
    editor.conflict = null; $('#link-conflict').hidden = true; $('#link-error').textContent = '';
    $('#link-delete').hidden = !saved; syncEditor();
  });
  dialog.addEventListener('cancel', (event) => { event.preventDefault(); closeEditor(); });
  form.addEventListener('input', syncEditor);
  form.addEventListener('submit', (event) => { event.preventDefault(); saveLink(); });
  function open() { state.active = true; state.monthSet = false; state.epoch += 1; state.refreshing = false; refresh(); }
  document.addEventListener('boys:open', open);
  document.addEventListener('boys:close', () => {
    state.active = false; state.trip = null; state.editor = null; state.epoch += 1;
    form.reset(); dialog.close(); $('#links-list').replaceChildren(); $('#trip-caption').textContent = ''; $('#links-status').textContent = '';
  });
  window.boysLinks = { dirty, saving: () => !!state.editor?.saving };
  window.addEventListener('focus', refresh);
  setInterval(() => { if (!document.hidden) refresh(); }, 30000);
  if (window.boysCalendar?.session()) open();
})();
