import { simulateScenario } from "./simulator.js";
const $ = (s) => document.querySelector(s);
const esc = (v) =>
    String(v ?? "").replace(
        /[&<>"']/g,
        (c) =>
            ({
                "&": "&amp;",
                "<": "&lt;",
                ">": "&gt;",
                '"': "&quot;",
                "'": "&#39;",
            })[c],
    );
const paragraphs = (values) =>
    (values || []).map((p) => `<p>${esc(p)}</p>`).join("");
const time = (seconds) =>
    `${Math.floor(seconds / 60)
        .toString()
        .padStart(2, "0")}:${Math.floor(seconds % 60)
        .toString()
        .padStart(2, "0")}`;
const playName = (seconds) =>
    `Play from ${Math.floor(seconds / 60)} minutes ${Math.floor(seconds % 60)} seconds`;
const stamp = (seconds) =>
    `<button class="time-button" data-seek="${Number(seconds)}" aria-label="${time(seconds)} — ${playName(seconds)}">${time(seconds)} <span aria-hidden="true">↗</span></button>`;
const tags = {
    SAID: ["◷", "said"],
    SHOWN: ["▣", "shown"],
    "OUR READ": ["↗", "read"],
    DOCS: ["⌑", "docs"],
    UNCLEAR: ["?", "unclear"],
};
const tag = (label) =>
    `<span class="tag ${tags[label]?.[1] || "unclear"}"><span aria-hidden="true">${tags[label]?.[0] || "?"}</span>${esc(label)}</span>`;
const storageKey = "soyspray-agents:v1";
let saved;
try {
    saved = JSON.parse(localStorage.getItem(storageKey) || "{}");
} catch {
    saved = {};
}
let state = {
    depth: "practitioner",
    theme: "auto",
    descriptions: false,
    completed: [],
    adoption: {},
    ...saved,
};
function save() {
    try {
        localStorage.setItem(storageKey, JSON.stringify(state));
    } catch {
        /* Private mode can deny storage. */
    }
}
function theme() {
    document.documentElement.dataset.theme = state.theme;
    $("#theme").value = state.theme;
    $("#depth").value = state.depth;
}
theme();
let content,
    pack,
    packBase = "",
    packError = "",
    route = "",
    follow = true,
    transcriptMode = "corrected",
    scenarioId,
    simResult,
    simStep = 0,
    simTimer;
let narrationCue = null,
    lastTime = 0;
const narrated = new Set();
const video = document.createElement("video");
video.controls = true;
video.preload = "metadata";
video.playsInline = true;
video.setAttribute("aria-label", "Replay the full talk");
const dock = document.createElement("div");
dock.hidden = true;
document.body.append(dock);
dock.append(video);
const narration = new Audio();
function status() {
    return pack
        ? '<div class="evidence-status">Full replay, transcript and frame evidence available. Machine transcription; uncertainties remain visible.</div>'
        : `<div class="evidence-status unavailable" role="status">Evidence pack unavailable. Original teaching content is still readable. ${esc(packError)} <a href="https://x.com/i/status/2108938132934533123" rel="noreferrer" target="_blank">Open source post</a></div>`;
}
function pageTitle(kicker, title, text) {
    return `<div class="page-title"><p class="eyebrow">${esc(kicker)}</p><h1>${esc(title)}</h1><p class="lead">${esc(text)}</p></div>`;
}
function evidenceCard(e, index) {
    const segment = pack?.segments?.find(
        (s) => s.end > e.start && s.start < e.end,
    );
    const frameIndex = pack?.frames?.findIndex((f) => f.id === e.frameId) ?? -1;
    const source =
        e.label === "SHOWN"
            ? frameIndex >= 0
                ? `<button data-frame="${frameIndex}">Inspect the cited frame · ${time(pack.frames[frameIndex].start)}</button>`
                : `<p class="muted">Cited frame unavailable with this evidence pack.</p>`
            : segment
              ? `<details><summary>Read source wording</summary><p>${esc(segment.corrected || segment.raw)}</p><small>Machine transcript · ${time(segment.start)}–${time(segment.end)}</small></details>`
              : "";
    return `<article class="evidence-card">${tag(e.label)} ${stamp(e.start)}<p>${esc(e.paraphrase)}</p><small>${esc(e.why)}</small>${source}</article>`;
}
function lessonCard(l, i) {
    return `<article class="card"><span class="number">${String(i + 1).padStart(2, "0")} / ${esc(l.minutes)} MIN</span><h3>${esc(l.title)}</h3><p>${esc(l.summary)}</p><a class="action" href="#lesson/${encodeURIComponent(l.id)}">Explore lesson ${state.completed.includes(l.id) ? "✓" : "↗"}</a></article>`;
}
function startPage() {
    const summary = Array.isArray(content.startSummary)
        ? content.startSummary.join(" ")
        : content.startSummary;
    const opening =
        summary.match(/^[\s\S]*?[.!?](?:\s|$)[\s\S]*?[.!?](?:\s|$)/)?.[0] ||
        summary;
    return `<section class="hero"><div><p class="eyebrow">Watch · test · apply</p><h1>${esc(content.title)}</h1><p class="lead">${esc(content.subtitle)}</p>${paragraphs([opening])}<div class="actions"><a class="action primary-action" href="#lessons">Start the lessons ↗</a><a class="action" href="#talk">Watch the full talk · 56:52</a></div><small>Lauren Tan · source recording via <a href="https://x.com/i/status/2108938132934533123" rel="noreferrer" target="_blank">X</a>. Recording date unknown.</small></div><aside class="panel"><p class="eyebrow">Your route through the topic</p><h2>From claims to controls</h2><ol><li>Locate the evidence in the replay.</li><li>Predict what happens without a control.</li><li>Run the model and compare.</li><li>Rehearse safely in the offline lab.</li><li>Write your adoption decision.</li></ol><small>Practitioner is the default. Basics and Deep add explanations; evidence is always visible.</small></aside></section>${status()}<details><summary>About this recording and study guide</summary>${paragraphs([summary])}</details><h2>What you’ll be able to do</h2>${paragraphs(Array.isArray(content.learningAim) ? content.learningAim : [content.learningAim])}<div class="legend">${Object.keys(tags).map(tag).join("")}</div><p class="muted">Said and Shown point to the recording. Our Read is an interpretation. Docs are dated external references. Unclear stays unresolved.</p><h2>The learning path</h2><div class="grid">${content.lessons.map(lessonCard).join("")}</div>`;
}
function talkPage() {
    return `${pageTitle("Source recording", "Watch with the evidence beside you", "Every chapter covers part of the full recording. Timestamp buttons seek the same player; playback starts only when you choose.")} ${status()}<div class="talk-layout"><section aria-label="Replay and transcript"><div id="video-slot" class="video-shell"></div><div class="player-tools"><label><input id="descriptions" type="checkbox" ${state.descriptions ? "checked" : ""}> Spoken visual descriptions</label><label>Transcript <select id="transcript-mode"><option value="corrected">Corrected</option><option value="raw">Raw ASR</option><option value="diff">Corrections and reasons</option></select></label><button id="resume-follow">${follow ? "Following playback" : "Resume following"}</button></div><div id="description-cue" class="description-text" aria-live="polite" hidden></div><p class="muted">Machine transcript · ${esc(pack?.captionStatus || "unreviewed")}. Playback and captions may contain transcription errors.</p><div id="transcript" class="transcript" tabindex="0" aria-label="Timestamped transcript">${transcriptHTML()}</div><div class="actions">${pack ? `<a class="action" href="${packBase}/transcript.vtt" download>Download captions</a><a class="action" href="${packBase}/transcript.txt" download>Download transcript</a>` : ""}</div></section><aside><h2>Full time map</h2><div class="chapters">${content.talkChapters.map((c) => `<button class="chapter-button" data-seek="${c.start}"><small>${time(c.start)}</small><span>${esc(c.title)}</span></button>`).join("")}</div><p class="muted">Opening preview included. Chapter summaries are original paraphrases.</p></aside></div><h2>Keyframes</h2><p class="muted">Real frames from scene changes and 20-second intervals. Enlarge a frame to inspect its OCR and visual description.</p><div class="filmstrip">${(pack?.frames || []).map((f, i) => `<article class="frame-card"><button data-frame="${i}" aria-label="${time(f.start)} · ${esc(f.kind)} — Inspect frame"><img loading="lazy" width="1924" height="1080" src="${packBase}/${esc(f.path)}" alt="${esc(f.description || `Frame at ${time(f.start)}; inspect for OCR`)}"><small>${time(f.start)} · ${esc(f.kind)}</small></button></article>`).join("") || '<p class="empty">Frames are unavailable while the evidence pack is offline.</p>'}</div>`;
}
function transcriptHTML() {
    if (!pack)
        return '<p class="empty">The full transcript is in the private evidence pack. Use the source link or read the lessons while it is unavailable.</p>';
    if (transcriptMode === "diff")
        return (
            (pack.corrections || [])
                .map(
                    (c) =>
                        `<article class="transcript-row">${stamp(c.start)}<div><del>${esc(c.raw)}</del><p>${esc(c.corrected)}</p><small>${esc(c.reason)} · ${esc(c.reviewStatus)} · ${esc(c.evidenceFrameId || "no frame evidence")}</small></div></article>`,
                )
                .join("") ||
            '<p class="empty">No reviewed corrections recorded for this version.</p>'
        );
    const rows = pack.segments.map((s) => ({
        start: s.start,
        html: `<article class="transcript-row" data-start="${s.start}" data-end="${s.end}">${stamp(s.start)}<div><p>${esc(transcriptMode === "raw" ? s.raw : s.corrected || s.raw)}</p>${s.uncertain ? `<small>${tag("UNCLEAR")} Low-confidence machine wording; check the audio.</small>` : ""}</div></article>`,
    }));
    for (const cue of pack.narrationCues || []) {
        rows.push({
            start: cue.start,
            html: `<aside class="description-row">${tag("SHOWN")} ${stamp(cue.start)}<p>Visual description: ${esc(cue.text)}</p></aside>`,
        });
    }
    return rows
        .sort((a, b) => a.start - b.start)
        .map((r) => r.html)
        .join("");
}
function checksHTML(checks, prefix) {
    return (checks || [])
        .map(
            (c, i) =>
                `<form class="check" data-check="${prefix}:${i}"><fieldset><legend>${esc(c.question)}</legend>${(c.options || c.choices).map((o, j) => `<label><input type="radio" name="answer" value="${j}" required><span>${esc(o)}</span></label>`).join("")}</fieldset><button type="submit">Check my reasoning</button><p class="feedback" role="status"></p></form>`,
        )
        .join("");
}
function docsHTML(docs) {
    return (docs || [])
        .filter(
            (d) =>
                d.date !== "pending-capture" && d.relation !== "unclassified",
        )
        .map(
            (d) =>
                `<p>${tag("DOCS")} <a href="${esc(d.url)}" target="_blank" rel="noreferrer">${esc(d.title)}</a><br><small>${esc(d.date)} · ${esc(d.relation)} · ${esc(d.note)}</small></p>`,
        )
        .join("");
}
function lessonPage(id) {
    const l = content.lessons.find((l) => l.id === id);
    if (!l)
        return '<h1>Lesson unavailable</h1><a href="#lessons">Return to lessons</a>';
    const index = content.lessons.indexOf(l);
    return `${pageTitle(`Lesson ${index + 1} · ${l.minutes} minutes`, l.title, l.question)}<div class="lesson-layout"><article>${tag("OUR READ")}${paragraphs(l.practitioner)}<details class="layer" ${state.depth === "basics" || state.depth === "deep" ? "open" : ""}><summary>Basics · the terms behind the workflow</summary>${paragraphs(l.basics)}</details><details class="layer" ${state.depth === "deep" ? "open" : ""}><summary>Deep · controls and limits</summary>${paragraphs(l.deep)}</details><h2>Where the analogy breaks</h2><ul>${l.analogyBreaks.map((p) => `<li>${esc(p)}</li>`).join("")}</ul><div class="actions">${l.scenarioId ? `<a class="action primary-action" href="#simulator/${l.scenarioId}">Predict, then run ↗</a>` : ""}${l.labStep ? `<a class="action" href="#lab/${l.labStep}">Rehearse in the lab ↗</a>` : ""}</div><h2>Retrieve it from memory</h2><p class="muted">Feedback for understanding. No scores.</p>${checksHTML(l.checks, l.id)}<h2>Dated references</h2>${docsHTML(l.docs) || '<p class="muted">Document comparisons await evidence classification. The recording remains the source for this lesson.</p>'}<button data-complete="${l.id}" aria-pressed="${state.completed.includes(l.id)}">${state.completed.includes(l.id) ? "Marked explored ✓" : "Mark lesson explored"}</button><div class="actions">${content.lessons[index + 1] ? `<a class="action" href="#lesson/${content.lessons[index + 1].id}">Next: ${esc(content.lessons[index + 1].title)} ↗</a>` : '<a class="action" href="#lab">Move to the lab ↗</a>'}</div></article><aside class="evidence-rail" aria-label="Recording evidence"><h2>Back to the source</h2>${l.evidence.map(evidenceCard).join("")}</aside></div>`;
}
function simulatorPage(id) {
    const scenario =
        content.simulator.find((s) => s.id === id) || content.simulator[0];
    scenarioId = scenario.id;
    const controlNames = {
        "s1-shared-vs-isolated": [
            "Workspace",
            "Shared tree",
            "Separate worktrees",
        ],
        "s2-plausible-vs-verified": [
            "Verification",
            "Accept reports",
            "Run the symptom probe",
        ],
        "s3-review-backlog": ["Hard checks", "Off", "Reject scripted bad PRs"],
        "s4-naive-retry": ["Retry", "Naive delivery", "Atomic task claim"],
        "s5-architecture-gate": [
            "Boundary enforcement",
            "Soft guidance",
            "Hard CI check",
        ],
    };
    const names = controlNames[scenarioId];
    return `${pageTitle("Predict · run · compare", "The coordination simulator", "A deterministic teaching model. Every bad outcome is scripted, never a measured probability or a prediction of agent performance.")}<label for="scenario">Choose a scenario</label><select id="scenario">${content.simulator.map((s) => `<option value="${s.id}" ${s.id === scenarioId ? "selected" : ""}>${esc(s.title)}</option>`).join("")}</select>${checksHTML([{ ...scenario, options: scenario.choices }], scenario.id)}<div class="panel"><h2>Change one control</h2><div class="sim-controls"><label>${names[0]}<select id="scenario-control"><option value="false">${names[1]}</option><option value="true">${names[2]}</option></select></label>${scenarioId === "s3-review-backlog" ? '<label>Agents<select id="scenario-agents"><option value="4">Four agents · 12 PRs</option><option value="1">One agent · 3 PRs</option></select></label>' : ""}</div><div class="actions"><button id="sim-run">Run this model</button><button id="sim-baseline">Compare with control enabled</button><button id="sim-next" disabled>Next event</button><button id="sim-finish" disabled>Show full event log</button></div><p class="muted">Fixed schedule · seed ${scenario.parameters.seed}. Ticks and cost units are abstract. A worktree isolates edits; competing changes still require integration review.</p></div><section id="sim-output" aria-label="Simulation results"></section><p id="sim-live" class="sr-only" aria-live="polite" aria-atomic="true"></p>`;
}
function simOutput(finish = false) {
    if (!simResult) return;
    if (finish) simStep = simResult.events.length;
    const shown = simResult.events.slice(0, simStep),
        m = simResult.metrics;
    $("#sim-output").innerHTML =
        `<h2>${simStep === simResult.events.length ? "Completed model" : "Event replay"}</h2><div class="run-visual">${simResult.tasks.map((t) => `<span class="task-chip ${t.state}">${esc(t.id)} · ${esc(t.state)}</span>`).join("")}</div><div class="metrics">${Object.entries(
            m,
        )
            .map(
                ([k, v]) =>
                    `<div class="metric"><strong>${v}</strong><span>${esc({ merged: "Merged changes", wasted: "Wasted attempts", conflicts: "Conflicts", defects: "Defects on main", reviewQueue: "Peak review queue", detectionLatency: "Detection ticks", cost: "Abstract cost units" }[k])}</span></div>`,
            )
            .join(
                "",
            )}</div><p class="muted">Metrics show the complete run. The event replay below reveals the sequence.</p><div class="table-scroll"><table class="event-table"><caption class="sr-only">Deterministic event log</caption><thead><tr><th>Tick</th><th>Task</th><th>Event</th><th>What happened</th></tr></thead><tbody>${shown.map((e) => `<tr><td>${e.tick}</td><td>${esc(e.task)}</td><td>${esc(e.kind)}</td><td>${esc(e.message)}</td></tr>`).join("")}</tbody></table></div>`;
    $("#sim-next").disabled = simStep >= simResult.events.length;
    $("#sim-finish").disabled = simStep >= simResult.events.length;
    $("#sim-live").textContent = shown.length
        ? `Event ${simStep} of ${simResult.events.length}. ${shown.at(-1).message}`
        : "Model ready. Advance the first event.";
}
function labPage(id) {
    return `${pageTitle("Offline · disposable · no credentials", "Rehearse the controls", "Deterministic stub agents operate only in an owned scratch repository. No tokens, remotes, cluster changes or downloaded executables.")}<div class="panel"><h2>Run the complete safe lab</h2><p>Save the script, inspect it, then run it with Python 3 and Git. It refuses an existing foreign directory, symlinks and repositories with remotes. Repeated runs use the same owned lab root.</p><a class="action" href="lab.py" download>Download the readable lab script</a><pre><code>python3 lab.py run --root ~/agent-lab
python3 lab.py verify --root ~/agent-lab
python3 lab.py cleanup --root ~/agent-lab</code></pre><button data-copy="python3 lab.py run --root ~/agent-lab">Copy run command</button><p class="muted">Only the downloaded script executes the steps below. A real-model rerun is optional and requires a separate uncredentialed VM or container; it is never started by this site.</p></div><h2>Offline practice steps</h2><div class="grid">${content.lab.map((l, i) => `<article class="card" id="${l.id}"><span class="number">STEP ${i + 1} · ${l.minutes} MIN</span><h3>${esc(l.title)}</h3><p>${esc(l.goal)}</p>${stamp(l.evidenceStart)}<details ${id === l.id ? "open" : ""}><summary>Plan, expected result and transfer</summary><p>${esc(l.expected)}</p><h4>Failure to rehearse</h4><p>${esc(l.failureVariant)}</p><h4>Transfer to Soyspray</h4><p>${esc(l.transfer)}</p></details></article>`).join("")}</div><h2>Your adoption decision</h2><p class="muted">This browser only. Export a Markdown decision sheet when you’re ready.</p><form id="adoption-form">${content.adoptionPrompts.map((p, i) => `<p><label for="adoption-${i}">${esc(p)}</label><textarea id="adoption-${i}" data-adoption="${i}">${esc(state.adoption[i] || "")}</textarea></p>`).join("")}</form><button id="adoption-export">Export adoption decision</button>`;
}
function ledgerPage() {
    const claims = content.lessons.flatMap((l) =>
        l.evidence.map((e) => ({ ...e, lesson: l })),
    );
    return `${pageTitle("Traceability · uncertainty · provenance", "The evidence ledger", "Every lesson points back to the recording. Interpretations and current documentation remain visibly separate.")} ${status()}<label for="ledger-filter">Filter claims</label><input id="ledger-filter" type="search" placeholder="Search a claim or lesson"><h2>Recording claims</h2><div id="claim-list">${claims.map((e) => `<article class="ledger-row" data-claim="${esc((e.paraphrase + " " + e.lesson.title).toLowerCase())}">${tag(e.label)} ${stamp(e.start)}<h3>${esc(e.paraphrase)}</h3><small>${time(e.start)}–${time(e.end)} · <a href="#lesson/${e.lesson.id}">${esc(e.lesson.title)}</a></small><p>${esc(e.why)}</p></article>`).join("")}</div><h2>Glossary</h2><div class="grid">${content.glossary.map((g) => `<article class="card"><h3>${esc(g.term)}</h3><p>${esc(g.plain)}</p><p>${esc(g.practitioner)}</p><details><summary>Deep</summary><p>${esc(g.deep)}</p></details>${g.start != null ? stamp(g.start) : ""}</article>`).join("")}</div><h2>Corrections and gaps</h2>${paragraphs(content.contentCautions)}${pack ? `<details><summary>Pack provenance and coverage</summary><pre>${esc(JSON.stringify(pack.provenance, null, 2))}</pre>${paragraphs((pack.gaps || []).map((g) => `${time(g.start)}–${time(g.end)} · ${g.kind}: ${g.note}`))}</details>` : ""}<h2>Accessibility checks</h2><p id="accessibility-status">Designed toward WCAG 2.2 Level AA. Validation is in progress; no formal conformance claim.</p><h2>Your local state</h2><div class="actions"><button id="state-export">Export settings and progress</button><label class="action">Import state<input id="state-import" type="file" accept="application/json" hidden></label><button id="state-reset">Reset local state</button></div><p id="state-message" role="status"></p>`;
}
function render() {
    clearInterval(simTimer);
    simTimer = null;
    dock.append(video);
    dock.hidden = true;
    const [area, id] = location.hash.slice(1).split("/");
    route = area || "start";
    $(".primary")
        .querySelectorAll("a")
        .forEach((a) => {
            const active =
                a.hash === `#${route === "lesson" ? "lessons" : route}`;
            if (active) a.setAttribute("aria-current", "page");
            else a.removeAttribute("aria-current");
        });
    const views = {
        start: startPage,
        talk: talkPage,
        lessons: () =>
            `${pageTitle("The learning path", "Work from evidence to a safe workflow", "Selective lessons, each grounded in this recording. Use the Talk time map to explore every part of the video.")}<h2>Choose a lesson</h2><div class="grid">${content.lessons.map(lessonCard).join("")}</div>`,
        lesson: () => lessonPage(decodeURIComponent(id || "")),
        simulator: () => simulatorPage(id),
        lab: () => labPage(id),
        ledger: ledgerPage,
    };
    $("#main").innerHTML = (views[route] || startPage)();
    if (route === "talk") {
        $("#video-slot").append(video);
        $("#transcript-mode").value = transcriptMode;
        $("#transcript").addEventListener("wheel", () => pauseFollow(), {
            passive: true,
        });
        $("#transcript").addEventListener("touchstart", () => pauseFollow(), {
            passive: true,
        });
        $("#transcript").addEventListener("keydown", (e) => {
            if (
                [
                    "PageDown",
                    "PageUp",
                    "ArrowDown",
                    "ArrowUp",
                    "Home",
                    "End",
                ].includes(e.key)
            )
                pauseFollow();
        });
        highlight();
    }
    if (id && route === "lab") document.getElementById(id)?.scrollIntoView();
    document.title = `${route === "lesson" ? content.lessons.find((l) => l.id === id)?.title || "Lesson" : route[0].toUpperCase() + route.slice(1)} · Agent workshop`;
}
function pauseFollow() {
    follow = false;
    if ($("#resume-follow"))
        $("#resume-follow").textContent = "Resume following";
}
function highlight() {
    if (route !== "talk") return;
    const rows = [...document.querySelectorAll(".transcript-row[data-start]")];
    const row = rows.find(
        (r) =>
            Number(r.dataset.start) <= video.currentTime &&
            Number(r.dataset.end) > video.currentTime,
    );
    const old = $(".transcript-row.active");
    if (old === row) return;
    old?.classList.remove("active");
    row?.classList.add("active");
    if (row && follow)
        $("#transcript").scrollTop = Math.max(
            0,
            row.offsetTop - $("#transcript").offsetTop - 80,
        );
}
function seek(seconds) {
    for (const dialog of document.querySelectorAll("dialog[open]"))
        dialog.close();
    const t = Math.max(0, Math.min(3412.1, Number(seconds)));
    narration.pause();
    narrationCue = null;
    narrated.clear();
    const url = new URL(location.href);
    url.searchParams.set("t", t.toFixed(1));
    url.hash = "talk";
    history.pushState({}, "", url);
    if (route !== "talk") render();
    video.currentTime = t;
    lastTime = t;
    follow = true;
    highlight();
    $("#mini-player").hidden = false;
}
async function describe(cue) {
    narrationCue = cue;
    narrated.add(cue.id);
    const wasPlaying = !video.paused;
    video.pause();
    const live = $("#description-announcement");
    if (live) {
        live.hidden = false;
        live.textContent = cue.text;
    }
    const inline = $("#description-cue");
    if (inline) {
        inline.hidden = false;
        inline.textContent = cue.text;
    }
    const finish = () => {
        narrationCue = null;
        if (wasPlaying) video.play().catch(() => {});
    };
    if (cue.audio) {
        narration.src = `${packBase}/${cue.audio}`;
        narration.onended = finish;
        narration.onerror = finish;
        try {
            await narration.play();
        } catch {
            finish();
        }
    } else {
        if (live)
            live.textContent = `Visual description: ${cue.text}. Resume replay when ready.`;
        narrationCue = null;
    }
}
video.addEventListener("timeupdate", () => {
    $("#mini-time").textContent = time(video.currentTime);
    highlight();
    if (state.descriptions && !video.paused && !narrationCue) {
        const cue = pack?.narrationCues?.find(
            (c) =>
                !narrated.has(c.id) &&
                lastTime <= c.start &&
                video.currentTime >= c.start &&
                video.currentTime - c.start < 1,
        );
        if (cue) describe(cue);
    }
    lastTime = video.currentTime;
});
video.addEventListener("seeking", () => {
    if (Math.abs(video.currentTime - lastTime) > 2) {
        narrated.clear();
        lastTime = video.currentTime;
        narration.pause();
        narrationCue = null;
    }
});
video.addEventListener("play", () => {
    $("#mini-play").textContent = "Pause";
    $("#mini-player").hidden = false;
});
video.addEventListener("pause", () => {
    $("#mini-play").textContent = "Play";
});
$("#mini-play").onclick = () =>
    video.paused ? video.play().catch(() => {}) : video.pause();
$("#mini-hide").onclick = () => {
    $("#mini-player").hidden = true;
};
document.addEventListener("click", async (e) => {
    const target = e.target.closest("button,a");
    if (!target) return;
    if (target.dataset.seek != null) {
        seek(target.dataset.seek);
        return;
    }
    if (target.dataset.frame != null) {
        const f = pack.frames[Number(target.dataset.frame)];
        $("#frame-title").textContent = `Frame at ${time(f.start)}`;
        $("#frame-detail").innerHTML =
            `<img width="1924" height="1080" src="${packBase}/${esc(f.path)}" alt="${esc(f.description || "Unreviewed frame; OCR text follows")}"><p>${esc(f.description)}</p>${stamp(f.start)}<h3>Machine OCR</h3><pre>${esc(f.ocr)}</pre><small>Machine OCR may contain errors. The bottom caption band is excluded from the searchable OCR; its words are not independent evidence. Frame hash: ${esc(f.sha256)}</small>`;
        $("#frame-dialog").showModal();
    }
    if (target.hasAttribute("data-close")) target.closest("dialog").close();
    if (target.dataset.complete) {
        const id = target.dataset.complete;
        state.completed = state.completed.includes(id)
            ? state.completed.filter((x) => x !== id)
            : [...state.completed, id];
        save();
        target.setAttribute("aria-pressed", state.completed.includes(id));
        target.textContent = state.completed.includes(id)
            ? "Marked explored ✓"
            : "Mark lesson explored";
    }
    if (target.dataset.copy) {
        try {
            await navigator.clipboard.writeText(target.dataset.copy);
            target.textContent = "Copied ✓";
        } catch {
            target.textContent = "Copy unavailable; select the command above";
        }
    }
    if (target.id === "resume-follow") {
        follow = true;
        target.textContent = "Following playback";
        highlight();
    }
    if (target.id === "sim-run" || target.id === "sim-baseline") {
        clearInterval(simTimer);
        const controlled =
            target.id === "sim-baseline" ||
            $("#scenario-control").value === "true";
        simResult = simulateScenario(
            scenarioId,
            controlled,
            Number($("#scenario-agents")?.value || 4),
        );
        simStep = 0;
        simOutput();
        $("#sim-next").disabled = false;
        $("#sim-finish").disabled = false;
        if (!matchMedia("(prefers-reduced-motion: reduce)").matches)
            simTimer = setInterval(() => {
                simStep++;
                simOutput();
                if (simStep >= simResult.events.length) clearInterval(simTimer);
            }, 1200);
    }
    if (target.id === "sim-next") {
        clearInterval(simTimer);
        simStep++;
        simOutput();
    }
    if (target.id === "sim-finish") {
        clearInterval(simTimer);
        simOutput(true);
    }
    if (target.id === "adoption-export") {
        const text = `# Agent adoption decision\n\n${content.adoptionPrompts.map((p, i) => `## ${p}\n\n${state.adoption[i] || "Not yet decided."}`).join("\n\n")}\n`;
        download("agent-adoption.md", text, "text/markdown");
    }
    if (target.id === "state-export")
        download(
            "agent-workshop-state.json",
            JSON.stringify({ version: 1, state }, null, 2),
            "application/json",
        );
    if (target.id === "state-reset") {
        state = {
            depth: "practitioner",
            theme: "auto",
            descriptions: false,
            completed: [],
            adoption: {},
        };
        save();
        theme();
        render();
        $("#state-message").textContent = "Local state reset.";
    }
});
document.addEventListener("submit", (e) => {
    if (!e.target.matches("[data-check]")) return;
    e.preventDefault();
    const [id, index] = e.target.dataset.check.split(":");
    const c =
        content.lessons.find((l) => l.id === id)?.checks[Number(index)] ||
        content.simulator.find((s) => s.id === id);
    const value = Number(new FormData(e.target).get("answer"));
    e.target.querySelector(".feedback").textContent =
        `${value === c.answer ? "That matches the reasoning." : "Compare your prediction with the explanation."} ${c.explanation}`;
});
document.addEventListener("change", async (e) => {
    if (e.target.id === "depth") {
        state.depth = e.target.value;
        save();
        render();
    }
    if (e.target.id === "theme") {
        state.theme = e.target.value;
        save();
        theme();
    }
    if (e.target.id === "transcript-mode") {
        transcriptMode = e.target.value;
        $("#transcript").innerHTML = transcriptHTML();
        highlight();
    }
    if (e.target.id === "descriptions") {
        state.descriptions = e.target.checked;
        save();
        if (!state.descriptions) {
            narration.pause();
            narrationCue = null;
        }
    }
    if (e.target.id === "scenario")
        location.hash = `simulator/${e.target.value}`;
    if (e.target.id === "state-import") {
        try {
            const imported = JSON.parse(await e.target.files[0].text());
            if (
                imported.version !== 1 ||
                !["basics", "practitioner", "deep"].includes(
                    imported.state.depth,
                ) ||
                !["auto", "light", "dark"].includes(imported.state.theme) ||
                !Array.isArray(imported.state.completed) ||
                !imported.state.adoption ||
                Array.isArray(imported.state.adoption) ||
                typeof imported.state.adoption !== "object" ||
                !Object.values(imported.state.adoption).every(
                    (v) => typeof v === "string" && v.length <= 10000,
                ) ||
                !imported.state.completed.every((v) =>
                    content.lessons.some((l) => l.id === v),
                )
            )
                throw Error("Invalid state format");
            state = { ...state, ...imported.state };
            save();
            theme();
            render();
            $("#state-message").textContent = "Imported local state.";
        } catch (err) {
            $("#state-message").textContent = err.message;
        }
    }
});
document.addEventListener("input", (e) => {
    if (e.target.dataset.adoption != null) {
        state.adoption[e.target.dataset.adoption] = e.target.value;
        save();
    }
    if (e.target.id === "ledger-filter")
        document.querySelectorAll("[data-claim]").forEach((el) => {
            el.hidden = !el.dataset.claim.includes(
                e.target.value.toLowerCase(),
            );
        });
});
function download(name, text, mime) {
    const url = URL.createObjectURL(new Blob([text], { type: mime }));
    const a = document.createElement("a");
    a.href = url;
    a.download = name;
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
}
function openSearch() {
    $("#search-dialog").showModal();
    $("#search-query").focus();
}
$("#search-open").onclick = openSearch;
document.addEventListener("keydown", (e) => {
    if (
        e.key === "/" &&
        !["INPUT", "TEXTAREA", "SELECT"].includes(
            document.activeElement.tagName,
        )
    ) {
        e.preventDefault();
        openSearch();
    }
});
$("#search-query").addEventListener("input", (e) => {
    const q = e.target.value.toLowerCase().trim();
    if (q.length < 2) {
        $("#search-results").textContent = "Type at least two characters.";
        return;
    }
    const groups = [
        [
            "Lessons",
            content.lessons
                .filter((l) =>
                    JSON.stringify([l.title, l.practitioner, l.basics, l.deep])
                        .toLowerCase()
                        .includes(q),
                )
                .map(
                    (l) =>
                        `<a class="search-result action" href="#lesson/${l.id}">${esc(l.title)}</a>`,
                ),
        ],
        [
            "Transcript (corrected and raw)",
            (pack?.segments || [])
                .filter((s) =>
                    `${s.raw} ${s.corrected}`.toLowerCase().includes(q),
                )
                .slice(0, 30)
                .map(
                    (s) =>
                        `<button class="search-result" data-seek="${s.start}">${time(s.start)}<small>${esc(s.corrected || s.raw)}</small></button>`,
                ),
        ],
        [
            "Frame OCR",
            (pack?.frames || [])
                .map((f, i) => ({ ...f, i }))
                .filter((f) => f.ocr?.toLowerCase().includes(q))
                .slice(0, 20)
                .map(
                    (f) =>
                        `<button class="search-result" data-frame="${f.i}">Frame ${time(f.start)}<small>${esc(f.ocr.slice(0, 160))}</small></button>`,
                ),
        ],
        [
            "Glossary",
            content.glossary
                .filter((g) => JSON.stringify(g).toLowerCase().includes(q))
                .map(
                    (g) =>
                        `<a class="search-result action" href="#ledger">${esc(g.term)}<small>${esc(g.plain)}</small></a>`,
                ),
        ],
    ];
    $("#search-results").innerHTML = groups
        .map(
            ([title, results]) =>
                `<section class="search-group"><h3>${title} · ${results.length}</h3>${results.join("") || '<p class="muted">No matches.</p>'}</section>`,
        )
        .join("");
});
$("#search-dialog").addEventListener("click", (e) => {
    if (e.target.closest("[data-seek],a")) $("#search-dialog").close();
});
window.addEventListener("hashchange", () => {
    render();
    $("#main").focus({ preventScroll: true });
    window.scrollTo(0, 0);
});
window.addEventListener("popstate", render);
async function boot() {
    try {
        const response = await fetch("content.json");
        if (!response.ok) throw Error("Teaching content unavailable");
        content = await response.json();
        try {
            const configResponse = await fetch("config.json", {
                cache: "no-store",
            });
            if (!configResponse.ok)
                throw Error("Pack configuration unavailable.");
            const config = await configResponse.json();
            if (!/^[a-f0-9]{64}$/.test(config.packHash))
                throw Error("Pack hash is not configured.");
            packBase = `/evidence/versions/${config.packHash}`;
            const response = await fetch(`${packBase}/index.json`);
            if (!response.ok)
                throw Error(`Pack request returned ${response.status}.`);
            pack = await response.json();
            if (pack.schemaVersion !== 1)
                throw Error("Unsupported evidence schema.");
            video.src = `${packBase}/video.mp4`;
            const track = document.createElement("track");
            track.kind = "captions";
            track.label = `English · machine transcript (${pack.captionStatus || "unreviewed"})`;
            track.srclang = "en";
            track.src = `${packBase}/transcript.vtt`;
            track.default = true;
            video.append(track);
            const chapters = document.createElement("track");
            chapters.kind = "chapters";
            chapters.src = `${packBase}/chapters.vtt`;
            chapters.srclang = "en";
            video.append(chapters);
        } catch (err) {
            pack = null;
            packError = err.message;
        }
        render();
        const t = Number(new URL(location.href).searchParams.get("t"));
        if (t > 0) seek(t);
    } catch (err) {
        $("#main").textContent = err.message;
    }
}
boot();
