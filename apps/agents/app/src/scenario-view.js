import { simulateScenario } from "./simulator.js";
import { scenarioPresentation } from "./scenario-data.js";

// This projects the canonical trace onto the design's stations. It does not
// schedule work, choose outcomes, or calculate an independent simulation.
export function projectScenario(id, controlled = true, agents = 4) {
    const presentation = scenarioPresentation[id];
    if (!presentation) throw new Error("Unknown scenario view");
    const model = simulateScenario(id, controlled, agents);
    const mode = controlled ? "on" : "off";
    const events = model.events.map(({ tick, task, kind, message }) => {
        if (presentation.queue) return [tick, task, kind, message];
        const placement = presentation.placements[mode][kind];
        if (!placement) throw new Error(`Unmapped scenario event: ${id}/${kind}`);
        return [
            tick,
            task,
            kind,
            message,
            { ...placement, lane: placement.lane === "$task" ? task : placement.lane },
        ];
    });
    return { model, events, lastTick: Math.max(0, ...model.events.map(event => event.tick)) };
}

export function compareScenario(id, agents = 4) {
    const off = simulateScenario(id, false, agents);
    const on = simulateScenario(id, true, agents);
    let values;
    let labels = scenarioPresentation[id]?.comparisonLabels;
    switch (id) {
        case "s1-shared-vs-isolated":
            values = [
                [off.metrics.merged, on.metrics.merged],
                [off.metrics.wasted, on.metrics.wasted],
                [off.metrics.conflicts, on.metrics.conflicts],
                [off.metrics.cost, on.metrics.cost],
            ];
            break;
        case "s2-plausible-vs-verified":
            values = [
                [off.metrics.merged, on.metrics.merged],
                [off.metrics.defects, on.metrics.defects],
                [off.tasks.filter(task => task.state === "queued").length, on.tasks.filter(task => task.state === "queued").length],
                [off.metrics.cost, on.metrics.cost],
            ];
            break;
        case "s3-review-backlog":
            labels = ["Rejected before review", "Peak review queue", "Ticks to clear review", "Merged"];
            values = [
                [off.tasks.filter(task => task.state === "rejected").length, on.tasks.filter(task => task.state === "rejected").length],
                [off.metrics.reviewQueue, on.metrics.reviewQueue],
                [Math.max(...off.events.map(event => event.tick)), Math.max(...on.events.map(event => event.tick))],
                [off.metrics.merged, on.metrics.merged],
            ];
            break;
        case "s4-naive-retry":
            values = [
                [off.metrics.merged, on.metrics.merged],
                [off.metrics.wasted, on.metrics.wasted],
                [off.metrics.cost, on.metrics.cost],
            ];
            break;
        case "s5-architecture-gate":
            values = [
                [`a user, tick ${off.events.find(event => event.kind === "jank_report").tick}`, `CI, tick ${on.events.find(event => event.kind === "ci_fail").tick}`],
                [off.metrics.defects, on.metrics.defects],
                [off.metrics.detectionLatency, on.metrics.detectionLatency],
                [off.metrics.cost, on.metrics.cost],
            ];
            break;
        default:
            throw new Error("Unknown scenario comparison");
    }
    return labels.map((label, index) => [label, ...values[index]]);
}
