export const storageKey = "soyspray-agents:v1";

export function defaultState() {
    return {
        completed: [],
        adoption: {},
    };
}

export function readState(value, lessonIds) {
    if (!value || typeof value !== "object" || Array.isArray(value)) {
        throw new Error("Invalid progress file.");
    }
    if (!((!("descriptions" in value) || typeof value.descriptions === "boolean") &&
        Array.isArray(value.completed) &&
        value.completed.every(id => lessonIds.includes(id)) &&
        value.adoption && typeof value.adoption === "object" &&
        !Array.isArray(value.adoption) &&
        Object.entries(value.adoption).every(([key, text]) =>
            !/^(?:[0-9])$/.test(key) || typeof text === "string" && text.length <= 10000) &&
        (!("playback" in value) || Number.isFinite(value.playback) && value.playback >= 0) &&
        (!("lastLesson" in value) || value.lastLesson === null || typeof value.lastLesson === "string"))) {
        throw new Error("This file does not contain valid version 1 progress.");
    }
    return {
        ...value,
        completed: [...new Set(value.completed)],
        adoption: Object.fromEntries(Object.entries(value.adoption)),
    };
}

export async function loadWorkshop() {
    const response = await fetch("content.json");
    if (!response.ok) throw new Error("The study guide could not be loaded. Please reload.");
    const content = await response.json();
    const listeners = new Set();
    let settleFirst;
    let flight = null;
    const data = {
        content, pack: null, packBase: "", packError: "", packErrorClass: "", ready: false,
        status: "idle", packPromise: new Promise(resolve => { settleFirst = resolve; }),
        subscribe(listener) { listeners.add(listener); return () => listeners.delete(listener); },
        startPrivate,
    };
    function notify() { listeners.forEach(listener => listener(data)); }
    function startPrivate() {
        if (data.status === "ready") return Promise.resolve();
        if (flight) return flight;
        data.status = "loading";
        data.ready = false;
        data.packError = "";
        data.packErrorClass = "";
        notify();
        flight = (async () => {
            const controller = new AbortController();
            const timeout = setTimeout(() => controller.abort(), 20000);
            let failure = "network";
            let status = null;
            try {
                const options = { cache: "no-store", signal: controller.signal };
                const configResponse = await fetch("config.json", options);
                if (!configResponse.ok) { failure = "http"; status = configResponse.status; throw new Error(); }
                failure = "format";
                const config = await configResponse.json();
                if (!/^[a-f0-9]{64}$/.test(config.packHash)) throw new Error();
                const packBase = `/evidence/versions/${config.packHash}`;
                failure = "network";
                const packResponse = await fetch(`${packBase}/index.json`, options);
                if (!packResponse.ok) { failure = "http"; status = packResponse.status; throw new Error(); }
                failure = "format";
                const pack = await packResponse.json();
                if (pack.schemaVersion !== 1 || !Array.isArray(pack.segments) || !Array.isArray(pack.frames) ||
                    !Array.isArray(pack.corrections) || !Array.isArray(pack.gaps) || !Array.isArray(pack.narrationCues) ||
                    !Number.isFinite(pack.duration)) throw new Error();
                data.packBase = packBase;
                data.pack = pack;
                data.status = "ready";
            } catch {
                data.status = "unavailable";
                data.packErrorClass = controller.signal.aborted ? "timeout" : failure;
                data.packError = data.packErrorClass === "http" ? `The recording server returned HTTP ${status}.`
                    : data.packErrorClass === "timeout" ? "The recording did not respond within 20 seconds."
                    : data.packErrorClass === "format" ? "The recording data could not be read."
                    : "The recording could not be reached over the network.";
            } finally {
                clearTimeout(timeout);
                data.ready = true;
                flight = null;
                settleFirst();
                notify();
            }
        })();
        return flight;
    }

    return data;
}

