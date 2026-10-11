// Illustrative event model. No measured rates, empirical probabilities or real agents.
const tasks = [
    {
        id: "sidebar",
        file: "ui.js",
        duration: 2,
        defect: true,
        permission: "code",
    },
    {
        id: "search",
        file: "ui.js",
        duration: 3,
        defect: false,
        permission: "code",
    },
    {
        id: "settings",
        file: "settings.js",
        duration: 2,
        defect: false,
        permission: "code",
    },
    {
        id: "deploy",
        file: "release.yaml",
        duration: 1,
        defect: false,
        permission: "release",
        dependency: "settings",
    },
    {
        id: "captions",
        file: "captions.js",
        duration: 2,
        defect: true,
        permission: "code",
    },
    {
        id: "docs",
        file: "guide.md",
        duration: 1,
        defect: false,
        permission: "code",
    },
];
export const defaults = Object.freeze({
    concurrency: 3,
    workspace: "isolated",
    verification: true,
    reviewCapacity: 1,
    mergePolicy: "review",
    retry: "idempotent",
    permission: "code",
    observability: true,
    context: "mapped",
    flakiness: false,
});
export function simulate(parameters = {}, seed = 7) {
    const p = { ...defaults, ...parameters };
    p.concurrency = Math.max(1, Math.min(6, Number(p.concurrency) || 1));
    p.reviewCapacity = Math.max(1, Math.min(3, Number(p.reviewCapacity) || 1));
    const queue = tasks.map((t) => ({
        ...t,
        state: "queued",
        remaining: t.duration,
        attempts: 0,
    }));
    // Stable permutation changes dispatch order, never defect frequency.
    if (Number(seed) % 2 === 0) queue.reverse();
    const events = [],
        active = [],
        review = [],
        merged = new Set();
    const metrics = {
        merged: 0,
        wasted: 0,
        conflicts: 0,
        defects: 0,
        reviewQueue: 0,
        detectionLatency: 0,
        cost: 0,
    };
    const event = (tick, task, kind, message) =>
        events.push({ tick, task, kind, message });
    let flakyConsumed = false;
    for (let tick = 0; tick < 40; tick++) {
        for (const t of [...active]) {
            metrics.cost++;
            t.remaining--;
            if (t.remaining > 0) continue;
            active.splice(active.indexOf(t), 1);
            if (t.collision) {
                metrics.conflicts++;
                metrics.wasted++;
                event(
                    tick,
                    t.id,
                    "conflict",
                    "Concurrent shared-file edit overwritten; work must be repeated.",
                );
                t.state = "conflicted";
                continue;
            }
            if (p.flakiness && p.verification && !flakyConsumed) {
                flakyConsumed = true;
                event(
                    tick,
                    t.id,
                    "retry",
                    "Check transport failed; the completed work is not a proven failure.",
                );
                if (p.retry === "naive") {
                    metrics.wasted++;
                    metrics.cost += t.duration;
                    event(
                        tick,
                        t.id,
                        "duplicate",
                        "Retry starts the same operation again without an idempotency key.",
                    );
                } else
                    event(
                        tick,
                        t.id,
                        "deduplicated",
                        "Operation key reuses the completed result; only the check is retried.",
                    );
            }
            if (t.defect && p.verification) {
                event(
                    tick,
                    t.id,
                    "caught",
                    "User-boundary check reproduces the defect. Fix, then rerun the same check.",
                );
                t.defect = false;
                metrics.cost++;
            } else if (t.defect)
                event(
                    tick,
                    t.id,
                    "unverified",
                    "Plausible summary submitted without running the user path.",
                );
            t.state = "review";
            t.finishedAt = tick;
            review.push(t);
            event(
                tick,
                t.id,
                "ready",
                "Branch enters the integration review queue.",
            );
        }
        metrics.reviewQueue = Math.max(metrics.reviewQueue, review.length);
        const capacity =
            p.mergePolicy === "auto" ? review.length : p.reviewCapacity;
        for (let n = 0; n < capacity && review.length; n++) {
            const t = review.shift();
            if (t.defect && p.mergePolicy === "review") {
                event(
                    tick,
                    t.id,
                    "caught",
                    "Reviewer reproduces the user path and returns the branch for repair.",
                );
                t.defect = false;
                metrics.cost += 2;
            }
            if (t.defect) {
                metrics.defects++;
                const delay = p.observability ? 1 : 6;
                metrics.detectionLatency = Math.max(
                    metrics.detectionLatency,
                    delay,
                );
                event(
                    tick + delay,
                    t.id,
                    "incident",
                    `Defect reaches main; detected ${delay} illustrative ticks later.`,
                );
            }
            t.state = "merged";
            merged.add(t.id);
            metrics.merged++;
            event(
                tick,
                t.id,
                "merged",
                "Integrated into the teaching repository; this is not a production promotion.",
            );
        }
        for (const t of queue) {
            if (active.length >= p.concurrency) break;
            if (
                t.state !== "queued" ||
                (t.dependency && !merged.has(t.dependency))
            )
                continue;
            if (t.permission === "release" && p.permission !== "release") {
                t.state = "blocked";
                event(
                    tick,
                    t.id,
                    "blocked",
                    "Release action exceeds the code-only capability; human promotion remains separate.",
                );
                continue;
            }
            t.state = "running";
            t.attempts++;
            if (p.context === "unmapped") {
                t.remaining += 2;
                event(
                    tick,
                    t.id,
                    "discovery",
                    "No feature map: two illustrative ticks spent discovering the user path.",
                );
            }
            if (
                p.workspace === "shared" &&
                active.some((a) => a.file === t.file)
            )
                t.collision = true;
            active.push(t);
            event(
                tick,
                t.id,
                "started",
                `Editing ${t.file} in ${p.workspace === "shared" ? "the shared tree" : "a separate worktree"}.`,
            );
        }
        if (
            !active.length &&
            !review.length &&
            !queue.some((t) => t.state === "queued")
        )
            break;
    }
    return {
        parameters: p,
        seed: Number(seed),
        events: events.sort((a, b) => a.tick - b.tick),
        metrics,
        tasks: queue.map(({ id, file, state }) => ({ id, file, state })),
    };
}

