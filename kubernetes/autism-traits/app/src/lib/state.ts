export type Language = "en" | "ru";
export type ThemePreference = "auto" | "light" | "dark";
export type ResolvedTheme = Exclude<ThemePreference, "auto">;
export type QuestionSet = "v1" | "v2";
export type AnswerValue = 0 | 1 | 2 | 3 | 4 | "unknown" | "not-applicable";

export type AssessmentState = {
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
