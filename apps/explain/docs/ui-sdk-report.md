# UI SDK: what it is, what the post claims, and a test on the guides catalog

15 Nov 2026. Written for the catalog in this folder (`apps/explain`).

## Short answer

UI SDK is a new open-source library from Vercel Labs, announced on 12 Nov 2026 by
shadcn (who made shadcn/ui) and Chris Tate. It gives you the hard parts of interface
controls, such as focus, keyboard moves, selection and popups, as small building
blocks, and ready-made components for React, Vue, Svelte, Solid and plain web
components. Its new idea is an **agent bridge**: a page can put an object at
`window.agent` that tells an AI agent exactly which controls are on the page, what
state they are in and what it can do with them, as JSON. The agent then changes them
by name in one call, instead of reading the whole page, clicking one thing at a time
and taking screenshots.

On the catalog, with the same task done three times each way by Claude Sonnet, the
bridge needed 4 page calls instead of 7, returned 10.3k characters instead of 94.4k,
and finished in 14.6 s instead of 23.0 s (medians). Every run got the task right
both ways. Neither way needed a screenshot. The post's direction holds up here; its
exact numbers depend on how messy the page without UI SDK is.

## What UI SDK is

- **Who:** Vercel Labs, repository `github.com/vercel-labs/ui`, Apache-2.0. shadcn
  announced it and reposted the post you saw; Chris Tate posted the launch thread.
  The thanks list names Radix, Base UI, React Aria, shadcn/ui, Nuxt UI and Geist.
- **Status:** beta. npm `@ui-sdk/core` and `@ui-sdk/web` (also `/react`, `/vue`,
  `/svelte`, `/solid`), first published 12 Nov, `0.1.0-beta.2` on 13 Nov. The docs say
  APIs may still change.
- **Behaviors:** over 50 framework-free functions, each doing one job: roving focus,
  typeahead, a popup, drag and drop, a tree. A **primitive** (`definePrimitive`)
  combines behaviors with state, methods and parts, and the same primitive renders in
  any of the five frameworks. The shipped components (select, tabs, switch, slider,
  dialog and so on) are primitives too. They come unstyled.
- **Built for agents both ways:** agents *build* with it (each package ships its own
  docs and a `ui-sdk` skill for coding agents), and agents *use* pages built with it
  (the bridge).

## How the `window.agent` bridge works

Nothing is built into the browser. The page calls `createAgent()` from
`@ui-sdk/<framework>/agent` and puts the result where an agent can reach it, usually
`window.agent`. The bridge keeps a registry of every UI SDK component on the page.

- `agent.snapshot()` returns a list such as
  `{ ref: "c5", component: "switch", label: "Hide done", checked: false, actions: ["setChecked"] }`.
  Only UI SDK components appear, not the rest of the page.
- `agent.act({ steps: [...] })` runs several steps in order, each naming a component
  by ref or by its visible label: `{ ref: "Guide", action: "setValue", args: ["assembly"] }`.
  It calls the component's own methods, the same ones a click would reach, so the
  page's change handlers run and see `source: "agent"`. It returns what changed.
- `agent.query({ text, within, kind })` finds components or list choices without
  listing the whole page.
- The page decides what an agent may do: an `allow` callback can refuse steps,
  `data-agent-confirm` makes a step wait for a person, `data-agent-hidden` hides
  parts of the page, and password-type fields are redacted.
- Your own components join the bridge by listing their actions in the primitive's
  `agent` key, as the catalog's chapter row does with `setDone` and `open`.

How an agent reaches it: any browser automation tool that can run JavaScript in the
page (Claude in Chrome, Playwright, Chrome DevTools) calls `window.agent.snapshot()`
and `act()`. The library also exports the three tools as JSON Schemas for your own
agent loop, and can register them through WebMCP (`document.modelContext`) for
browsers that support it. There is no browser extension and no MCP server in the
package.

## What the post's numbers mean

The post says that with UI SDK an agent was 43% faster, used 74% fewer tool calls and
took 0 screenshots, as the median of 3 runs with Claude Sonnet 5.5. In plain terms:

- **Tool calls.** Browser tools act one element at a time: read the page, click,
  read again, type, read again. The bridge takes one snapshot and one `act` with all
  the steps, so most of the round trips disappear.
- **Speed.** An agent's time is mostly model turns, not the browser. Fewer calls and
  shorter answers mean fewer, faster turns. In the catalog test the page itself
  answered in under 0.4 s per run either way; the rest was the model thinking.
- **0 screenshots.** A screenshot is what an agent falls back to when the page's
  text does not tell it enough, such as which option is selected or whether a popup
  opened. The bridge states that as data, so the agent never needs to look.

Caveats: the post and UI SDK's own benchmark (16 versus 5 calls, 41 s versus 16 s,
one settings task) are self-reported, with three runs. The docs say the page
without the bridge was built with *another component library*, so part of the gap is
that library's markup. A plain page with good native HTML is much easier for browser
tools, which is what the catalog test below shows: no screenshots on either side.

