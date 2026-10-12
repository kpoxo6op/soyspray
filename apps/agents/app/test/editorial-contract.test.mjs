import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, mkdtempSync, rmSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { editorialLessons } from '../src/lesson-content.js';
import { simulateScenario } from '../src/simulator.js';
import { scenarioPresentation } from '../src/scenario-data.js';
const source = JSON.parse(readFileSync(new URL('../src/content.json', import.meta.url), 'utf8'));
const html = lesson => lesson.bodyHtml.join('\n');
const decode = value => value.replace(/&(#x[0-9a-f]+|#\d+|amp|lt|gt|quot|apos);/gi, (_, entity) => {
    if (entity.startsWith('#')) return String.fromCodePoint(parseInt(entity.slice(entity[1]?.toLowerCase() === 'x' ? 2 : 1), entity[1]?.toLowerCase() === 'x' ? 16 : 10));
    return { amp: '&', lt: '<', gt: '>', quot: '"', apos: "'" }[entity.toLowerCase()];
});
const text = value => decode(value.replace(/<[^>]*>/g, '')).replace(/\s+/gu, ' ').trim();
const attrs = value => Object.fromEntries([...value.matchAll(/([^\s=/>]+)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+)))?/g)].map(match => [match[1].toLowerCase(), decode(match[2] ?? match[3] ?? match[4] ?? '')]));
const tags = value => [...value.matchAll(/<([a-z][\w:-]*)\b([^<>]*?)>/gi)].map(match => ({ name: match[1].toLowerCase(), attributes: attrs(match[2]) }));
const time = value => `${Math.floor(value / 60)}:${String(Math.floor(value % 60)).padStart(2, '0')}`;

// Contract: compiled markup cannot run code or redirect a cite. Authored bodies
// can break this while the unchanged engine and state tests remain green.
test('published lessons retain every source binding and use safe markup', () => {
    assert.deepEqual(Object.keys(editorialLessons).sort(), source.lessons.map(l => l.id).sort());
    const evidence = new Map(source.lessons.flatMap(l => l.evidence.map((n, i) => [`${l.id}:${i}`, n])));
    const cited = new Set();
    for (const lesson of Object.values(editorialLessons)) {
        const declared = new Set(lesson.notes.map(n => n.source));
        for (const note of lesson.notes) {
            const original = evidence.get(note.source);
            assert.ok(original, note.source);
            for (const field of ['start', 'end', 'label', 'frameId']) assert.deepEqual(note.evidence[field], original[field], `${note.source}: ${field}`);
            cited.add(note.source);
        }
        for (const { name, attributes: a } of tags(html(lesson))) {
            assert.ok(!['script', 'style', 'iframe', 'object', 'embed', 'base', 'video', 'audio', 'h1'].includes(name), name);
            assert.ok(!Object.keys(a).some(k => k === 'style' || k.startsWith('on')), name);
            if (a['data-lesson-source']) assert.ok(declared.has(a['data-lesson-source']), a['data-lesson-source']);
            for (const key of ['href', 'src', 'xlink:href']) if (a[key]) {
                const url = a[key].trim().replace(/[\u0000-\u0020]/g, '');
                assert.ok(!/^(?:javascript:|data:|\/\/)/i.test(url), a[key]);
                if (/^https?:/i.test(url)) {
                    assert.equal(name, 'a'); assert.equal(key, 'href'); assert.match(url, /^https:/i);
                    assert.ok(a.rel?.split(/\s+/).includes('noreferrer'), a[key]);
                }
            }
        }
    }
    assert.deepEqual([...cited].sort(), [...evidence.keys()].sort());
});

