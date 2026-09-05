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
  const expectedSectionIds = [
    "conversation",
    "relationships",
    "context-nonverbal",
    "speech-language",
    "masking",
    "repetition",
    "routine-interests",
    "interests-thinking",
    "sensory-body",
    "daily-regulation",
    "emotional-regulation",
    "childhood",
    "identity-style",
    "context-impact",
  ];

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

  test("provides a balanced bilingual form with one specific construct per question", () => {
    expect(sections.map((section) => section.id)).toEqual(expectedSectionIds);
    expect(questions.length).toBeGreaterThanOrEqual(220);
    expect(new Set(questions.map((question) => question.sectionId))).toEqual(
      new Set(sections.map((section) => section.id)),
    );

    const minimumSectionSizes: Record<string, number> = {
      conversation: 22,
      relationships: 18,
      "context-nonverbal": 12,
      "speech-language": 13,
      masking: 16,
      repetition: 12,
      "routine-interests": 15,
      "interests-thinking": 24,
      "sensory-body": 28,
      "daily-regulation": 17,
      "emotional-regulation": 17,
      childhood: 16,
      "identity-style": 12,
      "context-impact": 4,
    };
    for (const [sectionId, minimum] of Object.entries(minimumSectionSizes)) {
      expect(
        questions.filter((question) => question.sectionId === sectionId).length,
        sectionId,
      ).toBeGreaterThanOrEqual(minimum);
    }

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
    expect(childhood.length).toBeGreaterThanOrEqual(23);
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

  test("retains concrete daily-life, clothing, and humor constructs from the source corpus", () => {
    const constructs = new Set(questions.map((question) => question.construct));
    for (const construct of [
      "clothing-seams",
      "clothing-tags",
      "socks-sensory",
      "comfort-first-clothing",
      "bright-clothing-preference",
      "idiosyncratic-style-preference",
      "deadpan-humor",
      "inappropriate-moment-humor",
      "phone-call-avoidance",
      "delayed-text-reply",
      "toothbrushing-aversion",
      "familiar-service-preference",
      "noise-cancelling-support",
      "designated-seat",
      "chewing-sound-intolerance",
      "low-spontaneous-inviting",
      "low-spontaneous-daily-sharing",
      "others-need-extra-effort-to-understand",
      "invented-words",
      "masking-exposure-avoidance",
      "private-collapse-after-public-performance",
      "interest-collecting",
      "popular-culture-avoidance",
      "particular-voice-intolerance",
      "priority-setting-difficulty",
      "grocery-management",
      "education-difficulty-despite-ability",
      "sustained-nonspeaking",
      "vocabulary-mirroring",
      "defined-role-socializing-easier",
      "background-detail-overexplanation",
      "situational-speech-loss-under-stress",
      "fixed-task-method",
      "daily-ritual-sequence",
      "firm-contact-seeking",
      "deep-pressure-tool-preference",
      "strong-facial-expression",
      "delayed-emotional-expression",
      "excessive-gestures",
      "repetitive-gestures",
      "unnatural-gestures",
      "light-touch-intolerance",
      "sunscreen-aversion",
      "childhood-late-gestures",
      "childhood-late-receptive-language",
      "idiosyncratic-style-preference",
      "repeated-relationship-disruption",
      "repeated-housing-disruption",
      "face-to-face-communication-preference",
      "nonverbal-communication-preference",
      "call-ending-overthinking",
      "punctuation-overthinking",
      "emoji-overthinking",
      "reply-decision-overthinking",
      "rigid-dishwasher-loading",
      "rigid-grocery-bagging",
      "familiar-clothes-suddenly-wrong",
      "personally-loud-despite-sound-sensitivity",
      "ordinary-errand-exhaustion",
      "people-watching",
      "touch-greeting-discomfort",
      "missed-flirting",
      "literal-romantic-language",
      "sniffing-objects",
      "corner-of-eye-looking",
      "communicating-through-another-child",
      "third-person-self-reference",
      "self-taught-reading",
      "precocious-full-sentence-speech",
      "bra-sensory-intolerance",
      "jeans-sensory-intolerance",
      "protected-home-space",
      "hosting-distress",
      "literal-romance-sex-communication",
      "repeatedly-rewritten-lists",
      "bringing-own-food",
    ]) {
      expect(constructs.has(construct), construct).toBe(true);
    }

    for (const removed of ["atypical-humor", "vestibular-seeking", "vestibular-avoidance"]) {
      expect(constructs.has(removed), removed).toBe(false);
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

  test("applies the final wording and unsupported-item audit", () => {
    const byId = (id: string) => questions.find((question) => question.id === id);

    expect(byId("q91")?.text).toEqual({
      en: "I am, or have been, nonspeaking for a sustained period.",
      ru: "Я не пользуюсь устной речью сейчас или не пользовался ею в течение продолжительного периода.",
    });
    expect(byId("q177")?.text.ru).toBe(
      "Стремясь получить плотное телесное давление, я могу обнять человека сильнее, чем намеревался.",
    );
    expect(byId("q191")?.text.ru).toBe(
      "Сенсорные стимулы часто ощущаются необычно интенсивно сразу в нескольких видах ощущений.",
    );
    expect(byId("q242")?.text).toEqual({
      en: "During overload, I can become unable to respond.",
      ru: "Во время перегрузки я могу потерять способность отвечать.",
    });
    expect(byId("q248")?.construct).toBe("distress-when-misunderstood");
    expect(byId("q248")?.text).toEqual({
      en: "When I feel misunderstood, I can become very upset.",
      ru: "Когда мне кажется, что меня не поняли, я могу сильно расстроиться.",
    });
    expect(byId("q286")?.text).toEqual({
      en: "Managing groceries is unexpectedly difficult for me.",
      ru: "Мне неожиданно трудно организовывать всё, что связано с продуктами.",
    });
    expect(byId("q319")?.construct).toBe("literal-romantic-language");
    expect(byId("q319")?.text).toEqual({
      en: "In romantic relationships, I often take language literally.",
      ru: "В романтических отношениях я часто понимаю слова буквально.",
    });
    expect(byId("q234")).toBeUndefined();
    expect(byId("q283")).toBeUndefined();
  });

  test("keeps reviewed wording fixes and source-specific peer examples", () => {
    const byId = (id: string) => questions.find((question) => question.id === id);
    expect(byId("q72")?.text.en).toContain("younger");
    expect(byId("q72")?.text.en).toContain("older");
    expect(byId("q72")?.text.en).toContain("neurodivergent");
    expect(byId("q72")?.text.en).toContain("different gender");
    expect(byId("q137")?.text.ru).toBe(
      "Прерывание до завершения мысли или объяснения сильно выбивает меня из колеи.",
    );
    expect(byId("q176")?.text.ru).toContain("прикасаются ко мне");
    expect(byId("q217")?.text.ru).toContain("приёмы");
    expect(byId("q279")?.text.ru).toBe(
      "Я могу устанавливать зрительный контакт в необычный момент или поддерживать его дольше, чем ожидают другие.",
    );
    expect(byId("q289")?.text.en).toContain("public speaking");
    expect(byId("q289")?.text.en).toContain("in-person work");
    expect(byId("q166")?.sectionId).toBe("context-nonverbal");
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
