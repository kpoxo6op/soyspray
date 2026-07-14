---
name: demo-lab-experience
description: Improve a technical lab as a learnable product for operators and demo users. Use for setup journeys, power controls, sample applications, visible gateway behavior, browser UX, docs, evidence collection, reset or shutdown, and making a lab useful for future practice.
---

# Demo Lab Experience

Make the shortest successful journey obvious, while keeping the system deep enough to inspect.

## Review the journeys

Exercise these journeys separately:

1. **New operator:** discover prerequisites, run local checks, start the lab, know when it is ready, and find all surfaces.
2. **Learner:** send an accepted request, trigger an intentional rejection, see the gateway evidence, and connect the result to configuration.
3. **Demo viewer:** understand the page without repository context, use it with keyboard and mobile layouts, and recover from loading or API failures.
4. **Maintainer:** locate ownership, add an API or client using an existing pattern, validate locally, and roll back safely.
5. **Cost-conscious owner:** stop the lab with one documented command and prove no runtime workloads remain.

## Implementation rules

- Prefer one memorable command per lifecycle action and a status command that names OFF, ON, or PARTIAL explicitly.
- Use synthetic data and label intentional failures as learning controls, not application outages.
- Keep the demo UI focused on a real user task. Put platform diagnostics behind a clearly named disclosure.
- Render network data with safe DOM APIs such as `textContent`; do not trust mock APIs merely because they are local.
- Provide visible loading, success, rejection, and unavailable states. Preserve keyboard focus and announce async results.
- Test the browser in desktop and narrow viewports. Capture a semantic snapshot, console output, network evidence, and a screenshot when visual proof matters.
- Keep operator docs short and command-led. Link from the first page to the live app, dashboard, architecture, verification, and power controls.
- End every live test by restoring the documented parked state.

## Completion evidence

Report the exact commit, local gate result, live ON state, accepted and rejected interactions, browser result, and final OFF state. Separate observations from assumptions.