// Contract: a note's visible time and spoken name identify its real source.
// Metadata alone cannot catch a copied numeral or an incorrect displayed range.
test('source buttons and citation names describe their bound evidence', () => {
    for (const lesson of Object.values(editorialLessons)) {
        for (const match of html(lesson).matchAll(/<button\b([^>]*)>([\s\S]*?)<\/button>/g)) {
            const a = attrs(match[1]), classes = a.class?.split(/\s+/) || [];
            if (!classes.includes('cite') && !classes.includes('note__open')) continue;
            const index = lesson.notes.findIndex(n => n.source === a['data-lesson-source']);
            assert.ok(index >= 0);
            const evidence = lesson.notes[index].evidence, n = index + 1;
            const from = time(evidence.start), to = time(evidence.end), shown = evidence.label === 'SHOWN';
            const long = !shown && evidence.end - evidence.start >= 60;
            const when = shown ? `shown at ${from}` : long ? `said from ${from} to ${to}` : `said at ${from}`;
            if (classes.includes('cite')) {
                assert.equal(text(match[2]), String(n));
                assert.equal(a['aria-label'], `Note ${n}, ${when}`);
            } else {
                assert.equal(text(match[2]), `${long ? `${from}–${to}` : from} · ${shown ? 'shown' : 'said'}`);
                assert.equal(a['data-num'], String(n));
                assert.equal(a['aria-label'], shown ? `Open note ${n}, shown on screen at ${from}` : `Open note ${n} in the recording, ${when}`);
            }
        }
    }
});

// Contract: the article stays free of ingestion debris, and its next-step links
// resolve to this guide. Source-binding checks cannot detect an obsolete route.
test('lesson text excludes processing debris and links to known destinations', () => {
    const lessonIds = new Set(source.lessons.map(l => l.id)), labIds = new Set(source.lab.map(l => l.id));
    for (const lesson of Object.values(editorialLessons)) {
        assert.doesNotMatch(text(html(lesson)), /check audio|\b(?:SAID|SHOWN)\b|\b\d+\.\d+\s*[–-]\s*\d+\.\d+\b|\b[a-f0-9]{64}\b/);
        for (const { attributes: a } of tags(html(lesson))) {
            if (a.href?.startsWith('#lesson/')) assert.ok(lessonIds.has(a.href.split('/')[1]), a.href);
            if (a.href?.startsWith('#lab/')) assert.ok(labIds.has(a.href.split('/')[1]), a.href);
        }
    }
});

// Contract: visible choices match the feedback's inputs. Stale forms can grade
// the wrong answer; model tests do not own this public teaching boundary.
test('quizzes show the declared choices and retain the original answer', () => {
    for (const original of source.lessons) {
        const lesson = editorialLessons[original.id];
        const forms = [...html(lesson).matchAll(/<form\b([^>]*)>([\s\S]*?)<\/form>/g)].filter(m => attrs(m[1])['data-lesson-quiz']);
        assert.equal(forms.length, original.checks.length);
        for (const [i, form] of forms.entries()) {
            const check = lesson.checks[i];
            assert.equal(attrs(form[1])['data-lesson-quiz'], `${lesson.id}:${i}`);
            assert.equal(text(form[2].match(/<legend>([\s\S]*?)<\/legend>/)[1]), check.question);
            const choices = [...form[2].matchAll(/<label\b[^>]*>([\s\S]*?)<\/label>/g)];
            assert.deepEqual(choices.map(m => text(m[1])), check.options);
            assert.deepEqual(choices.map(m => Number(tags(m[1]).find(t => t.name === 'input').attributes.value)), check.options.map((_, n) => n));
            assert.equal(check.options[check.answer].replace(/’/g, "'"), original.checks[i].options[original.checks[i].answer].replace(/’/g, "'"));
            assert.deepEqual(choices.map(m => tags(m[1]).find(t => t.name === 'input').attributes.name), check.options.map(() => `q-${lesson.id}-${i}`));
        }
    }
});

// Contract: answer positions and lengths cannot reveal the answer. A publisher
// can regress that teaching boundary while grading and the engine stay correct.
test('checks and predictions do not reveal answers by position or length', () => {
    const checks = Object.values(editorialLessons).flatMap(l => l.checks);
    for (const index of [0, 1, 2, 3]) {
        const count = checks.filter(c => c.answer === index).length;
        assert.ok(count >= 2 && count <= 4);
    }
    const predictions = Object.values(scenarioPresentation);
    assert.ok(new Set(predictions.map(s => s.answer)).size >= 3);
    for (const c of [...checks, ...predictions.map(s => ({ options: s.choices, answer: s.answer }))]) {
        assert.ok(c.options.some((option, i) => i !== c.answer && option.length >= c.options[c.answer].length));
    }
});

