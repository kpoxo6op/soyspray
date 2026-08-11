import { describe, expect, test } from "vitest";

import {
  initialState,
  reduceAssessmentState,
  resolveTheme,
} from "./state";

describe("local assessment state", () => {
  test("resolves Auto from the system while explicit themes override it", () => {
    expect(initialState().theme).toBe("auto");
    expect(resolveTheme("auto", false)).toBe("light");
    expect(resolveTheme("auto", true)).toBe("dark");
    expect(resolveTheme("light", true)).toBe("light");
    expect(resolveTheme("dark", false)).toBe("dark");
  });

  test("hides a revealed result when an answer changes", () => {
    let state = reduceAssessmentState(initialState(), { type: "reveal" });
    expect(state.revealed).toBe(true);
    state = reduceAssessmentState(state, { type: "answer", questionId: "q01", value: 4 });
    expect(state.revealed).toBe(false);
  });

  test("start over and retake clear answers but preserve language and theme", () => {
    let state = reduceAssessmentState(initialState(), {
      type: "set-language",
      language: "ru",
    });
    state = reduceAssessmentState(state, { type: "set-theme", theme: "dark" });
    state = reduceAssessmentState(state, { type: "answer", questionId: "q01", value: 4 });

    const reset = reduceAssessmentState(state, { type: "reset" });
    expect(reset.language).toBe("ru");
    expect(reset.theme).toBe("dark");
    expect(reset.answers).toEqual({});
    expect(reset.started).toBe(false);

    const retake = reduceAssessmentState(state, {
      type: "retake",
      firstSectionId: "conversation",
    });
    expect(retake.language).toBe("ru");
    expect(retake.theme).toBe("dark");
    expect(retake.answers).toEqual({});
    expect(retake.started).toBe(true);
    expect(retake.lastSectionId).toBe("conversation");
  });

  test("switches question sets and clears answers from the other set", () => {
    let state = reduceAssessmentState(initialState(), {
      type: "answer",
      questionId: "q01",
      value: 4,
    });
    state = reduceAssessmentState(state, {
      type: "select-question-set",
      questionSet: "v1",
      firstSectionId: "conversation",
    });

    expect(state.questionSet).toBe("v1");
    expect(state.answers).toEqual({});
    expect(state.started).toBe(true);
    expect(state.lastSectionId).toBe("conversation");

    state = reduceAssessmentState(state, { type: "answer", questionId: "q01", value: 2 });
    state = reduceAssessmentState(state, {
      type: "select-question-set",
      questionSet: "v1",
      firstSectionId: "conversation",
    });
    expect(state.answers).toEqual({ q01: 2 });

    expect(reduceAssessmentState(state, { type: "reset" }).questionSet).toBe("v1");
  });
});
