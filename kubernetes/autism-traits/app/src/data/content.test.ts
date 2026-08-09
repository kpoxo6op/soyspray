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

  test("preserves the protected first-person and medical wording", () => {
    expect(appCopy.en.ownerIntro).toBe(
      "I am already diagnosed with mild ASD and am taking this test for a video.",
    );
    expect(appCopy.en.medicalNote).toBe(
      "This is not a diagnostic test. If it makes you curious, seek a professional assessment like I did.",
    );
    expect(appCopy.en.resultDisclaimer).toBe(
      "This is an estimate of trait resonance, not a diagnosis. Diagnosis requires a qualified specialist.",
    );
    expect(appCopy.ru.ownerIntro).toBeTruthy();
    expect(appCopy.ru.medicalNote).toBeTruthy();
    expect(appCopy.ru.resultDisclaimer).toBeTruthy();
  });

  test("lists every caption-backed source with bilingual metadata", () => {
    expect(sources).toHaveLength(30);
    expect(sources.map((source) => source.id)).toEqual(
      Array.from({ length: 30 }, (_, index) => `s${String(index + 1).padStart(2, "0")}`),
    );

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

    expect(new Set(sources.map((source) => source.languageCode))).toEqual(
      new Set(["en", "ru", "pt-BR", "ko"]),
    );
  });

  test("provides a balanced bilingual form with one reviewed construct per question", () => {
    expect(sections).toHaveLength(10);
    expect(questions).toHaveLength(50);
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
      expect(question.reviewedForDuplication).toBe(true);
      expect(question.reviewedForDoubleBarrelled).toBe(true);
      expect(question.sourceIds.length).toBeGreaterThanOrEqual(2);
      for (const sourceId of question.sourceIds) {
        expect(sources.some((source) => source.id === sourceId)).toBe(true);
      }
    }
  });

  test("keeps retrospective uncertainty separate and excludes weak scoring stereotypes", () => {
    const childhood = questions.filter((question) => question.responseKind === "retrospective");
    const other = questions.filter((question) => question.responseKind !== "retrospective");
    expect(childhood).toHaveLength(5);
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
      "depression",
      "sleep",
      "aggression",
      "self-injury",
      "gender",
      "bright colors",
      "clumsy",
    ]) {
      expect(scoringText).not.toContain(excluded);
    }
  });

  test("records one local CC0 image credit for every major assessment section", () => {
    expect(imageCredits).toHaveLength(sections.length);
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
    expect(officialGuidance.length).toBeGreaterThanOrEqual(5);
    expect(instrumentReviews.length).toBeGreaterThanOrEqual(8);
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
