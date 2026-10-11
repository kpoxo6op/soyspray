import test from "node:test";
import assert from "node:assert/strict";
import { simulate, simulateScenario } from "../src/simulator.js";

test("parallel edits collide in a shared tree, while worktrees preserve both results", () => {
    // Contract: workspace isolation preserves competing edits. Failure: overwrite silently loses work.
    const shared = simulate({ workspace: "shared" });
    const isolated = simulate({ workspace: "isolated" });
    assert(shared.metrics.conflicts > 0);
    assert.equal(isolated.metrics.conflicts, 0);
    assert(isolated.metrics.merged > shared.metrics.merged);
});

test("the five teaching scenarios expose each control at its actual boundary", () => {
    const shared = simulateScenario("s1-shared-vs-isolated", false),
        isolated = simulateScenario("s1-shared-vs-isolated", true);
    assert(shared.events.some((e) => e.kind === "lost_update"));
    assert(!isolated.events.some((e) => e.kind === "lost_update"));
    assert(isolated.events.some((e) => e.kind === "merge_conflict"));
    assert.equal(
        simulateScenario("s2-plausible-vs-verified", true).tasks.find(
            (t) => t.id === "T3",
        ).state,
        "queued",
    );
    assert(
        simulateScenario("s2-plausible-vs-verified", false).metrics.defects > 0,
    );
    assert(
        simulateScenario("s3-review-backlog", true).metrics.reviewQueue <
            simulateScenario("s3-review-backlog", false).metrics.reviewQueue,
    );
    assert(
        !simulateScenario("s4-naive-retry", true).events.some(
            (e) => e.kind === "duplicate_pr",
        ),
    );
    assert(
        simulateScenario("s4-naive-retry", false).events.some(
            (e) => e.kind === "duplicate_pr",
        ),
    );
    assert.equal(
        simulateScenario("s5-architecture-gate", true).metrics.defects,
        0,
    );
    assert(
        simulateScenario("s5-architecture-gate", false).events.some(
            (e) => e.kind === "jank_report",
        ),
    );
});
test("real verification stops fixture defects even with automatic integration", () => {
    // Contract: user-path verification precedes integration. No UI test owns the model's gate.
    assert.equal(
        simulate({ verification: true, mergePolicy: "auto" }).metrics.defects,
        0,
    );
    assert(
        simulate({ verification: false, mergePolicy: "auto" }).metrics.defects >
            0,
    );
});
test("capability scope holds the release boundary while code tasks still finish", () => {
    const code = simulate({ permission: "code" });
    assert.equal(code.tasks.find((t) => t.id === "deploy").state, "blocked");
    assert(code.metrics.merged > 0);
    assert.equal(
        simulate({ permission: "release" }).tasks.find((t) => t.id === "deploy")
            .state,
        "merged",
    );
});
test("idempotent retry avoids duplicate side effects after a flaky check", () => {
    const safe = simulate({ flakiness: true, retry: "idempotent" });
    const naive = simulate({ flakiness: true, retry: "naive" });
    assert(!safe.events.some((e) => e.kind === "duplicate"));
    assert(naive.events.some((e) => e.kind === "duplicate"));
    assert(naive.metrics.cost > safe.metrics.cost);
    assert.deepEqual(
        simulate({ flakiness: true }, 7),
        simulate({ flakiness: true }, 7),
    );
});