export function simulateScenario(id, controlled = true, agents = 4) {
    const events = [],
        taskStates = new Map();
    const metrics = {
        merged: 0,
        wasted: 0,
        conflicts: 0,
        defects: 0,
        reviewQueue: 0,
        detectionLatency: 0,
        cost: 0,
    };
    const emit = (tick, task, kind, message, state) => {
        events.push({ tick, task, kind, message });
        if (state) taskStates.set(task, state);
    };
    if (id === "s1-shared-vs-isolated") {
        metrics.cost = 6;
        emit(1, "T1", "started", "Agent A edits config line 1.", "running");
        emit(2, "T2", "started", "Agent B edits the same line.", "running");
        emit(
            3,
            "T1",
            "written",
            controlled
                ? "A commits in worktree A."
                : "A writes in the shared tree.",
            "ready",
        );
        emit(
            4,
            "T2",
            "written",
            controlled
                ? "B commits in worktree B."
                : "B writes in the same shared tree.",
            "ready",
        );
        if (controlled) {
            metrics.conflicts = 1;
            metrics.reviewQueue = 1;
            metrics.merged = 1;
            emit(5, "T1", "merged", "The first branch integrates.", "merged");
            emit(
                5,
                "T2",
                "merge_conflict",
                "Competing edits are visible at integration; route to human review.",
                "review",
            );
        } else {
            metrics.merged = 1;
            metrics.wasted = 1;
            emit(
                4,
                "T1",
                "lost_update",
                "B silently overwrites A; no Git merge occurred.",
                "lost",
            );
            emit(5, "T2", "merged", "Only B’s edit survives.", "merged");
        }
    } else if (id === "s2-plausible-vs-verified") {
        metrics.cost = 9 + (controlled ? 3 : 0);
        metrics.merged = controlled ? 2 : 3;
        metrics.defects = controlled ? 0 : 1;
        for (const task of ["T1", "T2", "T3"])
            emit(1, task, "started", "Agent attempts the fix.", "running");
        for (const task of ["T1", "T2", "T3"])
            emit(
                3,
                task,
                "reported_done",
                "Agent reports success; this statement is not a probe.",
                "ready",
            );
        for (const task of ["T1", "T2"])
            emit(
                4,
                task,
                controlled ? "verify_pass" : "accepted",
                controlled
                    ? "The actual symptom no longer reproduces."
                    : "Self-report accepted without reproduction.",
                "merged",
            );
        emit(
            4,
            "T3",
            controlled ? "verify_fail" : "defect_in_main",
            controlled
                ? "The symptom still reproduces. T3 returns to the queue; no fix has merged."
                : "The scripted non-fix reaches main. Detection is deferred.",
            controlled ? "queued" : "merged",
        );
        if (controlled)
            emit(
                5,
                "T3",
                "retry_pending",
                "A new repair attempt is pending; the model does not assume it succeeds.",
            );
    } else if (id === "s3-review-backlog") {
        const count = Number(agents) === 1 ? 3 : 12,
            failures = new Set(controlled ? ["P2", "P5", "P7", "P11"] : []);
        const review = [];
        for (let i = 1; i <= count; i++) {
            const task = `P${i}`;
            metrics.cost += 3;
            if (failures.has(task))
                emit(
                    1,
                    task,
                    "check_reject",
                    "Hard check rejects the scripted bad change before human review.",
                    "rejected",
                );
            else {
                review.push(task);
                emit(
                    1,
                    task,
                    "review_ready",
                    "Change arrives in the human review queue.",
                    "review",
                );
            }
        }
        for (let tick = 1; review.length; tick++) {
            for (let n = 0; n < 2 && review.length; n++) {
                const task = review.shift();
                metrics.merged++;
                emit(
                    tick,
                    task,
                    "reviewed",
                    "One of the two review slots for this tick is consumed.",
                    "merged",
                );
            }
            metrics.reviewQueue = Math.max(metrics.reviewQueue, review.length);
        }
    } else if (id === "s4-naive-retry") {
        metrics.cost = controlled ? 3 : 6;
        metrics.merged = controlled ? 1 : 2;
        metrics.wasted = controlled ? 0 : 3;
        emit(1, "R7", "delivery", "Bug report R7 arrives.");
        emit(
            1,
            "PR-a",
            controlled ? "claim" : "started",
            controlled
                ? "An atomic claim owns R7 before work starts."
                : "First delivery starts an agent.",
            "running",
        );
        emit(
            3,
            "R7",
            "redelivery",
            "A timeout causes the same report to be delivered again.",
        );
        emit(
            3,
            "R7",
            controlled ? "skip_already_claimed" : "duplicate_started",
            controlled
                ? "Existing claim prevents a second branch."
                : "A second agent starts with no claim key.",
        );
        emit(
            4,
            "PR-a",
            "ready",
            "The first agent opens one reviewable PR.",
            "merged",
        );
        if (!controlled)
            emit(
                6,
                "PR-b",
                "duplicate_pr",
                "Reviewer receives a second PR for the same report; three cost units are wasted.",
                "merged",
            );
    } else if (id === "s5-architecture-gate") {
        metrics.cost = controlled ? 4 : 3;
        metrics.merged = 1;
        metrics.defects = controlled ? 0 : 1;
        metrics.detectionLatency = controlled ? 0 : 5;
        emit(
            1,
            "C1",
            "shortcut_import",
            "Agent imports main-process work into the renderer.",
            "running",
        );
        if (controlled) {
            emit(
                2,
                "C1",
                "ci_fail",
                "Import-boundary check rejects the change before review.",
                "blocked",
            );
            emit(
                3,
                "C1",
                "revised",
                "Agent takes the allowed path and passes the boundary check.",
                "ready",
            );
            emit(
                4,
                "C1",
                "merged",
                "The corrected change integrates cleanly.",
                "merged",
            );
        } else {
            emit(
                2,
                "C1",
                "soft_rule_ignored",
                "README guidance cannot reject the import.",
                "ready",
            );
            emit(
                3,
                "C1",
                "boundary_violation_in_main",
                "The scripted reviewer misses the shortcut; it reaches main.",
                "merged",
            );
            emit(
                8,
                "C1",
                "jank_report",
                "A user reports the downstream symptom. This miss is scripted, not a probability.",
            );
        }
    } else throw new Error("Unknown teaching scenario");
    return {
        events: events.sort((a, b) => a.tick - b.tick),
        metrics,
        tasks: [...taskStates].map(([id, state]) => ({ id, state })),
        parameters: { scenario: id, controlled, agents },
    };
}
