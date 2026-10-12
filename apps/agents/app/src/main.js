import { scenarioPresentation as SCENARIOS } from "./scenario-data.js";
import { projectScenario, compareScenario } from "./scenario-view.js";
import { loadWorkshop } from "./workshop-data.js";
import { createProgress, downloadText } from "./progress.js";
import { createSourceView } from "./source-view.js";
import { renderLessonBody } from "./lesson-view.js";
import { editorialLessons } from "./lesson-content.js";
import { lessonMetadata as LESSONS } from "./guide-content.js";
(async () => {
    "use strict";

    const $ = (s, r = document) => r.querySelector(s);
    const $$ = (s, r = document) => [...r.querySelectorAll(s)];
    const esc = (v) =>
        String(v ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
    const reduced = () => matchMedia("(prefers-reduced-motion: reduce)").matches;
    const wide = () => matchMedia("(min-width: 1180px)").matches;
    const fmt = (seconds) => {
        const s = Math.floor(seconds);
        return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
    };

    const data = await loadWorkshop();
    const { content } = data;
    const progress = createProgress(content.lessons.map(lesson => lesson.id));
    const sourceView = createSourceView(data, progress);
    function applyTheme(t) {
        if (t === "light" || t === "dark") document.documentElement.dataset.theme = t;
        else delete document.documentElement.dataset.theme;
        $$('input[name="theme"]').forEach(input => input.checked = input.value === (["light", "dark"].includes(t) ? t : "auto"));
        const depth = ["basics", "practitioner", "deep"].includes(progress.state.depth) ? progress.state.depth : "practitioner";
        $$("input[name=depth]").forEach(input => input.checked = input.value === depth);
    }
    applyTheme(progress.state.theme);
    /* ------------------------------------------------------------- data */
    const STATIONS = {
        signal: {
            name: "Signal",
            group: "Admit · station 1 of 9",
            def: "Work arrives as a signal: a bug report, an issue, a failing check. Agents act on signals rather than on your keystrokes.",
            links: [["Lesson 6", "Start local, then scale on signals", "#lesson/l6-fleet-operations"]],
        },
        claim: {
            name: "Claim",
            group: "Admit · station 2 of 9",
            def: "One agent owns each task. A retried delivery finds the claim and stops, so one report cannot open two PRs.",
            links: [
                ["Lesson 6", "Start local, then scale on signals", "#lesson/l6-fleet-operations"],
                ["Experiment", "Retry without a claim", "#practice/s4-naive-retry"],
                ["Lab step 6", "Claim tasks atomically", "#lab/lab-5-idempotent-claim"],
            ],
        },
        worktree: {
            name: "Worktree",
            group: "Admit · station 3 of 9",
            def: "Each agent edits in its own isolated workspace with no credentials, so parallel edits surface as conflicts instead of silent overwrites.",
            links: [
                ["Lesson 6", "Start local, then scale on signals", "#lesson/l6-fleet-operations"],
                ["Experiment", "Two agents, one file", "#practice/s1-shared-vs-isolated"],
                ["Lab step 2", "Shared tree versus worktrees", "#lab/lab-1-worktrees"],
            ],
        },
        agent: {
            name: "Agent",
            group: "Build · station 4 of 9",
            def: "The agent works from skills grown out of observed failures and a feature map that tells it where things are.",
            links: [
                ["Lesson 3", "Agents need a map of the product", "#lesson/l3-feature-map"],
                ["Lesson 4", "Skills grow from failures; evals keep them honest", "#lesson/l4-pstack-evals"],
                ["Lab step 4", "A checkable feature map", "#lab/lab-3-feature-map"],
            ],
        },
        verify: {
            name: "Verify",
            group: "Build · station 5 of 9",
            def: "The agent reproduces the symptom, makes the change, then observes the symptom gone with the same probe. “Done” means observed, not claimed.",
            links: [
                ["Lesson 2", "Verification closes the loop", "#lesson/l2-verification"],
                ["Experiment", "Done, or verified?", "#practice/s2-plausible-vs-verified"],
                ["Lab step 3", "A check that runs the real thing", "#lab/lab-2-verify"],
            ],
        },
        checks: {
            name: "Checks",
            group: "Land · station 6 of 9",
            def: "Hard checks fail the build: lint, compiler, dependency boundaries. The shortest path an agent can take must also be the right one.",
            links: [
                ["Lesson 5", "Make the shortest path the right path", "#lesson/l5-agent-friendly-architecture"],
                ["Experiment", "The shortcut import", "#practice/s5-architecture-gate"],
                ["Lab step 5", "Make the shortcut fail", "#lab/lab-4-boundary"],
            ],
        },
        review: {
            name: "Review",
            group: "Land · station 7 of 9",
            def: "A person reviews small, revertible changes. Every check that rejects bad work first makes this queue shorter.",
            links: [
                ["Lesson 1", "Trust is the throttle on parallelism", "#lesson/l1-trust-curve"],
                ["Experiment", "The reviewer is the bottleneck", "#practice/s3-review-backlog"],
            ],
        },
        merge: {
            name: "Merge",
            group: "Land · station 8 of 9",
            def: "Changes land on main. Auto-merge belongs only behind hard checks, with review after landing.",
            links: [
                ["Lesson 1", "Trust is the throttle on parallelism", "#lesson/l1-trust-curve"],
                ["Lesson 6", "Start local, then scale on signals", "#lesson/l6-fleet-operations"],
            ],
        },
        promote: {
            name: "Promote",
            group: "Release · station 9 of 9",
            def: "A separate, human-approved change activates a build. Source and activation never travel together.",
            links: [
                ["Lesson 6", "Start local, then scale on signals", "#lesson/l6-fleet-operations"],
                ["Lesson 7", "Verification first, volume last", "#lesson/l7-cost-and-adoption"],
                ["Lab step 7", "Rehearse the promotion boundary", "#lab/lab-6-promotion"],
            ],
        },
    };
    const STATION_ORDER = ["signal", "claim", "worktree", "agent", "verify", "checks", "review", "merge", "promote"];

    const NOTES = Object.create(null);

    /* ------------------------------------------------------------ router */
    const SCREEN_NAV = { home: "lessons", lesson: "lessons", practice: "practice", scenario: "practice", lab: "practice", recording: "recording" };
    let searchArrival = null;
    let firstRoute = true;
    let renderedUrl = null;
    let historyEntry = null;
    let restoringScroll = false;
    let scrollSaveTimer = null;
    let fullscreenRouteFocus = null;
    const savedScroll = new Map();
    function focusRouteTarget(target) {
        if (!target) return;
        if (document.fullscreenElement) fullscreenRouteFocus = { target, href: location.href };
        else target.focus({ preventScroll: true });
    }
    window.addEventListener("fullscreenchange", () => {
        if (document.fullscreenElement || !fullscreenRouteFocus) return;
        const { target, href } = fullscreenRouteFocus;
        fullscreenRouteFocus = null;
        const active = document.activeElement;
        if (location.href === href && target.isConnected && target.getClientRects().length &&
            (!active || active === document.body || sourceView.video.contains(active))) target.focus({ preventScroll: true });
    });
    history.scrollRestoration = "manual";
    const entryState = () => history.state?.agentsScroll;
    function rememberScroll() {
        if (restoringScroll || location.href !== renderedUrl || entryState()?.entry !== historyEntry) return;
        savedScroll.set(historyEntry, window.scrollY);
        history.replaceState({ ...history.state, agentsScroll: { entry: historyEntry, y: window.scrollY } }, "");
    }
    window.addEventListener("scroll", () => {
        if (restoringScroll || location.href !== renderedUrl || entryState()?.entry !== historyEntry) return;
        savedScroll.set(historyEntry, window.scrollY);
        clearTimeout(scrollSaveTimer);
        scrollSaveTimer = setTimeout(rememberScroll, 150);
    }, { passive: true });
    window.addEventListener("scrollend", rememberScroll);
    window.addEventListener("pagehide", rememberScroll);
    document.addEventListener("click", rememberScroll, { capture: true });

    function parseHash() {
        const raw = location.hash.slice(1) || "home";
        const separator = raw.indexOf("?");
        const path = separator < 0 ? raw : raw.slice(0, separator);
        const query = separator < 0 ? "" : raw.slice(separator + 1);
        const parts = path.split("/").filter(Boolean).map(part => {
            try { return decodeURIComponent(part); } catch { return part; }
        });
        const params = new URLSearchParams(query);
        for (const flag of ["resume", "note", "unavailable", "checked", "finished", "done", "details", "about", "frame", "search", "settings"]) {
            params.delete(flag);
        }
        return { parts, params };
    }

    function route({ restoreY = null } = {}) {
        flushAdoption();
        const initialRoute = firstRoute;
        restoringScroll = true;
        fullscreenRouteFocus = null;
        const { parts, params } = parseHash();
        let screen = parts[0] || "home";
        const id = parts[1];
        const aliases = { start: "home", lessons: "home", talk: "recording", ledger: "recording/cited", simulator: "practice" };
        if (Object.hasOwn(aliases, screen)) {
            const suffix = ["talk", "simulator"].includes(screen) && id ? `/${encodeURIComponent(id)}` : "";
            const query = params.toString();
            history.replaceState(history.state, "", `#${aliases[screen]}${suffix}${query ? `?${query}` : ""}`);
        }
        if (screen === "start" || screen === "lessons") screen = "home";
        if (screen === "talk") screen = "recording";
        if (screen === "ledger") { screen = "recording"; params.set("cited", ""); }
        if (screen === "simulator") screen = "practice";
        if (screen === "recording") {
            if (id === "about" || id === "cited") params.set(id, "");
            else if (id && Number.isFinite(Number(id))) params.set("t", id);
        }
        if (screen === "practice" && id) screen = "scenario";
        if (screen === "terms") screen = "home";
        const unknownItem = ["lesson"].includes(screen) && !Object.hasOwn(LESSONS, id)
            || screen === "scenario" && !Object.hasOwn(SCENARIOS, id)
            || screen === "lab" && id && !content.lab.some(step => step.id === id)
            || screen === "recording" && id && !["about", "cited"].includes(id) && !Number.isFinite(Number(id));
        if (!Object.hasOwn(SCREEN_NAV, screen) || unknownItem) {
            screen = "home";
            history.replaceState(history.state, "", "#home");
        }

        stopAllPractice();
        sourceTrigger = null;
        if ($("#source").open && screen === "recording" && params.has("t")) sourceView.retainPanelPlayhead();
        for (const d of $$("dialog[open]")) d.close();

        $$(".screen").forEach((s) => (s.hidden = s.dataset.screen !== screen));
        $$("[data-nav]").forEach((a) => {
            if (a.dataset.nav === SCREEN_NAV[screen]) a.setAttribute("aria-current", "page");
            else a.removeAttribute("aria-current");
        });

        const view = $(`.screen[data-screen="${screen}"]`);
        let title = "Earning trust in coding agents";
        if (screen === "home") renderHome(params);
        if (screen === "lesson") title = `${renderLesson(id)} · ${title}`;
        if (screen === "practice") title = `Practice · ${title}`;
        if (screen === "scenario") title = `${renderScenarioPage(id === undefined ? "s2-plausible-vs-verified" : id, params)} · ${title}`;
        if (screen === "lab") title = `The offline lab · ${title}`;
        if (screen === "recording") {
            renderRecording(params);
            title = `The recording · ${title}`;
        }
        document.title = title;

        if (["lesson"].includes(screen)) prepareLesson(params);
        sourceView.updateNow();
        mountPracticeIn(view, params);

        if (restoreY !== null) {
            window.scrollTo(0, restoreY);
            if (!initialRoute) focusRouteTarget($("h1", view));
        } else if (!initialRoute) {
            const h1 = $("h1", view);
            if (screen === "lab" && id) {
                const step = document.getElementById(id);
                if (step) {
                    $$(".out__item.is-target").forEach((s) => s.classList.remove("is-target"));
                    step.classList.add("is-target");
                    $(".out__details", step)?.setAttribute("open", "");
                    step.scrollIntoView({ block: "start" });
                    focusRouteTarget($("summary", step));
                }
            } else {
                window.scrollTo(0, 0);
                focusRouteTarget(h1);
            }
        } else if (screen === "lab" && id) {
            const step = document.getElementById(id);
            step?.classList.add("is-target");
            $(".out__details", step)?.setAttribute("open", "");
            requestAnimationFrame(() => step?.scrollIntoView({ block: "start" }));
        }
        firstRoute = false;
        // Old #lessons links and the glossary anchor land on the home page section.
        if (restoreY === null && screen === "home" && ["lessons", "terms"].includes(parts[0])) {
            const heading = document.getElementById(`${parts[0]}-title`);
            heading?.scrollIntoView({ block: "start" });
            if (!initialRoute) focusRouteTarget(heading);
        }

        if (restoreY === null && screen === "lesson" && parts[2]) {
            const section = editorialLessons[id].sections.find(item => item.slug === parts[2]);
            const h1Target = !section || section.target === "h1";
            const target = h1Target ? $("h1", view) : document.getElementById(section.id);
            if (h1Target) history.replaceState(history.state, "", `#lesson/${id}`);
            if (target) {
                const block = h1Target ? $('[data-section="in-short"]', view) : target.closest("[data-section]") || target;
                if (searchArrival?.id === id) {
                    const query = searchArrival.query.toLowerCase();
                    $$("details", block).forEach(details => { if (details.textContent.toLowerCase().includes(query)) details.open = true; });
                }
                (h1Target ? target : block).scrollIntoView({ block: "start" });
                focusRouteTarget(target);
            }
        }
        searchArrival = null;
        if (screen === "recording" && (params.has("cited") || params.has("about"))) {
            const target = $(params.has("cited") ? "#cited-moments" : "#about-transcript");
            target.open = true;
            if (restoreY === null) target.scrollIntoView({ block: "start" });
            if (!initialRoute) focusRouteTarget($("summary", target));
        }
        if (restoreY === null && screen === "recording" && params.has("t")) sourceView.scrollToTime(Number(params.get("t")));
        const previousEntry = entryState();
        historyEntry = (initialRoute || restoreY !== null) && typeof previousEntry?.entry === "string"
            ? previousEntry.entry : crypto.randomUUID();
        renderedUrl = location.href;
        savedScroll.set(historyEntry, restoreY ?? window.scrollY);
        history.replaceState({ ...history.state, agentsScroll: { entry: historyEntry, y: restoreY ?? window.scrollY } }, "");
        const entry = historyEntry;
        requestAnimationFrame(() => {
            if (entry !== historyEntry) return;
            if (restoreY !== null) window.scrollTo(0, restoreY);
            restoringScroll = false;
            rememberScroll();
        });
    }

    /* -------------------------------------------------------------- home */
    function renderHome() {
        const unfinished = content.lessons.find(lesson => !progress.state.completed.includes(lesson.id));
        const id = unfinished?.id || content.lessons[0].id;
        const resume = progress.state.completed.length > 0;
        $$(".hero__actions").forEach(el => el.hidden = (el.dataset.variant === "resume") !== resume);
        if (resume) {
            const action = $('.hero__actions[data-variant="resume"] .btn');
            action.href = `#lesson/${id}`;
            action.textContent = `${unfinished ? "Continue" : "Revisit"} lesson ${LESSONS[id].n}`;
            const quiet = $('.hero__actions[data-variant="resume"] .link-quiet');
            quiet.href = unfinished ? "#lesson/l1-trust-curve" : "#lesson/l7-cost-and-adoption/adopt";
            quiet.textContent = unfinished ? "Start from lesson 1" : "Your adoption decision";
            $(".hero__resume-meta").textContent = unfinished ? `${LESSONS[id].title} · ${progress.state.completed.length} of 7 lessons finished` : "All 7 lessons finished";
        }
        $$(".toc__status[data-status]", $('.screen[data-screen="home"]')).forEach(el => {
            const done = progress.state.completed.includes(el.dataset.status);
            el.className = "toc__status";
            el.textContent = done ? "Finished" : el.dataset.status === progress.state.lastLesson ? "In progress" : "";
            el.classList.toggle("toc__status--progress", !done && el.dataset.status === progress.state.lastLesson);
        });
    }

    function selectStation(key, focus) {
        const tabs = $$(".path__station");
        tabs.forEach((t) => {
            const on = t.dataset.station === key;
            t.setAttribute("aria-selected", String(on));
            t.tabIndex = on ? 0 : -1;
            if (on && focus) t.focus();
        });
        const d = STATIONS[key];
        const panel = $("#station-panel");
        panel.setAttribute("aria-labelledby", `st-${key}`);
        $('[data-panel="name"]', panel).textContent = d.name;
        $('[data-panel="group"]', panel).textContent = d.group;
        $('[data-panel="def"]', panel).textContent = d.def;
        $('[data-panel="links"]', panel).innerHTML = d.links
            .map(([label, text, href]) => `<li><span class="label">${esc(label)}</span><a href="${esc(href)}">${esc(text)}</a></li>`)
            .join("");
        panel.classList.remove("is-swapping");
        void panel.offsetWidth;
        panel.classList.add("is-swapping");
    }
    $$(".path__station").forEach((tab) => {
        tab.addEventListener("click", () => selectStation(tab.dataset.station, false));
        tab.addEventListener("keydown", (e) => {
            const i = STATION_ORDER.indexOf(tab.dataset.station);
            let next = null;
            if (e.key === "ArrowRight" || e.key === "ArrowDown") next = STATION_ORDER[(i + 1) % STATION_ORDER.length];
            if (e.key === "ArrowLeft" || e.key === "ArrowUp") next = STATION_ORDER[(i - 1 + STATION_ORDER.length) % STATION_ORDER.length];
            if (e.key === "Home") next = STATION_ORDER[0];
            if (e.key === "End") next = STATION_ORDER[STATION_ORDER.length - 1];
            if (next) {
                e.preventDefault();
                selectStation(next, true);
            }
        });
    });

    /* ------------------------------------------------------------ lesson */
    function stripHTML(here, sentence) {
        const stops = STATION_ORDER.map(k => `<span aria-hidden="true" class="strip__stop${here.includes(k) ? " is-here" : ""}"><span class="strip__dot"></span>${esc(STATIONS[k].name)}</span>`).join("");
        return `<span class="strip__label" aria-hidden="true">Where this fits</span>${stops}<span class="strip__stop strip__stop--end" aria-hidden="true"><span class="strip__dot"></span>Cluster</span><p class="strip__sentence">${sentence}</p>`;
    }
    function renderLesson(id) {
        const lesson = editorialLessons[id];
        const view = $('.screen[data-screen="lesson"]');
        view.dataset.lesson = id;
        $('[data-lesson-field="kicker"]', view).textContent = `Lesson ${lesson.n} of 7 · ${lesson.minutes} min`;
        $('[data-lesson-field="title"]', view).textContent = lesson.title;
        $('[data-lesson-field="deck"]', view).textContent = lesson.deck;
        $('[data-lesson-field="strip"]', view).innerHTML = stripHTML(lesson.here, lesson.strip.sentenceHtml);
        $(".lesson-body", view).innerHTML = renderLessonBody(lesson);
        $$("textarea[data-adoption]", view).forEach(field => {
            field.maxLength = 10000;
            field.value = progress.state.adoption?.[field.dataset.adoption] ?? "";
        });
        applyReadingDepth(view);
        return lesson.title;
    }

    function setFinished(btn, on) {
        btn.setAttribute("aria-pressed", String(on));
        $("[data-finish-label]", btn).textContent = on ? "Finished" : "Mark lesson as finished";
        $$("[data-progress-count]").forEach(line => {
            line.textContent = progress.state.completed.length === 7 ? "All 7 lessons finished" : `${progress.state.completed.length} of 7 lessons finished`;
            line.hidden = progress.state.completed.length === 0;
        });
    }
    document.addEventListener("click", event => {
        const button = event.target.closest("[data-finish]");
        if (!button) return;
        const on = button.getAttribute("aria-pressed") !== "true";
        progress.finish(button.dataset.finish, on);
        setFinished(button, on);
        renderHome();
    });
    function prepareLesson() {
        const id = parseHash().parts[1] || "l7-cost-and-adoption";
        if (!Object.hasOwn(LESSONS, id)) return;
        progress.set("lastLesson", id);
        $$(`[data-finish="${id}"]`).forEach(button => setFinished(button, progress.state.completed.includes(id)));
    }

    /* ---------------------------------------------------- source panel */
    const source = $("#source");
    let sourceTrigger = null;
    function setActiveNote(key) {
        $$(".cite.is-active, .note.is-active").forEach((el) => el.classList.remove("is-active"));
        if (key == null) return;
        $$(`.cite[data-note="${key}"]`).forEach((el) => el.classList.add("is-active"));
        $$(`.note[data-note-box="${key}"]`).forEach((el) => el.classList.add("is-active"));
        $$(`[data-lesson-source="${key}"]`).forEach(el => {
            if (el.matches(".cite")) el.classList.add("is-active");
            el.closest(".note")?.classList.add("is-active");
        });
    }
    function openSource(key, trigger) {
        const n = Object.hasOwn(NOTES, key) ? NOTES[key] : { kind: "Recording", range: fmt(Number(key)), start: Number(key), para: "" };
        sourceTrigger = trigger || sourceTrigger;
        $('[data-src="range"]', source).textContent = `· ${n.range}`;
        $('[data-src="kind"]', source).textContent = n.kind;
        const para = $('[data-src="para"]', source);
        para.textContent = n.para || n.sub || "";
        para.hidden = !(n.para || n.sub);
        $('[data-src="play-label"]', source).textContent = `Play from ${fmt(n.start)}`;
        sourceView.fillSource(n);
        setActiveNote(Object.hasOwn(NOTES, key) ? key : null);
        if (!source.open) {
            const lessonVisible = $$('.screen[data-screen="lesson"]').some(view => !view.hidden);
            if (wide() && lessonVisible) { source.show(); document.body.classList.add("is-source-open"); }
            else source.showModal();
        } else $("#source-title").focus({ preventScroll: true });
        sourceView.updateNow();
    }
    function closeSource() {
        if (source.open) source.close();
    }
    source.addEventListener("close", () => {
        document.body.classList.remove("is-source-open");
        setActiveNote(null);
        if (sourceTrigger && document.contains(sourceTrigger)) sourceTrigger.focus({ preventScroll: true });
        sourceTrigger = null;
        sourceView.restoreVideo();
    });

    document.addEventListener("click", (e) => {
        const t = e.target.closest("button, a");
        if (!t) return;
        if (t.matches("[data-note]")) {
            e.preventDefault();
            openSource(t.dataset.note, t);
            return;
        }
        if (t.matches("[data-play-from]") && t.closest("#frame")) {
            e.preventDefault();
            $("#frame").close();
            const seconds = Number(t.dataset.time);
            if (!source.open && $('.screen[data-screen="recording"]').hidden) location.hash = `#recording/${seconds}`;
            sourceView.playFrom(seconds);
            return;
        }
        if (t.matches("[data-time]") && t.closest("#search")) {
            // Transcript hits go to the recording page at that moment.
            e.preventDefault();
            $("#search").close();
            const seconds = Number(t.dataset.time);
            const destination = `#recording/${seconds}`;
            if (location.hash === destination) {
                sourceView.seek(seconds);
                sourceView.scrollToTime(seconds);
                $("#rec-title").focus({ preventScroll: true });
            } else location.hash = destination;
            return;
        }
        if (t.matches("[data-time]") && !t.closest('.screen[data-screen="recording"]')) {
            e.preventDefault();
            if (t.closest("dialog") && t.closest("dialog") !== source) t.closest("dialog").close();
            openSource(t.dataset.time, t);
            return;
        }
        if (t.matches('[data-open]') && t.closest("#search")) $("#search").close();
        if (t.matches("[data-time]")) {
            e.preventDefault();
            sourceView.seek(Number(t.dataset.time), t.hasAttribute("data-play-from"));
            return;
        }
        if (t.matches("[data-close]")) {
            t.closest("dialog").close();
            return;
        }
        if (t.matches('[data-open="search"]')) openSearch("");
        if (t.matches('[data-open="settings"]')) openDialog($("#settings"));
        if (t.matches('[data-open="frame"]')) openDialog($("#frame"));
        if (t.matches("[data-copy]")) copy(t);
        if (t.matches("[data-theme-set]")) setTheme(t.dataset.themeSet);
        if (t.closest("#search") && t.matches("a")) $("#search").close();
    });
    document.addEventListener("keydown", (e) => {
        if (e.isComposing) return;
        if (e.key === "Escape") {
            const modal = document.activeElement.closest("dialog:modal");
            if (modal) { e.preventDefault(); modal.close(); return; }
        }
        if (e.key === "Escape" && source.open && !source.matches(":modal")) {
            e.preventDefault();
            closeSource();
        }
        if (e.key === "/" && !e.ctrlKey && !e.metaKey && !e.altKey) {
            const tag = document.activeElement?.tagName;
            if (["INPUT", "TEXTAREA", "SELECT"].includes(tag) || document.activeElement?.isContentEditable) return;
            if ($("dialog[open]:modal")) return;
            e.preventDefault();
            openSearch("");
        }
    });

    function copy(btn) {
        const label = btn.textContent;
        const done = (text) => {
            btn.textContent = text;
            setTimeout(() => (btn.textContent = label), 1600);
        };
        if (navigator.clipboard) navigator.clipboard.writeText(btn.dataset.copy).then(() => done("Copied"), () => done("Select the command"));
        else done("Select the command");
    }

    /* ---------------------------------------------------------- dialogs */
    function openDialog(d) {
        if (d.id === "settings") {
            $("[data-storage-unavailable]").hidden = progress.storageAvailable;
            $$("input[name=theme]", d).forEach(input => input.autofocus = input.checked);
        }
        if (!d.open) d.showModal();
    }
    function setTheme(t) {
        progress.set("theme", t);
        applyTheme(t);
    }
    $$('input[name="theme"]').forEach((i) => i.addEventListener("change", () => setTheme(i.value)));
    function refreshProgress() {
        renderHome();
        const { parts } = parseHash();
        if (parts[0] === "lesson" && editorialLessons[parts[1]]) { renderLesson(parts[1]); mountPracticeIn($('.screen[data-screen="lesson"]')); }
        $$("[data-finish]").forEach(button => setFinished(button, progress.state.completed.includes(button.dataset.finish)));
    }
    document.addEventListener("click", event => {
        const button = event.target.closest("[data-set]");
        if (!button) return;
        const status = $('[data-set="status"]');
        const confirm = $('[data-set="confirm"]');
        const act = button.dataset.set;
        if (act === "export") {
            flushAdoption();
            downloadText("agent-workshop-state.json", progress.export(), "application/json");
            status.textContent = "Saved agent-workshop-state.json.";
        }
        if (act === "import") $("#progress-import").click();
        if (act === "reset") confirm.hidden = false;
        if (act === "reset-no") confirm.hidden = true;
        if (act === "reset-yes") {
            cancelAdoption(); progress.reset(); sourceView.syncProgress(); applyTheme(progress.state.theme); refreshProgress();
            confirm.hidden = true;
            status.textContent = "Progress reset in this browser.";
        }
    });
    $("#progress-import").addEventListener("change", async event => {
        const file = event.target.files[0];
        if (!file) return;
        try {
            if (file.size > 1500000) throw new Error("This progress file is too large.");
            const imported = JSON.parse(await file.text());
            flushAdoption();
            progress.import(imported); sourceView.syncProgress();
            applyTheme(progress.state.theme); refreshProgress();
            $('[data-set="status"]').textContent = "Imported your progress.";
        } catch { $('[data-set="status"]').textContent = "That file isn’t a progress export from this guide."; }
        event.target.value = "";
    });
    function applyReadingDepth(view) {
        $$("details[data-depth-open]", view).forEach(disclosure => disclosure.open = disclosure.dataset.depthOpen === progress.state.depth);
    }
    $$("input[name=depth]").forEach(input => input.addEventListener("change", () => {
        progress.set("depth", input.value);
        applyReadingDepth($(".screen:not([hidden])"));
    }));
    const pendingAdoption = new Map();
    let adoptionTimer;
    function cancelAdoption() { clearTimeout(adoptionTimer); pendingAdoption.clear(); }
    function flushAdoption() {
        clearTimeout(adoptionTimer);
        for (const [key, value] of pendingAdoption) progress.note(key, value);
        pendingAdoption.clear();
        if (!progress.storageAvailable) {
            const status = $("[data-adoption-status]");
            if (status) status.textContent = "This browser isn’t saving your answers. Download them before you leave.";
        }
    }
    document.addEventListener("input", event => {
        if (event.target.dataset.adoption == null) return;
        pendingAdoption.set(event.target.dataset.adoption, event.target.value);
        clearTimeout(adoptionTimer);
        adoptionTimer = setTimeout(flushAdoption, 500);
    });
    document.addEventListener("change", event => {
        if (event.target.dataset.adoption != null) flushAdoption();
    });
    window.addEventListener("pagehide", flushAdoption);
    document.addEventListener("click", event => {
        if (event.target.closest("[data-adoption-export]")) {
            flushAdoption();
            const status = $("[data-adoption-status]");
            try {
                downloadText("agent-adoption.md", `# Agent adoption decision\n\n${content.adoptionPrompts.map((prompt, index) => `## ${prompt}\n\n${progress.state.adoption[index] || "Not yet decided."}`).join("\n\n")}\n`, "text/markdown");
                status.textContent = "Downloaded agent-adoption.md.";
            } catch { status.textContent = "The download didn’t start. Your answers are still saved in this browser."; }
        }
        const sourceButton = event.target.closest("[data-lesson-source]");
        if (sourceButton) {
            const [id, index] = sourceButton.dataset.lessonSource.split(":");
            const evidence = content.lessons.find(lesson => lesson.id === id).evidence[Number(index)];
            const key = sourceButton.dataset.lessonSource;
            const context = sourceButton.closest(".screen")?.dataset.lesson;
            const note = editorialLessons[context]?.notes.find(note => note.source === key) || editorialLessons[id]?.notes.find(note => note.source === key);
            NOTES[key] = { kind: note?.panelKind || (evidence.label === "SHOWN" ? "Shown on screen" : "Our paraphrase"), range: note?.range || `${fmt(evidence.start)}–${fmt(evidence.end)}`, start: evidence.start, end: evidence.end, para: note?.paraphrase || evidence.paraphrase, frame: evidence.label === "SHOWN", frameId: evidence.frameId };
            openSource(key, sourceButton);
        }
    });
    document.addEventListener("submit", event => {
        const form = event.target.closest("[data-lesson-quiz]");
        if (!form) return;
        event.preventDefault();
        const [id, index] = form.dataset.lessonQuiz.split(":");
        const check = (editorialLessons[id]?.checks || content.lessons.find(lesson => lesson.id === id).checks)[Number(index)];
        const picked = $("input:checked", form);
        const out = $(".quiz__feedback", form);
        const choices = $$(".choice", form);
        choices.forEach(choice => {
            choice.classList.remove("is-right", "is-wrong");
            $(".choice__verdict", choice).textContent = "";
        });
        if (!picked) { out.textContent = "Choose an answer first."; return; }
        const value = Number(picked.value);
        const correct = value === check.answer;
        choices[check.answer].classList.add("is-right");
        $(".choice__verdict", choices[check.answer]).textContent = correct ? "Your answer · correct" : "The answer";
        if (!correct) {
            choices[value].classList.add("is-wrong");
            $(".choice__verdict", choices[value]).textContent = "Your answer";
        }
        const explanation = check.explanationHtml || esc(check.explanation);
        out.innerHTML = correct ? `<strong>That’s it.</strong> ${explanation}`
            : `<strong>Not quite.</strong> The answer is “${esc(check.options[check.answer])}”. ${explanation}`;
    });

    /* search */
    function lessonSearchRecords(lesson, index) {
        const authored = editorialLessons[lesson.id];
        const template = document.createElement("template");
        template.innerHTML = authored.bodyHtml.join("\n");
        template.content.querySelectorAll(".side--intro, .practice").forEach(node => node.remove());
        return authored.sections.map(section => {
            const node = template.content.querySelector(`[data-section="${CSS.escape(section.slug)}"]`);
            const text = [section.target === "h1" ? authored.deck : "", node?.textContent || ""].join(" ").replace(/\s+/gu, " ").trim();
            return { g: "Lessons", title: authored.title, text,
                search: section.target === "h1" ? `${lesson.title} ${text}` : text,
                meta: `Lesson ${index + 1} · ${section.heading || "In short"}`, href: `#lesson/${lesson.id}/${section.slug}` };
        });
    }
    const SEARCH = [
        ...content.lessons.flatMap(lessonSearchRecords),
        ...Object.entries(SCENARIOS).map(([id, scenario]) => ({ g: "Practice and lab", title: scenario.title, text: `${scenario.setup} ${scenario.question}`, meta: "Experiment", href: `#practice/${id}` })),
        ...content.lab.map(step => ({ g: "Practice and lab", title: step.title, text: `${step.goal} ${step.verify} ${step.expected}`, meta: "Offline lab", href: `#lab/${step.id}` })),
        ...content.glossary.map(term => ({ g: "Terms", title: term.term, text: `${term.plain} ${term.practitioner} ${term.deep}`, meta: "Term", href: "#terms" })),

    ];
    let searchQuery = "";
    const expandedSearchGroups = new Set();
    function snippet(text, q) {
        const i = text.toLowerCase().indexOf(q);
        if (i < 0) return esc(text.slice(0, 150));
        const start = Math.max(0, i - 60);
        const pre = (start ? "…" : "") + text.slice(start, i);
        const hit = text.slice(i, i + q.length);
        const post = text.slice(i + q.length, i + q.length + 90) + (i + q.length + 90 < text.length ? "…" : "");
        return `${esc(pre)}<mark>${esc(hit)}</mark>${esc(post)}`;
    }
    let searchStatusTimer;
    function announceSearch(text, immediate = false) {
        clearTimeout(searchStatusTimer);
        if (immediate) $("#search-status").textContent = text;
        else searchStatusTimer = setTimeout(() => $("#search-status").textContent = text, 400);
    }
    function runSearch(raw, immediate = false) {
        const q = raw.trim().toLowerCase();
        if (q !== searchQuery) expandedSearchGroups.clear();
        searchQuery = q;
        const out = $('[data-search="results"]');
        const status = $("#search-status");
        const help = $("#search-help");
        const activeKey = out.contains(document.activeElement) ? document.activeElement.dataset.searchKey : null;
        $('[data-search="suggest"]').hidden = q.length >= 2;
        if (q.length < 2) {
            out.innerHTML = "";
            clearTimeout(searchStatusTimer);
            status.textContent = "";
            status.hidden = true;
            help.hidden = false;
            return;
        }
        help.hidden = true;
        status.hidden = false;
        const hits = [...SEARCH, ...sourceView.searchRecords].filter(record => `${record.title} ${record.search || record.text}`.toLowerCase().includes(q));
        const relevance = record => record.title.toLowerCase() === q ? 0 : record.title.toLowerCase().includes(q) ? 1 : 2;
        hits.sort((a, b) => relevance(a) - relevance(b));
        out.innerHTML = ["Lessons", "Practice and lab", "Terms", "Recording", "Shown on screen"].map(group => {
            const rows = hits.filter(hit => hit.g === group);
            if (!rows.length) return "";
            const label = group === "Recording" ? "Recording · machine transcript"
                : group === "Shown on screen" ? "Shown on screen · machine OCR" : group;
            return `<section class="rgroup" data-search-group="${esc(group)}"><h3 class="rgroup__title">${esc(label)} · ${rows.length}</h3><ul>${rows.slice(0, expandedSearchGroups.has(group) ? rows.length : 5).map(row => {
                const inside = `<span class="result__title">${esc(row.title)}</span><span class="result__snippet">${snippet(row.text, q)}</span><span class="result__meta">${esc(row.meta || `${row.frame ? "Machine OCR" : "Machine transcript"} · ${fmt(row.t)}`)}</span>`;
                const key = esc(JSON.stringify([row.g, row.href ?? row.frame ?? row.t]));
                return `<li>${row.frame ? `<button class="result" type="button" data-search-key="${key}" data-frame="${esc(row.frame)}">${inside}</button>` : row.t != null ? `<button class="result" type="button" data-search-key="${key}" data-time="${row.t}">${inside}</button>` : `<a class="result" data-search-key="${key}" href="${esc(row.href)}">${inside}</a>`}</li>`;
            }).join("")}</ul>${rows.length > 5 && !expandedSearchGroups.has(group) ? `<button class="btn btn--text" type="button" data-search-expand="${esc(group)}">Show all ${rows.length}</button>` : ""}</section>`;
        }).join("") || '<p class="search__status">Nothing matches. Try a shorter word.</p>';
        if (activeKey) $$("[data-search-key]", out).find(row => row.dataset.searchKey === activeKey)?.focus({ preventScroll: true });
        const suffix = data.status === "ready" ? "" : data.status === "unavailable" ? " · transcript unavailable" : " · transcript still loading";
        announceSearch(`${hits.length === 0 ? "No results" : hits.length === 1 ? "1 result" : `${hits.length} results`}${suffix}`, immediate);
    }
    function openSearch(q) {
        const d = $("#search");
        const input = $("#search-input");
        const alreadyOpen = d.open;
        input.value = q;
        runSearch(q, true);
        openDialog(d);
        if (alreadyOpen) input.focus();
    }
    $('[data-search="results"]').addEventListener("click", event => {
        const link = event.target.closest('a[href^="#lesson/"]');
        if (link && !event.ctrlKey && !event.metaKey && !event.shiftKey && !event.altKey) searchArrival = { id: decodeURIComponent(link.hash.split("/")[1]), query: $("#search-input").value.trim() };
        const button = event.target.closest("[data-search-expand]");
        if (!button) return;
        const group = button.dataset.searchExpand;
        expandedSearchGroups.add(group);
        runSearch($("#search-input").value, true);
        $$(`[data-search-group="${CSS.escape(group)}"] .result`)[5]?.focus();
    });
    data.subscribe(() => { if ($("#search").open) runSearch($("#search-input").value); });
    $("#search-input").addEventListener("input", (e) => runSearch(e.target.value));
    $$("[data-q]").forEach((b) =>
        b.addEventListener("click", () => {
            $("#search-input").value = b.dataset.q;
            runSearch(b.dataset.q, true);
            $("#search-input").focus();
        }),
    );

    /* -------------------------------------------------------- recording */
    function renderRecording(params) {
        sourceView.render(params);
    }
    function seekRecording(t) { sourceView.seek(t, true); }

    /* ---------------------------------------------------------- practice */
    const practiceStates = new Set();
    function stopAllPractice() {
        for (const st of practiceStates) {
            clearTimeout(st.timer);
            st.running = false;
            if (!st.el.isConnected) practiceStates.delete(st);
        }
    }
    function renderScenarioPage(id, params) {
        const sc = Object.hasOwn(SCENARIOS, id) ? SCENARIOS[id] : SCENARIOS["s2-plausible-vs-verified"];
        const view = $('.screen[data-screen="scenario"]');
        $('[data-scn="kicker"]', view).textContent = `Experiment · ${sc.station} station`;
        $('[data-scn="title"]', view).textContent = sc.title;
        $('[data-scn="setup"]', view).textContent = sc.setup;
        $('[data-scn="from"]', view).innerHTML = `From <a href="${esc(sc.lesson[2])}">${esc(sc.lesson[0])} · ${esc(sc.lesson[1])}</a>`;
        $(".practice", view).dataset.scenario = Object.hasOwn(SCENARIOS, id) ? id : "s2-plausible-vs-verified";
        return sc.title;
    }
    function mountPracticeIn(view, params) {
        $$(".practice", view).forEach((el) => mountPractice(el, el.dataset.scenario));
    }

    function practiceHTML(id, sc, context) {
        const head =
            context === "lesson"
                ? `<p class="practice__station meta"><span class="dot dot--signal"></span>${esc(sc.station)} station</p><h3 class="practice__title">${esc(sc.title)}</h3><p class="practice__setup">${esc(sc.setup)}</p>`
                : "";
        const choices = sc.choices.map((c, i) => `<label class="choice"><input type="radio" name="pred-${id}-${context}" value="${i}" /><span>${esc(c)}</span></label>`).join("");
        const seg = (name, legend, options) =>
            `<fieldset class="segmented"><legend class="segmented__legend">${esc(legend)}</legend><span class="segmented__options">${options
                .map(([value, label, checked]) => `<input type="radio" id="${name}-${value}" name="${name}" value="${value}"${checked ? " checked" : ""} /><label for="${name}-${value}">${esc(label)}</label>`)
                .join("")}</span></fieldset>`;
        const controls =
            seg(`ctl-${id}-${context}`, sc.control.legend, [
                ["off", sc.control.off, true],
                ["on", sc.control.on, false],
            ]) +
            (sc.queue
                ? seg(`agents-${id}-${context}`, "Agents", [
                      ["4", "4", true],
                      ["1", "1", false],
                  ])
                : "");
        const diagram = sc.queue ? queueHTML() : lanesHTML(sc);
        return `${head}<ol class="steps">
<li class="step"><h4 class="step__label"><span class="step__num">1</span>Predict</h4><fieldset class="choices"><legend>${esc(sc.question)}</legend>${choices}</fieldset></li>
<li class="step"><h4 class="step__label"><span class="step__num">2</span>Run</h4><p class="step__hint">Start with the control off. Run plays the fixed schedule; Step goes one tick at a time.</p><div class="instrument"><div class="controls"><div class="controls__set">${controls}</div><div class="controls__actions"><button class="btn btn--primary btn--run" type="button" data-act="run">Run</button><button class="btn" type="button" data-act="step">Step</button><button class="btn btn--text" type="button" data-act="reset">Reset</button></div></div>${diagram}<div class="readout"><p class="readout__tick" aria-hidden="true">Ready</p><ul class="readout__events" aria-hidden="true"><li>Choose a prediction, then run the model.</li></ul><span class="visually-hidden" role="status" aria-live="polite" aria-atomic="true" data-prediction-live></span></div></div></li>
<li class="step"><h4 class="step__label"><span class="step__num">3</span>Compare</h4><table class="compare"><caption class="visually-hidden">Outcomes with the control off and on</caption><thead><tr><th scope="col">Outcome</th><th scope="col" class="num">${esc(sc.control.colOff)}</th><th scope="col" class="num">${esc(sc.control.colOn)}</th></tr></thead><tbody></tbody></table><div class="feedback"></div><details class="log"><summary>Event log</summary><table><caption class="visually-hidden">Every event in tick order</caption><thead><tr><th scope="col">Tick</th><th scope="col">Task</th><th scope="col">Event</th><th scope="col">What happened</th></tr></thead><tbody></tbody></table></details></li>
</ol>`;
    }
    function lanesHTML(sc) {
        const n = sc.stations.length;
        const guides = sc.stations.map(() => '<span class="guide"></span>').join("");
        const lanes = sc.lanes
            .map(([key, label]) => `<span class="lane__label">${esc(label)}</span><div class="lane__track" data-lane="${esc(key)}"><span class="token is-idle" data-token="${esc(key)}"><span class="token__mark"></span></span></div>`)
            .join("");
        const stations = sc.stations.map((s) => `<span class="station">${esc(s)}<small></small></span>`).join("");
        return `<div class="lanes lanes--n${n}" aria-hidden="true"><div class="lanes__grid"><div class="lanes__guides">${guides}</div>${lanes}</div><div class="lanes__stations"><span></span>${stations}</div></div>`;
    }
    function queueHTML() {
        return `<div class="queue" aria-hidden="true">${[
            ["rejected", "Rejected by checks"],
            ["waiting", "Waiting for review"],
            ["merged", "Merged"],
        ]
            .map(([k, label]) => `<div class="queue__zone" data-zone="${k}"><p class="queue__name">${label} <span class="queue__count">0</span></p><ul class="queue__items"></ul>${k === "waiting" ? '<p class="queue__peak">Peak 0</p>' : ""}</div>`)
            .join("")}</div>`;
    }

    function mountPractice(el, id) {
        const sc = SCENARIOS[id];
        if (!sc) return;
        if (el._practice) practiceStates.delete(el._practice);
        const context = el.dataset.context || "page";
        el.innerHTML = practiceHTML(id, sc, context);
        const st = { el, id, sc, mode: "off", agents: 4, tick: 0, timer: null, running: false, done: {}, shown: [] };
        el._practice = st;
        practiceStates.add(st);
        $$(`input[name="ctl-${id}-${context}"]`, el).forEach((i) =>
            i.addEventListener("change", () => {
                st.mode = i.value;
                resetRun(st);
            }),
        );
        $$(`input[name="agents-${id}-${context}"]`, el).forEach((i) =>
            i.addEventListener("change", () => {
                st.agents = Number(i.value);
                resetRun(st);
                renderCompare(st);
            }),
        );
        $('[data-act="run"]', el).addEventListener("click", () => (st.running ? pause(st) : play(st)));
        $('[data-act="step"]', el).addEventListener("click", () => {
            pause(st);
            if (st.tick >= maxTick(st)) resetRun(st);
            stepTick(st, true);
        });
        $('[data-act="reset"]', el).addEventListener("click", () => resetRun(st));
        resetRun(st);
        renderCompare(st);
    }

    function eventsFor(st) { return projectScenario(st.id, st.mode === "on", st.agents).events; }
    function maxTick(st) {
        return Math.max(...eventsFor(st).map((e) => e[0]));
    }
    function setRunLabel(st, text) {
        $('[data-act="run"]', st.el).textContent = text;
    }
    function play(st) {
        if (st.tick >= maxTick(st)) resetRun(st);
        if (reduced()) {
            while (st.tick < maxTick(st)) stepTick(st, false);
            const r = $(".readout__tick", st.el);
            r.textContent = `All ${maxTick(st)} ticks shown · use Step to go through them one at a time`;
            setRunLabel(st, "Run again");
            announcePractice(st);
            return;
        }
        st.running = true;
        setRunLabel(st, "Pause");
        const loop = () => {
            const had = stepTick(st, true);
            if (st.tick >= maxTick(st)) {
                st.running = false;
                setRunLabel(st, "Run again");
                return;
            }
            st.timer = setTimeout(loop, had ? 1400 : 360);
        };
        st.timer = setTimeout(loop, 0);
    }
    function pause(st) {
        clearTimeout(st.timer);
        if (st.running) {
            st.running = false;
            setRunLabel(st, st.tick >= maxTick(st) ? "Run again" : "Resume");
        }
    }
    function resetRun(st) {
        clearTimeout(st.timer);
        st.running = false;
        st.tick = 0;
        st.shown = [];
        setRunLabel(st, "Run");
        const el = st.el;
        if (st.sc.queue) {
            $$(".queue__items", el).forEach((u) => (u.innerHTML = ""));
            $$(".queue__count", el).forEach((c) => (c.textContent = "0"));
            $(".queue__peak", el).textContent = "Peak 0";
            st.q = { rejected: [], waiting: [], merged: [], peak: 0 };
        } else {
            const lanes = $(".lanes", el);
            lanes.classList.add("is-resetting");
            $$(".token", el).forEach((tok) => {
                tok.className = "token is-idle";
                tok.style.setProperty("--x", "0");
                $(".token__mark", tok).textContent = "";
            });
            $$(".pass", el).forEach((p) => p.remove());
            const bypass = st.sc.bypass[st.mode] || [];
            $$(".guide", el).forEach((g, i) => g.classList.toggle("guide--off", bypass.includes(i)));
            $$(".station", el).forEach((s, i) => {
                s.classList.toggle("station--off", bypass.includes(i));
                $("small", s).textContent = (st.sc.sub[st.mode] || {})[i] || "";
            });
            void lanes.offsetWidth;
            lanes.classList.remove("is-resetting");
        }
        $(".readout__tick", el).textContent = `Ready · ${st.sc.control.legend.toLowerCase()} ${st.mode === "on" ? st.sc.control.on.toLowerCase() : st.sc.control.off.toLowerCase()} · ${maxTick(st)} ticks`;
        st.prediction = "";
        $(".readout__events", el).innerHTML = `<li>${st.done[doneKey(st)] ? "Run it again, step through it, or switch the control." : "Choose a prediction, then run the model."}</li>`;
        renderLog(st);
        announcePractice(st);
    }
    function doneKey(st) {
        return st.sc.queue ? `${st.agents}-${st.mode}` : st.mode;
    }

    function stepTick(st, animate) {
        st.tick += 1;
        const events = eventsFor(st).filter((e) => e[0] === st.tick);
        st.shown.push(...events);
        const el = st.el;
        if (st.sc.queue) applyQueue(st, events, animate);
        else
            for (const e of events) {
                const p = e[4];
                const tok = $(`.token[data-token="${p.lane}"]`, el);
                const n = st.sc.stations.length;
                tok.classList.remove("is-idle", "token--done", "token--pending", "token--lost", "token--caught", "token--defect", "token--stopped", "is-marked");
                if (p.s) tok.classList.add(`token--${p.s}`);
                tok.classList.toggle("is-flipped", p.x >= n - 1);
                tok.style.setProperty("--x", String(p.x));
                const mark = $(".token__mark", tok);
                mark.textContent = p.m || "";
                if (p.m) {
                    void tok.offsetWidth;
                    tok.classList.add("is-marked");
                }
                for (const x of p.pass || []) {
                    const pass = document.createElement("span");
                    pass.className = "pass";
                    pass.style.setProperty("--x", String(x));
                    tok.parentElement.append(pass);
                }
            }
        renderReadout(st, events, animate);
        renderLog(st);
        if (st.tick >= maxTick(st)) complete(st);
        announcePractice(st);
        return events.length > 0;
    }

    function applyQueue(st, events, animate) {
        const q = st.q;
        const fresh = new Set();
        for (const [, task, kind] of events) {
            if (kind === "check_reject") q.rejected.push(task);
            if (kind === "review_ready") q.waiting.push(task);
            if (kind === "reviewed") {
                q.waiting = q.waiting.filter((t) => t !== task);
                q.merged.push(task);
            }
            fresh.add(task);
        }
        // Same measure as simulateScenario: queue length after this tick's reviews.
        q.peak = Math.max(q.peak, q.waiting.length);
        const zone = (k, cls) => {
            const z = $(`[data-zone="${k}"]`, st.el);
            $(".queue__items", z).innerHTML = q[k].map((t) => `<li class="qtok ${cls}${animate && fresh.has(t) ? " is-new" : ""}" title="${esc(t)}"></li>`).join("");
            $(".queue__count", z).textContent = String(q[k].length);
        };
        zone("rejected", "qtok--rejected");
        zone("waiting", "");
        zone("merged", "qtok--merged");
        $(".queue__peak", st.el).textContent = `Peak ${q.peak}`;
    }

    function announcePractice(st) {
        // One text update keeps the tick, events and verdict together in
        // Chrome's accessibility tree, including repeated queue messages.
        const parts = [$(".readout__tick", st.el).textContent,
            ...$$(".readout__events li", st.el).map(node => node.textContent),
            st.prediction];
        $("[data-prediction-live]", st.el).textContent = parts.filter(Boolean).map(text => text.replace(/\.+$/u, "")).join(". ").replace(/\s+/gu, " ").trim() + ".";
    }

    function renderReadout(st, events, animate) {
        const box = $(".readout", st.el);
        $(".readout__tick", st.el).textContent = `Tick ${st.tick} of ${maxTick(st)}`;
        const list = $(".readout__events", st.el);
        if (!events.length) list.innerHTML = "<li>Nothing happens this tick.</li>";
        else {
            const groups = [];
            for (const [, task, , message] of events) {
                const g = groups.find((x) => x.message === message);
                if (g) g.tasks.push(task);
                else groups.push({ message, tasks: [task] });
            }
            list.innerHTML = groups.map((g) => `<li><span class="readout__task">${esc(g.tasks.join(", "))}</span> ${esc(g.message)}</li>`).join("");
        }
        if (animate) {
            box.classList.remove("is-swapping");
            void box.offsetWidth;
            box.classList.add("is-swapping");
        }
    }
    function renderLog(st) {
        $(".log tbody", st.el).innerHTML = st.shown.map(([tick, task, kind, message]) => `<tr><td>${tick}</td><td>${esc(task)}</td><td>${esc(kind)}</td><td>${esc(message)}</td></tr>`).join("");
        $(".log summary", st.el).textContent = st.shown.length ? `Event log · ${st.shown.length} events` : "Event log";
    }

    function compareRows(st) { return compareScenario(st.id, st.agents); }
    function renderCompare(st, fresh) {
        const key = (m) => (st.sc.queue ? `${st.agents}-${m}` : m);
        const cell = (v, m) => {
            const done = st.done[key(m)];
            return `<td class="num${done ? "" : " is-empty"}${done && fresh === m ? " is-fresh" : ""}">${done ? esc(v) : "–"}</td>`;
        };
        $(".compare tbody", st.el).innerHTML = compareRows(st)
            .map(([label, off, on]) => `<tr><th scope="row">${esc(label)}</th>${cell(off, "off")}${cell(on, "on")}</tr>`)
            .join("");
    }
    function complete(st) {
        st.done[doneKey(st)] = true;
        renderCompare(st, st.mode);
        const sc = st.sc;
        const picked = $(`.choices input:checked`, st.el);
        const both = st.done[st.sc.queue ? `${st.agents}-off` : "off"] && st.done[st.sc.queue ? `${st.agents}-on` : "on"];
        const ready = sc.predictOn === "both" ? both : st.done[sc.queue ? `${st.agents}-${sc.predictOn}` : sc.predictOn];
        const fb = $(".feedback", st.el);
        let html = "";
        if (ready) {
            if (picked) {
                const v = Number(picked.value);
                html += v === sc.answer
                    ? `<p><span class="feedback__verdict">Your prediction matches the run.</span> You chose “${esc(sc.choices[v])}”.</p>`
                    : `<p><span class="feedback__verdict">The run disagrees with your prediction.</span> You chose “${esc(sc.choices[v])}”; the model shows “${esc(sc.choices[sc.answer])}”.</p>`;
            }
            html += `<p>${esc(sc.explanation)}</p>`;
        }
        const otherMode = st.mode === "off" ? "on" : "off";
        if (!st.done[sc.queue ? `${st.agents}-${otherMode}` : otherMode]) {
            const label = otherMode === "on" ? `Run with ${sc.control.colOn.toLowerCase()}` : `Run with ${sc.control.colOff.toLowerCase()}`;
            html += `<p class="feedback__next"><button class="btn" type="button" data-act="other">${esc(label)}</button></p>`;
        }
        fb.innerHTML = html;
        st.prediction = ready && picked ? Number(picked.value) === sc.answer ? "Your prediction matches the run." : "The run disagrees with your prediction." : "";
        const next = $('[data-act="other"]', fb);
        if (next)
            next.addEventListener("click", () => {
                const input = $(`input[name^="ctl-${st.id}-"][value="${otherMode}"]`, st.el);
                input.checked = true;
                st.mode = otherMode;
                resetRun(st);
                $(".instrument", st.el).scrollIntoView({ block: "nearest", behavior: reduced() ? "auto" : "smooth" });
                play(st);
            });
    }

    /* ------------------------------------------------------------- boot */
    $(".skip").addEventListener("click", event => {
        event.preventDefault();
        const heading = $(".screen:not([hidden]) h1") || $("#main");
        heading.focus({ preventScroll: true });
        heading.scrollIntoView({ block: "nearest" });
    });
    window.addEventListener("popstate", event => {
        const saved = event.state?.agentsScroll;
        if (typeof saved?.entry !== "string" || saved.entry === historyEntry || !Number.isFinite(saved.y)) return;
        route({ restoreY: savedScroll.get(saved.entry) ?? Math.max(0, saved.y) });
    });
    window.addEventListener("hashchange", () => {
        if (location.href !== renderedUrl || entryState()?.entry !== historyEntry) route();
    });
    route();
    requestAnimationFrame(() => setTimeout(() => data.startPrivate(), 0));
})().catch(error => {
    document.querySelector("#main").textContent = error.message;
});