## What I built

`explain.soyspray.vip` (this app) is one site for both guides:

- `/` is the catalog: both guides with their progress, then every chapter (37 Soyrack,
  7 Pearl) with search, a guide picker, Hide done, a Done toggle per chapter and a link
  that opens the guide at that chapter (`/assembly/#crimp-plan`, `/pearl/#t=191`).
- `/assembly/` and `/pearl/` are the existing guides, served by their own images. A
  second Ingress per guide adds the path to the new host, and each guide's nginx strips
  its prefix. The bytes, caching and gzip are the same as on the old hosts.
- `assembly.soyspray.vip` and `pearl.soyspray.vip` now redirect here for good (your
  call, 15 Nov). The old Pearl host first carries the reader's ticks across, since
  browsers keep them per site. A third guide, `/network/`, explains the home network
  from zero and is built into this image.
- Where UI SDK fits: the catalog's controls (search, picker, switch, meters, buttons)
  and a custom chapter primitive, plus the bridge. I did not put it inside the 3D
  guides. Their player is a canvas, which is where a bridge would help agents most
  (read the chapter and caption, jump, play), but it would add about 45 KB gzipped to
  pages we just made fast, and the guides would need their own primitive. Worth a
  separate trial if you want agents to drive the 3D players.

Cost of UI SDK here: the catalog script is 126 KB (45 KB gzipped), almost all UI SDK,
against 7 KB for the same page with native controls. The page is server-rendered, so
the list shows before the script runs. Snags met: change events do not bubble (one
listener per element), a `ui-button` around a link shows no action and no link in the
snapshot, and a link only appears if a primitive exposes it, as the chapter row does.

## The comparison on the catalog

Method (in `app/tools/agent-bench/`, logs in `results-2026-11-15/`):

- Two builds of the same page from the same data: UI SDK with the bridge (`dist/`),
  and native HTML controls with no UI SDK (`dist-plain/`).
- One Chromium page per run, behind a small local server that logs every call.
  **Browser tools** mode mirrors the Playwright MCP tools: an accessibility snapshot
  with refs, click, type, press and screenshot, each action answering with a fresh
  snapshot. **Bridge** mode offers only `snapshot`, `act` and `query`.
- The agent was Claude Sonnet, as a fresh subagent per run with the same task and only
  the tool description changed. Three runs each, all six in parallel.
- Task: mark the Pearl chapters "Buy the kit" and "Load the printer" done; show only
  Soyrack, search "crimp", turn on Hide done; mark "Strip 3 cm of jacket" done; report
  the chapter count, the link of "When the lamps are wrong" and Pearl progress.
- Scored from the page itself afterwards: storage, filter and visible rows.

| Median of 3          | Browser tools | UI SDK bridge | Change |
| -------------------- | ------------- | ------------- | ------ |
| Page calls           | 7             | 4             | −43%   |
| Agent tool calls     | 8             | 4             | −50%   |
| Text returned        | 94.4k chars   | 10.3k chars   | −89%   |
| Agent time           | 23.0 s        | 14.6 s        | −37%   |
| Screenshots          | 0             | 0             |        |
| Correct, by page state | 3 of 3      | 3 of 3        |        |

Run by run: browser 23.0, 22.5 and 25.8 s, bridge 14.9, 14.1 and 14.6 s. Each browser run
went snapshot, three clicks, type, two clicks; the bridge runs went snapshot, one or two
`act` calls with every step, and a final snapshot. The agents' final context was about
80k tokens against 75k, most of it their fixed instructions, so the saving in tokens
is smaller than the saving in text.

Limits: one task, three runs, designed on a page I built for the bridge, with Sonnet
as a subagent rather than Claude Code with real MCP tools. The plain page had clean
native controls, which is the best case for browser tools. A page with custom popups,
a canvas or vague labels would widen the gap.

## Recommendation

Keep the catalog with UI SDK as a trial: it works, it is small enough for a text page,
and the bridge makes the site easy for any agent to drive. Treat UI SDK as beta and
pin it, as done here. Do not add it to the 3D guides for now; if you want agents to
drive them, a small bridge-only primitive for the player is the next experiment.

## Sources

- UI SDK launch: https://ui-sdk.dev/docs/core/changelog/introducing-ui-sdk
- Agent bridge docs (shipped in `@ui-sdk/web/docs/agents.md`): https://ui-sdk.dev/docs/agents/llms.txt
- Repository: https://github.com/vercel-labs/ui
- shadcn's announcement: https://x.com/shadcn/status/2120951116682682646
- Chris Tate's launch thread: https://x.com/ctatedev/status/2120966861252960508
- The demo from the post: https://ui-sdkdemo.vercel.app
- Reviews: https://azukiazusa.dev/en/blog/ui-sdk-agent-ready-behaviors/ and
  https://dev.to/dishant0406/vercels-ui-sdk-hands-agents-behaviors-not-components-25n0
