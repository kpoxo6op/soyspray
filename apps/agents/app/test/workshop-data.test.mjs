import test from "node:test";
import assert from "node:assert/strict";
import { chapterPassages, defaultState, readState, sourceExcerpt, sourceSearch } from "../src/workshop-data.js";

// Contract: a chapter reader keeps every source segment in order, including a
// final short passage, and assigns boundary segments to one chapter. A grouping
// loop could drop its unfinished tail; the media intake tests do not own UI
// passage grouping.
test("reading passages preserve source identity, wording and chapter boundaries", () => {
    const segments = [
        { id: "a", start: 0, end: 2, raw: "raw a", corrected: "one two three" },
        { id: "b", start: 2, end: 4, raw: "raw b", corrected: "four five" },
        { id: "c", start: 4, end: 5, raw: "raw c", corrected: "six" },
        { id: "d", start: 5, end: 7, raw: "raw d", corrected: "next chapter" },
    ];
    const first = chapterPassages(segments, { start: 0, end: 5 }, 4);
    const second = chapterPassages(segments, { start: 5, end: 7 }, 4);
    assert.deepEqual(first.map(passage => passage.text), ["one two three four five", "six"]);
    assert.deepEqual([...first, ...second].flatMap(passage => passage.segments), segments);
    assert.equal(first[1].start, 4);
    assert.equal(first[1].end, 5);
});

// Contract: legacy v1 progress imports without discarding valid extra fields,
// while malformed identities, known field types and prompt answers are rejected. A whitelist
// reader loses preferences written by a newer client; extend this existing
// import-boundary case rather than add an overlapping storage test.
test("progress imports retain v1 notes and reject malformed local data", () => {
    const old = { ...defaultState(), completed: ["l1"], adoption: { 0: "Try one verifier." },
        depth: { futurePreference: "open-example" }, theme: "future-theme",
        recordingPreferences: { captions: false, transcriptDetails: true },
        futureReadingNotes: ["Keep this value unchanged.", { revision: 2 }],
    };
    old.adoption.future = { preserve: [true, 2] };
    delete old.playback;
    delete old.lastLesson;
    const imported = readState(old, ["l1"]);
    assert.deepEqual(imported, { ...defaultState(), ...old });
    assert.deepEqual(readState(JSON.parse(JSON.stringify(imported)), ["l1"]), imported);
    for (const bad of [
        { ...old, completed: ["missing"] },
        { ...old, descriptions: "true" },
        { ...old, adoption: { 0: ["not a note"] } },
        { ...old, playback: -1 },
        { ...old, lastLesson: {} },
    ]) assert.throws(() => readState(bad, ["l1"]));
});

// Contract: cited speech has bounded context, unchanged corrected wording and
// real timing. Passage grouping does not own citation highlighting; distributing
// new words across a corrected segment would fabricate alignment.
test("source excerpts bound context and retain honest timing for corrections", () => {
    const words = Array.from({ length: 70 }, (_, i) => ({ word: `word${i}`, start: i, end: i + 1 }));
    const segment = { id: "owned", start: 0, end: 70, corrected: words.map(w => w.word).join(" "), words };
    const excerpt = sourceExcerpt([segment], { start: 0, end: 60 }, 20, 25);
    assert.equal(excerpt.words, 35);
    assert.equal(excerpt.start, 5);
    assert.equal(excerpt.end, 40);
    assert.equal(excerpt.paragraphs.flat().filter(p => p.cited).map(p => p.text).join("").trim(), "word20 word21 word22 word23 word24");
    const edge = sourceExcerpt([segment], { start: 20, end: 30 }, 21, 25);
    assert.equal(edge.start, 20);
    assert.equal(edge.end, 30);
    const corrected = { id: "reviewed", start: 10, end: 20, corrected: "Reviewed replacement <script> text.", words: [{ word: "Original", start: 10, end: 11 }] };
    const coarse = sourceExcerpt([corrected], { start: 0, end: 30 }, 12, 13);
    assert.equal(coarse.start, 10);
    assert.equal(coarse.end, 20);
    assert.deepEqual(coarse.paragraphs, [[{ text: corrected.corrected, cited: true }]]);
    const longSegments = Array.from({ length: 7 }, (_, n) => {
        const words = Array.from({ length: 50 }, (_, i) => ({ word: `s${n}w${i}`, start: n * 50 + i, end: n * 50 + i + 1 }));
        return { id: `s${n}`, start: n * 50, end: (n + 1) * 50, words, corrected: words.map(w => w.word).join(" ") };
    });
    const long = sourceExcerpt(longSegments, { start: 0, end: 350 }, 50, 300);
    assert.ok(long.long);
    assert.ok(long.paragraphs.length > 1);
    assert.equal(long.paragraphs.flat().filter(p => p.cited).map(p => p.text).join(" ").trim().split(/\s+/).length, 250);
});

// Contract: source search indexes original and corrected recognition plus every
// OCR-bearing frame, seeking to the readable passage start. Searching only a
// curated list would miss source wording; segment-level results would fragment
// one reading passage. The grouping test does not own the search projection.
test("source search reaches original recognition and frame OCR", () => {
    const pack = {
        segments: [
            { id: "s", start: 2, end: 3, raw: "recogniser spelling", corrected: "reviewed spelling" },
            { id: "t", start: 3, end: 4, raw: "another recognition", corrected: "more reviewed wording" },
            { id: "u", start: 5, end: 6, raw: "next chapter", corrected: "next chapter" },
        ],
        frames: [{ id: "f", start: 3, ocr: "text on a slide" }, { id: "empty", start: 4, ocr: "" }],
    };
    const records = sourceSearch(pack, [{ start: 0, end: 5, title: "Chapter" }, { start: 5, end: 8, title: "Next" }]);
    assert.equal(records.length, 3);
    assert.match(records[0].search, /recogniser spelling/);
    assert.match(records[0].search, /another recognition/);
    assert.equal(records[0].text, "reviewed spelling more reviewed wording");
    assert.equal(records[0].t, 2);
    assert.equal(records[1].t, 5);
    assert.equal(records[2].frame, "f");
    assert.equal(records[2].text, "text on a slide");
});
