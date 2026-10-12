import test from "node:test";
import assert from "node:assert/strict";
import { projectScenario } from "../src/scenario-view.js";
import { scenarioPresentation } from "../src/scenario-data.js";

// Contract: prediction answers describe the canonical outcome in both workload
// modes. Engine tests do not own presentation choices or their grading keys.
test("prediction keys describe observable engine outcomes", () => {
    const answers = {
        "s1-shared-vs-isolated": "A’s edit is silently overwritten by B",
        "s2-plausible-vs-verified": "Three, including the non-fix",
        "s3-review-backlog": "The review queue shrinks because checks reject faulty PRs first",
        "s4-naive-retry": "Two duplicates",
        "s5-architecture-gate": "At CI, before review",
    };
    for (const [id, answer] of Object.entries(answers)) {
        const view = scenarioPresentation[id];
        assert.equal(view.choices[view.answer], answer);
    }
    const shared = projectScenario("s1-shared-vs-isolated", false).model;
    assert.ok(shared.events.some(e => e.kind === "lost_update"));
    assert.equal(projectScenario("s2-plausible-vs-verified", false).model.metrics.merged, 3);
    for (const agents of [4, 1]) {
        const off = projectScenario("s3-review-backlog", false, agents).model;
        const on = projectScenario("s3-review-backlog", true, agents).model;
        assert.ok(on.tasks.some(t => t.state === "rejected"));
        assert.ok(on.metrics.merged < off.metrics.merged);
        assert.ok(on.metrics.reviewQueue < off.metrics.reviewQueue);
    }
    assert.equal(projectScenario("s4-naive-retry", false).model.metrics.merged, 2);
    const gate = projectScenario("s5-architecture-gate", true).events;
    assert.ok(gate.findIndex(e => e[2] === "ci_fail") < gate.findIndex(e => e[2] === "revised"));
});

// Contract: the visible verification trace catches the failed fix and returns it
// to work, rather than showing it as merged. A wrong placement can misteach this
// while simulator.test.mjs still passes: that test owns the engine, not its view.
test("a failed verification visibly returns the same task to the queue", () => {
    const { model, events } = projectScenario("s2-plausible-vs-verified", true);
    const failed = events.find(event => event[2] === "verify_fail");
    const retry = events.find(event => event[2] === "retry_pending");
    assert.equal(failed[1], retry[1]);
    assert.equal(failed[4].lane, failed[1]);
    assert.equal(failed[4].s, "caught");
    assert.equal(retry[4].lane, failed[1]);
    assert.equal(retry[4].s, "pending");
    assert.equal(retry[4].m, "queued");
    assert.equal(model.tasks.find(task => task.id === retry[1]).state, "queued");
    assert.ok(!events.some(event => event[1] === failed[1] && event[4].s === "done"));
});

// Contract: a redelivery with a claim stops the second delivery at the claim,
// while the first delivery can finish. Confusing report IDs with delivery lanes
// could animate duplicate work despite a correct canonical deduplication trace.
test("claim protection visibly stops redelivery without stopping the owner", () => {
    const { events } = projectScenario("s4-naive-retry", true);
    const redelivery = events.find(event => event[2] === "redelivery");
    const skipped = events.find(event => event[2] === "skip_already_claimed");
    const ready = events.find(event => event[2] === "ready");
    assert.equal(redelivery[1], skipped[1]);
    assert.equal(redelivery[4].lane, skipped[4].lane);
    assert.equal(skipped[4].s, "stopped");
    assert.notEqual(skipped[4].lane, ready[4].lane);
    assert.equal(ready[4].s, "done");
    assert.ok(!events.some(event => event[2] === "duplicate_started" || event[2] === "duplicate_pr"));
});
