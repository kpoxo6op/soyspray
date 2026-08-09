import type { Question, Section } from "../data";
import type { AnswerValue } from "./state";

export type Answer = AnswerValue;
export type Band = "almost-none" | "low" | "moderate" | "high" | "very-high";

export const DOMAIN_WEIGHTS: Record<string, number> = {
  conversation: 0.1,
  relationships: 0.08,
  "context-nonverbal": 0.09,
  "speech-language": 0.07,
  masking: 0.07,
  repetition: 0.08,
  "routine-interests": 0.09,
  "interests-thinking": 0.09,
  "sensory-body": 0.1,
  "daily-regulation": 0.05,
  "emotional-regulation": 0.05,
  childhood: 0.07,
  "identity-style": 0.03,
  "context-impact": 0.03,
};

const isNumericAnswer = (answer: Answer | undefined): answer is 0 | 1 | 2 | 3 | 4 =>
  typeof answer === "number" && Number.isInteger(answer) && answer >= 0 && answer <= 4;

export const normalizeAnswers = (answers: Answer[]): number | null => {
  const scored = answers.filter(isNumericAnswer);
  if (scored.length === 0) return null;
  return Math.round(
    (scored.reduce<number>((sum, answer) => sum + answer, 0) / (scored.length * 4)) * 100,
  );
};

export const combineDomainScores = (
  domains: Array<{ score: number | null; weight: number; answered: number }>,
): number => {
  const available = domains.filter(
    (domain): domain is { score: number; weight: number; answered: number } =>
      domain.score !== null && domain.weight > 0,
  );
  const availableWeight = available.reduce((sum, domain) => sum + domain.weight, 0);
  if (availableWeight === 0) return 0;
  return Math.round(
    available.reduce((sum, domain) => sum + domain.score * domain.weight, 0) / availableWeight,
  );
};

export const canReveal = (
  answers: Record<string, Answer>,
  assessmentQuestions: Question[],
): boolean => {
  if (assessmentQuestions.length === 0) return false;
  const everyPromptAnswered = assessmentQuestions.every((question) => {
    const answer = answers[question.id];
    if (isNumericAnswer(answer)) return true;
    return (
      question.responseKind === "retrospective" &&
      ((question.allowUnknown && answer === "unknown") ||
        (question.allowNotApplicable && answer === "not-applicable"))
    );
  });
  if (!everyPromptAnswered) return false;

  const numericAnswers = assessmentQuestions.filter((question) =>
    isNumericAnswer(answers[question.id]),
  );
  const numericDomains = new Set(numericAnswers.map((question) => question.sectionId));
  return numericAnswers.length >= Math.ceil(assessmentQuestions.length * 0.75) && numericDomains.size >= 8;
};

export const getBand = (score: number): Band => {
  const bounded = markerPercent(score);
  if (bounded < 15) return "almost-none";
  if (bounded < 35) return "low";
  if (bounded < 55) return "moderate";
  if (bounded < 75) return "high";
  return "very-high";
};

export const markerPercent = (score: number): number =>
  Math.min(100, Math.max(0, Number.isFinite(score) ? score : 0));

export type DomainScore = {
  sectionId: string;
  score: number | null;
  answered: number;
};

export type AssessmentResult = {
  overall: number;
  band: Band;
  domains: DomainScore[];
  strongestSectionId: string | null;
  weakestSectionId: string | null;
};

export const scoreAssessment = (
  answers: Record<string, Answer>,
  assessmentQuestions: Question[],
  assessmentSections: Section[],
): AssessmentResult => {
  if (!canReveal(answers, assessmentQuestions)) {
    throw new Error("The assessment does not have enough completed answers.");
  }

  const domains = assessmentSections.map((section) => {
    const sectionAnswers = assessmentQuestions
      .filter((question) => question.sectionId === section.id)
      .map((question) => answers[question.id]);
    return {
      sectionId: section.id,
      score: normalizeAnswers(sectionAnswers),
      answered: sectionAnswers.filter(isNumericAnswer).length,
    };
  });
  const overall = combineDomainScores(
    domains.map((domain) => ({
      ...domain,
      weight: DOMAIN_WEIGHTS[domain.sectionId] ?? 0,
    })),
  );
  const comparable = domains.filter(
    (domain): domain is DomainScore & { score: number } =>
      domain.score !== null && domain.sectionId !== "context-impact",
  );
  const strongest = comparable.reduce<(DomainScore & { score: number }) | null>(
    (current, domain) => (!current || domain.score > current.score ? domain : current),
    null,
  );
  const weakest = comparable.reduce<(DomainScore & { score: number }) | null>(
    (current, domain) => (!current || domain.score < current.score ? domain : current),
    null,
  );

  return {
    overall,
    band: getBand(overall),
    domains,
    strongestSectionId: strongest?.sectionId ?? null,
    weakestSectionId: weakest?.sectionId ?? null,
  };
};
