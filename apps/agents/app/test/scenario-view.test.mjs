import test from "node:test";
import assert from "node:assert/strict";
import { projectScenario } from "../src/scenario-view.js";

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
