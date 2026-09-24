import { describe, expect, test } from "vitest";

import {
  appCopy,
  imageCredits,
  instrumentReviews,
  officialGuidance,
  questions,
  sections,
  sources,
} from "./index";
import { uiCopy } from "../ui-copy";

const normalized = (value: string) =>
  value
    .normalize("NFKC")
    .toLocaleLowerCase("en")
    .replace(/[^\p{L}\p{N}]+/gu, " ")
    .trim();

describe("assessment content", () => {
  test("keeps every interface string available in both languages", () => {
    expect(Object.keys(uiCopy.en).sort()).toEqual(Object.keys(uiCopy.ru).sort());
  });

  test("keeps the owner's disclosure and medical limits clear in both languages", () => {
    expect(appCopy.en.ownerIntro).toBe(
      "I am already diagnosed with mild ASD and am taking this test for a video.",
    );
    expect(appCopy.ru.ownerIntro).toBeTruthy();
    for (const copy of [appCopy.en, appCopy.ru]) {
      expect(copy.medicalNote).toBeTruthy();
      expect(copy.resultDisclaimer).toBeTruthy();
    }
    expect(appCopy.en.medicalNote).toMatch(/not a diagnos/i);
    expect(appCopy.en.resultDisclaimer).toMatch(/not a diagnos/i);
    expect(appCopy.en.resultDisclaimer).toMatch(/qualified specialist/i);
    expect(appCopy.ru.medicalNote).toMatch(/не диагност/i);
    expect(appCopy.ru.resultDisclaimer).toMatch(/не диагноз/i);
    expect(appCopy.ru.resultDisclaimer).toMatch(/специалист/i);
  });

  test("lists every caption-backed source with bilingual metadata", () => {
    expect(sources.length).toBeGreaterThan(0);
    expect(new Set(sources.map((source) => source.id)).size).toBe(sources.length);

    for (const source of sources) {
      expect(source.title).toBeTruthy();
      expect(source.creator).toBeTruthy();
      expect(source.url).toMatch(/^https:\/\/www\.youtube\.com\/watch\?v=[\w-]+$/);
      expect(source.sourceType.en).toBeTruthy();
      expect(source.sourceType.ru).toBeTruthy();
      expect(source.originalLanguage.en).toBeTruthy();
      expect(source.originalLanguage.ru).toBeTruthy();
      expect(source.captionBasis.en).toBeTruthy();
      expect(source.captionBasis.ru).toBeTruthy();
    }
  });

  test("provides a sourced bilingual form with unique questions in every section", () => {
    expect(sections.length).toBeGreaterThan(0);
    expect(new Set(sections.map((section) => section.id)).size).toBe(sections.length);
    expect(new Set(questions.map((question) => question.sectionId))).toEqual(
      new Set(sections.map((section) => section.id)),
    );

    const ids = questions.map((question) => question.id);
    const constructs = questions.map((question) => question.construct);
    const english = questions.map((question) => normalized(question.text.en));
    const russian = questions.map((question) => normalized(question.text.ru));

    expect(new Set(ids).size).toBe(ids.length);
    expect(new Set(constructs).size).toBe(constructs.length);
    expect(new Set(english).size).toBe(english.length);
    expect(new Set(russian).size).toBe(russian.length);

    for (const question of questions) {
      expect(question.text.en).toBeTruthy();
      expect(question.text.ru).toBeTruthy();
      expect(question.construct).toMatch(/^[a-z0-9-]+$/);
      expect(question).not.toHaveProperty("reviewedForDuplication");
      expect(question).not.toHaveProperty("reviewedForDoubleBarrelled");
      expect(question.sourceIds.length).toBeGreaterThanOrEqual(1);
      for (const sourceId of question.sourceIds) {
        expect(sources.some((source) => source.id === sourceId)).toBe(true);
      }
    }
  });

  test("keeps retrospective uncertainty separate and excludes unsafe scoring labels", () => {
    const childhood = questions.filter((question) => question.responseKind === "retrospective");
    const other = questions.filter((question) => question.responseKind !== "retrospective");
    expect(childhood.length).toBeGreaterThan(0);
    expect(childhood.every((question) => question.allowUnknown && question.allowNotApplicable)).toBe(
      true,
    );
    expect(other.every((question) => !question.allowUnknown && !question.allowNotApplicable)).toBe(
      true,
    );

    const scoringText = questions.map((question) => question.text.en).join(" ").toLowerCase();
    for (const excluded of [
      "high functioning",
      "low functioning",
      "asperger",
      "aggression",
      "self-injury",
    ]) {
      expect(scoringText).not.toContain(excluded);
    }
  });

  test("keeps reviewed raw-source provenance exact where the audit identified one source", () => {
    const sourceByQuestion: Record<string, string> = {
      q91: "s18",
      q185: "s07",
      q248: "s05",
      q263: "s03",
      q264: "s04",
      q267: "s04",
      q269: "s04",
      q270: "s04",
      q272: "s04",
      q277: "s06",
      q92: "s17",
      q188: "s04",
      q192: "s06",
      q197: "s21",
      q198: "s21",
      q203: "s24",
      q205: "s12",
      q207: "s07",
      q208: "s07",
      q216: "s15",
      q220: "s12",
      q280: "s21",
      q281: "s04",
      q285: "s07",
      q286: "s15",
      q287: "s14",
      q289: "s21",
    };

    for (const [id, sourceId] of Object.entries(sourceByQuestion)) {
      expect(questions.find((question) => question.id === id)?.sourceIds, id).toEqual([sourceId]);
    }
  });

  test("keeps each new human example tied to its exact raw source", () => {
    const sourceByConstruct: Record<string, string> = {
      "vocabulary-mirroring": "s11",
      "defined-role-socializing-easier": "s11",
      "conversation-information-monologue": "s09",
      "background-detail-overexplanation": "s12",
      "copied-social-presentation": "s14",
      "structured-socializing-easier": "s14",
      "situational-speech-loss-under-stress": "s12",
      "overload-inward-shutdown": "s02",
      "fixed-task-method": "s02",
      "daily-ritual-sequence": "s22",
      "firm-contact-seeking": "s02",
      "deep-pressure-tool-preference": "s09",
      "deadpan-humor": "s06",
      "strong-facial-expression": "s09",
      "repetitive-gestures": "s21",
      "unnatural-gestures": "s21",
      "excessive-gestures": "s21",
      "light-touch-intolerance": "s14",
      "sunscreen-aversion": "s12",
      "childhood-late-gestures": "s17",
      "childhood-late-receptive-language": "s30",
      "idiosyncratic-style-preference": "s14",
      "repeated-relationship-disruption": "s14",
      "repeated-housing-disruption": "s14",
      "face-to-face-communication-preference": "s04",
      "nonverbal-communication-preference": "s04",
      "call-ending-overthinking": "s07",
      "punctuation-overthinking": "s07",
      "emoji-overthinking": "s07",
      "reply-decision-overthinking": "s07",
      "rigid-dishwasher-loading": "s07",
      "rigid-grocery-bagging": "s07",
      "familiar-clothes-suddenly-wrong": "s06",
      "personally-loud-despite-sound-sensitivity": "s05",
      "ordinary-errand-exhaustion": "s06",
      "people-watching": "s06",
      "touch-greeting-discomfort": "s06",
      "missed-flirting": "s11",
      "literal-romantic-language": "s11",
      "sniffing-objects": "s17",
      "corner-of-eye-looking": "s17",
      "communicating-through-another-child": "s21",
      "third-person-self-reference": "s21",
      "self-taught-reading": "s04",
      "precocious-full-sentence-speech": "s04",
      "bra-sensory-intolerance": "s14",
      "jeans-sensory-intolerance": "s14",
      "protected-home-space": "s05",
      "hosting-distress": "s05",
      "literal-romance-sex-communication": "s14",
      "repeatedly-rewritten-lists": "s14",
      "bringing-own-food": "s14",
    };

    for (const [construct, sourceId] of Object.entries(sourceByConstruct)) {
      expect(
        questions.find((question) => question.construct === construct)?.sourceIds,
        construct,
      ).toEqual([sourceId]);
    }
  });

  test("keeps developmental language regression retrospective and honest about uncertainty", () => {
    const regression = questions.find((question) => question.id === "q92");
    expect(regression?.sectionId).toBe("childhood");
    expect(regression?.responseKind).toBe("retrospective");
    expect(regression?.allowUnknown).toBe(true);
    expect(regression?.allowNotApplicable).toBe(true);
    expect(regression?.text.en).toContain("Before age 12");
    expect(regression?.text.ru).toContain("До 12 лет");
  });

  test("records one local CC0 image credit for every major assessment section", () => {
    expect(new Set(sections.map((section) => section.imageId))).toEqual(
      new Set(imageCredits.map((image) => image.id)),
    );
    for (const image of imageCredits) {
      expect(image.localPath).toMatch(/^\/images\/[a-z0-9-]+\.webp$/);
      expect(image.creator).toBeTruthy();
      expect(image.license).toBe("CC0 1.0");
      expect(image.sourceUrl).toMatch(/^https:\/\//);
      expect(image.downloadUrl).toMatch(/^https:\/\//);
      expect(image.alt.en).toBeTruthy();
      expect(image.alt.ru).toBeTruthy();
    }
  });

  test("documents official cross-checks and questionnaire reuse decisions", () => {
    expect(officialGuidance.length).toBeGreaterThan(0);
    expect(instrumentReviews.length).toBeGreaterThan(0);
    for (const item of [...officialGuidance, ...instrumentReviews]) {
      expect(item.name).toBeTruthy();
      expect(item.url).toMatch(/^https:\/\//);
    }
    expect(instrumentReviews.every((item) => item.reuseDecision.en && item.reuseDecision.ru)).toBe(
      true,
    );
    expect(instrumentReviews.every((item) => item.included === false)).toBe(true);
  });
});
