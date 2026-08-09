export const CURRENT_STATE_VERSION = 1;

export type Language = "en" | "ru";
export type AnswerValue = 0 | 1 | 2 | 3 | 4 | "unknown" | "not-applicable";

export type AssessmentState = {
  version: number;
  language: Language;
  answers: Record<string, AnswerValue>;
  revealed: boolean;
  started: boolean;
  lastSectionId: string | null;
};

export type AssessmentAction =
  | { type: "set-language"; language: Language }
  | { type: "visit-section"; sectionId: string }
  | { type: "answer"; questionId: string; value: AnswerValue }
  | { type: "reveal" }
  | { type: "reset" }
  | { type: "retake"; firstSectionId: string };

export const initialState = (language: Language = "en"): AssessmentState => ({
  version: CURRENT_STATE_VERSION,
  language,
  answers: {},
  revealed: false,
  started: false,
  lastSectionId: null,
});

export const reduceAssessmentState = (
  state: AssessmentState,
  action: AssessmentAction,
): AssessmentState => {
  switch (action.type) {
    case "set-language":
      return { ...state, language: action.language };
    case "visit-section":
      return { ...state, started: true, lastSectionId: action.sectionId };
    case "answer":
      return {
        ...state,
        answers: { ...state.answers, [action.questionId]: action.value },
        revealed: false,
      };
    case "reveal":
      return { ...state, revealed: true };
    case "reset":
      return initialState(state.language);
    case "retake":
      return {
        ...initialState(state.language),
        started: true,
        lastSectionId: action.firstSectionId,
      };
  }
};

const isAnswerValue = (value: unknown): value is AnswerValue =>
  (typeof value === "number" && Number.isInteger(value) && value >= 0 && value <= 4) ||
  value === "unknown" ||
  value === "not-applicable";

const isAssessmentState = (value: unknown): value is AssessmentState => {
  if (!value || typeof value !== "object") return false;
  const candidate = value as Partial<AssessmentState>;
  if (
    candidate.version !== CURRENT_STATE_VERSION ||
    (candidate.language !== "en" && candidate.language !== "ru") ||
    typeof candidate.revealed !== "boolean" ||
    typeof candidate.started !== "boolean" ||
    (candidate.lastSectionId !== null && typeof candidate.lastSectionId !== "string") ||
    !candidate.answers ||
    typeof candidate.answers !== "object" ||
    Array.isArray(candidate.answers)
  ) {
    return false;
  }
  return Object.entries(candidate.answers).every(
    ([questionId, answer]) => questionId.length > 0 && isAnswerValue(answer),
  );
};

export const serializeState = (state: AssessmentState): string => JSON.stringify(state);

export const restoreState = (raw: string | null): AssessmentState => {
  if (!raw) return initialState();
  try {
    const parsed: unknown = JSON.parse(raw);
    return isAssessmentState(parsed) ? parsed : initialState();
  } catch {
    return initialState();
  }
};