// A passage groups consecutive source segments for reading. The original IDs,
// timings and wording stay available; grouping never manufactures punctuation,
// rewrites a quotation, or treats an untranscribed interval as silence.
export function chapterPassages(segments, chapter, targetWords = 95) {
    const selected = segments.filter(segment => segment.start >= chapter.start && segment.start < chapter.end);
    const passages = [];
    let group = [];
    let words = 0;
    function flush() {
        if (!group.length) return;
        passages.push({
            id: group[0].id,
            start: group[0].start,
            end: group[group.length - 1].end,
            segments: group,
            text: group.map(segment => segment.corrected).join(" "),
        });
        group = [];
        words = 0;
    }
    for (const segment of selected) {
        group.push(segment);
        words += segment.corrected.trim().split(/\s+/).length;
        if (words >= targetWords) flush();
    }
    flush();
    return passages;
}

export function sourceExcerpt(segments, chapter, from, to, contextWords = 15) {
    const normal = word => word.toLowerCase().replace(/[^\p{L}\p{N}]/gu, "");
    const passages = chapterPassages(segments, chapter);
    const passageBySegment = new Map(passages.flatMap(passage => passage.segments.map(segment => [segment.id, passage.id])));
    const tokens = [];
    for (const segment of segments) {
        if (segment.start >= chapter.end || segment.end <= chapter.start) continue;
        const matches = [...segment.corrected.matchAll(/\S+/gu)];
        const words = segment.words || [];
        const aligned = matches.length === words.length && matches.every((match, i) =>
            normal(match[0]) === normal(words[i].word) && Number.isFinite(words[i].start) && Number.isFinite(words[i].end));
        // Corrected wording without a proven word alignment keeps its segment
        // timing. Do not manufacture word times or cross a chapter boundary.
        if (!aligned && (segment.start < chapter.start || segment.end > chapter.end)) continue;
        let previous = 0;
        for (const [i, match] of matches.entries()) {
            const start = aligned ? words[i].start : segment.start;
            const end = aligned ? words[i].end : segment.end;
            const prefix = segment.corrected.slice(previous, match.index);
            previous = match.index + match[0].length;
            if (start < chapter.start || end > chapter.end) continue;
            tokens.push({ text: `${i === 0 && tokens.length ? " " : ""}${prefix}${match[0]}`, start, end,
                cited: end > from && start < to, passage: passageBySegment.get(segment.id) || segment.id });
        }
    }
    const first = tokens.findIndex(token => token.cited);
    if (first < 0) return { paragraphs: [], start: from, end: Math.min(to, chapter.end), words: 0, long: false };
    const last = tokens.findLastIndex(token => token.cited);
    const selected = tokens.slice(Math.max(0, first - contextWords), Math.min(tokens.length, last + contextWords + 1));
    const long = tokens.slice(first, last + 1).filter(token => token.cited).length > 200;
    const paragraphs = [];
    let passage;
    for (const token of selected) {
        if (!paragraphs.length || long && passage !== token.passage) paragraphs.push([]);
        passage = token.passage;
        const parts = paragraphs.at(-1), previous = parts.at(-1);
        if (previous?.cited === token.cited) previous.text += token.text;
        else parts.push({ text: token.text, cited: token.cited });
    }
    paragraphs[0][0].text = paragraphs[0][0].text.trimStart();
    return { paragraphs, start: selected[0].start, end: selected.at(-1).end, words: selected.length, long };
}

export function sourceSearch(pack, chapters) {
    if (!pack) return [];
    return [
        ...chapters.flatMap(chapter => chapterPassages(pack.segments, chapter).map(passage => ({
            g: "Recording", title: chapter.title,
            text: passage.text, search: `${passage.text} ${passage.segments.map(segment => segment.raw).join(" ")}`,
            t: passage.start,
        }))),
        ...pack.frames.filter(frame => frame.ocr).map(frame => ({
            g: "Shown on screen", title: "Text on screen · machine OCR",
            text: frame.ocr, search: frame.ocr, t: frame.start, frame: frame.id,
        })),
    ];
}
