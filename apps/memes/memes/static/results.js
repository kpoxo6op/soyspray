const pct = x => x === null ? 'n/a' : (100*x).toFixed(1)+'%';
function table(title, arms) {
  const heading = document.createElement('h2'); heading.textContent = title;
  const table = document.createElement('table');
  const labels = ['Group','Like / Dislike','Skip','Like rate (95%)'];
  const tr = table.insertRow(); labels.forEach(label => {const th = document.createElement('th'); th.textContent = label; tr.append(th);});
  for (const arm of ['rec','random']) {
    const s = arms[arm];
    const row = table.insertRow();
    [arm, `${s.likes} / ${s.dislikes}`, String(s.skips), `${pct(s.like_rate)}${s.wilson95 ? ' ('+s.wilson95.map(pct).join('–')+')' : ''}`].forEach(text => {row.insertCell().textContent = text;});
  }
  document.querySelector('#stats').append(heading,table);
}
fetch('/api/results').then(r => r.json()).then(data => {
  document.querySelector('#verdict').textContent = data.verdict;
  table('All picks', data.arms); table('First half', data.halves[0]); table('Second half', data.halves[1]);
  const note = document.createElement('p'); note.className = 'note';
  note.textContent = `Warm-up: ${data.warmup.likes} likes, ${data.warmup.dislikes} dislikes, ${data.warmup.skips} skips. Random-pick score AUC: ${data.auc === null ? 'n/a' : data.auc.toFixed(3)}.${data.excluded ? ' This tester is excluded from group analysis.' : ''}`;
  document.querySelector('#stats').append(note);
}).catch(() => {document.querySelector('#verdict').textContent = 'Results could not load. Reload to try again.';});
