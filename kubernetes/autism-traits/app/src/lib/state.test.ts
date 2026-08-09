import { describe, expect, test } from "vitest";

import {
  CURRENT_STATE_VERSION,
  initialState,
  reduceAssessmentState,
  restoreState,
  serializeState,
} from "./state";

describe("local assessment state", () => {
  test("round-trips answers, language, and the last section", () => {
    let state = initialState();
    state = reduceAssessmentState(state, { type: "set-language", language: "ru" });
    state = reduceAssessmentState(state, { type: "visit-section", sectionId: "masking" });
    state = reduceAssessmentState(state, { type: "answer", questionId: "q01", value: 3 });

    expect(restoreState(serializeState(state))).toEqual(state);
  });

  test("rejects corrupt or outdated saved state", () => {
    expect(restoreState("not json")).toEqual(initialState());
    expect(
      restoreState(JSON.stringify({ ...initialState(), version: CURRENT_STATE_VERSION - 1 })),
    ).toEqual(initialState());
    expect(restoreState(JSON.stringify({ ...initialState(), language: "de" }))).toEqual(
      initialState(),
    );
    expect(restoreState(JSON.stringify({ ...initialState(), answers: { q01: 8 } }))).toEqual(
      initialState(),
    );
  });

  test("hides a revealed result when an answer changes", () => {
    let state = reduceAssessmentState(initialState(), { type: "reveal" });
    expect(state.revealed).toBe(true);
    state = reduceAssessmentState(state, { type: "answer", questionId: "q01", value: 4 });
    expect(state.revealed).toBe(false);
  });

  test("start over and retake clear answers but preserve language", () => {
    let state = reduceAssessmentState(initialState(), {
      type: "set-language",
      language: "ru",
    });
    state = reduceAssessmentState(state, { type: "answer", questionId: "q01", value: 4 });

    const reset = reduceAssessmentState(state, { type: "reset" });
    expect(reset.language).toBe("ru");
    expect(reset.answers).toEqual({});
    expect(reset.started).toBe(false);

    const retake = reduceAssessmentState(state, {
      type: "retake",
      firstSectionId: "conversation",
    });
    expect(retake.language).toBe("ru");
    expect(retake.answers).toEqual({});
    expect(retake.started).toBe(true);
    expect(retake.lastSectionId).toBe("conversation");
  });
});
