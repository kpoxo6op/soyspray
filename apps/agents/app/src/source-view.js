import { lessonMetadata } from "./guide-content.js";
import { chapterPassages, sourceExcerpt, sourceSearch } from "./workshop-data.js";
import { downloadText } from "./progress.js";
import { createMediaPlayer } from "./media-player.js";

const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
const esc = value => String(value ?? "").replace(/[&<>"']/g, character =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[character]);
const time = seconds => `${Math.floor(seconds / 60)}:${String(Math.floor(seconds % 60)).padStart(2, "0")}`;
const playButton = (seconds, label = `Play from ${time(seconds)}`) =>
    `<button class="btn btn--text" type="button" data-time="${seconds}" data-play-from>${esc(label)}</button>`;
const lessonTitle = lesson => lessonMetadata[lesson.id]?.title ?? lesson.title;

export function createSourceView(data, progress) {
    const { content } = data;
    let pack = null;
    let packBase = "";
    const chapters = content.talkChapters;
    const recording = $('.screen[data-screen="recording"]');
    const recordingHost = $(".video-wrap", recording);
    const video = $("video", recordingHost);
    const narration = new Audio();
    narration.preload = "none";
    narration.hidden = true;
    narration.setAttribute("aria-hidden", "true");
    document.body.append(narration);
    let sourceStart = 0;
    let currentFrame = 0;
    let captionsInitialized = false;
    let settingCaptionMode = false;
    let expandedChapter = -1;
    let frameTrigger = null;
    let activeNote = null;
    let panelReturnTime = null;
    let panelPlayed = false;
    let videoPrepared = false;
    let suppressPlaybackSave = false;
    let shelfLayoutText = null;
    let continueRecordingHash = null;
    let pendingTimeScroll = null;
    const shelf = $("[data-playback-shelf]");
    const shelfHome = shelf.parentElement;
    const shelfNext = shelf.nextSibling;
    const rootRule = [...document.styleSheets].flatMap(sheet => [...sheet.cssRules])
        .find(rule => rule.selectorText === ":root");
    video.preload = "none";
    video.playsInline = true;
    video.setAttribute("aria-label", "Recording of the talk");
    const player = createMediaPlayer(video, narration, {
        pack: () => pack, base: () => packBase,
        descriptionsEnabled: () => progress.state.descriptions,
        update: updateNow,
        save: seconds => { if (!suppressPlaybackSave && progress.state.playback !== seconds) progress.set("playback", seconds); },
    });
    function prepareVideo() {
        if (!pack || videoPrepared) return;
        videoPrepared = true;
        video.preload = "metadata";
        const captions = document.createElement("track");
        Object.assign(captions, { kind: "captions", label: "English (machine transcription, corrected)", srclang: "en", src: `${packBase}/transcript.vtt`, default: true });
        const chapterTrack = document.createElement("track");
        Object.assign(chapterTrack, { kind: "chapters", srclang: "en", src: `${packBase}/chapters.vtt` });
        video.append(captions, chapterTrack);
        video.addEventListener("loadedmetadata", () => {
            applyCaptionPreference();
            captionsInitialized = true;
            updateNow();
        }, { once: true });
        video.src = `${packBase}/video.mp4`;
    }
    const address = new URL(location.href);
    const hashParams = new URLSearchParams(location.hash.split("?")[1]);
    const linkedTime = address.searchParams.has("t") ? Number(address.searchParams.get("t"))
        : hashParams.has("t") ? Number(hashParams.get("t")) : null;
    player.seek(linkedTime !== null && Number.isFinite(linkedTime) ? linkedTime : progress.state.playback);
    $$("[data-opt=describe]").forEach(input => input.checked = progress.state.descriptions);
    $("[data-opt=captions]").checked = progress.state.captions !== false;
    $("[data-opt=details]").checked = progress.state.transcriptDetails === true;

    function applyCaptionPreference() {
        settingCaptionMode = true;
        const enabled = progress.state.captions !== false;
        [...video.textTracks].filter(track => track.kind === "captions")
            .forEach(track => track.mode = enabled ? "showing" : "hidden");
        $("[data-opt=captions]").checked = enabled;
        settingCaptionMode = false;
    }
    video.textTracks.addEventListener("change", () => {
        if (!captionsInitialized || settingCaptionMode) return;
        const caption = [...video.textTracks].find(track => track.kind === "captions");
        if (!caption) return;
        const enabled = caption.mode === "showing";
        $("[data-opt=captions]").checked = enabled;
        if ((typeof progress.state.captions === "boolean" && progress.state.captions !== enabled) ||
            (progress.state.captions === undefined && !enabled)) progress.set("captions", enabled);
    });
    function chapterAt(seconds) {
        const found = chapters.findIndex(chapter => seconds >= chapter.start && seconds < chapter.end);
        return found < 0 ? seconds >= chapters.at(-1).end ? chapters.length - 1 : 0 : found;
    }
    function seek(seconds, play = false) {
        player.seek(seconds, play);
        const index = chapterAt(Number(seconds));
        if (!recording.hidden && expandedChapter !== index) openChapter(index);
    }
    function playFrom(seconds) {
        if ($("#source").open) {
            panelPlayed = true;
            const media = $("[data-src=media]", $("#source"));
            if (player.move(media)) [...media.children].filter(child => child !== video).forEach(child => child.remove());
        }
        seek(seconds, true);
    }
    function scrollToTime(seconds) {
        if (!Number.isFinite(seconds) || recording.hidden) return;
        const chapter = $$(".chapter", recording)[chapterAt(seconds)];
        const passages = $$(".passage[data-start]", chapter);
        const passage = passages.find(item => Number(item.dataset.start) <= seconds && Number(item.dataset.end) > seconds)
            || passages.find(item => Number(item.dataset.start) >= seconds) || passages.at(-1);
        (passage || $(".chapter__btn", chapter))?.scrollIntoView({ block: "start" });
        pendingTimeScroll = !pack && data.status !== "unavailable" ? { seconds, href: location.href } : null;
    }
    // A deep link may arrive before its transcript. Fulfil that link when
    // available, unless the reader has already chosen another position.
    for (const event of ["wheel", "touchmove", "pointerdown", "keydown"]) {
        window.addEventListener(event, () => pendingTimeScroll = null, { passive: true });
    }
    function updateNow() {
        const seconds = video.currentTime;
        const index = chapterAt(seconds);
        const description = player.description;
        const describing = player.describing;
        const now = describing ? `Describing the screen at ${time(description.start)}`
            : `At ${time(seconds)}\u00a0· chapter ${index + 1} of ${chapters.length}`;
        $(".rec__now", recording).textContent = now;
        const [previousChapter, nextChapter] = $$(".rec__chnav button", recording);
        previousChapter?.setAttribute("aria-disabled", String(index === 0));
        nextChapter?.setAttribute("aria-disabled", String(index === chapters.length - 1));
        const text = $("[data-description-status]", recording);
        text.textContent = description?.text || "";
        text.hidden = !description;
        const source = $("#source");
        const playerInSource = source.open && video.parentElement === $("[data-src=media]", source);
        const sourceNow = $("[data-src-description-now]", source);
        sourceNow.textContent = now;
        sourceNow.hidden = !playerInSource || !description;
        const sourceText = $("[data-src-description-text]", source);
        sourceText.textContent = description?.text || "";
        sourceText.hidden = !playerInSource || !description;
        $$("[data-narration-toggle]").forEach(button => {
            const activeHost = button.closest("#source") ? playerInSource : !recording.hidden;
            button.hidden = !activeHost || !describing;
            button.textContent = player.playing ? "Pause description" : "Resume description";
        });
        $$(".chapter", recording).forEach((chapter, i) => chapter.classList.toggle("is-now", i === index));
        $$(".passage[data-start]", recording).forEach(passage =>
            passage.classList.toggle("is-now", Number(passage.dataset.start) <= seconds && Number(passage.dataset.end) > seconds));
        const visible = recording.hidden && !playerInSource &&
            (player.playing || shelf.contains(document.activeElement));
        const barHost = source.open && source.matches(":modal") && !playerInSource
            ? $(".source__body", source) : shelfHome;
        if (shelf.parentElement !== barHost) {
            if (barHost === shelfHome) shelfHome.insertBefore(shelf, shelfNext);
            else barHost.prepend(shelf);
        }
        shelf.hidden = !visible;
        document.documentElement.classList.toggle("has-playbar", visible && barHost === shelfHome);
        const label = describing ? `Describing ${time(description.start)}`
            : `${player.playing ? "Playing" : "Paused"} ${time(seconds)}`;
        if ($("[data-playback-position]", shelf).textContent !== label) $("[data-playback-position]", shelf).textContent = label;
        $("[data-playback-description]", shelf).textContent = describing ? ` · ${description.text}` : "";
        $("[data-playback-pause]", shelf).textContent = player.playing ? "Pause" : "Resume";
        $("[data-playback-recording]", shelf).href = `#recording/${Math.floor(seconds)}`;
        // Routing may scroll a heading before ResizeObserver's next delivery.
        // Reserve the actual bar height in that same task as well.
        const layoutText = visible && barHost === shelfHome
            ? `${label}|${describing ? description.text : ""}|${player.playing}` : null;
        if (layoutText !== shelfLayoutText && layoutText !== null) {
            rootRule.style.setProperty("--playbar-h", `${shelf.getBoundingClientRect().height}px`);
        }
        shelfLayoutText = layoutText;
    }
    new ResizeObserver(entries => {
        const height = entries[0].borderBoxSize?.[0]?.blockSize || shelf.getBoundingClientRect().height;
        rootRule.style.setProperty("--playbar-h", `${height}px`);
    }).observe(shelf);
    shelf.addEventListener("focusout", () => queueMicrotask(updateNow));
    shelf.addEventListener("click", event => {
        const link = event.target.closest("[data-playback-recording]");
        if (link && event.button === 0 && !event.ctrlKey && !event.metaKey && !event.shiftKey && !event.altKey) {
            continueRecordingHash = link.hash;
        }
    });
    video.addEventListener("play", () => { if (activeNote && $("#source").open) panelPlayed = true; });

    function correctionDetails(correction) {
        return `<details class="tx-correction" data-correction-detail="${esc(correction.segmentId)}"><summary>Correction at ${time(correction.start)}</summary><p>Recognised: ${esc(correction.raw)}</p><p>Reviewed: ${esc(correction.corrected)}</p><p>${esc(correction.reason)}</p><p class="meta">${esc(correction.reviewStatus)}</p>${correction.evidenceFrameId ? `<button class="btn btn--text" type="button" data-frame="${esc(correction.evidenceFrameId)}">View supporting frame</button>` : ""}</details>`;
    }
    function recognisedWords(text, words) {
        const tokens = [...text.matchAll(/\S+/gu)];
        const normal = word => word.toLowerCase().replace(/[^\p{L}\p{N}]/gu, "");
        // Only apply word-level confidence to text with a proven alignment.
        // Unaligned or reviewed text keeps its recognition details separately.
        if (tokens.length !== words.length || !tokens.every((token, i) => normal(token[0]) === normal(words[i].word))) return esc(text);
        let end = 0;
        const parts = tokens.map((token, i) => {
            const before = esc(text.slice(end, token.index));
            end = token.index + token[0].length;
            return before + (words[i].uncertain ? `<span class="tx-uncertain">${esc(token[0])}</span>` : esc(token[0]));
        });
        return parts.join("") + esc(text.slice(end));
    }
    function segmentHTML(segment) {
        const correction = pack.corrections.find(item => item.segmentId === segment.id);
        if (correction) return `<button class="tx-fix" type="button" data-correction="${esc(segment.id)}" aria-expanded="false" title="Read the reviewed correction">${esc(segment.corrected)}</button>`;
        return segment.raw === segment.corrected ? recognisedWords(segment.corrected, segment.words) : esc(segment.corrected);
    }
    function passageHTML(passage) {
        const corrections = pack.corrections.filter(correction => passage.segments.some(segment => segment.id === correction.segmentId));
        const gaps = pack.gaps.filter(gap => gap.start >= passage.start && gap.start < passage.end);
        return `<div class="passage" id="t-${passage.id}" data-start="${passage.start}" data-end="${passage.end}">
            <a class="passage__time" href="#recording?t=${passage.start}" data-time="${passage.start}">${time(passage.start)}</a>
            <p class="passage__text">${passage.segments.map(segmentHTML).join(" ")}</p>
            ${corrections.length ? `<div class="passage__corrections" hidden>${corrections.map(correctionDetails).join("")}</div>` : ""}
            <details class="tx-details-only"><summary>Original segments and recognition details</summary>
                ${passage.segments.map(segment => `<div class="tx-original" data-segment="${segment.id}"><p class="meta">${esc(segment.id)} · ${time(segment.start)}–${time(segment.end)}</p><p>${esc(segment.raw)}</p>${segment.uncertain ? `<p class="meta">Low-confidence recognition. ${esc(segment.words.filter(word => word.uncertain).map(word => word.word).join(" "))}</p>` : ""}</div>`).join("")}
                ${gaps.map(gap => `<p class="meta">${time(gap.start)}–${time(gap.end)} · ${(gap.end - gap.start).toFixed(2)} s with no transcribed speech. ${esc(gap.note)}</p>`).join("")}
            </details></div>`;
    }
    function frameHTML(frame) {
        return `<figure class="tx-frame"><button class="frame-image" type="button" data-frame="${esc(frame.id)}" aria-label="View frame at ${time(frame.start)}"><img src="${packBase}/${esc(frame.path)}" width="${frame.width}" height="${frame.height}" loading="lazy" alt="${esc(frame.description || `Source frame at ${time(frame.start)}`)}" /></button><figcaption><span class="meta">Shown on screen · ${time(frame.start)}</span>${esc(frame.description)}</figcaption><div class="frame-actions"><button class="btn btn--text" type="button" data-frame="${esc(frame.id)}">View larger</button>${playButton(frame.start)}</div></figure>`;
    }
    function citationsIn(chapter) {
        return content.lessons.flatMap(lesson => lesson.evidence
            .filter(evidence => evidence.start >= chapter.start && evidence.start < chapter.end)
            .map(evidence => ({ ...evidence, lesson })));
    }
    function privateChapterHTML(index) {
        if (!pack) return data.status === "unavailable" ? ""
            : '<p class="meta">Transcript loading…</p>';
        const chapter = chapters[index];
        const frameIds = [...new Set(citationsIn(chapter).map(evidence => evidence.frameId).filter(Boolean))];
        const frames = frameIds.map(id => pack.frames.find(frame => frame.id === id)).filter(Boolean).slice(0, 3);
        const entries = [...chapterPassages(pack.segments, chapter).map(passage => ({ start: passage.start, html: passageHTML(passage) })),
            ...frames.map(frame => ({ start: frame.start, html: frameHTML(frame) })),
            ...pack.gaps.filter(gap => gap.start >= chapter.start && gap.start < chapter.end).map(gap => ({
                start: gap.start,
                html: `<p class="tx-details-only"><span class="tx-gap">${time(gap.start)}–${time(gap.end)} · Untranscribed</span></p>`,
            }))].sort((a, b) => a.start - b.start);
        return `<div class="transcript"><div class="transcript__head"><h3 class="label">Machine transcript, corrected</h3><p class="transcript__legend tx-details-only">Original recognition and low-confidence words appear beneath each passage. An untranscribed interval does not prove silence.</p></div>${entries.map(entry => entry.html).join("")}</div>`;
    }
    function chapterHTML(index) {
        const chapter = chapters[index];
        const citations = citationsIn(chapter);
        return `<p class="chapter__summary">${esc(chapter.summary)}</p><div class="chapter__actions" data-private-play ${pack ? "" : "hidden"}>${playButton(chapter.start)}</div>
            ${citations.length ? `<div class="cited"><h3 class="label">Cited in the guide</h3><ul>${citations.map(evidence => `<li><button class="time-link" type="button" data-time="${evidence.start}">${time(evidence.start)}</button><span>${esc(evidence.paraphrase)}<a class="cited__lesson" href="#lesson/${evidence.lesson.id}">${esc(lessonTitle(evidence.lesson))}</a></span></li>`).join("")}</ul></div>` : ""}
            <div data-private-chapter="${index}" data-status="${data.status}">${privateChapterHTML(index)}</div>
            ${index + 1 < chapters.length ? `<div class="chapter__next"><button class="btn btn--text" type="button" data-chapter="${index + 1}">Next chapter: ${index + 2} · ${esc(chapters[index + 1].title)}</button></div>` : ""}`;
    }
    function openChapter(index) {
        const list = $("[data-transcript]", recording);
        $$(".chapter", list).forEach((element, i) => {
            const on = i === index;
            element.classList.toggle("is-open", on);
            $(".chapter__btn", element).setAttribute("aria-expanded", String(on));
            const panel = $(".chapter__panel", element);
            panel.hidden = !on;
            if (on && !panel.childElementCount) panel.innerHTML = chapterHTML(index);
        });
        expandedChapter = index;
        updateNow();
    }
    function aboutHTML() {
        if (!pack) return "";
        const provenance = pack.provenance;
        return `<p>Machine transcription with reviewed corrections, version ${esc(provenance.correctionVersion)}. It is not human-certified and may be wrong. The guide’s notes paraphrase the source rather than claiming verified quotations.</p>
            <p>${pack.corrections.length} corrections are disclosed at their passages. ${pack.gaps.length} intervals (${pack.gaps.reduce((sum, gap) => sum + gap.end - gap.start, 0).toFixed(2)} s in total) contain no transcribed speech; that is not proof of silence.</p>
            <div class="downloads"><a href="${packBase}/transcript.vtt" download>Captions (WebVTT)</a><button class="btn btn--text" type="button" data-transcript-download>Transcript (plain text)</button></div>
            <h3>About the source</h3><p>An on-screen caption labels Lauren Tan a software engineer at SpaceXAI. In speech, she says she joined Cursor about five months earlier and works at an AI lab. Both are retained; her employer is unresolved and the recording date is unknown. <a href="https://x.com/i/status/2108938132934533123" target="_blank" rel="noreferrer">Original post on X ↗</a></p>
            <details><summary>Corrections · ${pack.corrections.length}</summary>${pack.corrections.map(correctionDetails).join("")}</details>
            <details><summary>Untranscribed intervals · ${pack.gaps.length}</summary>${pack.gaps.map(gap => `<p>${time(gap.start)}–${time(gap.end)} · ${(gap.end - gap.start).toFixed(2)} s · ${esc(gap.note)}</p>`).join("")}</details>
            <details><summary>Editorial notes · ${content.contentCautions.length}</summary><ul>${content.contentCautions.map(note => `<li>${esc(note)}</li>`).join("")}</ul></details>
            <h3>Provenance</h3><dl><dt>Transcription</dt><dd>${esc(typeof provenance.models === "string" ? provenance.models : JSON.stringify(provenance.models))}</dd><dt>Speakers</dt><dd>${esc(provenance.speakerAssignment)}</dd><dt>Text on screen</dt><dd>${esc(provenance.ocrSearchPolicy)}</dd><dt>Source SHA-256</dt><dd class="source-hash">${esc(provenance.sourceSHA256)}</dd></dl>`;
    }
    const allCitations = content.lessons.flatMap((lesson, lessonIndex) => lesson.evidence.map((evidence, noteIndex) =>
        ({ ...evidence, lesson, lessonIndex, noteIndex })));
    $("[data-cited-total]").textContent = ` · ${allCitations.length}`;
    const citedIndex = $("[data-cited-index]");
    citedIndex.innerHTML = `<p class="cited-index__lead">Each line is our paraphrase, with the time it was said or shown and the lesson that cites it. Corrections, gaps and provenance are in <a href="#recording/about">About this transcript</a>; <a href="#terms">terms</a> are on the home page; your saved progress is in <button class="btn btn--text" type="button" data-open="settings">Settings</button>.</p>
        <label class="label" for="cited-filter">Filter</label><input type="search" id="cited-filter" placeholder="A word, a time or a lesson" />
        <p class="meta cited-index__count" role="status" data-cited-count>${allCitations.length} moments</p>
        ${content.lessons.map((lesson, lessonIndex) => `<section class="cited cited-index__group"><h3 class="label">Lesson ${lessonIndex + 1}\u00a0· ${esc(lessonTitle(lesson))}</h3><ul>${allCitations.filter(note => note.lesson === lesson).map(note => {
            const kind = note.label === "SHOWN" ? "shown on screen" : "said";
            const search = `${note.paraphrase} ${lessonTitle(lesson)} ${lesson.title} ${time(note.start)} ${time(note.end)} ${kind} ${lessonIndex + 1}`;
            return `<li data-cited-search="${esc(search)}"><button class="time-link" type="button" data-time="${note.start}">${time(note.start)}</button><span>${esc(note.paraphrase)}<a class="cited__lesson" href="#lesson/${lesson.id}/in-short">${kind} · note ${note.noteIndex + 1}</a></span></li>`;
        }).join("")}</ul></section>`).join("")}`;
    let citedTimer;
    const fold = text => text.normalize("NFD").replace(/\p{Diacritic}/gu, "").toLowerCase();
    $("#cited-filter").addEventListener("input", event => {
        const raw = event.target.value.trim();
        const query = fold(raw);
        let shown = 0;
        $$("[data-cited-search]", citedIndex).forEach(row => {
            row.hidden = !fold(row.dataset.citedSearch).includes(query);
            if (!row.hidden) shown++;
        });
        $$(".cited-index__group", citedIndex).forEach(group => group.hidden = !$$("li", group).some(row => !row.hidden));
        clearTimeout(citedTimer);
        citedTimer = setTimeout(() => $("[data-cited-count]").textContent = !query ? `${allCitations.length} moments`
            : shown ? `${shown} of ${allCitations.length}` : `Nothing matches “${raw}”`, 400);
    });
    $("[data-transcript]", recording).innerHTML = chapters.map((chapter, index) =>
        `<li class="chapter"><h2 class="chapter__h"><button class="chapter__btn" type="button" data-chapter="${index}" aria-expanded="false" aria-controls="ch${index + 1}"><span class="chapter__num">${index + 1}</span><span class="chapter__title">${esc(chapter.title)}</span><span class="chapter__time">${time(chapter.start)}–${time(chapter.end)}</span></button></h2><div class="chapter__panel" id="ch${index + 1}" hidden></div></li>`).join("");
    $$(".rec__chnav button", recording).forEach((button, index) => button.addEventListener("click", () => {
        if (button.getAttribute("aria-disabled") === "true") return;
        const next = Math.max(0, Math.min(chapters.length - 1, chapterAt(video.currentTime) + (index ? 1 : -1)));
        openChapter(next);
        seek(chapters[next].start);
    }));
    $("[data-transcript]").classList.toggle("show-details", progress.state.transcriptDetails === true);
    $("[data-opt=details]").addEventListener("change", event => {
        progress.set("transcriptDetails", event.target.checked);
        $("[data-transcript]").classList.toggle("show-details", event.target.checked);
    });
    $("[data-opt=describe]").addEventListener("change", event => {
        progress.set("descriptions", event.target.checked);
        $("[data-rec=describe-hint]").hidden = !event.target.checked;
        if (!event.target.checked) {
            const playing = player.playing;
            player.cancelDescription();
            if (playing) player.resume();
        }
    });
    $("[data-opt=captions]").addEventListener("change", event => {
        progress.set("captions", event.target.checked);
        applyCaptionPreference();
    });
    document.addEventListener("click", event => {
        const button = event.target.closest("button");
        if (!button) return;
        if (button.dataset.chapter != null) {
            const index = Number(button.dataset.chapter);
            openChapter(expandedChapter === index && button.matches(".chapter__btn") ? -1 : index);
        }
        if (button.dataset.frame) showFrame(button.dataset.frame);
        if (button.hasAttribute("data-recording-retry")) data.startPrivate();
        if (button.dataset.correction) {
            const container = $(".passage__corrections", button.closest(".passage"));
            const detail = $$("[data-correction-detail]", container).find(item => item.dataset.correctionDetail === button.dataset.correction);
            const open = button.getAttribute("aria-expanded") !== "true";
            button.setAttribute("aria-expanded", String(open));
            detail.open = open;
            container.hidden = !$$("details", container).some(item => item.open);
        }
        if (button.hasAttribute("data-transcript-download")) {
            downloadText("lauren-machine-transcript.txt", pack.segments.map(segment => `${time(segment.start)} ${segment.corrected}`).join("\n"));
        }
        if (button.hasAttribute("data-source-play")) {
            playFrom(sourceStart);
        }
        if (button.hasAttribute("data-playback-pause") || button.hasAttribute("data-narration-toggle")) {
            if (player.playing) player.pause(); else player.resume();
        }
    });

    function showFrame(id) {
        if (!pack) return;
        const direction = document.activeElement.closest("#frame")?.querySelector(":focus")?.dataset.frameStep;
        const found = pack.frames.findIndex(frame => frame.id === id);
        currentFrame = found < 0 ? 0 : found;
        const frame = pack.frames[currentFrame];
        const previous = pack.frames[currentFrame - 1];
        const next = pack.frames[currentFrame + 1];
        const dialog = $("#frame");
        if (!dialog.open) {
            frameTrigger = document.activeElement.closest("#search")
                ? $('[data-open="search"]') : document.activeElement;
        }
        if ($("#search").open) $("#search").close();
        $("#frame-title").textContent = `Shown on screen · ${time(frame.start)}`;
        $(".dlg__body", dialog).innerHTML = `<div class="frame-view"><div><img class="source-frame" src="${packBase}/${esc(frame.path)}" width="${frame.width}" height="${frame.height}" alt="${esc(frame.description)}" /><div class="frame-view__nav"><button class="btn" type="button" data-frame-step="previous" data-frame="${esc(previous?.id || frame.id)}" aria-label="${previous ? `Previous frame at ${time(previous.start)}` : "No previous frame"}" ${previous ? "" : "disabled"}>← ${previous ? time(previous.start) : "Previous"}</button><span class="meta">Frame ${currentFrame + 1} of ${pack.frames.length}</span><button class="btn" type="button" data-frame-step="next" data-frame="${esc(next?.id || frame.id)}" aria-label="${next ? `Next frame at ${time(next.start)}` : "No next frame"}" ${next ? "" : "disabled"}>${next ? time(next.start) : "Next"} →</button></div></div><div class="frame-view__meta"><p>${esc(frame.description)}</p>${playButton(frame.start)}<details class="ocr"><summary>Text on screen (machine OCR)</summary><pre><code>${esc(frame.ocr)}</code></pre></details><details><summary>Frame details</summary><p class="meta">${esc(frame.kind)} · ${esc(frame.timestampProvenance)} · ${esc(frame.visualConfidence)}</p><p class="source-hash">SHA-256 ${esc(frame.sha256)}</p></details></div></div>`;
        if (!dialog.open) dialog.showModal();
        else if (direction) {
            const candidate = $(`[data-frame-step="${direction}"]`, dialog);
            (candidate.disabled ? $("[data-frame-step]:not(:disabled)", dialog) || $("[data-close]", dialog) : candidate).focus({ preventScroll: true });
        }
    }
    $("#frame").addEventListener("close", () => {
        if (frameTrigger?.isConnected && frameTrigger.getClientRects().length) frameTrigger.focus({ preventScroll: true });
        frameTrigger = null;
    });
    const view = {
        video,
        get available() { return !!pack; },
        get searchRecords() { return sourceSearch(pack, chapters); },
        seek,
        playFrom,
        scrollToTime,
        retainPanelPlayhead() { panelReturnTime = null; },
        render(params) {
            if (pendingTimeScroll?.href !== location.href) pendingTimeScroll = null;
            const failed = data.status === "unavailable";
            const loading = !pack && !failed;
            const unavailable = $("[data-rec=unavailable]");
            const reason = `${data.packError} The lessons, experiments and lab still work, and every source note shows its time.`;
            if ($("p", unavailable).textContent !== reason) $("p", unavailable).textContent = reason;
            unavailable.hidden = !failed;
            $("[data-rec=available]").hidden = false;
            $(".rec__player", recording).hidden = failed;
            video.hidden = !pack;
            $("[data-rec=loading]").hidden = !loading;
            $$(".rec__options input", recording).forEach(input => input.disabled = !pack);
            $(".rec__now", recording).hidden = !pack;
            $(".rec__chnav", recording).hidden = !pack;
            $("#about-transcript").hidden = failed;
            $(".about-tx__body", recording).innerHTML = pack ? aboutHTML() : "<p class='meta'>Loading…</p>";
            $$("[data-private-chapter]", recording).forEach(region => {
                if (region.dataset.status !== data.status) {
                    region.innerHTML = privateChapterHTML(Number(region.dataset.privateChapter));
                    region.dataset.status = data.status;
                }
            });
            $$("[data-private-play]", recording).forEach(element => element.hidden = !pack);
            $("[data-rec=describe-hint]").hidden = !pack || !progress.state.descriptions;
            const resume = $("[data-recording-resume]");
            resume.hidden = !pack || progress.state.playback <= 0;
            resume.dataset.time = progress.state.playback;
            resume.textContent = `Resume at ${time(progress.state.playback)}`;
            if (params.has("about")) $("#about-transcript").open = true;
            if (params.has("cited")) $("#cited-moments").open = true;
            if (params.has("t")) {
                const continuing = continueRecordingHash === location.hash;
                continueRecordingHash = null;
                if (!continuing) seek(Number(params.get("t")));
                else openChapter(chapterAt(video.currentTime));
            }
            if (expandedChapter === -1 && !recording.hidden) openChapter(chapterAt(video.currentTime));
            updateNow();
        },
        fillSource(note) {
            const sameNote = activeNote === note;
            if (!sameNote) {
                if (!activeNote) { panelReturnTime = player.playing ? null : video.currentTime; panelPlayed = false; }
                player.clearDescription();
            }
            activeNote = note;
            sourceStart = note.start;
            if (!sameNote && !note.frame && !player.playing) seek(note.start);
            const source = $("#source");
            const media = $("[data-src=media]", source);
            const frame = note.frame ? pack?.frames.find(frame => frame.id === note.frameId) ||
                pack?.frames.reduce((best, frame) => Math.abs(frame.start - note.start) < Math.abs(best.start - note.start) ? frame : best) : null;
            if (video.parentElement === media && note.frame) player.move(recordingHost);
            [...media.children].filter(child => child !== video).forEach(child => child.remove());
            if (pack && frame) {
                media.insertAdjacentHTML("beforeend", `<button class="frame-image" type="button" data-frame="${esc(frame.id)}" aria-label="View frame at ${time(frame.start)}"><img class="source-frame" src="${packBase}/${esc(frame.path)}" width="${frame.width}" height="${frame.height}" alt="${esc(frame.description)}" /></button>`);
            } else if (pack) {
                player.move(media);
            }
            const rangeEnd = note.range?.split("–")[1]?.split(":").map(Number);
            const end = note.end ?? (rangeEnd?.length === 2 ? rangeEnd[0] * 60 + rangeEnd[1] : null);
            const excerpt = sourceExcerpt(pack?.segments || [], chapters[chapterAt(note.start)], note.start, end ?? note.start + 35);
            const prefix = note.frame ? "Said while it was on screen" : "Machine transcript";
            $("[data-src=tx-label]", source).textContent = excerpt.words
                ? `${prefix} · ${time(excerpt.start)}–${time(excerpt.end)}` : prefix;
            $("[data-src=tx-text]", source).innerHTML = excerpt.paragraphs.map(parts =>
                `<p>${parts.map(part => part.cited ? `<mark>${esc(part.text)}</mark>` : esc(part.text)).join("")}</p>`).join("");
            $("[data-src=play]", source).dataset.sourcePlay = "";
            $("[data-src=open]", source).href = `#recording/${note.start}`;
            $("[data-src=open]", source).textContent = "Open in the recording";
            const failed = data.status === "unavailable";
            media.hidden = failed;
            $("[data-src=actions]", source).hidden = !pack;
            $("[data-src=tx]", source).hidden = failed || Boolean(pack && !excerpt.words);
            if (!pack && !failed) {
                media.innerHTML = '<div class="media-loading"><span>Loading the recording…</span></div>';
                $("[data-src=tx-text]", source).textContent = "Loading the transcript…";
            }
            $("[data-src=unavailable]", source).hidden = !failed;
            $("[data-src=unavailable] p", source).textContent = "The recording isn’t available right now, so this note shows our paraphrase and its time only. The lessons and experiments still work.";
            updateNow();
        },
        restoreVideo() {
            if (panelReturnTime !== null && !panelPlayed) seek(panelReturnTime);
            panelReturnTime = null;
            panelPlayed = false;
            activeNote = null;
            player.clearDescription();
            player.move(recordingHost);
            updateNow();
        },
        syncProgress() {
            const target = progress.state.playback;
            suppressPlaybackSave = true;
            player.cancelDescription();
            player.clearDescription();
            player.pause();
            $("[data-opt=describe]").checked = progress.state.descriptions;
            applyCaptionPreference();
            $("[data-opt=details]").checked = progress.state.transcriptDetails === true;
            $("[data-transcript]").classList.toggle("show-details", progress.state.transcriptDetails === true);
            $("[data-rec=describe-hint]").hidden = !progress.state.descriptions;
            seek(target);
            suppressPlaybackSave = false;
        },
        updateNow,
        showFrame,
    };
    data.subscribe(() => {
        pack = data.pack;
        packBase = data.packBase;
        prepareVideo();
        view.render(new URLSearchParams());
        if (activeNote && $("#source").open) view.fillSource(activeNote);
        if (pack && pendingTimeScroll?.href === location.href && !recording.hidden) {
            const { seconds } = pendingTimeScroll;
            pendingTimeScroll = null;
            scrollToTime(seconds);
        }
    });
    view.ready = data.packPromise;
    view.render(new URLSearchParams());
    return view;
}
