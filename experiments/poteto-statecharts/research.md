# What Poteto does, and where it fits here

Inspected on 30 October 2026 using the original posts in signed-in Chrome and
the official `cursor/plugins` source. Upstream was pstack **0.15.36**, commit
`4dd1d05818d19792e7cd6e818f1667f95f7e1dbe`. Community ports appeared in search,
but these experiments use the official implementation.

## Her published workflow

In the [formal-verification announcement](https://x.com/poteto/status/2111926622278521253),
Lauren Tan describes creating a project-specific verification skill, choosing
TLA+ for state machines/concurrency and tools such as Kani for properties of
Rust code. She says she found bugs while modeling her code. This is her report;
the post does not provide enough product code and traces to reproduce those
private findings. She explicitly discusses the difficulty of keeping models
aligned with implementation.

Her [21 October example](https://x.com/poteto/status/2112736749281759566) uses a
statechart to reason about behavior and then check it with formal verification.
She labels that picture hypothetical. Her
[companion-skill preview](https://x.com/poteto/status/2113398433977659654) adds
Pele for rendering. The [30 October release post](https://x.com/poteto/status/2115880102601101414)
announces stable `/statechart`, recommends combining it with the generator,
and shows the tool's own workflow with two bugs she says she found. The
blueprint appearance is presentation; the solver and model carry the check.

## What the code actually does

The official [statechart skill](https://github.com/cursor/plugins/blob/4dd1d05818d19792e7cd6e818f1667f95f7e1dbe/pstack/skills/statechart/SKILL.md)
takes a TLA+ specification/configuration and a JavaScript view. Its pipeline
runs TLC, parses results into an intermediate representation, projects states
into reader-facing labels, and emits Mermaid plus a report and raw checker
output. It is not a compiler that translates arbitrary Soyspray code into a
verified model. The agent still has to choose faithful states, atomic steps,
properties and bounds.

It reports shortest counterexamples, distinguishes definite from possible
violations after state merging, and can retain multiple rule failures. A chart
has a 500-state drawing budget; follow-up checking after an initial violation
has a separate 100,000-state bound. Neither makes a whole application verified.
The skill requires replaying modeled bugs against real code and treating a
failed replay as a likely modeling mistake. That requirement is particularly
valuable here: the intake finding was confirmed with real process interruptions.

The [formal-verification generator](https://github.com/cursor/plugins/blob/4dd1d05818d19792e7cd6e818f1667f95f7e1dbe/pstack/skills/create-formal-verification-skill/SKILL.md)
asks for a high-value property, source mapping, explicit limits, a deliberately
broken variant, a repeatable project-local check and a coverage commit. Its
companion maintenance workflow revisits that mapping after source changes.
These experiments exercise that method but do not install a new verification
skill or claim the policy-only promotion model verifies production execution.

[Pele](https://pele.run/) renders Mermaid to SVG. Its
[API](https://pele.run/api) and [CSS variables](https://pele.run/theming)
support local rendering and styling. The skill pins Pele 1.9.0, which is what
we used. No model content was uploaded to Pele's website. The stale-operation
experiment assumes Kubernetes' documented
[conditional-update contract](https://kubernetes.io/docs/reference/using-api/api-concepts/#updates-to-existing-resources).

## Recommended Soyspray use

Use this for changes where event ordering is the risk: interrupted publication,
retry ownership, replacement objects, backup/restore gates and stateful
handoffs. Keep ordinary tests for actual parsing, filesystem behavior and API
integration. The two approaches answered different questions in this trial:
existing tests passed while the bounded model led to two later crash windows.

For the next consequential recovery change, write one property, map its steps
to code, generate the chart, and replay any failing path locally. Put the model,
raw output and replay evidence beside the app, and review their source mapping
when the covered implementation changes. A small project-specific skill could
make that routine after this experiment is reviewed.

The strongest immediate follow-up is the intake retry gap. Separate digest
promotion also makes a clear onboarding/review diagram, though its simple
policy model adds less assurance than the crash experiment. No reason emerged
to install all of pstack or replace Soyspray's existing Git, Ansible, Argo and
backup/restore gates.
