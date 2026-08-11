export const CURRENT_STATE_VERSION = 1;

export type Language = "en" | "ru";
export type ThemePreference = "auto" | "light" | "dark";
export type ResolvedTheme = Exclude<ThemePreference, "auto">;
export type QuestionSet = "v1" | "v2";
export type AnswerValue = 0 | 1 | 2 | 3 | 4 | "unknown" | "not-applicable";

export type AssessmentState = {
  version: number;
  language: Language;
  theme: ThemePreference;
  questionSet: QuestionSet;
  answers: Record<string, AnswerValue>;
  revealed: boolean;
  started: boolean;
  lastSectionId: string | null;
};

export type AssessmentAction =
  | { type: "set-language"; language: Language }
  | { type: "set-theme"; theme: ThemePreference }
  | { type: "visit-section"; sectionId: string }
  | { type: "answer"; questionId: string; value: AnswerValue }
  | { type: "select-question-set"; questionSet: QuestionSet; firstSectionId: string }
  | { type: "reveal" }
  | { type: "reset" }
  | { type: "retake"; firstSectionId: string };

export const initialState = (
  language: Language = "en",
  theme: ThemePreference = "auto",
  questionSet: QuestionSet = "v2",
): AssessmentState => ({
  version: CURRENT_STATE_VERSION,
  language,
  theme,
  questionSet,
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
    case "set-theme":
      return { ...state, theme: action.theme };
    case "visit-section":
      return { ...state, started: true, lastSectionId: action.sectionId };
    case "answer":
      return {
        ...state,
        answers: { ...state.answers, [action.questionId]: action.value },
        revealed: false,
      };
    case "select-question-set":
      if (state.questionSet === action.questionSet) {
        return { ...state, started: true, lastSectionId: action.firstSectionId };
      }
      return {
        ...initialState(state.language, state.theme, action.questionSet),
        started: true,
        lastSectionId: action.firstSectionId,
      };
    case "reveal":
      return { ...state, revealed: true };
    case "reset":
      return initialState(state.language, state.theme, state.questionSet);
    case "retake":
      return {
        ...initialState(state.language, state.theme, state.questionSet),
        started: true,
        lastSectionId: action.firstSectionId,
      };
  }
};

export const resolveTheme = (
  preference: ThemePreference,
  systemPrefersDark: boolean,
): ResolvedTheme => (preference === "auto" ? (systemPrefersDark ? "dark" : "light") : preference);

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
    (candidate.theme !== "auto" && candidate.theme !== "light" && candidate.theme !== "dark") ||
    (candidate.questionSet !== "v1" && candidate.questionSet !== "v2") ||
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
    const migrated =
      parsed && typeof parsed === "object" && !Array.isArray(parsed)
        ? {
            ...parsed,
            theme: "theme" in parsed ? parsed.theme : "auto",
            questionSet: "questionSet" in parsed ? parsed.questionSet : "v2",
          }
        : parsed;
    return isAssessmentState(migrated) ? migrated : initialState();
  } catch {
    return initialState();
  }
};
