import { describe, expect, test } from "vitest";

import { questions, sections } from "../data";
import {
  DOMAIN_WEIGHTS,
  canReveal,
  combineDomainScores,
  getBand,
  markerPercent,
  normalizeAnswers,
  scoreAssessment,
  type Answer,
} from "./scoring";

const answeredWith = (value: Answer): Record<string, Answer> =>
  Object.fromEntries(questions.map((question) => [question.id, value]));

describe("custom trait-resonance scoring", () => {
  test("normalizes answered values and excludes unavailable retrospective values", () => {
    expect(normalizeAnswers([0, 4])).toBe(50);
    expect(normalizeAnswers([4, "unknown", "not-applicable"])).toBe(100);
    expect(normalizeAnswers(["unknown", "not-applicable"])).toBeNull();
  });

  test("normalizes domains before applying domain weights", () => {
    expect(
      combineDomainScores([
        { score: 100, weight: 1, answered: 2 },
        { score: 0, weight: 1, answered: 20 },
      ]),
    ).toBe(50);
    expect(
      combineDomainScores([
        { score: null, weight: 2, answered: 0 },
        { score: 75, weight: 1, answered: 4 },
      ]),
    ).toBe(75);
  });

  test("requires every prompt while accepting unknown childhood history", () => {
    const complete = answeredWith(2);
    expect(canReveal(complete, questions)).toBe(true);

    const missing = { ...complete };
    delete missing[questions[0].id];
    expect(canReveal(missing, questions)).toBe(false);

    const uncertainHistory = { ...complete };
    for (const question of questions.filter((item) => item.responseKind === "retrospective")) {
      uncertainHistory[question.id] = "unknown";
    }
    expect(canReveal(uncertainHistory, questions)).toBe(true);
  });

  test("covers both extreme answer patterns without decimal precision", () => {
    const minimum = scoreAssessment(answeredWith(0), questions, sections);
    const maximum = scoreAssessment(answeredWith(4), questions, sections);

    expect(minimum.overall).toBe(0);
    expect(maximum.overall).toBe(100);
    expect(Number.isInteger(minimum.overall)).toBe(true);
    expect(Number.isInteger(maximum.overall)).toBe(true);
    expect(minimum.band).toBe(getBand(minimum.overall));
    expect(maximum.band).toBe(getBand(maximum.overall));
  });

  test("handles missing childhood history without lowering other domains", () => {
    const answers = answeredWith(3);
    for (const question of questions.filter((item) => item.responseKind === "retrospective")) {
      answers[question.id] = "not-applicable";
    }

    const result = scoreAssessment(answers, questions, sections);
    const childhood = result.domains.find((domain) => domain.sectionId === "childhood");
    expect(childhood?.score).toBeNull();
    expect(result.overall).toBe(75);
  });

  test("defines every interpretation boundary and keeps the marker on the continuum", () => {
    expect(getBand(0)).toBe("almost-none");
    expect(getBand(14)).toBe("almost-none");
    expect(getBand(15)).toBe("low");
    expect(getBand(34)).toBe("low");
    expect(getBand(35)).toBe("moderate");
    expect(getBand(54)).toBe("moderate");
    expect(getBand(55)).toBe("high");
    expect(getBand(74)).toBe("high");
    expect(getBand(75)).toBe("very-high");
    expect(getBand(100)).toBe("very-high");
    expect(markerPercent(-1)).toBe(0);
    expect(markerPercent(50)).toBe(50);
    expect(markerPercent(101)).toBe(100);
  });

  test("keeps core domains stronger than general impact context", () => {
    expect(Object.keys(DOMAIN_WEIGHTS)).toEqual([
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
    ]);
    const total = Object.values(DOMAIN_WEIGHTS).reduce((sum, weight) => sum + weight, 0);
    expect(total).toBeCloseTo(1, 10);
    expect(DOMAIN_WEIGHTS["context-impact"]).toBeLessThan(
      DOMAIN_WEIGHTS["context-nonverbal"],
    );
    expect(DOMAIN_WEIGHTS["daily-regulation"]).toBeLessThan(
      DOMAIN_WEIGHTS["routine-interests"],
    );
  });
});