// Contract: a deep link reaches its owned heading. Duplicate SVG IDs or missing
// section targets are not covered by the source-passage grouping tests.
test('authored section targets are present and IDs are unique', () => {
    const seen = new Set();
    for (const lesson of Object.values(editorialLessons)) {
        const ids = tags(html(lesson)).map(t => t.attributes.id).filter(Boolean);
        for (const id of ids) { assert.ok(!seen.has(id), id); seen.add(id); }
        for (const section of lesson.sections) if (section.target !== 'h1') assert.ok(ids.includes(section.id), section.id);
    }
});

// Contract: each control has one lesson rehearsal without duplicate timers.
// Projection tests own the trace, not where authored lessons mount it.
test('each canonical experiment has one lesson embedding', () => {
    const ids = Object.values(editorialLessons).flatMap(l => tags(html(l)).map(t => t.attributes['data-scenario']).filter(Boolean));
    assert.deepEqual(ids.sort(), source.simulator.map(s => s.id).sort());
});

// Contract: cost advice describes computed outcomes. An edited table can give
// the opposite advice while the engine's own tests remain correct.
test('the adoption cost table agrees with the scenario engine', () => {
    let checked = 0;
    for (const row of html(editorialLessons['l7-cost-and-adoption']).matchAll(/<tr>([\s\S]*?)<\/tr>/g)) {
        const id = row[1].match(/href=['"]#practice\/([^'"]+)/)?.[1];
        if (!id) continue;
        const off = simulateScenario(id, false, 4), on = simulateScenario(id, true, 4);
        const pair = text(row[1]).match(id === 's3-review-backlog' ? /queue falls from (\d+) to (\d+)/ : /(\d+) → (\d+)/);
        assert.deepEqual(pair.slice(1).map(Number), id === 's3-review-backlog' ? [off.metrics.reviewQueue, on.metrics.reviewQueue] : [off.metrics.cost, on.metrics.cost]);
        checked++;
    }
    assert.equal(checked, source.simulator.length);
});

// Contract: rehearsal text matches actual execution and prompts retain the
// answers' meaning. Lab confinement and state parsing do not own public copy.
test('rehearsal lines match the lab and adoption prompts remain compatible', () => {
    const temporary = mkdtempSync('/var/tmp/agents-editorial-contract-');
    const root = `${temporary}/lab`, script = fileURLToPath(new URL('../src/lab.py', import.meta.url));
    try {
        const output = execFileSync('python3', ['-I', script, 'run', '--root', root], { cwd: temporary, encoding: 'utf8', timeout: 30000 });
        for (const lesson of Object.values(editorialLessons)) assert.ok(output.split('\n').includes(lesson.lab.outputLine), lesson.lab.outputLine);
        execFileSync('python3', ['-I', script, 'verify', '--root', root], { cwd: temporary, timeout: 30000 });
        execFileSync('python3', ['-I', script, 'cleanup', '--root', root], { cwd: temporary, timeout: 30000 });
    } finally { rmSync(temporary, { recursive: true, force: true }); }
    const body = html(editorialLessons['l7-cost-and-adoption']);
    const prompts = [...body.matchAll(/<label\b([^>]*)>([\s\S]*?)<\/label>/g)].filter(m => attrs(m[1]).class?.split(/\s+/).includes('adopt__prompt'));
    assert.deepEqual(prompts.map(m => text(m[2].replace(/<span\b[^>]*class=['"]adopt__num['"][^>]*>[\s\S]*?<\/span>/g, ''))), source.adoptionPrompts);
    assert.deepEqual(tags(body).filter(t => t.name === 'textarea').map(t => t.attributes['data-adoption']), source.adoptionPrompts.map((_, i) => String(i)));
});
