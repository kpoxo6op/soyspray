// Editorial lessons authored by the design master. Original source metadata remains in content.json.
export const editorialLessons = {
  "l1-trust-curve": {
    "schemaVersion": 1,
    "id": "l1-trust-curve",
    "n": 1,
    "title": "Trust is the throttle on parallelism",
    "deck": "Why can’t I simply run more agents, and what actually lets me add them?",
    "summary": "The talk treats trust, not compute, as the limit on how many agents one person can run. Trust comes from evidence that agents behave correctly while you are not watching, so you add agents only as fast as that evidence grows.",
    "minutes": 6,
    "here": [
      "review",
      "merge"
    ],
    "strip": {
      "sentenceHtml": "Where this fits: <strong>Review · Merge</strong>, where your attention sets the limit."
    },
    "decision": "Add agents only as fast as you add evidence, other than your own eyes, that their output is correct.",
    "sections": [
      {
        "slug": "in-short",
        "heading": null,
        "target": "h1"
      },
      {
        "slug": "why-distrust",
        "heading": "Why distrust comes first",
        "id": "l1-why-distrust"
      },
      {
        "slug": "the-curve",
        "heading": "The curve",
        "id": "l1-the-curve"
      },
      {
        "slug": "what-lets-you-add",
        "heading": "What lets you add agents",
        "id": "l1-what-lets-you-add"
      },
      {
        "slug": "her-numbers",
        "heading": "Her numbers, and what transfers",
        "id": "l1-her-numbers"
      },
      {
        "slug": "breaks",
        "heading": "Where the analogy breaks",
        "id": "l1-breaks"
      },
      {
        "slug": "try",
        "heading": "Try it",
        "id": "l1-try"
      },
      {
        "slug": "further",
        "heading": "Going further",
        "id": "l1-further"
      },
      {
        "slug": "check",
        "heading": "Check yourself",
        "id": "l1-check"
      },
      {
        "slug": "rehearse",
        "heading": "Rehearse it",
        "id": "l1-rehearse"
      }
    ],
    "bodyHtml": [
      "<div class='block in-short' data-section='in-short'>",
      "<div class='side side--quiet side--intro' role='note'><p>Numbered notes paraphrase the recording. Select a time to watch and read that moment.</p></div>",
      "<span class='label'>In short</span>",
      "<p class='lead'>The talk treats trust, not compute, as the limit on how many agents one person can run. Trust comes from evidence that agents behave correctly while you are not watching, so you add agents only as fast as that evidence grows.</p>",
      "<details class='terms-inline' data-depth-open='basics'>",
      "<summary>Terms in this lesson · 2</summary>",
      "<p>An agent here means a language model that can run tools, such as editing files, running commands or opening a browser, in a loop until it decides it is done. Its confident tone tells you nothing about whether it is right.</p>",
      "<p>Auto-merge means a change lands on the main branch without a person approving it first. Review happens afterwards, if at all.</p>",
      "</details>",
      "</div>",
      "<div class='block' data-section='why-distrust'>",
      "<div class='side notes' role='group' aria-label='Notes from the talk'>",
      "<p class='notes__label'>From the talk</p>",
      "<ol>",
      "<li class='note'><span class='note__num'>1</span><p class='note__text'>Agents that guess and overclaim root causes destroy an experienced engineer’s trust.</p><button class='note__open' type='button' data-lesson-source='l1-trust-curve:0' data-num='1' aria-label='Open note 1 in the recording, said at 1:03'>1:03 · said</button></li>",
      "<li class='note'><span class='note__num'>2</span><p class='note__text'>Distrusting your agents pushes you into micromanagement, as with a distrusted team.</p><button class='note__open' type='button' data-lesson-source='l1-trust-curve:1' data-num='2' aria-label='Open note 2 in the recording, said at 1:43'>1:43 · said</button></li>",
      "</ol>",
      "</div>",
      "<h2 class='h3 para-head' id='l1-why-distrust' tabindex='-1'>Why distrust comes first</h2>",
      "<p class='para'>Tan opens with the problem rather than the tools. Agents that guess, invent causes and announce again and again that they have found the culprit teach an experienced engineer to distrust <span class='nobr'>them<button class='cite' type='button' data-lesson-source='l1-trust-curve:0' aria-label='Note 1, said at 1:03'>1</button>.</span> She compares the result to managing engineers you do not trust: you end up hovering over every <span class='nobr'>change<button class='cite' type='button' data-lesson-source='l1-trust-curve:1' aria-label='Note 2, said at 1:43'>2</button>.</span></p>",
      "</div>",
      "<div class='block' data-section='the-curve'>",
      "<div class='side notes' role='group' aria-label='Notes from the talk'>",
      "<p class='notes__label'>From the talk</p>",
      "<ol>",
      "<li class='note'><span class='note__num'>3</span><p class='note__text'>An informal chart: heavy supervision of a few agents; no parallelism without trust.</p><button class='note__open' type='button' data-lesson-source='l1-trust-curve:2' data-num='3' aria-label='Open note 3 in the recording, said from 2:13 to 3:16'>2:13–3:16 · said</button></li>",
      "<li class='note'><span class='note__num'>4</span><p class='note__text'>A hand-drawn chart labels its axes trust and number of agents, from 1 through thousands. A single curve rises steeply, then levels off.</p><button class='note__open' type='button' data-lesson-source='l1-trust-curve:3' data-num='4' aria-label='Open note 4, shown on screen at 0:52'>0:52 · shown</button></li>",
      "<li class='note'><span class='note__num'>5</span><p class='note__text'>After about five months, agents auto-merge and she reviews landed changes on main; about 20 landed overnight.</p><button class='note__open' type='button' data-lesson-source='l1-trust-curve:4' data-num='5' aria-label='Open note 5 in the recording, said at 3:18'>3:18 · said</button></li>",
      "</ol>",
      "</div>",
      "<h2 class='h3 para-head' id='l1-the-curve' tabindex='-1'>The curve</h2>",
      "<p class='para'>Her hand-drawn chart, which she calls unscientific, plots this as a <span class='nobr'>curve<button class='cite' type='button' data-lesson-source='l1-trust-curve:2' aria-label='Note 3, said from 2:13 to 3:16'>3</button>.</span> Trust is on one axis and the number of agents on the other, marked from one up to <span class='nobr'>thousands<button class='cite' type='button' data-lesson-source='l1-trust-curve:3' aria-label='Note 4, shown at 0:52'>4</button>.</span> At the low end you supervise one or a few agents and read every output. You cannot fan out, because spawning many agents is pointless while you do not trust the output of one.</p>",
      "<p class='para'>Over about five months, she says, she climbed the curve. She reached the point where agents merge their own PRs and she reviews what has already landed on <span class='nobr'>main<button class='cite' type='button' data-lesson-source='l1-trust-curve:4' aria-label='Note 5, said at 3:18'>5</button>.</span></p>",
      "</div>",
      "<div class='block' data-section='what-lets-you-add'>",
      "<div class='side notes' role='group' aria-label='Notes from the talk'>",
      "<p class='notes__label'>From the talk</p>",
      "<ol>",
      "<li class='note'><span class='note__num'>6</span><p class='note__text'>Do not jump from close supervision straight to huge cloud fleets; it wastes tokens.</p><button class='note__open' type='button' data-lesson-source='l1-trust-curve:7' data-num='6' aria-label='Open note 6 in the recording, said at 27:19'>27:19 · said</button></li>",
      "</ol>",
      "</div>",
      "<h2 class='h3 para-head' id='l1-what-lets-you-add' tabindex='-1'>What lets you add agents</h2>",
      "<p class='para'>For an operator the shape is familiar. You do not raise a deployment’s replica count until its readiness probe means something. Agents are the same: adding them is safe only after something other than your eyes can tell good output from bad. She also warns against skipping the climb, because jumping from close supervision straight to huge fleets of cloud agents mostly burns <span class='nobr'>tokens<button class='cite' type='button' data-lesson-source='l1-trust-curve:7' aria-label='Note 6, said at 27:19'>6</button>.</span></p>",
      "</div>",
      "<div class='block'>",
      "<div class='side side--quiet' role='note'><p>Our steps, not her chart. Her chart is one hand-drawn curve; the steps name the controls this guide teaches.</p></div>",
      "<figure class='figure' aria-labelledby='l1-fig-title'>",
      "<p class='figure__title' id='l1-fig-title'>What has to be true before you add agents</p>",
      "<ol class='ladder__steps'>",
      "<li class='ladder__step'><span class='ladder__count'>One agent</span><p>You read every output and run every check yourself.<span class='ladder__where'>Where everyone starts</span></p></li>",
      "<li class='ladder__step'><span class='ladder__count'>A few</span><p>Each agent attaches evidence from running the real thing, so you check results instead of claims.<span class='ladder__where'><a href='#lesson/l2-verification'>Lesson 2</a> · Verify</span></p></li>",
      "<li class='ladder__step'><span class='ladder__count'>Many</span><p>Hard checks reject bad changes before a person sees them, so review grows more slowly than the agent count.<span class='ladder__where'><a href='#lesson/l5-agent-friendly-architecture'>Lesson 5</a> · Checks</span></p></li>",
      "<li class='ladder__step'><span class='ladder__count'>Merging</span><p>Agents merge behind those checks. You review what landed and count what escaped.<span class='ladder__where'><a href='#lesson/l6-fleet-operations'>Lesson 6</a> · Merge</span></p></li>",
      "</ol>",
      "<p class='ladder__skip'><span class='ladder__skip-mark' aria-hidden='true'></span><span>Skipping steps: a huge fleet checked by nothing but your eyes mostly burns tokens, she <span class='nobr'>warns<button class='cite' type='button' data-lesson-source='l1-trust-curve:7' aria-label='Note 6, said at 27:19'>6</button>.</span></span></p>",
      "</figure>",
      "</div>",
      "<div class='block' data-section='her-numbers'>",
      "<div class='side notes' role='group' aria-label='Notes from the talk'>",
      "<p class='notes__label'>From the talk</p>",
      "<ol>",
      "<li class='note'><span class='note__num'>7</span><p class='note__text'>Self-reported PR volume, with the speaker expecting listeners to question its quality.</p><button class='note__open' type='button' data-lesson-source='l1-trust-curve:5' data-num='7' aria-label='Open note 7 in the recording, said at 4:52'>4:52 · said</button></li>",
      "<li class='note'><span class='note__num'>8</span><p class='note__text'>A slide claims more than 3000 PRs in five months beside a contribution chart labelled with a commit count; the units differ and are not reconciled.</p><button class='note__open' type='button' data-lesson-source='l1-trust-curve:6' data-num='8' aria-label='Open note 8, shown on screen at 4:17'>4:17 · shown</button></li>",
      "</ol>",
      "</div>",
      "<h2 class='h3 para-head' id='l1-her-numbers' tabindex='-1'>Her numbers, and what transfers</h2>",
      "<p class='para'>Treat her numbers as one person’s self-report under unusual conditions. She mentions around a thousand PRs in a month and about 800 by the twelfth of the next, and expects listeners to question how good that code <span class='nobr'>is<button class='cite' type='button' data-lesson-source='l1-trust-curve:5' aria-label='Note 7, said at 4:52'>7</button>.</span> A slide on screen while she talks claims more than 3000 PRs in five months, beside a contribution chart labelled with a commit <span class='nobr'>count<button class='cite' type='button' data-lesson-source='l1-trust-curve:6' aria-label='Note 8, shown at 4:17'>8</button>.</span> PRs and commits are different units, and we do not reconcile them. What transfers is the order of the climb, not the volume.</p>",
      "</div>",
      "<section class='block section-block' data-section='breaks' aria-labelledby='l1-breaks'>",
      "<h2 class='h2' id='l1-breaks' tabindex='-1'>Where the analogy breaks</h2>",
      "<ul class='dash-list'>",
      "<li>Replicas of a service are identical; agent runs are not, because the same task can produce a different change each time.</li>",
      "<li>A failing pod usually fails loudly. A failing agent often reports success, which is the whole trust problem.</li>",
      "<li>Human trust in an engineer accumulates in that person. Agent trust lives mostly in your skills, checks and architecture, and resets when you change models or repositories.</li>",
      "</ul>",
      "</section>",
      "<section class='block section-block' data-section='try' aria-labelledby='l1-try'>",
      "<div class='side side--quiet' role='note'><p>A deterministic teaching model with a fixed schedule. The four rejected PRs are scripted to show a cause, not a measured rate. Ticks are abstract.</p></div>",
      "<h2 class='h2' id='l1-try' tabindex='-1'>Try it</h2>",
      "<p class='para'>The curve in miniature: more agents help only if something other than the reviewer rejects bad work first. Run it with four agents, then switch to one.</p>",
      "<div class='practice' data-scenario='s3-review-backlog' data-context='lesson'></div>",
      "</section>",
      "<section class='block section-block' data-section='further' aria-labelledby='l1-further'>",
      "<h2 class='h2' id='l1-further' tabindex='-1'>Going further</h2>",
      "<p class='para'>Model the curve as a control loop whose gain you raise only as your measurement improves. Without a trustworthy sensor, which here is verification, raising the gain (the agent count) amplifies error; you just see it later. The talk’s later sections are all about improving that sensor.</p>",
      "<p class='para'>Note what she does not claim. She offers no error rate for the auto-merged PRs, and the figure of about 20 PRs landed overnight is an <span class='nobr'>anecdote<button class='cite' type='button' data-lesson-source='l1-trust-curve:4' aria-label='Note 5, said at 3:18'>5</button>.</span> If you adopt auto-merge, define your own escaped-defect measure first, for example reverts per landed change, measured by you.</p>",
      "<details class='limits' data-depth-open='deep'>",
      "<summary>Limits of the evidence · 2</summary>",
      "<ul class='limits__list'>",
      "<li>The recording date is unknown, so her five months and remarks such as the twelfth of the month cannot be dated. Every count in this lesson is her own report.</li>",
      "<li><a href='https://docs.x.ai/grok-bot/overview' rel='noreferrer'>Grok Bot overview ↗</a>, docs.x.ai, retrieved 11 October 2026, page updated 7 October 2026. It describes the product as it ships now: named Bots that share one persistent cloud computer, run in parallel and message each other. That fits her description of named agents you orchestrate, but the page may postdate the recording, so it is not evidence of what she ran.</li>",
      "</ul>",
      "</details>",
      "</section>",
      "<section class='block section-block' data-section='check' aria-labelledby='l1-check'>",
      "<div class='side side--quiet' role='note'><p>Feedback, not a score. Nothing is recorded or sent.</p></div>",
      "<h2 class='h2' id='l1-check' tabindex='-1'>Check yourself</h2>",
      "<form class='quiz' data-lesson-quiz='l1-trust-curve:0' novalidate>",
      "<fieldset class='choices'>",
      "<legend>According to the talk, what should limit how many agents you run in parallel?</legend>",
      "<label class='choice'><input type='radio' name='q-l1-trust-curve-0' value='0' /><span>Available CPU on the build machine<span class='choice__verdict'></span></span></label>",
      "<label class='choice'><input type='radio' name='q-l1-trust-curve-0' value='1' /><span>How much you can trust each agent’s output without watching it<span class='choice__verdict'></span></span></label>",
      "<label class='choice'><input type='radio' name='q-l1-trust-curve-0' value='2' /><span>The number of open issues<span class='choice__verdict'></span></span></label>",
      "<label class='choice'><input type='radio' name='q-l1-trust-curve-0' value='3' /><span>Model context length<span class='choice__verdict'></span></span></label>",
      "</fieldset>",
      "<div class='quiz__actions'><button class='btn' type='submit'>Check</button></div>",
      "<div class='quiz__feedback' role='status'></div>",
      "</form>",
      "<form class='quiz' data-lesson-quiz='l1-trust-curve:1' novalidate>",
      "<fieldset class='choices'>",
      "<legend>Which of these is the speaker’s own framing of her PR counts?</legend>",
      "<label class='choice'><input type='radio' name='q-l1-trust-curve-1' value='0' /><span>A controlled benchmark<span class='choice__verdict'></span></span></label>",
      "<label class='choice'><input type='radio' name='q-l1-trust-curve-1' value='1' /><span>An invitation to question how good the code is<span class='choice__verdict'></span></span></label>",
      "<label class='choice'><input type='radio' name='q-l1-trust-curve-1' value='2' /><span>A guarantee for any team<span class='choice__verdict'></span></span></label>",
      "<label class='choice'><input type='radio' name='q-l1-trust-curve-1' value='3' /><span>A company-wide average<span class='choice__verdict'></span></span></label>",
      "</fieldset>",
      "<div class='quiz__actions'><button class='btn' type='submit'>Check</button></div>",
      "<div class='quiz__feedback' role='status'></div>",
      "</form>",
      "</section>",
      "<section class='block section-block' data-section='rehearse' aria-labelledby='l1-rehearse'>",
      "<div class='side side--quiet' role='note'><p>The lab runs on your machine with stub agents. This site never executes it.</p></div>",
      "<h2 class='h2' id='l1-rehearse' tabindex='-1'>Rehearse it</h2>",
      "<div class='rehearse__line'><pre><code>PREFLIGHT: owned root; no symlinks or Git remotes; stub agents only</code></pre></div>",
      "<p class='para'><strong>Lab step 1 · Preflight and ownership · 5 min.</strong> Before any stub agent runs, the script proves where it may write: a new folder it owns, with no symlinks and no Git repository with a remote in its parents. The first trust you extend to an agent is a workspace that cannot reach anything that matters.</p>",
      "<a class='btn' href='#lab/lab-0-preflight'>Open lab step 1</a>",
      "</section>",
      "<div class='lesson-end'>",
      "<div class='lesson-end__finish'><button class='btn finish' type='button' aria-pressed='false' data-finish='l1-trust-curve'><span class='finish__mark' aria-hidden='true'></span><span data-finish-label>Mark lesson as finished</span></button><p class='lesson-end__progress meta' data-progress-count hidden></p></div>",
      "<nav class='lesson-end__nav' aria-label='Lesson navigation'>",
      "<a class='next' href='#lesson/l2-verification'><span class='next__label'>Next · Lesson 2 · 7 min</span><span class='next__title'>Verification closes the loop<span class='next__arrow' aria-hidden='true'>→</span></span></a>",
      "<a class='prev' href='#home'>Back to the path of one agent change</a>",
      "</nav>",
      "</div>"
    ],
    "notes": [
      {
        "n": 1,
        "source": "l1-trust-curve:0",
        "kind": "said",
        "time": "1:03",
        "range": "1:03–1:35",
        "panelKind": "Our paraphrase · said at 1:03",
        "paraphrase": "Agents that guess and overclaim root causes destroy an experienced engineer’s trust.",
        "evidence": {
          "start": 63.1,
          "end": 95.1,
          "label": "SAID"
        }
      },
      {
        "n": 2,
        "source": "l1-trust-curve:1",
        "kind": "said",
        "time": "1:43",
        "range": "1:43–2:11",
        "panelKind": "Our paraphrase · said at 1:43",
        "paraphrase": "Distrusting your agents pushes you into micromanagement, as with a distrusted team.",
        "evidence": {
          "start": 103.2,
          "end": 131.4,
          "label": "SAID"
        }
      },
      {
        "n": 3,
        "source": "l1-trust-curve:2",
        "kind": "said-long",
        "time": "2:13–3:16",
        "range": "2:13–3:16",
        "panelKind": "A longer stretch · said from 2:13 to 3:16",
        "paraphrase": "An informal chart: heavy supervision of a few agents; no parallelism without trust.",
        "evidence": {
          "start": 133.2,
          "end": 196.4,
          "label": "SAID"
        }
      },
      {
        "n": 4,
        "source": "l1-trust-curve:3",
        "kind": "shown",
        "time": "0:52",
        "range": "0:52–4:07",
        "panelKind": "Shown on screen at 0:52 · not narrated",
        "paraphrase": "A hand-drawn chart labels its axes trust and number of agents, from 1 through thousands. A single curve rises steeply, then levels off.",
        "evidence": {
          "start": 52.3,
          "end": 247.0,
          "label": "SHOWN",
          "frameId": "lauren_00h02m20.000s_periodic"
        }
      },
      {
        "n": 5,
        "source": "l1-trust-curve:4",
        "kind": "said",
        "time": "3:18",
        "range": "3:18–3:52",
        "panelKind": "Our paraphrase · said at 3:18",
        "paraphrase": "After about five months, agents auto-merge and she reviews landed changes on main; about 20 landed overnight.",
        "evidence": {
          "start": 198.4,
          "end": 232.0,
          "label": "SAID"
        }
      },
      {
        "n": 6,
        "source": "l1-trust-curve:7",
        "kind": "said",
        "time": "27:19",
        "range": "27:19–27:37",
        "panelKind": "Our paraphrase · said at 27:19",
        "paraphrase": "Do not jump from close supervision straight to huge cloud fleets; it wastes tokens.",
        "evidence": {
          "start": 1639.9,
          "end": 1657.3,
          "label": "SAID"
        }
      },
      {
        "n": 7,
        "source": "l1-trust-curve:5",
        "kind": "said",
        "time": "4:52",
        "range": "4:52–5:29",
        "panelKind": "Our paraphrase · said at 4:52",
        "paraphrase": "Self-reported PR volume, with the speaker expecting listeners to question its quality.",
        "evidence": {
          "start": 292.3,
          "end": 329.4,
          "label": "SAID"
        }
      },
      {
        "n": 8,
        "source": "l1-trust-curve:6",
        "kind": "shown",
        "time": "4:17",
        "range": "4:17–5:30",
        "panelKind": "Shown on screen at 4:17 · not narrated",
        "paraphrase": "A slide claims more than 3000 PRs in five months beside a contribution chart labelled with a commit count; the units differ and are not reconciled.",
        "evidence": {
          "start": 257.6,
          "end": 330.0,
          "label": "SHOWN",
          "frameId": "visual-257.6.jpg"
        }
      }
    ],
    "checks": [
      {
        "index": 0,
        "question": "According to the talk, what should limit how many agents you run in parallel?",
        "options": [
          "Available CPU on the build machine",
          "How much you can trust each agent’s output without watching it",
          "The number of open issues",
          "Model context length"
        ],
        "answer": 1,
        "explanationHtml": "She ties parallelism to trust: spawning many agents is pointless while you cannot trust the output of one. CPU, open issues and context length are real limits, but not the one she argues from. She says so at <button class='time-link' type='button' data-lesson-source='l1-trust-curve:2' aria-label='Note 3, said from 2:13 to 3:16'>2:13</button>.",
        "status": "question, options and answer verbatim (typographic apostrophe); explanation rewritten without the numeric range"
      },
      {
        "index": 1,
        "question": "Which of these is the speaker’s own framing of her PR counts?",
        "options": [
          "A controlled benchmark",
          "An invitation to question how good the code is",
          "A guarantee for any team",
          "A company-wide average"
        ],
        "answer": 1,
        "explanationHtml": "She raises the question of quality herself, at <button class='time-link' type='button' data-lesson-source='l1-trust-curve:5' aria-label='Note 7, said at 4:52'>4:52</button>. The counts are one person’s self-report, not a benchmark, a guarantee or a team average.",
        "status": "question, options and answer verbatim (typographic apostrophe); explanation rewritten without the numeric range"
      }
    ],
    "practice": [
      {
        "scenario": "s3-review-backlog",
        "section": "try",
        "role": "home lesson of this experiment (design-spec simulator.scenarios)"
      }
    ],
    "lab": {
      "step": "lab-0-preflight",
      "n": 1,
      "title": "Preflight and ownership",
      "minutes": 5,
      "outputLine": "PREFLIGHT: owned root; no symlinks or Git remotes; stub agents only"
    },
    "supplements": {
      "basics": "Both original basics paragraphs retained verbatim in Terms in this lesson (typographic quotes only).",
      "deep": "Both original deep paragraphs retained in Going further, lightly edited for flow. The repeated-anecdote range (2099.2–2106.1) is dropped because it has no evidence entry. Limits of the evidence carries the dating caution and the l1 docs entry.",
      "practitioner": "All four original paragraphs rewritten as four argued sections without numeric ranges; every factual claim kept, each cited to its evidence entry."
    },
    "end": {
      "next": {
        "href": "#lesson/l2-verification",
        "label": "Next · Lesson 2 · 7 min",
        "title": "Verification closes the loop"
      },
      "previous": {
        "href": "#home",
        "text": "Back to the path of one agent change"
      }
    }
  },
  "l2-verification": {
    "schemaVersion": 1,
    "id": "l2-verification",
    "n": 2,
    "title": "Verification closes the loop",
    "deck": "What does it mean for an agent to verify its own work, and why does that matter more than code quality?",
    "summary": "Verification means the agent exercises the real system as a user or profiler would. Without it, you become the verifier and the bottleneck.",
    "minutes": 7,
    "here": [
      "verify"
    ],
    "strip": {
      "sentenceHtml": "Where this fits: <strong>Verify</strong>, between the agent’s change and the hard checks."
    },
    "decision": "An agent’s task is done only when it attaches evidence from running the real thing: the symptom reproduced first, then observed absent with the same probe.",
    "sections": [
      {
        "slug": "in-short",
        "heading": null,
        "target": "h1"
      },
      {
        "slug": "what-verification-means",
        "heading": "What verification means",
        "id": "l2-what-verification-means"
      },
      {
        "slug": "you-are-the-verifier",
        "heading": "When you are the verifier",
        "id": "l2-you-are-the-verifier"
      },
      {
        "slug": "a-probe-for-every-agent",
        "heading": "A probe for every agent",
        "id": "l2-a-probe-for-every-agent"
      },
      {
        "slug": "no-evidence-not-done",
        "heading": "No evidence, not done",
        "id": "l2-no-evidence-not-done"
      },
      {
        "slug": "breaks",
        "heading": "Where the analogy breaks",
        "id": "l2-breaks"
      },
      {
        "slug": "try",
        "heading": "Try it",
        "id": "l2-try"
      },
      {
        "slug": "further",
        "heading": "Going further",
        "id": "l2-further"
      },
      {
        "slug": "check",
        "heading": "Check yourself",
        "id": "l2-check"
      },
      {
        "slug": "rehearse",
        "heading": "Rehearse it",
        "id": "l2-rehearse"
      }
    ],
    "bodyHtml": [
      "<div class='block in-short' data-section='in-short'>",
      "<div class='side side--quiet side--intro' role='note'><p>Numbered notes paraphrase the recording. Select a time to watch and read that moment.</p></div>",
      "<span class='label'>In short</span>",
      "<p class='lead'>Verification means the agent exercises the real system as a user or profiler would. Without it, you become the verifier and the bottleneck.</p>",
      "<details class='terms-inline' data-depth-open='basics'>",
      "<summary>Terms in this lesson · 2</summary>",
      "<p>A trace is a recording of what a program did over time, often shown as a flame graph where wide blocks used the most time. A heap snapshot records memory in use.</p>",
      "<p>A simulator or debugging protocol lets software click, type and measure inside an application the way a person would.</p>",
      "</details>",
      "</div>",
      "<div class='block' data-section='what-verification-means'>",
      "<div class='side notes' role='group' aria-label='Notes from the talk'>",
      "<p class='notes__label'>From the talk</p>",
      "<ol>",
      "<li class='note'><span class='note__num'>1</span><p class='note__text'>Verification is the most important skill to give an agent.</p><button class='note__open' type='button' data-lesson-source='l2-verification:0' data-num='1' aria-label='Open note 1 in the recording, said at 5:46'>5:46 · said</button></li>",
      "<li class='note'><span class='note__num'>2</span><p class='note__text'>Agents should run the real app, profile and simulate as users would; this yields correct, not necessarily good, code.</p><button class='note__open' type='button' data-lesson-source='l2-verification:1' data-num='2' aria-label='Open note 2 in the recording, said at 6:00'>6:00 · said</button></li>",
      "</ol>",
      "</div>",
      "<h2 class='h3 para-head' id='l2-what-verification-means' tabindex='-1'>What verification means</h2>",
      "<p class='para'>Tan names verification as the most important skill to give <span class='nobr'>agents<button class='cite' type='button' data-lesson-source='l2-verification:0' aria-label='Note 1, said at 5:46'>1</button>.</span> She means real execution: running the code, capturing CPU traces or heap snapshots, driving an iOS simulator, using the product the way users do. Her careful claim is that verification does not make agents write good code; it makes them write correct code, and that is the step that earns <span class='nobr'>trust<button class='cite' type='button' data-lesson-source='l2-verification:1' aria-label='Note 2, said at 6:00'>2</button>.</span></p>",
      "</div>",
      "<div class='block' data-section='you-are-the-verifier'>",
      "<div class='side notes' role='group' aria-label='Notes from the talk'>",
      "<p class='notes__label'>From the talk</p>",
      "<ol>",
      "<li class='note'><span class='note__num'>3</span><p class='note__text'>Given screenshots and traces, the agent confidently named a cause that was wrong.</p><button class='note__open' type='button' data-lesson-source='l2-verification:2' data-num='3' aria-label='Open note 3 in the recording, said at 8:15'>8:15 · said</button></li>",
      "<li class='note'><span class='note__num'>4</span><p class='note__text'>Without a verification skill, the human becomes the verifier and bottleneck, and nothing parallelises.</p><button class='note__open' type='button' data-lesson-source='l2-verification:3' data-num='4' aria-label='Open note 4 in the recording, said at 8:37'>8:37 · said</button></li>",
      "</ol>",
      "</div>",
      "<h2 class='h3 para-head' id='l2-you-are-the-verifier' tabindex='-1'>When you are the verifier</h2>",
      "<p class='para'>Her early performance story shows the alternative. New to the codebase and under deadline, she captured traces by hand and passed screenshots to an agent. It confidently named a cause, and fixing it did not solve the <span class='nobr'>problem<button class='cite' type='button' data-lesson-source='l2-verification:2' aria-label='Note 3, said at 8:15'>3</button>.</span> In that workflow the human runs the build, spots the failure and pastes errors back. You are the loop’s sensor, so nothing <span class='nobr'>parallelises<button class='cite' type='button' data-lesson-source='l2-verification:3' aria-label='Note 4, said at 8:37'>4</button>.</span></p>",
      "</div>",
      "<div class='block'>",
      "<div class='side side--quiet' role='note'><p>Our diagram of the contrast in her performance story. It is not a slide from the talk.</p></div>",
      "<figure class='figure' aria-labelledby='l2-fig-title'>",
      "<p class='figure__title' id='l2-fig-title'>Who closes the loop</p>",
      "<div class='loops'>",
      "<div class='loops__panel'>",
      "<p class='loops__title'>Without a probe, the loop runs through you</p>",
      "<svg viewBox='0 0 300 240' role='img' aria-labelledby='l2-fig-a-t l2-fig-a-d'>",
      "<title id='l2-fig-a-t'>Without a probe</title>",
      "<desc id='l2-fig-a-d'>Three agents send their changes to you. You run each one and paste the errors back, so every agent waits on you.</desc>",
      "<defs><marker id='l2-ahA' viewBox='0 0 10 10' refX='8.5' refY='5' markerWidth='7' markerHeight='7' orient='auto-start-reverse'><path d='M0 0 L10 5 L0 10 z' class='fig-arrowhead' /></marker></defs>",
      "<path d='M80 50 V190' class='fig-line fig-line--quiet' />",
      "<circle cx='60' cy='60' r='6' class='fig-node' />",
      "<circle cx='60' cy='120' r='6' class='fig-node' />",
      "<circle cx='60' cy='180' r='6' class='fig-node' />",
      "<text x='46' y='65' text-anchor='end' class='fig-text'>agent</text>",
      "<text x='46' y='125' text-anchor='end' class='fig-text'>agent</text>",
      "<text x='46' y='185' text-anchor='end' class='fig-text'>agent</text>",
      "<path d='M90 104 Q 138 64 182 110' class='fig-line' marker-end='url(#l2-ahA)' />",
      "<path d='M182 130 Q 138 176 90 136' class='fig-line' marker-end='url(#l2-ahA)' />",
      "<text x='136' y='70' text-anchor='middle' class='fig-text'>change</text>",
      "<text x='136' y='186' text-anchor='middle' class='fig-text'>errors back</text>",
      "<circle cx='196' cy='120' r='11' class='fig-node fig-node--signal' />",
      "<text x='216' y='116' class='fig-text fig-text--signal'>you,</text>",
      "<text x='216' y='134' class='fig-text fig-text--signal'>the probe</text>",
      "</svg>",
      "<p>You run the build, spot the failure and paste errors back. Every agent waits on the same probe, so adding agents adds waiting.</p>",
      "</div>",
      "<div class='loops__panel'>",
      "<p class='loops__title'>With a probe, each agent closes its own loop</p>",
      "<svg viewBox='0 0 300 240' role='img' aria-labelledby='l2-fig-b-t l2-fig-b-d'>",
      "<title id='l2-fig-b-t'>With a probe</title>",
      "<desc id='l2-fig-b-d'>Each of three agents runs its own probe in a small loop, then sends evidence to you for review afterwards.</desc>",
      "<defs><marker id='l2-ahB' viewBox='0 0 10 10' refX='8.5' refY='5' markerWidth='7' markerHeight='7' orient='auto-start-reverse'><path d='M0 0 L10 5 L0 10 z' class='fig-arrowhead' /></marker><marker id='l2-ahBq' viewBox='0 0 10 10' refX='8.5' refY='5' markerWidth='6' markerHeight='6' orient='auto-start-reverse'><path d='M0 0 L10 5 L0 10 z' class='fig-arrowhead fig-arrowhead--quiet' /></marker></defs>",
      "<text x='150' y='22' text-anchor='middle' class='fig-text'>probe</text>",
      "<circle cx='56' cy='48' r='6' class='fig-node' />",
      "<rect x='144' y='42' width='12' height='12' class='fig-probe' />",
      "<path d='M63 43 Q 100 20 141 42' class='fig-line' marker-end='url(#l2-ahB)' />",
      "<path d='M144 57 Q 100 78 64 54' class='fig-line' marker-end='url(#l2-ahB)' />",
      "<circle cx='56' cy='128' r='6' class='fig-node' />",
      "<rect x='144' y='122' width='12' height='12' class='fig-probe' />",
      "<path d='M63 123 Q 100 100 141 122' class='fig-line' marker-end='url(#l2-ahB)' />",
      "<path d='M144 137 Q 100 158 64 134' class='fig-line' marker-end='url(#l2-ahB)' />",
      "<circle cx='56' cy='208' r='6' class='fig-node' />",
      "<rect x='144' y='202' width='12' height='12' class='fig-probe' />",
      "<path d='M63 203 Q 100 180 141 202' class='fig-line' marker-end='url(#l2-ahB)' />",
      "<path d='M144 217 Q 100 238 64 214' class='fig-line' marker-end='url(#l2-ahB)' />",
      "<text x='42' y='53' text-anchor='end' class='fig-text'>agent</text>",
      "<text x='42' y='133' text-anchor='end' class='fig-text'>agent</text>",
      "<text x='42' y='213' text-anchor='end' class='fig-text'>agent</text>",
      "<path d='M162 52 L 242 121' class='fig-line fig-line--quiet' marker-end='url(#l2-ahBq)' />",
      "<path d='M162 128 L 239 128' class='fig-line fig-line--quiet' marker-end='url(#l2-ahBq)' />",
      "<path d='M162 204 L 242 135' class='fig-line fig-line--quiet' marker-end='url(#l2-ahBq)' />",
      "<circle cx='252' cy='128' r='9' class='fig-node fig-node--hollow' />",
      "<text x='252' y='158' text-anchor='middle' class='fig-text fig-text--strong'>you</text>",
      "<text x='252' y='176' text-anchor='middle' class='fig-text'>review</text>",
      "<text x='252' y='194' text-anchor='middle' class='fig-text'>evidence</text>",
      "</svg>",
      "<p>Each agent runs the real thing and attaches the evidence. You review results afterwards, so agents can work in parallel.</p>",
      "</div>",
      "</div>",
      "</figure>",
      "</div>",
      "<div class='block' data-section='a-probe-for-every-agent'>",
      "<h2 class='h3 para-head' id='l2-a-probe-for-every-agent' tabindex='-1'>A probe for every agent</h2>",
      "<p class='para'>An agent that only edits code is an actuator with no feedback. Verification gives each agent its own probe, so that ‘done’ means the system was observed in the target state, the same standard as a reconciliation loop comparing observed with desired state. Her later evals section, in <a href='#lesson/l4-pstack-evals'>lesson 4</a>, is the next layer: checking that the verification itself works.</p>",
      "</div>",
      "<div class='block' data-section='no-evidence-not-done'>",
      "<h2 class='h3 para-head' id='l2-no-evidence-not-done' tabindex='-1'>No evidence, not done</h2>",
      "<p class='para'>The rule to adopt: an agent may not report a task done without attaching evidence from running the thing. That evidence is a test run, a trace, a screenshot from automation or a command output. ‘I changed the code that should fix it’ is a hypothesis, not a result.</p>",
      "</div>",
      "<section class='block section-block' data-section='breaks' aria-labelledby='l2-breaks'>",
      "<h2 class='h2' id='l2-breaks' tabindex='-1'>Where the analogy breaks</h2>",
      "<ul class='dash-list'>",
      "<li>A readiness probe is written by you. An agent may write or edit its own check, so it can quietly weaken the verification it reports.</li>",
      "<li>Correct is not the same as maintainable; she says so directly, which is why the <a href='#lesson/l5-agent-friendly-architecture'>architecture lesson</a> exists.</li>",
      "</ul>",
      "</section>",
      "<section class='block section-block' data-section='try' aria-labelledby='l2-try'>",
      "<div class='side side--quiet' role='note'><p>A deterministic teaching model with a fixed schedule. T3’s failure is scripted to show a cause; it is not a measured rate. Ticks and cost units are abstract.</p></div>",
      "<h2 class='h2' id='l2-try' tabindex='-1'>Try it</h2>",
      "<p class='para'>Three agents report a fix and one of them is wrong. Predict what reaches main with the gate off, then switch verification on.</p>",
      "<div class='practice' data-scenario='s2-plausible-vs-verified' data-context='lesson'></div>",
      "</section>",
      "<section class='block section-block' data-section='further' aria-labelledby='l2-further'>",
      "<div class='side notes' role='group' aria-label='Notes from the talk'>",
      "<p class='notes__label'>From the talk</p>",
      "<ol>",
      "<li class='note'><span class='note__num'>5</span><p class='note__text'>In a briefly visible chat thread, an agent’s reply to a bug report tells the fixing agent to write a failing test first. It then asks the agent to prove the fix on a real build, with before-and-after recordings showing the symptom disappear.</p><button class='note__open' type='button' data-lesson-source='l2-verification:4' data-num='5' aria-label='Open note 5, shown on screen at 6:49'>6:49 · shown</button></li>",
      "</ol>",
      "</div>",
      "<h2 class='h2' id='l2-further' tabindex='-1'>Going further</h2>",
      "<p class='para'>The standard shows up once more, on screen and unnarrated. In a chat thread, an agent answering a bug report asks the fixing agent for a failing test first, then for before-and-after recordings on a real build that show the symptom <span class='nobr'>gone<button class='cite' type='button' data-lesson-source='l2-verification:4' aria-label='Note 5, shown at 6:49'>5</button>.</span> It separates three claims an agent can make.</p>",
      "<figure class='claims' aria-label='Three claims an agent can make'>",
      "<dl class='claims__list'>",
      "<div class='claims__row'><dt>Proposed</dt><dd>Here is a change.</dd></div>",
      "<div class='claims__row' data-gap-start><dt>Plausible</dt><dd>The change matches the described symptom.</dd></div>",
      "<div class='claims__row claims__row--verified' data-gap-end><dt>Verified</dt><dd>The symptom was reproduced, then shown absent after the change, using the same probe.</dd></div>",
      "</dl>",
      "<span class='claims__gap-label'>the gap</span>",
      "</figure>",
      "<p class='para'>Most agent overconfidence lives in the gap between plausible and verified. Make your check harness reproduce the failure before the fix, or you only test that something runs.</p>",
      "<p class='para'>Verification has its own failure modes: probes that always pass, environments that differ from production, flaky measurements. Treat a verifier like a monitoring check. Prove it fires on a known-bad case before trusting its green.</p>",
      "<details class='limits' data-depth-open='deep'>",
      "<summary>Limits of the evidence · 2</summary>",
      "<ul class='limits__list'>",
      "<li>Her performance story is one anecdote, told in her words. The lesson relies only on its shape: an agent named a cause confidently and was wrong.</li>",
      "<li>The chat thread in note 5 is on screen for about two seconds and is not narrated. The guide reads it from the frame, and the three claims are our framing of it.</li>",
      "</ul>",
      "</details>",
      "</section>",
      "<section class='block section-block' data-section='check' aria-labelledby='l2-check'>",
      "<h2 class='h2' id='l2-check' tabindex='-1'>Check yourself</h2>",
      "<form class='quiz' data-lesson-quiz='l2-verification:0' novalidate>",
      "<fieldset class='choices'>",
      "<legend>What does the speaker say verification gives you?</legend>",
      "<label class='choice'><input type='radio' name='q-l2-verification-0' value='0' /><span>Good, idiomatic code<span class='choice__verdict'></span></span></label>",
      "<label class='choice'><input type='radio' name='q-l2-verification-0' value='1' /><span>At least correct code<span class='choice__verdict'></span></span></label>",
      "<label class='choice'><input type='radio' name='q-l2-verification-0' value='2' /><span>Faster models<span class='choice__verdict'></span></span></label>",
      "<label class='choice'><input type='radio' name='q-l2-verification-0' value='3' /><span>Fewer tokens<span class='choice__verdict'></span></span></label>",
      "</fieldset>",
      "<div class='quiz__actions'><button class='btn' type='submit'>Check</button></div>",
      "<div class='quiz__feedback' role='status'></div>",
      "</form>",
      "<form class='quiz' data-lesson-quiz='l2-verification:1' novalidate>",
      "<fieldset class='choices'>",
      "<legend>An agent says it found the bug and edited the file. Under this lesson’s rule, what is missing?</legend>",
      "<label class='choice'><input type='radio' name='q-l2-verification-1' value='0' /><span>Nothing<span class='choice__verdict'></span></span></label>",
      "<label class='choice'><input type='radio' name='q-l2-verification-1' value='1' /><span>Evidence that the symptom was reproduced and then observed absent<span class='choice__verdict'></span></span></label>",
      "<label class='choice'><input type='radio' name='q-l2-verification-1' value='2' /><span>A longer explanation<span class='choice__verdict'></span></span></label>",
      "<label class='choice'><input type='radio' name='q-l2-verification-1' value='3' /><span>A second model’s opinion<span class='choice__verdict'></span></span></label>",
      "</fieldset>",
      "<div class='quiz__actions'><button class='btn' type='submit'>Check</button></div>",
      "<div class='quiz__feedback' role='status'></div>",
      "</form>",
      "</section>",
      "<section class='block section-block' data-section='rehearse' aria-labelledby='l2-rehearse'>",
      "<h2 class='h2' id='l2-rehearse' tabindex='-1'>Rehearse it</h2>",
      "<div class='rehearse__line'><pre><code>VERIFICATION: sh check.sh proves PASS on baseline and FAIL on a known-bad branch</code></pre></div>",
      "<p class='para'><strong>Lab step 3 · A check that runs the real thing · 8 min.</strong> Reject a plausible but wrong change with a check that runs the app. The script requires the check to fail on a known-bad branch: a check that cannot fail on a known-bad change proves nothing.</p>",
      "<a class='btn' href='#lab/lab-2-verify'>Open lab step 3</a>",
      "</section>",
      "<div class='lesson-end'>",
      "<div class='lesson-end__finish'><button class='btn finish' type='button' aria-pressed='false' data-finish='l2-verification'><span class='finish__mark' aria-hidden='true'></span><span data-finish-label>Mark lesson as finished</span></button><p class='lesson-end__progress meta' data-progress-count hidden></p></div>",
      "<nav class='lesson-end__nav' aria-label='Lesson navigation'>",
      "<a class='next' href='#lesson/l3-feature-map'><span class='next__label'>Next · Lesson 3 · 6 min</span><span class='next__title'>Agents need a map of the product<span class='next__arrow' aria-hidden='true'>→</span></span></a>",
      "<a class='prev' href='#lesson/l1-trust-curve'>Previous: Trust is the throttle on parallelism</a>",
      "</nav>",
      "</div>"
    ],
    "notes": [
      {
        "n": 1,
        "source": "l2-verification:0",
        "kind": "said",
        "time": "5:46",
        "range": "5:46–6:00",
        "panelKind": "Our paraphrase · said at 5:46",
        "paraphrase": "Verification is the most important skill to give an agent.",
        "evidence": {
          "start": 346.0,
          "end": 360.4,
          "label": "SAID"
        }
      },
      {
        "n": 2,
        "source": "l2-verification:1",
        "kind": "said",
        "time": "6:00",
        "range": "6:00–6:38",
        "panelKind": "Our paraphrase · said at 6:00",
        "paraphrase": "Agents should run the real app, profile and simulate as users would; this yields correct, not necessarily good, code.",
        "evidence": {
          "start": 360.4,
          "end": 398.5,
          "label": "SAID"
        }
      },
      {
        "n": 3,
        "source": "l2-verification:2",
        "kind": "said",
        "time": "8:15",
        "range": "8:15–8:34",
        "panelKind": "Our paraphrase · said at 8:15",
        "paraphrase": "Given screenshots and traces, the agent confidently named a cause that was wrong.",
        "evidence": {
          "start": 495.2,
          "end": 514.2,
          "label": "SAID"
        }
      },
      {
        "n": 4,
        "source": "l2-verification:3",
        "kind": "said",
        "time": "8:37",
        "range": "8:37–9:15",
        "panelKind": "Our paraphrase · said at 8:37",
        "paraphrase": "Without a verification skill, the human becomes the verifier and bottleneck, and nothing parallelises.",
        "evidence": {
          "start": 517.9,
          "end": 555.9,
          "label": "SAID"
        }
      },
      {
        "n": 5,
        "source": "l2-verification:4",
        "kind": "shown",
        "time": "6:49",
        "range": "6:49–6:51",
        "panelKind": "Shown on screen at 6:49 · not narrated",
        "paraphrase": "In a briefly visible chat thread, an agent’s reply to a bug report tells the fixing agent to write a failing test first. It then asks the agent to prove the fix on a real build, with before-and-after recordings showing the symptom disappear.",
        "evidence": {
          "start": 409.3,
          "end": 411.5,
          "label": "SHOWN",
          "frameId": "lauren_00h06m49.333s_transition"
        }
      }
    ],
    "checks": [
      {
        "index": 0,
        "question": "What does the speaker say verification gives you?",
        "options": [
          "Good, idiomatic code",
          "At least correct code",
          "Faster models",
          "Fewer tokens"
        ],
        "answer": 1,
        "explanationHtml": "Verification makes agents write correct code, she says, not necessarily good code; good code is what the architecture lesson is for. She draws the line at <button class='time-link' type='button' data-lesson-source='l2-verification:1' aria-label='Note 2, said at 6:00'>6:00</button>.",
        "status": "question, options and answer verbatim; explanation rewritten without the numeric range"
      },
      {
        "index": 1,
        "question": "An agent says it found the bug and edited the file. Under this lesson’s rule, what is missing?",
        "options": [
          "Nothing",
          "Evidence that the symptom was reproduced and then observed absent",
          "A longer explanation",
          "A second model’s opinion"
        ],
        "answer": 1,
        "explanationHtml": "Editing the file is a proposed change, not a result. Verified means the symptom was reproduced first, then observed absent after the change, using the same probe.",
        "status": "question, options and answer verbatim (typographic apostrophes); explanation expanded with the same answer"
      }
    ],
    "practice": [
      {
        "scenario": "s2-plausible-vs-verified",
        "section": "try",
        "role": "home lesson of this experiment (design-spec simulator.scenarios)"
      }
    ],
    "lab": {
      "step": "lab-2-verify",
      "n": 3,
      "title": "A check that runs the real thing",
      "minutes": 8,
      "outputLine": "VERIFICATION: sh check.sh proves PASS on baseline and FAIL on a known-bad branch"
    },
    "supplements": {
      "basics": "Both original basics paragraphs retained verbatim in Terms in this lesson.",
      "deep": "Both original deep paragraphs retained in Going further, with the three claims set as the typographic figure from the reference and introduced through the unnarrated chat thread (note 5). Limits of the evidence holds two editorial notes.",
      "practitioner": "All four original paragraphs retained in substance under four specific heads. Numeric ranges removed; each claim cited to its evidence entry."
    },
    "end": {
      "next": {
        "href": "#lesson/l3-feature-map",
        "label": "Next · Lesson 3 · 6 min",
        "title": "Agents need a map of the product"
      },
      "previous": {
        "href": "#lesson/l1-trust-curve",
        "text": "Previous: Trust is the throttle on parallelism"
      }
    }
  },
  "l3-feature-map": {
    "schemaVersion": 1,
    "id": "l3-feature-map",
    "n": 3,
    "title": "Agents need a map of the product",
    "deck": "How does an agent find the feature a vague bug report is about, and reach it in the running app?",
    "summary": "The ability to drive the app is not enough; agents also need a maintained map from user-visible features to UI paths, shortcuts, selectors and code.",
    "minutes": 6,
    "here": [
      "agent",
      "verify"
    ],
    "strip": {
      "sentenceHtml": "Where this fits: <strong>Agent · Verify</strong>, before an agent can reproduce anything."
    },
    "decision": "Give agents a maintained map from features to UI paths and selectors, and make every entry checkable so a stale one fails instead of misleading.",
    "sections": [
      {
        "slug": "in-short",
        "heading": null,
        "target": "h1"
      },
      {
        "slug": "drive-the-app",
        "heading": "First, a way to drive the app",
        "id": "l3-drive-the-app"
      },
      {
        "slug": "map-of-the-product",
        "heading": "Then, a map of the product",
        "id": "l3-map-of-the-product"
      },
      {
        "slug": "triage",
        "heading": "Triage for vague reports",
        "id": "l3-triage"
      },
      {
        "slug": "runbook-index",
        "heading": "A runbook index for a UI",
        "id": "l3-runbook-index"
      },
      {
        "slug": "breaks",
        "heading": "Where the analogy breaks",
        "id": "l3-breaks"
      },
      {
        "slug": "further",
        "heading": "Going further",
        "id": "l3-further"
      },
      {
        "slug": "check",
        "heading": "Check yourself",
        "id": "l3-check"
      },
      {
        "slug": "rehearse",
        "heading": "Rehearse it",
        "id": "l3-rehearse"
      }
    ],
    "bodyHtml": [
      "<div class='block in-short' data-section='in-short'>",
      "<div class='side side--quiet side--intro' role='note'><p>Numbered notes paraphrase the recording. Select a time to watch and read that moment.</p></div>",
      "<span class='label'>In short</span>",
      "<p class='lead'>The ability to drive the app is not enough; agents also need a maintained map from user-visible features to UI paths, shortcuts, selectors and code.</p>",
      "<details class='terms-inline' data-depth-open='basics'>",
      "<summary>Terms in this lesson · 2</summary>",
      "<p>DOM attributes are labels on page elements that automation uses to find a button or panel reliably.</p>",
      "<p>A skill, in this talk, is mostly a markdown file of instructions that an agent loads for a kind of task.</p>",
      "</details>",
      "</div>",
      "<div class='block' data-section='drive-the-app'>",
      "<div class='side notes' role='group' aria-label='Notes from the talk'>",
      "<p class='notes__label'>From the talk</p>",
      "<ol>",
      "<li class='note'><span class='note__num'>1</span><p class='note__text'>The control skill lets agents run and inspect the app via debugging protocols, and similar tools exist for iOS.</p><button class='note__open' type='button' data-lesson-source='l3-feature-map:0' data-num='1' aria-label='Open note 1 in the recording, said at 9:16'>9:16 · said</button></li>",
      "<li class='note'><span class='note__num'>2</span><p class='note__text'>The control skill’s documentation describes driving a running dev build over CDP, with separate worktree-isolated instances.</p><button class='note__open' type='button' data-lesson-source='l3-feature-map:1' data-num='2' aria-label='Open note 2, shown on screen at 7:20'>7:20 · shown</button></li>",
      "</ol>",
      "</div>",
      "<h2 class='h3 para-head' id='l3-drive-the-app' tabindex='-1'>First, a way to drive the app</h2>",
      "<p class='para'>Her first skill, Control Glass, drives the agents window through the Chrome DevTools Protocol. She says the window is internally called Glass, that Apple tooling plays a similar role for iOS, and that the code itself is unremarkable: an agent can write one for <span class='nobr'>you<button class='cite' type='button' data-lesson-source='l3-feature-map:0' aria-label='Note 1, said at 9:16'>1</button>.</span> The skill’s documentation, shown on screen, describes driving a running development build over that protocol with Playwright, including separate worktree-isolated <span class='nobr'>instances<button class='cite' type='button' data-lesson-source='l3-feature-map:1' aria-label='Note 2, shown at 7:20'>2</button>.</span></p>",
      "</div>",
      "<div class='block' data-section='map-of-the-product'>",
      "<div class='side notes' role='group' aria-label='Notes from the talk'>",
      "<p class='notes__label'>From the talk</p>",
      "<ol>",
      "<li class='note'><span class='note__num'>3</span><p class='note__text'>Able to run the app but ignorant of it, agents flailed on feature-specific reports.</p><button class='note__open' type='button' data-lesson-source='l3-feature-map:2' data-num='3' aria-label='Open note 3 in the recording, said at 10:23'>10:23 · said</button></li>",
      "<li class='note'><span class='note__num'>4</span><p class='note__text'>Map entries cover location, navigation, shortcuts and selector attributes from the user’s view.</p><button class='note__open' type='button' data-lesson-source='l3-feature-map:4' data-num='4' aria-label='Open note 4 in the recording, said at 12:49'>12:49 · said</button></li>",
      "<li class='note'><span class='note__num'>5</span><p class='note__text'>The feature-map README describes one file per feature from the user’s side, plus preferred selector attributes for automation.</p><button class='note__open' type='button' data-lesson-source='l3-feature-map:3' data-num='5' aria-label='Open note 5, shown on screen at 10:20'>10:20 · shown</button></li>",
      "</ol>",
      "</div>",
      "<h2 class='h3 para-head' id='l3-map-of-the-product' tabindex='-1'>Then, a map of the product</h2>",
      "<p class='para'>Once agents could run the app, they still did not know it. A report about a laggy sidebar or a broken PR tab left them searching code and clicking <span class='nobr'>aimlessly<button class='cite' type='button' data-lesson-source='l3-feature-map:2' aria-label='Note 3, said at 10:23'>3</button>.</span> Her fix was a feature map that ships with the skill. Each entry describes a feature from the user’s side: where it is, how to reach it, its keyboard shortcuts, and the DOM attributes that select it through the <span class='nobr'>protocol<button class='cite' type='button' data-lesson-source='l3-feature-map:4' aria-label='Note 4, said at 12:49'>4</button>.</span> The README on screen calls the map the maintained verification source for the <span class='nobr'>app<button class='cite' type='button' data-lesson-source='l3-feature-map:3' aria-label='Note 5, shown at 10:20'>5</button>.</span></p>",
      "</div>",
      "<div class='block' data-section='triage'>",
      "<div class='side notes' role='group' aria-label='Notes from the talk'>",
      "<p class='notes__label'>From the talk</p>",
      "<ol>",
      "<li class='note'><span class='note__num'>6</span><p class='note__text'>pstack includes a skill to create a verification setup and an initial feature map by exploring code.</p><button class='note__open' type='button' data-lesson-source='l3-feature-map:5' data-num='6' aria-label='Open note 6 in the recording, said at 11:32'>11:32 · said</button></li>",
      "<li class='note'><span class='note__num'>7</span><p class='note__text'>A companion skill maintains the verification setup over time.</p><button class='note__open' type='button' data-lesson-source='l3-feature-map:6' data-num='7' aria-label='Open note 7 in the recording, said at 13:24'>13:24 · said</button></li>",
      "</ol>",
      "</div>",
      "<h2 class='h3 para-head' id='l3-triage' tabindex='-1'>Triage for vague reports</h2>",
      "<p class='para'>The map pays off on poor input. Internal feedback often arrives as a screenshot and a few question marks; with the map, an agent can locate the feature anyway. She says pstack includes a skill that creates such a verification setup, with an initial map built by exploring the <span class='nobr'>code<button class='cite' type='button' data-lesson-source='l3-feature-map:5' aria-label='Note 6, said at 11:32'>6</button>,</span> and a companion skill that keeps it <span class='nobr'>current<button class='cite' type='button' data-lesson-source='l3-feature-map:6' aria-label='Note 7, said at 13:24'>7</button>.</span></p>",
      "</div>",
      "<div class='block' data-section='runbook-index'>",
      "<h2 class='h3 para-head' id='l3-runbook-index' tabindex='-1'>A runbook index for a UI</h2>",
      "<p class='para'>In operations terms this is a service catalog, or a runbook index, for a UI. On-call engineers with a good catalog quickly resolve a report that the dashboard is slow; without one, they search. And like a catalog, a stale map misleads, which is why maintenance is a separate, named skill.</p>",
      "</div>",
      "<div class='block'>",
      "<div class='side side--quiet' role='note'><p>Our example, written against this guide. The redesign removed the Ledger tab, so its entry no longer resolves.</p></div>",
      "<figure class='figure specimen' aria-labelledby='l3-fig-title'>",
      "<p class='figure__title' id='l3-fig-title'>Two map entries, one check</p>",
      "<div class='specimen__entry'>",
      "<p class='specimen__name'>Search</p>",
      "<dl class='specimen__fields'>",
      "<dt>Where</dt><dd>The header, beside Settings</dd>",
      "<dt>How to reach</dt><dd>Select Search on any page</dd>",
      "<dt>Shortcut</dt><dd><kbd>/</kbd> outside a text field</dd>",
      "<dt>Selector</dt><dd><code>#search-input</code></dd>",
      "</dl>",
      "<p class='specimen__check'>Check · resolves after Search opens</p>",
      "</div>",
      "<div class='specimen__entry'>",
      "<p class='specimen__name'>Evidence ledger</p>",
      "<dl class='specimen__fields'>",
      "<dt>Where</dt><dd>The sixth tab in the header</dd>",
      "<dt>How to reach</dt><dd>Select Ledger on any page</dd>",
      "<dt>Shortcut</dt><dd>None</dd>",
      "<dt>Selector</dt><dd><code>a[href='#ledger']</code></dd>",
      "</dl>",
      "<p class='specimen__check specimen__check--stale'>Check · no match in the header · stale</p>",
      "</div>",
      "</figure>",
      "</div>",
      "<section class='block section-block' data-section='breaks' aria-labelledby='l3-breaks'>",
      "<h2 class='h2' id='l3-breaks' tabindex='-1'>Where the analogy breaks</h2>",
      "<ul class='dash-list'>",
      "<li>A service catalog is read by people who ask when unsure; agents act on stale entries without hesitation.</li>",
      "<li>UI paths change with every redesign far more often than service endpoints do. This guide’s own redesign is the example above.</li>",
      "</ul>",
      "</section>",
      "<section class='block section-block' data-section='further' aria-labelledby='l3-further'>",
      "<h2 class='h2' id='l3-further' tabindex='-1'>Going further</h2>",
      "<p class='para'>Make the map checkable. Every entry should name a selector or path that a script can resolve, so CI can flag entries that no longer exist. A map you cannot test drifts silently, which is the same failure as an undocumented runbook.</p>",
      "<p class='para'>The map is also a context-budget tool. Pointing the agent at the right files and UI path replaces open-ended searching, which spends tokens and invites wrong guesses.</p>",
      "<p class='para'>And the map is what makes verification possible for interface bugs. An agent that cannot reach the sidebar cannot reproduce its lag, so the best it can offer is a plausible fix: the gap that the gate closes in <a href='#practice/s2-plausible-vs-verified'>Done, or verified?</a></p>",
      "<details class='limits' data-depth-open='deep'>",
      "<summary>Limits of the evidence · 1</summary>",
      "<ul class='limits__list'>",
      "<li><a href='https://raw.githubusercontent.com/cursor/plugins/978ca6e9c0e012047cd5058b8e829240336e704e/pstack/README.md' rel='noreferrer'>pstack README at a pinned commit ↗</a>, retrieved 11 October 2026. It lists a skill that generates a project-local verify skill with a feature map, and a second that corrects a drifted map, which matches her description. It is a dated capture, so names may differ from what she used.</li>",
      "</ul>",
      "</details>",
      "</section>",
      "<section class='block section-block' data-section='check' aria-labelledby='l3-check'>",
      "<h2 class='h2' id='l3-check' tabindex='-1'>Check yourself</h2>",
      "<form class='quiz' data-lesson-quiz='l3-feature-map:0' novalidate>",
      "<fieldset class='choices'>",
      "<legend>After agents could launch the app, what problem remained?</legend>",
      "<label class='choice'><input type='radio' name='q-l3-feature-map-0' value='0' /><span>Slow builds<span class='choice__verdict'></span></span></label>",
      "<label class='choice'><input type='radio' name='q-l3-feature-map-0' value='1' /><span>They did not know where features were or how to reach them<span class='choice__verdict'></span></span></label>",
      "<label class='choice'><input type='radio' name='q-l3-feature-map-0' value='2' /><span>Missing credentials<span class='choice__verdict'></span></span></label>",
      "<label class='choice'><input type='radio' name='q-l3-feature-map-0' value='3' /><span>Merge conflicts<span class='choice__verdict'></span></span></label>",
      "</fieldset>",
      "<div class='quiz__actions'><button class='btn' type='submit'>Check</button></div>",
      "<div class='quiz__feedback' role='status'></div>",
      "</form>",
      "<form class='quiz' data-lesson-quiz='l3-feature-map:1' novalidate>",
      "<fieldset class='choices'>",
      "<legend>What is the best way to keep a feature map trustworthy?</legend>",
      "<label class='choice'><input type='radio' name='q-l3-feature-map-1' value='0' /><span>Rewrite it yearly<span class='choice__verdict'></span></span></label>",
      "<label class='choice'><input type='radio' name='q-l3-feature-map-1' value='1' /><span>Make each entry machine-checkable so stale entries fail a check<span class='choice__verdict'></span></span></label>",
      "<label class='choice'><input type='radio' name='q-l3-feature-map-1' value='2' /><span>Keep it private<span class='choice__verdict'></span></span></label>",
      "<label class='choice'><input type='radio' name='q-l3-feature-map-1' value='3' /><span>Let any agent edit it freely<span class='choice__verdict'></span></span></label>",
      "</fieldset>",
      "<div class='quiz__actions'><button class='btn' type='submit'>Check</button></div>",
      "<div class='quiz__feedback' role='status'></div>",
      "</form>",
      "</section>",
      "<section class='block section-block' data-section='rehearse' aria-labelledby='l3-rehearse'>",
      "<h2 class='h2' id='l3-rehearse' tabindex='-1'>Rehearse it</h2>",
      "<div class='rehearse__line'><pre><code>FEATURE MAP: check listed paths exist; billing.sh is the known stale entry</code></pre></div>",
      "<p class='para'><strong>Lab step 4 · A checkable feature map · 6 min.</strong> The script writes a three-entry map from feature names to files, then checks every path. One entry is deliberately stale, and the check must find exactly that one. It is this lesson’s rule at its smallest: an entry a script cannot resolve is a bug.</p>",
      "<a class='btn' href='#lab/lab-3-feature-map'>Open lab step 4</a>",
      "</section>",
      "<div class='lesson-end'>",
      "<div class='lesson-end__finish'><button class='btn finish' type='button' aria-pressed='false' data-finish='l3-feature-map'><span class='finish__mark' aria-hidden='true'></span><span data-finish-label>Mark lesson as finished</span></button><p class='lesson-end__progress meta' data-progress-count hidden></p></div>",
      "<nav class='lesson-end__nav' aria-label='Lesson navigation'>",
      "<a class='next' href='#lesson/l4-pstack-evals'><span class='next__label'>Next · Lesson 4 · 8 min</span><span class='next__title'>Skills grow from failures; evals keep them honest<span class='next__arrow' aria-hidden='true'>→</span></span></a>",
      "<a class='prev' href='#lesson/l2-verification'>Previous: Verification closes the loop</a>",
      "</nav>",
      "</div>"
    ],
    "notes": [
      {
        "n": 1,
        "source": "l3-feature-map:0",
        "kind": "said",
        "time": "9:16",
        "range": "9:16–10:01",
        "panelKind": "Our paraphrase · said at 9:16",
        "paraphrase": "The control skill lets agents run and inspect the app via debugging protocols, and similar tools exist for iOS.",
        "evidence": {
          "start": 556.9,
          "end": 601.9,
          "label": "SAID"
        }
      },
      {
        "n": 2,
        "source": "l3-feature-map:1",
        "kind": "shown",
        "time": "7:20",
        "range": "7:20–10:06",
        "panelKind": "Shown on screen at 7:20 · not narrated",
        "paraphrase": "The control skill’s documentation describes driving a running dev build over CDP, with separate worktree-isolated instances.",
        "evidence": {
          "start": 440.0,
          "end": 606.7,
          "label": "SHOWN",
          "frameId": "lauren_00h07m20.000s_periodic"
        }
      },
      {
        "n": 3,
        "source": "l3-feature-map:2",
        "kind": "said",
        "time": "10:23",
        "range": "10:23–11:17",
        "panelKind": "Our paraphrase · said at 10:23",
        "paraphrase": "Able to run the app but ignorant of it, agents flailed on feature-specific reports.",
        "evidence": {
          "start": 623.4,
          "end": 677.7,
          "label": "SAID"
        }
      },
      {
        "n": 4,
        "source": "l3-feature-map:4",
        "kind": "said",
        "time": "12:49",
        "range": "12:49–13:24",
        "panelKind": "Our paraphrase · said at 12:49",
        "paraphrase": "Map entries cover location, navigation, shortcuts and selector attributes from the user’s view.",
        "evidence": {
          "start": 769.8,
          "end": 804.4,
          "label": "SAID"
        }
      },
      {
        "n": 5,
        "source": "l3-feature-map:3",
        "kind": "shown",
        "time": "10:20",
        "range": "10:20–12:51",
        "panelKind": "Shown on screen at 10:20 · not narrated",
        "paraphrase": "The feature-map README describes one file per feature from the user’s side, plus preferred selector attributes for automation.",
        "evidence": {
          "start": 620.0,
          "end": 771.6,
          "label": "SHOWN",
          "frameId": "lauren_00h10m20.000s_periodic"
        }
      },
      {
        "n": 6,
        "source": "l3-feature-map:5",
        "kind": "said",
        "time": "11:32",
        "range": "11:32–12:04",
        "panelKind": "Our paraphrase · said at 11:32",
        "paraphrase": "pstack includes a skill to create a verification setup and an initial feature map by exploring code.",
        "evidence": {
          "start": 692.9,
          "end": 724.9,
          "label": "SAID"
        }
      },
      {
        "n": 7,
        "source": "l3-feature-map:6",
        "kind": "said",
        "time": "13:24",
        "range": "13:24–13:33",
        "panelKind": "Our paraphrase · said at 13:24",
        "paraphrase": "A companion skill maintains the verification setup over time.",
        "evidence": {
          "start": 804.4,
          "end": 813.5,
          "label": "SAID"
        }
      }
    ],
    "checks": [
      {
        "index": 0,
        "question": "After agents could launch the app, what problem remained?",
        "options": [
          "Slow builds",
          "They did not know where features were or how to reach them",
          "Missing credentials",
          "Merge conflicts"
        ],
        "answer": 1,
        "explanationHtml": "Once they could run the app, agents still did not know where a laggy sidebar or a broken PR tab lived, so they searched code and clicked around. She describes it at <button class='time-link' type='button' data-lesson-source='l3-feature-map:2' aria-label='Note 3, said at 10:23'>10:23</button>.",
        "status": "question, options and answer verbatim; explanation rewritten without the numeric range"
      },
      {
        "index": 1,
        "question": "What is the best way to keep a feature map trustworthy?",
        "options": [
          "Rewrite it yearly",
          "Make each entry machine-checkable so stale entries fail a check",
          "Keep it private",
          "Let any agent edit it freely"
        ],
        "answer": 1,
        "explanationHtml": "This is our recommendation rather than something she says: give every entry a path or selector that a script can resolve, so a check flags entries that no longer exist. She does make maintenance a skill of its own.",
        "status": "question, options and answer verbatim; explanation rewritten, still labelled as interpretation"
      }
    ],
    "practice": [],
    "lab": {
      "step": "lab-3-feature-map",
      "n": 4,
      "title": "A checkable feature map",
      "minutes": 6,
      "outputLine": "FEATURE MAP: check listed paths exist; billing.sh is the known stale entry"
    },
    "supplements": {
      "basics": "Both original basics paragraphs retained; the second loses its numeric range (963.8–972.4).",
      "deep": "Both original deep paragraphs retained verbatim in Going further, plus one authored paragraph that carries the deliberate s2 cross-reference. Limits of the evidence holds the dated pstack README entry.",
      "practitioner": "All four original paragraphs retained in substance under four specific heads. Numeric ranges removed; each claim cited to its evidence entry. The screenshot-with-question-marks example (724.9–771.2) has no evidence entry and stays uncited."
    },
    "end": {
      "next": {
        "href": "#lesson/l4-pstack-evals",
        "label": "Next · Lesson 4 · 8 min",
        "title": "Skills grow from failures; evals keep them honest"
      },
      "previous": {
        "href": "#lesson/l2-verification",
        "text": "Previous: Verification closes the loop"
      }
    }
  },
  "l4-pstack-evals": {
    "schemaVersion": 1,
    "id": "l4-pstack-evals",
    "n": 4,
    "title": "Skills grow from failures; evals keep them honest",
    "deck": "Where do good agent skills come from, and how do I know a skill still works after I change it?",
    "summary": "pstack started as individual skills, each written after watching a specific agent failure. Changes are tested with evals, which are unit tests for agent behaviour, run across models and judged independently.",
    "minutes": 8,
    "here": [
      "agent"
    ],
    "strip": {
      "sentenceHtml": "Where this fits: <strong>Agent</strong>, in the skills it works from."
    },
    "decision": "Write a skill only from a failure you have watched, and rerun its evals, across models and judged by another model, every time the skill or the model changes.",
    "sections": [
      {
        "slug": "in-short",
        "heading": null,
        "target": "h1"
      },
      {
        "slug": "a-plugin-that-grew",
        "heading": "A plugin that grew",
        "id": "l4-a-plugin-that-grew"
      },
      {
        "slug": "failure-becomes-skill",
        "heading": "Each failure becomes a skill",
        "id": "l4-failure-becomes-skill"
      },
      {
        "slug": "evals",
        "heading": "Evals: unit tests for agents",
        "id": "l4-evals"
      },
      {
        "slug": "skills-are-configuration",
        "heading": "Skills are configuration",
        "id": "l4-skills-are-configuration"
      },
      {
        "slug": "breaks",
        "heading": "Where the analogy breaks",
        "id": "l4-breaks"
      },
      {
        "slug": "further",
        "heading": "Going further",
        "id": "l4-further"
      },
      {
        "slug": "check",
        "heading": "Check yourself",
        "id": "l4-check"
      },
      {
        "slug": "rehearse",
        "heading": "Rehearse it",
        "id": "l4-rehearse"
      }
    ],
    "bodyHtml": [
      "<div class='block in-short' data-section='in-short'>",
      "<div class='side side--quiet side--intro' role='note'><p>Numbered notes paraphrase the recording. Select a time to watch and read that moment.</p></div>",
      "<span class='label'>In short</span>",
      "<p class='lead'>pstack started as individual skills, each written after watching a specific agent failure. Changes are tested with evals, which are unit tests for agent behaviour, run across models and judged independently.</p>",
      "<details class='terms-inline' data-depth-open='basics'>",
      "<summary>Terms in this lesson · 2</summary>",
      "<p>A plugin here is a package of skills and settings you install into an agent tool.</p>",
      "<p>A rubric is a written list of what a good result must include, used to score attempts consistently.</p>",
      "</details>",
      "</div>",
      "<div class='block' data-section='a-plugin-that-grew'>",
      "<div class='side notes' role='group' aria-label='Notes from the talk'>",
      "<p class='notes__label'>From the talk</p>",
      "<ol>",
      "<li class='note'><span class='note__num'>1</span><p class='note__text'>pstack is her plugin encoding her practices; it grew without a plan.</p><button class='note__open' type='button' data-lesson-source='l4-pstack-evals:0' data-num='1' aria-label='Open note 1 in the recording, said at 13:44'>13:44 · said</button></li>",
      "</ol>",
      "</div>",
      "<h2 class='h3 para-head' id='l4-a-plugin-that-grew' tabindex='-1'>A plugin that grew</h2>",
      "<p class='para'>Tan’s plugin, pstack, is a bundle of skills that encodes her engineering practices. She explains the name as a joke and says she never set out to build <span class='nobr'>it<button class='cite' type='button' data-lesson-source='l4-pstack-evals:0' aria-label='Note 1, said at 13:44'>1</button>.</span> It accreted one skill at a time, starting with the control skill from <a href='#lesson/l3-feature-map'>lesson 3</a>.</p>",
      "</div>",
      "<div class='block' data-section='failure-becomes-skill'>",
      "<div class='side notes' role='group' aria-label='Notes from the talk'>",
      "<p class='notes__label'>From the talk</p>",
      "<ol>",
      "<li class='note'><span class='note__num'>2</span><p class='note__text'>Reading tool calls revealed agents asserting causes without reading the relevant code.</p><button class='note__open' type='button' data-lesson-source='l4-pstack-evals:1' data-num='2' aria-label='Open note 2 in the recording, said at 15:06'>15:06 · said</button></li>",
      "<li class='note'><span class='note__num'>3</span><p class='note__text'>Each observed failure mode became a new skill.</p><button class='note__open' type='button' data-lesson-source='l4-pstack-evals:2' data-num='3' aria-label='Open note 3 in the recording, said at 16:51'>16:51 · said</button></li>",
      "</ol>",
      "</div>",
      "<h2 class='h3 para-head' id='l4-failure-becomes-skill' tabindex='-1'>Each failure becomes a skill</h2>",
      "<p class='para'>Her method is observation. Early on she read the agent’s tool calls and saw it assert a cause without ever opening the code she expected it to <span class='nobr'>inspect<button class='cite' type='button' data-lesson-source='l4-pstack-evals:1' aria-label='Note 2, said at 15:06'>2</button>.</span> Each failure mode like that became a skill: go and read the code, stop <span class='nobr'>guessing<button class='cite' type='button' data-lesson-source='l4-pstack-evals:2' aria-label='Note 3, said at 16:51'>3</button>.</span> She frames a skill as onboarding a strong coder who has no business context, and as markdown that steers the model with better starting context.</p>",
      "</div>",
      "<div class='block' data-section='evals'>",
      "<div class='side notes' role='group' aria-label='Notes from the talk'>",
      "<p class='notes__label'>From the talk</p>",
      "<ol>",
      "<li class='note'><span class='note__num'>4</span><p class='note__text'>Evals are like unit tests for agents and need no special framework.</p><button class='note__open' type='button' data-lesson-source='l4-pstack-evals:3' data-num='4' aria-label='Open note 4 in the recording, said at 18:04'>18:04 · said</button></li>",
      "<li class='note'><span class='note__num'>5</span><p class='note__text'>A coordinator writes a rubric and spawns disguised sub-agents; evals run across models.</p><button class='note__open' type='button' data-lesson-source='l4-pstack-evals:4' data-num='5' aria-label='Open note 5 in the recording, said from 19:11 to 20:16'>19:11–20:16 · said</button></li>",
      "<li class='note'><span class='note__num'>6</span><p class='note__text'>A judge from another model cross-checks scores, and a loop iterates toward the target.</p><button class='note__open' type='button' data-lesson-source='l4-pstack-evals:5' data-num='6' aria-label='Open note 6 in the recording, said at 22:00'>22:00 · said</button></li>",
      "<li class='note'><span class='note__num'>7</span><p class='note__text'>Maintaining skills is hard and demands active, critical observation of agent behaviour.</p><button class='note__open' type='button' data-lesson-source='l4-pstack-evals:6' data-num='7' aria-label='Open note 7 in the recording, said at 20:29'>20:29 · said</button></li>",
      "</ol>",
      "</div>",
      "<h2 class='h3 para-head' id='l4-evals' tabindex='-1'>Evals: unit tests for agents</h2>",
      "<p class='para'>To maintain skills she uses evals, which she describes as unit tests for agents that need no special <span class='nobr'>framework<button class='cite' type='button' data-lesson-source='l4-pstack-evals:3' aria-label='Note 4, said at 18:04'>4</button>;</span> pstack includes an eval playbook. Her process runs like this:</p>",
      "<ul class='dash-list'>",
      "<li>A coordinator agent writes a rubric and spawns sub-agents in directories named so they cannot tell they are being tested. Agents act differently, she says, when they suspect a test.</li>",
      "<li>She runs the same eval across several <span class='nobr'>models<button class='cite' type='button' data-lesson-source='l4-pstack-evals:4' aria-label='Note 5, said from 19:11 to 20:16'>5</button>.</span></li>",
      "<li>A judge agent from a different model cross-checks the scoring, and a loop repeats until the rubric is <span class='nobr'>met<button class='cite' type='button' data-lesson-source='l4-pstack-evals:5' aria-label='Note 6, said at 22:00'>6</button>.</span></li>",
      "</ul>",
      "<p class='para'>She reruns evals whenever she modifies a skill, and calls maintenance hard: it takes close, critical observation, like an active pairing <span class='nobr'>partner<button class='cite' type='button' data-lesson-source='l4-pstack-evals:6' aria-label='Note 7, said at 20:29'>7</button>.</span></p>",
      "</div>",
      "<div class='block'>",
      "<div class='side side--quiet' role='note'><p>Our table of the separations in her process. The roles are hers; the reasons on each row’s second line are partly ours.</p></div>",
      "<figure class='figure' aria-labelledby='l4-fig-title'>",
      "<p class='figure__title' id='l4-fig-title'>Who does what in an eval</p>",
      "<dl class='roles'>",
      "<div class='roles__row'><dt>Coordinator</dt><dd>Writes the rubric and starts the runs.</dd><dd class='roles__why'>The rubric is fixed before anything is scored.</dd></div>",
      "<div class='roles__row'><dt>Sub-agents</dt><dd>Do the task in directories named so they cannot tell it is a test.</dd><dd class='roles__why'>Agents act differently when they suspect a test.</dd></div>",
      "<div class='roles__row'><dt>Several models</dt><dd>Run the same eval.</dd><dd class='roles__why'>A skill that works on one model can fail on another.</dd></div>",
      "<div class='roles__row'><dt>Judge</dt><dd>An agent from a different model cross-checks the scores.</dd><dd class='roles__why'>The model under test does not grade itself.</dd></div>",
      "<div class='roles__row'><dt>You</dt><dd>Read the tool calls and decide the next change to the skill.</dd><dd class='roles__why'>A loop left alone can climb the rubric instead of the job.</dd></div>",
      "</dl>",
      "</figure>",
      "</div>",
      "<div class='block' data-section='skills-are-configuration'>",
      "<h2 class='h3 para-head' id='l4-skills-are-configuration' tabindex='-1'>Skills are configuration</h2>",
      "<p class='para'>In operations terms a skill is configuration that changes system behaviour, so changes need tests, canaries and review like any config. Evals are your regression suite. Running across models is a compatibility matrix. A judge from another model is separation of duties: the component under test does not grade itself.</p>",
      "</div>",
      "<section class='block section-block' data-section='breaks' aria-labelledby='l4-breaks'>",
      "<h2 class='h2' id='l4-breaks' tabindex='-1'>Where the analogy breaks</h2>",
      "<ul class='dash-list'>",
      "<li>Unit tests are deterministic; eval runs are sampled, so a single pass proves little and you need repetitions.</li>",
      "<li>A config change has bounded effects; a skill wording change can alter behaviour on tasks it never mentions.</li>",
      "</ul>",
      "</section>",
      "<section class='block section-block' data-section='further' aria-labelledby='l4-further'>",
      "<h2 class='h2' id='l4-further' tabindex='-1'>Going further</h2>",
      "<p class='para'>Looping on a score invites overfitting: the skill learns the rubric, not the job. Keep a held-out set of tasks the loop never sees, and track at least one outcome that cannot be argued with, such as tests passing in a clean checkout.</p>",
      "<p class='para'>Disguising eval directories addresses evaluation awareness. In your own setup, also isolate side effects: eval runs belong in disposable worktrees or containers with no credentials, so a test agent cannot touch anything real.</p>",
      "<p class='para'>Pin what you evaluated: model identifier, skill commit, tool versions. An eval result without that context, like a load test without the build ID, cannot be reproduced.</p>",
      "<details class='limits' data-depth-open='deep'>",
      "<summary>Limits of the evidence · 2</summary>",
      "<ul class='limits__list'>",
      "<li>Three sources name pstack’s main mode differently: her speech, a skill title on screen and the README. The name is unresolved, so this lesson does not use it.</li>",
      "<li><a href='https://raw.githubusercontent.com/cursor/plugins/978ca6e9c0e012047cd5058b8e829240336e704e/pstack/README.md' rel='noreferrer'>pstack README at a pinned commit ↗</a>, retrieved 11 October 2026. It lists an eval playbook for testing how a skill change affects agent behaviour, run blinded, which matches her disguised-directory evals. It also invites forking, as she does. Treat its names as dated.</li>",
      "</ul>",
      "</details>",
      "</section>",
      "<section class='block section-block' data-section='check' aria-labelledby='l4-check'>",
      "<h2 class='h2' id='l4-check' tabindex='-1'>Check yourself</h2>",
      "<form class='quiz' data-lesson-quiz='l4-pstack-evals:0' novalidate>",
      "<fieldset class='choices'>",
      "<legend>Why use a judge from a different model?</legend>",
      "<label class='choice'><input type='radio' name='q-l4-pstack-evals-0' value='0' /><span>It is cheaper<span class='choice__verdict'></span></span></label>",
      "<label class='choice'><input type='radio' name='q-l4-pstack-evals-0' value='1' /><span>To reduce one model grading itself favourably<span class='choice__verdict'></span></span></label>",
      "<label class='choice'><input type='radio' name='q-l4-pstack-evals-0' value='2' /><span>Required by Git<span class='choice__verdict'></span></span></label>",
      "<label class='choice'><input type='radio' name='q-l4-pstack-evals-0' value='3' /><span>To speed up the loop<span class='choice__verdict'></span></span></label>",
      "</fieldset>",
      "<div class='quiz__actions'><button class='btn' type='submit'>Check</button></div>",
      "<div class='quiz__feedback' role='status'></div>",
      "</form>",
      "<form class='quiz' data-lesson-quiz='l4-pstack-evals:1' novalidate>",
      "<fieldset class='choices'>",
      "<legend>Which risk does looping toward a perfect score create?</legend>",
      "<label class='choice'><input type='radio' name='q-l4-pstack-evals-1' value='0' /><span>None<span class='choice__verdict'></span></span></label>",
      "<label class='choice'><input type='radio' name='q-l4-pstack-evals-1' value='1' /><span>Optimising to the rubric rather than the task<span class='choice__verdict'></span></span></label>",
      "<label class='choice'><input type='radio' name='q-l4-pstack-evals-1' value='2' /><span>Merge conflicts<span class='choice__verdict'></span></span></label>",
      "<label class='choice'><input type='radio' name='q-l4-pstack-evals-1' value='3' /><span>Lost credentials<span class='choice__verdict'></span></span></label>",
      "</fieldset>",
      "<div class='quiz__actions'><button class='btn' type='submit'>Check</button></div>",
      "<div class='quiz__feedback' role='status'></div>",
      "</form>",
      "</section>",
      "<section class='block section-block' data-section='rehearse' aria-labelledby='l4-rehearse'>",
      "<h2 class='h2' id='l4-rehearse' tabindex='-1'>Rehearse it</h2>",
      "<div class='rehearse__line'><pre><code>VERIFICATION: sh check.sh proves PASS on baseline and FAIL on a known-bad branch</code></pre></div>",
      "<p class='para'><strong>Lab step 3 · A check that runs the real thing · 8 min.</strong> An eval is evidence only if it can fail. This step requires the check to fail on a known-bad branch before its pass on main counts: the proof you want from an eval after every skill change. The same probe stands behind the gate in <a href='#practice/s2-plausible-vs-verified'>Done, or verified?</a></p>",
      "<a class='btn' href='#lab/lab-2-verify'>Open lab step 3</a>",
      "</section>",
      "<div class='lesson-end'>",
      "<div class='lesson-end__finish'><button class='btn finish' type='button' aria-pressed='false' data-finish='l4-pstack-evals'><span class='finish__mark' aria-hidden='true'></span><span data-finish-label>Mark lesson as finished</span></button><p class='lesson-end__progress meta' data-progress-count hidden></p></div>",
      "<nav class='lesson-end__nav' aria-label='Lesson navigation'>",
      "<a class='next' href='#lesson/l5-agent-friendly-architecture'><span class='next__label'>Next · Lesson 5 · 9 min</span><span class='next__title'>Make the shortest path the right path<span class='next__arrow' aria-hidden='true'>→</span></span></a>",
      "<a class='prev' href='#lesson/l3-feature-map'>Previous: Agents need a map of the product</a>",
      "</nav>",
      "</div>"
    ],
    "notes": [
      {
        "n": 1,
        "source": "l4-pstack-evals:0",
        "kind": "said",
        "time": "13:44",
        "range": "13:44–14:35",
        "panelKind": "Our paraphrase · said at 13:44",
        "paraphrase": "pstack is her plugin encoding her practices; it grew without a plan.",
        "evidence": {
          "start": 824.6,
          "end": 875.0,
          "label": "SAID"
        }
      },
      {
        "n": 2,
        "source": "l4-pstack-evals:1",
        "kind": "said",
        "time": "15:06",
        "range": "15:06–15:30",
        "panelKind": "Our paraphrase · said at 15:06",
        "paraphrase": "Reading tool calls revealed agents asserting causes without reading the relevant code.",
        "evidence": {
          "start": 906.2,
          "end": 930.1,
          "label": "SAID"
        }
      },
      {
        "n": 3,
        "source": "l4-pstack-evals:2",
        "kind": "said",
        "time": "16:51",
        "range": "16:51–17:15",
        "panelKind": "Our paraphrase · said at 16:51",
        "paraphrase": "Each observed failure mode became a new skill.",
        "evidence": {
          "start": 1011.0,
          "end": 1035.2,
          "label": "SAID"
        }
      },
      {
        "n": 4,
        "source": "l4-pstack-evals:3",
        "kind": "said",
        "time": "18:04",
        "range": "18:04–18:18",
        "panelKind": "Our paraphrase · said at 18:04",
        "paraphrase": "Evals are like unit tests for agents and need no special framework.",
        "evidence": {
          "start": 1084.5,
          "end": 1098.4,
          "label": "SAID"
        }
      },
      {
        "n": 5,
        "source": "l4-pstack-evals:4",
        "kind": "said-long",
        "time": "19:11–20:16",
        "range": "19:11–20:16",
        "panelKind": "A longer stretch · said from 19:11 to 20:16",
        "paraphrase": "A coordinator writes a rubric and spawns disguised sub-agents; evals run across models.",
        "evidence": {
          "start": 1151.7,
          "end": 1216.2,
          "label": "SAID"
        }
      },
      {
        "n": 6,
        "source": "l4-pstack-evals:5",
        "kind": "said",
        "time": "22:00",
        "range": "22:00–22:33",
        "panelKind": "Our paraphrase · said at 22:00",
        "paraphrase": "A judge from another model cross-checks scores, and a loop iterates toward the target.",
        "evidence": {
          "start": 1320.0,
          "end": 1353.7,
          "label": "SAID"
        }
      },
      {
        "n": 7,
        "source": "l4-pstack-evals:6",
        "kind": "said",
        "time": "20:29",
        "range": "20:29–21:27",
        "panelKind": "Our paraphrase · said at 20:29",
        "paraphrase": "Maintaining skills is hard and demands active, critical observation of agent behaviour.",
        "evidence": {
          "start": 1229.6,
          "end": 1287.2,
          "label": "SAID"
        }
      }
    ],
    "checks": [
      {
        "index": 0,
        "question": "Why use a judge from a different model?",
        "options": [
          "It is cheaper",
          "To reduce one model grading itself favourably",
          "Required by Git",
          "To speed up the loop"
        ],
        "answer": 1,
        "explanationHtml": "She has a judge from a different model cross-check the scores, so the model under test does not grade its own work; in operations terms, separation of duties. She explains it at <button class='time-link' type='button' data-lesson-source='l4-pstack-evals:5' aria-label='Note 6, said at 22:00'>22:00</button>.",
        "status": "question, options and answer verbatim; explanation rewritten without the numeric range"
      },
      {
        "index": 1,
        "question": "Which risk does looping toward a perfect score create?",
        "options": [
          "None",
          "Optimising to the rubric rather than the task",
          "Merge conflicts",
          "Lost credentials"
        ],
        "answer": 1,
        "explanationHtml": "Our reading, not hers: a loop that climbs a score can learn the rubric instead of the job. Keep held-out tasks the loop never sees, and one outcome that cannot be argued with, such as tests passing in a clean checkout.",
        "status": "question, options and answer verbatim; explanation expanded, still labelled as interpretation"
      }
    ],
    "practice": [],
    "lab": {
      "step": "lab-2-verify",
      "n": 3,
      "title": "A check that runs the real thing",
      "minutes": 8,
      "outputLine": "VERIFICATION: sh check.sh proves PASS on baseline and FAIL on a known-bad branch"
    },
    "supplements": {
      "basics": "Both original basics paragraphs retained verbatim.",
      "deep": "All three original deep paragraphs retained verbatim in Going further. Limits of the evidence holds the unresolved mode name and the dated pstack README entry.",
      "practitioner": "All four original paragraphs retained in substance under four specific heads; the evals process keeps its four-part list (judge and loop merged into one item because they share one evidence entry). Numeric ranges removed. The skill-as-onboarding framing (942.8–1004.6), the playbook (1137.6–1144.2) and rerunning on change (1218.1–1228.7) have no evidence entries and stay uncited. The person behind the similarly named plugin is omitted, as the cautions require."
    },
    "end": {
      "next": {
        "href": "#lesson/l5-agent-friendly-architecture",
        "label": "Next · Lesson 5 · 9 min",
        "title": "Make the shortest path the right path"
      },
      "previous": {
        "href": "#lesson/l3-feature-map",
        "text": "Previous: Agents need a map of the product"
      }
    }
  },
  "l5-agent-friendly-architecture": {
    "schemaVersion": 1,
    "id": "l5-agent-friendly-architecture",
    "n": 5,
    "title": "Make the shortest path the right path",
    "deck": "How can a codebase stop agents from producing plausible but harmful changes before any human reads them?",
    "summary": "Agents copy patterns and take shortcuts. Dune, the architecture behind Grok Bot, turns lessons into hard CI failures and conventional structure, leaving soft rules as backup only.",
    "minutes": 9,
    "here": [
      "checks"
    ],
    "strip": {
      "sentenceHtml": "Where this fits: <strong>Checks</strong>, before any person reads the change."
    },
    "decision": "Turn each recurring agent mistake into structure or a check that fails the build; keep written rules, skills and review bots as backup only.",
    "sections": [
      {
        "slug": "in-short",
        "heading": null,
        "target": "h1"
      },
      {
        "slug": "where-agents-do-damage",
        "heading": "Where agents do damage",
        "id": "l5-where-agents-do-damage"
      },
      {
        "slug": "dune",
        "heading": "Dune: lessons as CI failures",
        "id": "l5-dune"
      },
      {
        "slug": "layers",
        "heading": "Layers of enforcement",
        "id": "l5-layers"
      },
      {
        "slug": "admission-control",
        "heading": "Admission control for code",
        "id": "l5-admission-control"
      },
      {
        "slug": "breaks",
        "heading": "Where the analogy breaks",
        "id": "l5-breaks"
      },
      {
        "slug": "try",
        "heading": "Try it",
        "id": "l5-try"
      },
      {
        "slug": "further",
        "heading": "Going further",
        "id": "l5-further"
      },
      {
        "slug": "check",
        "heading": "Check yourself",
        "id": "l5-check"
      },
      {
        "slug": "rehearse",
        "heading": "Rehearse it",
        "id": "l5-rehearse"
      }
    ],
    "bodyHtml": [
      "<div class='block in-short' data-section='in-short'>",
      "<div class='side side--quiet side--intro' role='note'><p>Numbered notes paraphrase the recording. Select a time to watch and read that moment.</p></div>",
      "<span class='label'>In short</span>",
      "<p class='lead'>Agents copy patterns and take shortcuts. Dune, the architecture behind Grok Bot, turns lessons into hard CI failures and conventional structure, leaving soft rules as backup only.</p>",
      "<details class='terms-inline' data-depth-open='basics'>",
      "<summary>Terms in this lesson · 3</summary>",
      "<p>CI is the automated pipeline that runs checks on every proposed change and can block it.</p>",
      "<p>Lint rules are automated style and safety checks that flag known-bad patterns.</p>",
      "<p>An Electron app has a main process and a renderer process that draws the UI; heavy work in the renderer makes the UI stutter.</p>",
      "</details>",
      "</div>",
      "<div class='block' data-section='where-agents-do-damage'>",
      "<div class='side notes' role='group' aria-label='Notes from the talk'>",
      "<p class='notes__label'>From the talk</p>",
      "<ol>",
      "<li class='note'><span class='note__num'>1</span><p class='note__text'>Big-company guardrails and restricted credentials already let agents work with limited damage.</p><button class='note__open' type='button' data-lesson-source='l5-agent-friendly-architecture:0' data-num='1' aria-label='Open note 1 in the recording, said from 31:19 to 32:50'>31:19–32:50 · said</button></li>",
      "<li class='note'><span class='note__num'>2</span><p class='note__text'>Unread, quickly generated greenfield code lacks guardrails and drifts into shortcut-driven chaos.</p><button class='note__open' type='button' data-lesson-source='l5-agent-friendly-architecture:1' data-num='2' aria-label='Open note 2 in the recording, said from 32:51 to 34:31'>32:51–34:31 · said</button></li>",
      "<li class='note'><span class='note__num'>3</span><p class='note__text'>A refactor of over 600 PRs; she says she no longer reads the code.</p><button class='note__open' type='button' data-lesson-source='l5-agent-friendly-architecture:2' data-num='3' aria-label='Open note 3 in the recording, said at 35:03'>35:03 · said</button></li>",
      "</ol>",
      "</div>",
      "<h2 class='h3 para-head' id='l5-where-agents-do-damage' tabindex='-1'>Where agents do damage</h2>",
      "<p class='para'>Tan argues that established big-company codebases already suit agents. They were built around guardrails, conventions and restricted credentials, so that the least experienced contributor cannot do much <span class='nobr'>damage<button class='cite' type='button' data-lesson-source='l5-agent-friendly-architecture:0' aria-label='Note 1, said from 31:19 to 32:50'>1</button>.</span> The risk is greenfield code written quickly by agents with nobody reading it. Without guardrails, agents solve each task by the most convenient route until the codebase <span class='nobr'>spirals<button class='cite' type='button' data-lesson-source='l5-agent-friendly-architecture:1' aria-label='Note 2, said from 32:51 to 34:31'>2</button>.</span></p>",
      "<p class='para'>She describes refactoring Grok Bot onto a new architecture in over 600 PRs, after which, she says, she no longer reads the <span class='nobr'>code<button class='cite' type='button' data-lesson-source='l5-agent-friendly-architecture:2' aria-label='Note 3, said at 35:03'>3</button>.</span></p>",
      "</div>",
      "<div class='block' data-section='dune'>",
      "<div class='side notes' role='group' aria-label='Notes from the talk'>",
      "<p class='notes__label'>From the talk</p>",
      "<ol>",
      "<li class='note'><span class='note__num'>4</span><p class='note__text'>Dune’s CI bans a risky React hook and code comments.</p><button class='note__open' type='button' data-lesson-source='l5-agent-friendly-architecture:3' data-num='4' aria-label='Open note 4 in the recording, said from 39:12 to 40:41'>39:12–40:41 · said</button></li>",
      "<li class='note'><span class='note__num'>5</span><p class='note__text'>Main and renderer code are separated, and CI checks the dependency graph to block crossing imports.</p><button class='note__open' type='button' data-lesson-source='l5-agent-friendly-architecture:4' data-num='5' aria-label='Open note 5 in the recording, said from 41:39 to 43:07'>41:39–43:07 · said</button></li>",
      "<li class='note'><span class='note__num'>6</span><p class='note__text'>The Dune page lists agent habits as design inputs and five rules, including that forbidden dependencies fail mechanically.</p><button class='note__open' type='button' data-lesson-source='l5-agent-friendly-architecture:5' data-num='6' aria-label='Open note 6, shown on screen at 45:00'>45:00 · shown</button></li>",
      "</ol>",
      "</div>",
      "<h2 class='h3 para-head' id='l5-dune' tabindex='-1'>Dune: lessons as CI failures</h2>",
      "<p class='para'>Dune is described as something like Next.js for Electron apps, designed for agents to write. It encodes lessons as CI failures. A React hook that commonly causes bugs is banned, and so are code comments, because agents fill them with stale, misattributed <span class='nobr'>history<button class='cite' type='button' data-lesson-source='l5-agent-friendly-architecture:3' aria-label='Note 4, said from 39:12 to 40:41'>4</button>.</span></p>",
      "<p class='para'>Electron main and renderer code live in separate directories, and a dependency-graph check fails any import across the boundary. The reason is concrete: work that leaks onto the renderer competes with a frame budget of about 16 ms, causing jank and long <span class='nobr'>tasks<button class='cite' type='button' data-lesson-source='l5-agent-friendly-architecture:4' aria-label='Note 5, said from 41:39 to 43:07'>5</button>.</span> She says the existing agents window lacks this isolation and regresses often. The Dune page on screen treats agent habits, such as copying the nearest pattern, as design inputs; one of its five rules is that forbidden dependencies fail <span class='nobr'>mechanically<button class='cite' type='button' data-lesson-source='l5-agent-friendly-architecture:5' aria-label='Note 6, shown at 45:00'>6</button>.</span></p>",
      "</div>",
      "<div class='block' data-section='layers'>",
      "<div class='side notes' role='group' aria-label='Notes from the talk'>",
      "<p class='notes__label'>From the talk</p>",
      "<ol>",
      "<li class='note'><span class='note__num'>7</span><p class='note__text'>A handwritten five-item list ranks codebase, static analysis, rules and Bugbot, skills, and a style guide.</p><button class='note__open' type='button' data-lesson-source='l5-agent-friendly-architecture:7' data-num='7' aria-label='Open note 7, shown on screen at 43:25'>43:25 · shown</button></li>",
      "<li class='note'><span class='note__num'>8</span><p class='note__text'>Co-located feature directories and making the shortest path the best one.</p><button class='note__open' type='button' data-lesson-source='l5-agent-friendly-architecture:6' data-num='8' aria-label='Open note 8 in the recording, said from 43:38 to 45:15'>43:38–45:15 · said</button></li>",
      "<li class='note'><span class='note__num'>9</span><p class='note__text'>Static checks make CI fail; rules, skills and the review bot are soft and get forgotten.</p><button class='note__open' type='button' data-lesson-source='l5-agent-friendly-architecture:8' data-num='9' aria-label='Open note 9 in the recording, said at 46:01'>46:01 · said</button></li>",
      "<li class='note'><span class='note__num'>10</span><p class='note__text'>Repeating a review comment signals a missing lint rule or CI check.</p><button class='note__open' type='button' data-lesson-source='l5-agent-friendly-architecture:9' data-num='10' aria-label='Open note 10 in the recording, said at 47:49'>47:49 · said</button></li>",
      "</ol>",
      "</div>",
      "<h2 class='h3 para-head' id='l5-layers' tabindex='-1'>Layers of enforcement</h2>",
      "<p class='para'>She ranks enforcement in layers and shows them as a handwritten list: codebase, static analysis, rules and Bugbot, skills, and a style <span class='nobr'>guide<button class='cite' type='button' data-lesson-source='l5-agent-friendly-architecture:7' aria-label='Note 7, shown at 43:25'>7</button>.</span> The strongest layer is conventional structure. Each feature lives in one directory, because agents copy the patterns they find, and her principle is to make the shortest path the best path, since agents take shortcuts <span class='nobr'>anyway<button class='cite' type='button' data-lesson-source='l5-agent-friendly-architecture:6' aria-label='Note 8, said from 43:38 to 45:15'>8</button>.</span></p>",
      "<p class='para'>Static analysis, lint and compiler diagnostics fail CI. Rules, skills and the AI review bot she calls Bugbot are soft, because agents forget <span class='nobr'>them<button class='cite' type='button' data-lesson-source='l5-agent-friendly-architecture:8' aria-label='Note 9, said at 46:01'>9</button>.</span> She points to strict compilers as a source of trust, and treats a repeated human review comment as a smell: turn it into a lint rule or a CI failure, or remove the possibility <span class='nobr'>entirely<button class='cite' type='button' data-lesson-source='l5-agent-friendly-architecture:9' aria-label='Note 10, said at 47:49'>10</button>.</span></p>",
      "</div>",
      "<div class='block'>",
      "<div class='side side--quiet' role='note'><p>Our layout of the handwritten list in note 7. The order and the split between hard and soft are hers; the one-line descriptions are ours.</p></div>",
      "<figure class='figure layers' aria-labelledby='l5-fig-title'>",
      "<p class='figure__title' id='l5-fig-title'>Her five layers, strongest first</p>",
      "<p class='layers__group'>Hard · the wrong path fails, or is never the shortest</p>",
      "<ol class='layers__list'>",
      "<li><span class='layers__rank' aria-hidden='true'>1</span><span class='layers__name'>Codebase</span><span class='layers__what'>A conventional structure that agents copy: one directory per feature.</span></li>",
      "<li><span class='layers__rank' aria-hidden='true'>2</span><span class='layers__name'>Static analysis</span><span class='layers__what'>Lint, compiler errors and dependency checks that fail CI.</span></li>",
      "</ol>",
      "<div class='layers__line' aria-hidden='true'></div>",
      "<p class='layers__group'>Soft · advice an agent can forget</p>",
      "<ol class='layers__list' start='3'>",
      "<li><span class='layers__rank' aria-hidden='true'>3</span><span class='layers__name'>Rules and Bugbot</span><span class='layers__what'>Written rules and an AI review bot. They advise; they do not block.</span></li>",
      "<li><span class='layers__rank' aria-hidden='true'>4</span><span class='layers__name'>Skills</span><span class='layers__what'>Instructions an agent loads, and can forget.</span></li>",
      "<li><span class='layers__rank' aria-hidden='true'>5</span><span class='layers__name'>Style guide</span><span class='layers__what'>Prose for people and agents to read.</span></li>",
      "</ol>",
      "</figure>",
      "</div>",
      "<div class='block' data-section='admission-control'>",
      "<h2 class='h3 para-head' id='l5-admission-control' tabindex='-1'>Admission control for code</h2>",
      "<p class='para'>In operations terms this is admission control for code. Policy as code rejects a pod that runs as root; a review comment asking people not to run as root would not. The main and renderer import boundary is network segmentation. Soyspray already works this way, with NetworkPolicy, non-root images and digest promotion. The lesson is to apply the same reflex to the code agents write.</p>",
      "</div>",
      "<section class='block section-block' data-section='breaks' aria-labelledby='l5-breaks'>",
      "<h2 class='h2' id='l5-breaks' tabindex='-1'>Where the analogy breaks</h2>",
      "<ul class='dash-list'>",
      "<li>Admission policies govern a small, stable schema; code-level rules must anticipate creative violations by an agent optimising to pass.</li>",
      "<li>A human intern learns the reason behind a guardrail; an agent mostly learns only that the check fails.</li>",
      "</ul>",
      "</section>",
      "<section class='block section-block' data-section='try' aria-labelledby='l5-try'>",
      "<div class='side side--quiet' role='note'><p>A deterministic teaching model with a fixed schedule. The reviewer’s miss is scripted to show the gap, not a measured miss rate. Ticks and cost units are abstract.</p></div>",
      "<h2 class='h2' id='l5-try' tabindex='-1'>Try it</h2>",
      "<p class='para'>One shortcut, two defences: a soft rule that depends on the reviewer noticing, then a CI check. Predict where the check catches it.</p>",
      "<div class='practice' data-scenario='s5-architecture-gate' data-context='lesson'></div>",
      "</section>",
      "<section class='block section-block' data-section='further' aria-labelledby='l5-further'>",
      "<h2 class='h2' id='l5-further' tabindex='-1'>Going further</h2>",
      "<p class='para'>Rank every invariant by enforcement strength: impossible by construction, then compile error, then CI failure, then review-bot warning, then written rule. Push each one as high as is affordable. Anything enforced only by written rules will eventually be violated at agent volume.</p>",
      "<p class='para'>Encoding is not free. Every hard rule needs a clear failure message telling an agent how to fix it, or agents will work around the check, for example by moving code to dodge an import rule. Review the workarounds as seriously as the rules.</p>",
      "<p class='para'>Bans like no comments are local choices with tradeoffs, made for her codebase. Copy the method of observing a recurring agent failure and making it unrepresentable, not the specific bans.</p>",
      "<details class='limits' data-depth-open='deep'>",
      "<summary>Limits of the evidence · 4</summary>",
      "<ul class='limits__list'>",
      "<li>She presents Dune as a set of ideas and principles, not a planned open-source release.</li>",
      "<li>On-screen documents, including the Dune page, call the application Sand, while speech names Grok Bot. We do not reconcile the two.</li>",
      "<li>The 600-PR refactor, and her no longer reading the code, are her own report.</li>",
      "<li><a href='https://raw.githubusercontent.com/cursor/plugins/978ca6e9c0e012047cd5058b8e829240336e704e/pstack/README.md' rel='noreferrer'>pstack README at a pinned commit ↗</a>, retrieved 11 October 2026. It describes a skill that mines repeated agent corrections and encodes each fix at the strongest workable level, architecture first and documentation last. That parallels her layers; it is a dated capture.</li>",
      "</ul>",
      "</details>",
      "</section>",
      "<section class='block section-block' data-section='check' aria-labelledby='l5-check'>",
      "<h2 class='h2' id='l5-check' tabindex='-1'>Check yourself</h2>",
      "<form class='quiz' data-lesson-quiz='l5-agent-friendly-architecture:0' novalidate>",
      "<fieldset class='choices'>",
      "<legend>Which layer does the speaker call the strongest enforcement?</legend>",
      "<label class='choice'><input type='radio' name='q-l5-agent-friendly-architecture-0' value='0' /><span>A style guide<span class='choice__verdict'></span></span></label>",
      "<label class='choice'><input type='radio' name='q-l5-agent-friendly-architecture-0' value='1' /><span>A strict, conventional codebase architecture<span class='choice__verdict'></span></span></label>",
      "<label class='choice'><input type='radio' name='q-l5-agent-friendly-architecture-0' value='2' /><span>Code review comments<span class='choice__verdict'></span></span></label>",
      "<label class='choice'><input type='radio' name='q-l5-agent-friendly-architecture-0' value='3' /><span>Agent memory<span class='choice__verdict'></span></span></label>",
      "</fieldset>",
      "<div class='quiz__actions'><button class='btn' type='submit'>Check</button></div>",
      "<div class='quiz__feedback' role='status'></div>",
      "</form>",
      "<form class='quiz' data-lesson-quiz='l5-agent-friendly-architecture:1' novalidate>",
      "<fieldset class='choices'>",
      "<legend>You keep writing the same review comment. What does the talk suggest?</legend>",
      "<label class='choice'><input type='radio' name='q-l5-agent-friendly-architecture-1' value='0' /><span>Write it louder<span class='choice__verdict'></span></span></label>",
      "<label class='choice'><input type='radio' name='q-l5-agent-friendly-architecture-1' value='1' /><span>Turn it into a lint rule or CI failure, or make it impossible<span class='choice__verdict'></span></span></label>",
      "<label class='choice'><input type='radio' name='q-l5-agent-friendly-architecture-1' value='2' /><span>Add it to a code comment<span class='choice__verdict'></span></span></label>",
      "<label class='choice'><input type='radio' name='q-l5-agent-friendly-architecture-1' value='3' /><span>Ignore it<span class='choice__verdict'></span></span></label>",
      "</fieldset>",
      "<div class='quiz__actions'><button class='btn' type='submit'>Check</button></div>",
      "<div class='quiz__feedback' role='status'></div>",
      "</form>",
      "</section>",
      "<section class='block section-block' data-section='rehearse' aria-labelledby='l5-rehearse'>",
      "<h2 class='h2' id='l5-rehearse' tabindex='-1'>Rehearse it</h2>",
      "<div class='rehearse__line'><pre><code>BOUNDARY: execute check-boundary.py; allowed import passes, shortcut fails</code></pre></div>",
      "<p class='para'><strong>Lab step 5 · Make the shortcut fail · 8 min.</strong> A stub agent takes the shortcut and makes a renderer script source the main one. The boundary check must reject it. The script deliberately has no soft-rule version to compare, because a README sentence would not have stopped anything.</p>",
      "<a class='btn' href='#lab/lab-4-boundary'>Open lab step 5</a>",
      "</section>",
      "<div class='lesson-end'>",
      "<div class='lesson-end__finish'><button class='btn finish' type='button' aria-pressed='false' data-finish='l5-agent-friendly-architecture'><span class='finish__mark' aria-hidden='true'></span><span data-finish-label>Mark lesson as finished</span></button><p class='lesson-end__progress meta' data-progress-count hidden></p></div>",
      "<nav class='lesson-end__nav' aria-label='Lesson navigation'>",
      "<a class='next' href='#lesson/l6-fleet-operations'><span class='next__label'>Next · Lesson 6 · 7 min</span><span class='next__title'>Start local, then scale on signals<span class='next__arrow' aria-hidden='true'>→</span></span></a>",
      "<a class='prev' href='#lesson/l4-pstack-evals'>Previous: Skills grow from failures; evals keep them honest</a>",
      "</nav>",
      "</div>"
    ],
    "notes": [
      {
        "n": 1,
        "source": "l5-agent-friendly-architecture:0",
        "kind": "said-long",
        "time": "31:19–32:50",
        "range": "31:19–32:50",
        "panelKind": "A longer stretch · said from 31:19 to 32:50",
        "paraphrase": "Big-company guardrails and restricted credentials already let agents work with limited damage.",
        "evidence": {
          "start": 1879.2,
          "end": 1970.7,
          "label": "SAID"
        }
      },
      {
        "n": 2,
        "source": "l5-agent-friendly-architecture:1",
        "kind": "said-long",
        "time": "32:51–34:31",
        "range": "32:51–34:31",
        "panelKind": "A longer stretch · said from 32:51 to 34:31",
        "paraphrase": "Unread, quickly generated greenfield code lacks guardrails and drifts into shortcut-driven chaos.",
        "evidence": {
          "start": 1971.0,
          "end": 2071.9,
          "label": "SAID"
        }
      },
      {
        "n": 3,
        "source": "l5-agent-friendly-architecture:2",
        "kind": "said",
        "time": "35:03",
        "range": "35:03–35:38",
        "panelKind": "Our paraphrase · said at 35:03",
        "paraphrase": "A refactor of over 600 PRs; she says she no longer reads the code.",
        "evidence": {
          "start": 2103.6,
          "end": 2138.2,
          "label": "SAID"
        }
      },
      {
        "n": 4,
        "source": "l5-agent-friendly-architecture:3",
        "kind": "said-long",
        "time": "39:12–40:41",
        "range": "39:12–40:41",
        "panelKind": "A longer stretch · said from 39:12 to 40:41",
        "paraphrase": "Dune’s CI bans a risky React hook and code comments.",
        "evidence": {
          "start": 2352.8,
          "end": 2441.4,
          "label": "SAID"
        }
      },
      {
        "n": 5,
        "source": "l5-agent-friendly-architecture:4",
        "kind": "said-long",
        "time": "41:39–43:07",
        "range": "41:39–43:07",
        "panelKind": "A longer stretch · said from 41:39 to 43:07",
        "paraphrase": "Main and renderer code are separated, and CI checks the dependency graph to block crossing imports.",
        "evidence": {
          "start": 2499.6,
          "end": 2587.8,
          "label": "SAID"
        }
      },
      {
        "n": 6,
        "source": "l5-agent-friendly-architecture:5",
        "kind": "shown",
        "time": "45:00",
        "range": "45:00–45:15",
        "panelKind": "Shown on screen at 45:00 · not narrated",
        "paraphrase": "The Dune page lists agent habits as design inputs and five rules, including that forbidden dependencies fail mechanically.",
        "evidence": {
          "start": 2700.0,
          "end": 2715.0,
          "label": "SHOWN",
          "frameId": "visual-2700.jpg"
        }
      },
      {
        "n": 7,
        "source": "l5-agent-friendly-architecture:7",
        "kind": "shown",
        "time": "43:25",
        "range": "43:25–53:50",
        "panelKind": "Shown on screen at 43:25 · not narrated",
        "paraphrase": "A handwritten five-item list ranks codebase, static analysis, rules and Bugbot, skills, and a style guide.",
        "evidence": {
          "start": 2605.0,
          "end": 3230.0,
          "label": "SHOWN",
          "frameId": "visual-2605.jpg"
        }
      },
      {
        "n": 8,
        "source": "l5-agent-friendly-architecture:6",
        "kind": "said-long",
        "time": "43:38–45:15",
        "range": "43:38–45:15",
        "panelKind": "A longer stretch · said from 43:38 to 45:15",
        "paraphrase": "Co-located feature directories and making the shortest path the best one.",
        "evidence": {
          "start": 2618.9,
          "end": 2715.6,
          "label": "SAID"
        }
      },
      {
        "n": 9,
        "source": "l5-agent-friendly-architecture:8",
        "kind": "said",
        "time": "46:01",
        "range": "46:01–46:59",
        "panelKind": "Our paraphrase · said at 46:01",
        "paraphrase": "Static checks make CI fail; rules, skills and the review bot are soft and get forgotten.",
        "evidence": {
          "start": 2761.4,
          "end": 2819.8,
          "label": "SAID"
        }
      },
      {
        "n": 10,
        "source": "l5-agent-friendly-architecture:9",
        "kind": "said",
        "time": "47:49",
        "range": "47:49–48:31",
        "panelKind": "Our paraphrase · said at 47:49",
        "paraphrase": "Repeating a review comment signals a missing lint rule or CI check.",
        "evidence": {
          "start": 2869.4,
          "end": 2911.2,
          "label": "SAID"
        }
      }
    ],
    "checks": [
      {
        "index": 0,
        "question": "Which layer does the speaker call the strongest enforcement?",
        "options": [
          "A style guide",
          "A strict, conventional codebase architecture",
          "Code review comments",
          "Agent memory"
        ],
        "answer": 1,
        "explanationHtml": "Her handwritten list puts the codebase first: a strict, conventional structure that agents copy. Static analysis comes next, and a style guide last. She explains why at <button class='time-link' type='button' data-lesson-source='l5-agent-friendly-architecture:6' aria-label='Note 8, said from 43:38 to 45:15'>43:38</button>.",
        "status": "question, options and answer verbatim; explanation rewritten without the numeric range"
      },
      {
        "index": 1,
        "question": "You keep writing the same review comment. What does the talk suggest?",
        "options": [
          "Write it louder",
          "Turn it into a lint rule or CI failure, or make it impossible",
          "Add it to a code comment",
          "Ignore it"
        ],
        "answer": 1,
        "explanationHtml": "She treats a repeated review comment as a smell: turn it into a lint rule or a CI failure, or remove the possibility entirely. She says so at <button class='time-link' type='button' data-lesson-source='l5-agent-friendly-architecture:9' aria-label='Note 10, said at 47:49'>47:49</button>.",
        "status": "question, options and answer verbatim; explanation rewritten without the numeric range"
      }
    ],
    "practice": [
      {
        "scenario": "s5-architecture-gate",
        "section": "try",
        "role": "home lesson of this experiment (design-spec simulator.scenarios)"
      }
    ],
    "lab": {
      "step": "lab-4-boundary",
      "n": 5,
      "title": "Make the shortcut fail",
      "minutes": 8,
      "outputLine": "BOUNDARY: execute check-boundary.py; allowed import passes, shortcut fails"
    },
    "supplements": {
      "basics": "All three original basics paragraphs retained verbatim.",
      "deep": "All three original deep paragraphs retained verbatim in Going further. Limits of the evidence holds the open-source caveat, the Sand naming conflict, the self-report caveat and the dated pstack README entry.",
      "practitioner": "All four original paragraphs retained in substance under four specific heads; the original bulleted lists become prose because each item now carries its own citation. The handwritten list is drawn as the layers figure. Next.js-for-Electron (2346.3–2389.5), the regressing agents window (2462.7–2499.6) and strict compilers (2823.9–2869.4) have no evidence entries and stay uncited."
    },
    "end": {
      "next": {
        "href": "#lesson/l6-fleet-operations",
        "label": "Next · Lesson 6 · 7 min",
        "title": "Start local, then scale on signals"
      },
      "previous": {
        "href": "#lesson/l4-pstack-evals",
        "text": "Previous: Skills grow from failures; evals keep them honest"
      }
    }
  },
  "l6-fleet-operations": {
    "schemaVersion": 1,
    "id": "l6-fleet-operations",
    "n": 6,
    "title": "Start local, then scale on signals",
    "deck": "Once verification exists, how do agents pick up work and land it safely at volume?",
    "summary": "Build and watch verification locally, then let cloud agents act on signals such as bug reports. Keep changes small and revertible, and promote only through hard gates.",
    "minutes": 7,
    "here": [
      "signal",
      "claim",
      "worktree",
      "promote"
    ],
    "strip": {
      "sentenceHtml": "Where this fits: <strong>Signal · Claim · Worktree · Promote</strong>, where work enters the path and where it leaves for the cluster."
    },
    "decision": "Admit each signal once: claim it atomically, give it its own worktree, reproduce before fixing, keep the PR small, and let only a human-approved promotion reach the cluster.",
    "sections": [
      {
        "slug": "in-short",
        "heading": null,
        "target": "h1"
      },
      {
        "slug": "start-local",
        "heading": "Start where you can watch",
        "id": "l6-start-local"
      },
      {
        "slug": "signals",
        "heading": "Signals, not keystrokes",
        "id": "l6-signals"
      },
      {
        "slug": "small-changes",
        "heading": "Small changes, and a gate that holds",
        "id": "l6-small-changes"
      },
      {
        "slug": "soyspray",
        "heading": "Your queue, your gates",
        "id": "l6-soyspray"
      },
      {
        "slug": "breaks",
        "heading": "Where the analogy breaks",
        "id": "l6-breaks"
      },
      {
        "slug": "try",
        "heading": "Try it",
        "id": "l6-try"
      },
      {
        "slug": "further",
        "heading": "Going further",
        "id": "l6-further"
      },
      {
        "slug": "check",
        "heading": "Check yourself",
        "id": "l6-check"
      },
      {
        "slug": "rehearse",
        "heading": "Rehearse it",
        "id": "l6-rehearse"
      }
    ],
    "bodyHtml": [
      "<div class='block in-short' data-section='in-short'>",
      "<div class='side side--quiet side--intro' role='note'><p>Numbered notes paraphrase the recording. Select a time to watch and read that moment.</p></div>",
      "<span class='label'>In short</span>",
      "<p class='lead'>Build and watch verification locally, then let cloud agents act on signals such as bug reports. Keep changes small and revertible, and promote only through hard gates.</p>",
      "<details class='terms-inline' data-depth-open='basics'>",
      "<summary>Terms in this lesson · 2</summary>",
      "<p>A cloud agent runs on a remote machine rather than your laptop, so it can work while you are away.</p>",
      "<p>A git worktree is a second working directory attached to the same repository, letting several agents edit in parallel without overwriting each other.</p>",
      "</details>",
      "</div>",
      "<div class='block' data-section='start-local'>",
      "<div class='side notes' role='group' aria-label='Notes from the talk'>",
      "<p class='notes__label'>From the talk</p>",
      "<ol>",
      "<li class='note'><span class='note__num'>1</span><p class='note__text'>Start local so you can observe how the agent drives the application.</p><button class='note__open' type='button' data-lesson-source='l6-fleet-operations:0' data-num='1' aria-label='Open note 1 in the recording, said at 24:27'>24:27 · said</button></li>",
      "<li class='note'><span class='note__num'>2</span><p class='note__text'>She mostly uses cloud agents; verification skills benefit the whole team there.</p><button class='note__open' type='button' data-lesson-source='l6-fleet-operations:1' data-num='2' aria-label='Open note 2 in the recording, said at 25:05'>25:05 · said</button></li>",
      "</ol>",
      "</div>",
      "<h2 class='h3 para-head' id='l6-start-local' tabindex='-1'>Start where you can watch</h2>",
      "<p class='para'>Asked where to start, Tan says to start locally, where you can watch the agent operate the app and its <span class='nobr'>interfaces<button class='cite' type='button' data-lesson-source='l6-fleet-operations:0' aria-label='Note 1, said at 24:27'>1</button>.</span> She herself mostly uses cloud agents, and argues that verification skills pay off team-wide once agents run <span class='nobr'>remotely<button class='cite' type='button' data-lesson-source='l6-fleet-operations:1' aria-label='Note 2, said at 25:05'>2</button>.</span></p>",
      "</div>",
      "<div class='block' data-section='signals'>",
      "<div class='side notes' role='group' aria-label='Notes from the talk'>",
      "<p class='notes__label'>From the talk</p>",
      "<ol>",
      "<li class='note'><span class='note__num'>3</span><p class='note__text'>An internal agent reproduces bug reports in the cloud and found one already fixed on main.</p><button class='note__open' type='button' data-lesson-source='l6-fleet-operations:2' data-num='3' aria-label='Open note 3 in the recording, said from 25:54 to 26:57'>25:54–26:57 · said</button></li>",
      "<li class='note'><span class='note__num'>4</span><p class='note__text'>The agent’s message reports the bug reproduced on the prior commit and gone on the fix.</p><button class='note__open' type='button' data-lesson-source='l6-fleet-operations:3' data-num='4' aria-label='Open note 4, shown on screen at 25:53'>25:53 · shown</button></li>",
      "<li class='note'><span class='note__num'>5</span><p class='note__text'>The host recaps the path from verification to auto-merge; she agrees.</p><button class='note__open' type='button' data-lesson-source='l6-fleet-operations:4' data-num='5' aria-label='Open note 5 in the recording, said at 27:38'>27:38 · said</button></li>",
      "</ol>",
      "</div>",
      "<h2 class='h3 para-head' id='l6-signals' tabindex='-1'>Signals, not keystrokes</h2>",
      "<p class='para'>Her example is an internal agent she calls Benny. It takes incoming bug reports, runs the app on its own cloud machine with the same control skills, and tries to reproduce each issue. In one case it reproduced a bug that was already fixed on main, so the answer was simply to ship a <span class='nobr'>build<button class='cite' type='button' data-lesson-source='l6-fleet-operations:2' aria-label='Note 3, said from 25:54 to 26:57'>3</button>.</span> Its message on screen says the bug reproduced on the earlier commit and is gone on the <span class='nobr'>fix<button class='cite' type='button' data-lesson-source='l6-fleet-operations:3' aria-label='Note 4, shown at 25:53'>4</button>.</span> That is verification used for triage, not only for fixes.</p>",
      "<p class='para'>The host then recaps the path as verification, local trust, cloud agents responding to signals, then auto-merge, and she <span class='nobr'>agrees<button class='cite' type='button' data-lesson-source='l6-fleet-operations:4' aria-label='Note 5, said at 27:38'>5</button>.</span></p>",
      "</div>",
      "<div class='block'>",
      "<div class='side side--quiet' role='note'><p>Our table. Her example is the middle row; the other two rows extend it.</p></div>",
      "<figure class='figure' aria-labelledby='l6-fig-title'>",
      "<p class='figure__title' id='l6-fig-title'>Reproduce first, then decide what to ship</p>",
      "<table class='compare triage'>",
      "<caption class='visually-hidden'>What to ship for a bug report, by where it reproduces</caption>",
      "<thead><tr><th scope='col'>Reproduces on main</th><th scope='col'>On an earlier commit</th><th scope='col'>Ship</th></tr></thead>",
      "<tbody>",
      "<tr><td>Yes</td><td>Not needed</td><td>A fix, as one small PR</td></tr>",
      "<tr><td>No</td><td>Yes</td><td>Already fixed: ship a build</td></tr>",
      "<tr><td>No</td><td>No</td><td>A note on the report, not a PR</td></tr>",
      "</tbody>",
      "</table>",
      "</figure>",
      "</div>",
      "<div class='block' data-section='small-changes'>",
      "<div class='side notes' role='group' aria-label='Notes from the talk'>",
      "<p class='notes__label'>From the talk</p>",
      "<ol>",
      "<li class='note'><span class='note__num'>6</span><p class='note__text'>No hard PR size cap; agents split work so history stays atomic and revertible.</p><button class='note__open' type='button' data-lesson-source='l6-fleet-operations:5' data-num='6' aria-label='Open note 6 in the recording, said at 37:57'>37:57 · said</button></li>",
      "<li class='note'><span class='note__num'>7</span><p class='note__text'>An agent’s notes list one human approval from a review group as the last dependency before merging.</p><button class='note__open' type='button' data-lesson-source='l6-fleet-operations:6' data-num='7' aria-label='Open note 7, shown on screen at 6:51'>6:51 · shown</button></li>",
      "<li class='note'><span class='note__num'>8</span><p class='note__text'>An agent’s project overview says the merge policy needs reviews from two teams, and one security approval still blocks the final four merges. It adds a correction: an earlier reading that the gate had cleared was wrong, and merge attempts were refused, not bypassed.</p><button class='note__open' type='button' data-lesson-source='l6-fleet-operations:7' data-num='8' aria-label='Open note 8, shown on screen at 37:20'>37:20 · shown</button></li>",
      "</ol>",
      "</div>",
      "<h2 class='h3 para-head' id='l6-small-changes' tabindex='-1'>Small changes, and a gate that holds</h2>",
      "<p class='para'>On PR size there is no hard cap. Agents are encouraged to split work, because she values a history in which each PR describes one small change that is easy to revert and to <span class='nobr'>bisect<button class='cite' type='button' data-lesson-source='l6-fleet-operations:5' aria-label='Note 6, said at 37:57'>6</button>.</span></p>",
      "<p class='para'>Two unnarrated screens bear on the human gate. An agent’s working notes name one human approval from a security or build review group as the last dependency before merging, with no bot <span class='nobr'>route<button class='cite' type='button' data-lesson-source='l6-fleet-operations:6' aria-label='Note 7, shown at 6:51'>7</button>.</span> A later panel, which describes the policy differently, reports that merge attempts were refused while a security approval was <span class='nobr'>pending<button class='cite' type='button' data-lesson-source='l6-fleet-operations:7' aria-label='Note 8, shown at 37:20'>8</button>.</span> Our read: even at the top of her curve, some changes still wait for a person, and the tooling refuses rather than bypasses.</p>",
      "</div>",
      "<div class='block' data-section='soyspray'>",
      "<h2 class='h3 para-head' id='l6-soyspray' tabindex='-1'>Your queue, your gates</h2>",
      "<p class='para'>For Soyspray, signals are your queue. Before an agent starts, each task needs a claim, so it is not done twice, and an isolated worktree. Before it lands, it needs a check that runs the real thing and a PR small enough to review. The existing digest promotion PR stays the only path to the cluster. Agents never hold cluster credentials. If you ever adopt auto-merge, apply it to source PRs behind hard checks, never to promotion.</p>",
      "</div>",
      "<section class='block section-block' data-section='breaks' aria-labelledby='l6-breaks'>",
      "<h2 class='h2' id='l6-breaks' tabindex='-1'>Where the analogy breaks</h2>",
      "<ul class='dash-list'>",
      "<li>Queue consumers process identical message types; agent tasks vary widely, and some cannot be finished.</li>",
      "<li>Kubernetes rollouts can be undone automatically; a merged bad change needs a revert PR and someone to notice.</li>",
      "</ul>",
      "</section>",
      "<section class='block section-block' data-section='try' aria-labelledby='l6-try'>",
      "<div class='side side--quiet' role='note'><p>Deterministic teaching models with fixed schedules. The duplicate PR and the lost edit are scripted to show a cause, not measured rates. Ticks and cost units are abstract.</p></div>",
      "<h2 class='h2' id='l6-try' tabindex='-1'>Try it</h2>",
      "<p class='para'>Two ways work goes wrong on the way in: one report delivered twice, then two agents editing the same line.</p>",
      "<div class='practice' data-scenario='s4-naive-retry' data-context='lesson'></div>",
      "<div class='practice' data-scenario='s1-shared-vs-isolated' data-context='lesson'></div>",
      "</section>",
      "<section class='block section-block' data-section='further' aria-labelledby='l6-further'>",
      "<div class='side notes' role='group' aria-label='Notes from the talk'>",
      "<p class='notes__label'>From the talk</p>",
      "<ol>",
      "<li class='note'><span class='note__num'>9</span><p class='note__text'>The control skill’s documentation describes driving a running dev build over CDP, with separate worktree-isolated instances.</p><button class='note__open' type='button' data-lesson-source='l3-feature-map:1' data-num='9' aria-label='Open note 9, shown on screen at 7:20'>7:20 · shown</button></li>",
      "</ol>",
      "</div>",
      "<h2 class='h2' id='l6-further' tabindex='-1'>Going further</h2>",
      "<p class='para'>Retries in agent pipelines are not idempotent by default: re-sending a bug report can spawn a second agent and a second PR. Key each task by a stable identifier, such as report ID plus repository, and make claiming atomic.</p>",
      "<p class='para'>Reproduction before fixing doubles as deduplication: if the issue does not reproduce on main, the right output is a note, not a PR. Her Benny example shows this outcome.</p>",
      "<p class='para'>The host asks about worktrees and isolated sub-agents, and the spoken answer is practical advice, not an isolation design. The only isolation detail is on screen: the control skill’s documentation describes worktree-isolated instances, which she does not <span class='nobr'>narrate<button class='cite' type='button' data-lesson-source='l3-feature-map:1' aria-label='Note 9, shown at 7:20'>9</button>.</span> Treat everything else about isolation in this lesson as our recommendation.</p>",
      "<details class='limits' data-depth-open='deep'>",
      "<summary>Limits of the evidence · 2</summary>",
      "<ul class='limits__list'>",
      "<li>The two screens about the human gate describe the requirement differently: one approval from either review group, or reviews from two teams. Both are shown, neither is narrated, and we do not reconcile them.</li>",
      "<li><a href='https://git-scm.com/docs/git-worktree' rel='noreferrer'>git-worktree manual ↗</a>, Git 2.56.0, retrieved 11 October 2026. The talk does not say how agents are isolated; this manual documents the mechanism the lab uses. One repository can have several working trees, each with its own HEAD and index. By default Git refuses to check out a branch that another worktree holds, and removing a worktree with uncommitted or untracked changes requires force.</li>",
      "</ul>",
      "</details>",
      "</section>",
      "<section class='block section-block' data-section='check' aria-labelledby='l6-check'>",
      "<h2 class='h2' id='l6-check' tabindex='-1'>Check yourself</h2>",
      "<form class='quiz' data-lesson-quiz='l6-fleet-operations:0' novalidate>",
      "<fieldset class='choices'>",
      "<legend>What did the bug-reproduction agent conclude in her example?</legend>",
      "<label class='choice'><input type='radio' name='q-l6-fleet-operations-0' value='0' /><span>The bug was unfixable<span class='choice__verdict'></span></span></label>",
      "<label class='choice'><input type='radio' name='q-l6-fleet-operations-0' value='1' /><span>It reproduced the bug, which was already fixed on main<span class='choice__verdict'></span></span></label>",
      "<label class='choice'><input type='radio' name='q-l6-fleet-operations-0' value='2' /><span>It needed a rewrite<span class='choice__verdict'></span></span></label>",
      "<label class='choice'><input type='radio' name='q-l6-fleet-operations-0' value='3' /><span>It was a duplicate PR<span class='choice__verdict'></span></span></label>",
      "</fieldset>",
      "<div class='quiz__actions'><button class='btn' type='submit'>Check</button></div>",
      "<div class='quiz__feedback' role='status'></div>",
      "</form>",
      "<form class='quiz' data-lesson-quiz='l6-fleet-operations:1' novalidate>",
      "<fieldset class='choices'>",
      "<legend>Where should auto-merge stop in Soyspray’s model?</legend>",
      "<label class='choice'><input type='radio' name='q-l6-fleet-operations-1' value='0' /><span>Nowhere<span class='choice__verdict'></span></span></label>",
      "<label class='choice'><input type='radio' name='q-l6-fleet-operations-1' value='1' /><span>Before the digest promotion that activates a workload<span class='choice__verdict'></span></span></label>",
      "<label class='choice'><input type='radio' name='q-l6-fleet-operations-1' value='2' /><span>After cluster sync<span class='choice__verdict'></span></span></label>",
      "<label class='choice'><input type='radio' name='q-l6-fleet-operations-1' value='3' /><span>At secret rotation<span class='choice__verdict'></span></span></label>",
      "</fieldset>",
      "<div class='quiz__actions'><button class='btn' type='submit'>Check</button></div>",
      "<div class='quiz__feedback' role='status'></div>",
      "</form>",
      "</section>",
      "<section class='block section-block' data-section='rehearse' aria-labelledby='l6-rehearse'>",
      "<h2 class='h2' id='l6-rehearse' tabindex='-1'>Rehearse it</h2>",
      "<div class='rehearse__line'><pre><code>RETRY: atomic mkdir claims/R7 succeeds once; repeated claim is skipped</code></pre></div>",
      "<p class='para'><strong>Lab step 6 · Claim tasks atomically · 6 min.</strong> Creating a directory either succeeds or fails as one operation, so only one delivery of report R7 can claim it; the second is skipped. <a href='#lab/lab-1-worktrees'>Lab step 2</a> rehearses the other half of admission: two worktrees turn a silent overwrite into a merge conflict.</p>",
      "<a class='btn' href='#lab/lab-5-idempotent-claim'>Open lab step 6</a>",
      "</section>",
      "<div class='lesson-end'>",
      "<div class='lesson-end__finish'><button class='btn finish' type='button' aria-pressed='false' data-finish='l6-fleet-operations'><span class='finish__mark' aria-hidden='true'></span><span data-finish-label>Mark lesson as finished</span></button><p class='lesson-end__progress meta' data-progress-count hidden></p></div>",
      "<nav class='lesson-end__nav' aria-label='Lesson navigation'>",
      "<a class='next' href='#lesson/l7-cost-and-adoption'><span class='next__label'>Next · Lesson 7 · 5 min</span><span class='next__title'>Verification first, volume last<span class='next__arrow' aria-hidden='true'>→</span></span></a>",
      "<a class='prev' href='#lesson/l5-agent-friendly-architecture'>Previous: Make the shortest path the right path</a>",
      "</nav>",
      "</div>"
    ],
    "notes": [
      {
        "n": 1,
        "source": "l6-fleet-operations:0",
        "kind": "said",
        "time": "24:27",
        "range": "24:27–25:03",
        "panelKind": "Our paraphrase · said at 24:27",
        "paraphrase": "Start local so you can observe how the agent drives the application.",
        "evidence": {
          "start": 1467.7,
          "end": 1503.1,
          "label": "SAID"
        }
      },
      {
        "n": 2,
        "source": "l6-fleet-operations:1",
        "kind": "said",
        "time": "25:05",
        "range": "25:05–25:48",
        "panelKind": "Our paraphrase · said at 25:05",
        "paraphrase": "She mostly uses cloud agents; verification skills benefit the whole team there.",
        "evidence": {
          "start": 1505.7,
          "end": 1548.4,
          "label": "SAID"
        }
      },
      {
        "n": 3,
        "source": "l6-fleet-operations:2",
        "kind": "said-long",
        "time": "25:54–26:57",
        "range": "25:54–26:57",
        "panelKind": "A longer stretch · said from 25:54 to 26:57",
        "paraphrase": "An internal agent reproduces bug reports in the cloud and found one already fixed on main.",
        "evidence": {
          "start": 1554.5,
          "end": 1617.9,
          "label": "SAID"
        }
      },
      {
        "n": 4,
        "source": "l6-fleet-operations:3",
        "kind": "shown",
        "time": "25:53",
        "range": "25:53–27:13",
        "panelKind": "Shown on screen at 25:53 · not narrated",
        "paraphrase": "The agent’s message reports the bug reproduced on the prior commit and gone on the fix.",
        "evidence": {
          "start": 1553.8,
          "end": 1633.8,
          "label": "SHOWN",
          "frameId": "visual-1584.8.jpg"
        }
      },
      {
        "n": 5,
        "source": "l6-fleet-operations:4",
        "kind": "said",
        "time": "27:38",
        "range": "27:38–28:33",
        "panelKind": "Our paraphrase · said at 27:38",
        "paraphrase": "The host recaps the path from verification to auto-merge; she agrees.",
        "evidence": {
          "start": 1658.2,
          "end": 1713.6,
          "label": "SAID"
        }
      },
      {
        "n": 6,
        "source": "l6-fleet-operations:5",
        "kind": "said",
        "time": "37:57",
        "range": "37:57–38:45",
        "panelKind": "Our paraphrase · said at 37:57",
        "paraphrase": "No hard PR size cap; agents split work so history stays atomic and revertible.",
        "evidence": {
          "start": 2277.7,
          "end": 2325.5,
          "label": "SAID"
        }
      },
      {
        "n": 7,
        "source": "l6-fleet-operations:6",
        "kind": "shown",
        "time": "6:51",
        "range": "6:51–7:01",
        "panelKind": "Shown on screen at 6:51 · not narrated",
        "paraphrase": "An agent’s notes list one human approval from a review group as the last dependency before merging.",
        "evidence": {
          "start": 411.9,
          "end": 421.6,
          "label": "SHOWN",
          "frameId": "visual-411.9.jpg"
        }
      },
      {
        "n": 8,
        "source": "l6-fleet-operations:7",
        "kind": "shown",
        "time": "37:20",
        "range": "37:20–37:31",
        "panelKind": "Shown on screen at 37:20 · not narrated",
        "paraphrase": "An agent’s project overview says the merge policy needs reviews from two teams, and one security approval still blocks the final four merges. It adds a correction: an earlier reading that the gate had cleared was wrong, and merge attempts were refused, not bypassed.",
        "paraphraseNormalisation": "The source paraphrase’s quoted phrase ‘gate cleared’ is rewritten without quotation marks so the paraphrase cannot read as a quotation.",
        "evidence": {
          "start": 2240.0,
          "end": 2251.7,
          "label": "SHOWN",
          "frameId": "lauren_00h37m20.000s_periodic"
        }
      },
      {
        "n": 9,
        "source": "l3-feature-map:1",
        "kind": "shown",
        "time": "7:20",
        "range": "7:20–10:06",
        "panelKind": "Shown on screen at 7:20 · not narrated",
        "crossLesson": true,
        "paraphrase": "The control skill’s documentation describes driving a running dev build over CDP, with separate worktree-isolated instances.",
        "evidence": {
          "start": 440.0,
          "end": 606.7,
          "label": "SHOWN",
          "frameId": "lauren_00h07m20.000s_periodic"
        }
      }
    ],
    "checks": [
      {
        "index": 0,
        "question": "What did the bug-reproduction agent conclude in her example?",
        "options": [
          "The bug was unfixable",
          "It reproduced the bug, which was already fixed on main",
          "It needed a rewrite",
          "It was a duplicate PR"
        ],
        "answer": 1,
        "explanationHtml": "Her bug-reproduction agent reproduced the report on the earlier commit and found it gone on main, so the answer was to ship a build. Verification did the triage. She tells it at <button class='time-link' type='button' data-lesson-source='l6-fleet-operations:2' aria-label='Note 3, said from 25:54 to 26:57'>25:54</button>.",
        "status": "question, options and answer verbatim; explanation rewritten without the numeric ranges"
      },
      {
        "index": 1,
        "question": "Where should auto-merge stop in Soyspray’s model?",
        "options": [
          "Nowhere",
          "Before the digest promotion that activates a workload",
          "After cluster sync",
          "At secret rotation"
        ],
        "answer": 1,
        "explanationHtml": "This is our Soyspray rule, not hers: auto-merge may apply to source PRs behind hard checks, but the digest promotion that activates a workload stays a reviewed human step.",
        "status": "question, options and answer verbatim (typographic apostrophe); explanation expanded, still labelled as interpretation"
      }
    ],
    "practice": [
      {
        "scenario": "s4-naive-retry",
        "section": "try",
        "role": "lesson-source mapping and home lesson (design-spec simulator.scenarios)"
      },
      {
        "scenario": "s1-shared-vs-isolated",
        "section": "try",
        "role": "home lesson in design-spec simulator.scenarios; deliberate addition, since lesson-source maps no lesson to s1"
      }
    ],
    "lab": {
      "step": "lab-5-idempotent-claim",
      "n": 6,
      "title": "Claim tasks atomically",
      "minutes": 6,
      "outputLine": "RETRY: atomic mkdir claims/R7 succeeds once; repeated claim is skipped",
      "alsoLinked": "lab-1-worktrees"
    },
    "supplements": {
      "basics": "Both original basics paragraphs retained verbatim.",
      "deep": "All three original deep paragraphs retained in Going further; the third loses its numeric ranges and cites the on-screen isolation detail through a deliberate cross-lesson note (l3-feature-map:1). Limits of the evidence holds the unreconciled gate screens and the dated git-worktree manual.",
      "practitioner": "All five original paragraphs retained in substance under four specific heads; the two lists become prose so each item carries its own citation. The Soyspray translation keeps every required element: claim, isolated worktree, real check, small PR, digest promotion as the only path, no cluster credentials, auto-merge never on promotion."
    },
    "end": {
      "next": {
        "href": "#lesson/l7-cost-and-adoption",
        "label": "Next · Lesson 7 · 5 min",
        "title": "Verification first, volume last"
      },
      "previous": {
        "href": "#lesson/l5-agent-friendly-architecture",
        "text": "Previous: Make the shortest path the right path"
      }
    }
  },
  "l7-cost-and-adoption": {
    "schemaVersion": 1,
    "id": "l7-cost-and-adoption",
    "n": 7,
    "title": "Verification first, volume last",
    "deck": "Is this worth it without unlimited tokens, and what should I adopt first?",
    "summary": "She is candid that her token budget is unusual and frames setup as an ROI question. The cheap, transferable parts are verification and hard checks; volume comes last.",
    "minutes": 5,
    "here": [
      "signal",
      "claim",
      "worktree",
      "agent",
      "verify",
      "checks",
      "review",
      "merge",
      "promote"
    ],
    "strip": {
      "sentenceHtml": "Where this fits: <strong>the whole path</strong>, in the order you adopt it."
    },
    "decision": "Adopt in order: verification evidence, then checks from repeated review comments, then isolation and claims, and only then unattended agents, with promotion kept human.",
    "sections": [
      {
        "slug": "in-short",
        "heading": null,
        "target": "h1"
      },
      {
        "slug": "her-budget",
        "heading": "Her budget is not yours",
        "id": "l7-her-budget"
      },
      {
        "slug": "payoff",
        "heading": "The claimed payoff",
        "id": "l7-payoff"
      },
      {
        "slug": "order",
        "heading": "Order over scale",
        "id": "l7-order"
      },
      {
        "slug": "breaks",
        "heading": "Where the analogy breaks",
        "id": "l7-breaks"
      },
      {
        "slug": "further",
        "heading": "Going further",
        "id": "l7-further"
      },
      {
        "slug": "check",
        "heading": "Check yourself",
        "id": "l7-check"
      },
      {
        "slug": "rehearse",
        "heading": "Rehearse it",
        "id": "l7-rehearse"
      },
      {
        "slug": "adopt",
        "heading": "Your adoption decision",
        "id": "l7-adopt"
      }
    ],
    "bodyHtml": [
      "<div class='block in-short' data-section='in-short'>",
      "<div class='side side--quiet side--intro' role='note'><p>Numbered notes paraphrase the recording. Select a time to watch and read that moment.</p></div>",
      "<span class='label'>In short</span>",
      "<p class='lead'>She is candid that her token budget is unusual and frames setup as an ROI question. The cheap, transferable parts are verification and hard checks; volume comes last.</p>",
      "<details class='terms-inline' data-depth-open='basics'>",
      "<summary>Terms in this lesson · 1</summary>",
      "<p>Tokens are the units that model usage is billed in; long contexts and many parallel agents multiply them.</p>",
      "</details>",
      "</div>",
      "<div class='block' data-section='her-budget'>",
      "<div class='side notes' role='group' aria-label='Notes from the talk'>",
      "<p class='notes__label'>From the talk</p>",
      "<ol>",
      "<li class='note'><span class='note__num'>1</span><p class='note__text'>She has effectively unlimited tokens at work and cautions against copying her approach exactly.</p><button class='note__open' type='button' data-lesson-source='l7-cost-and-adoption:0' data-num='1' aria-label='Open note 1 in the recording, said at 49:33'>49:33 · said</button></li>",
      "<li class='note'><span class='note__num'>2</span><p class='note__text'>Up-front token spend is an ROI decision that lets weaker agents and fewer people do good work.</p><button class='note__open' type='button' data-lesson-source='l7-cost-and-adoption:1' data-num='2' aria-label='Open note 2 in the recording, said from 50:00 to 52:06'>50:00–52:06 · said</button></li>",
      "</ol>",
      "</div>",
      "<h2 class='h3 para-head' id='l7-her-budget' tabindex='-1'>Her budget is not yours</h2>",
      "<p class='para'>Asked whether this is realistic on a normal budget, Tan says she works at an AI lab with effectively unlimited tokens, so her approach should not be copied wholesale, though she thinks it can be done without breaking the <span class='nobr'>bank<button class='cite' type='button' data-lesson-source='l7-cost-and-adoption:0' aria-label='Note 1, said at 49:33'>1</button>.</span> She frames it as a return on investment: setup and refactoring consume many tokens up front, in exchange for a codebase where even weaker agents do good work, and for constraints one person could never enforce <span class='nobr'>alone<button class='cite' type='button' data-lesson-source='l7-cost-and-adoption:1' aria-label='Note 2, said from 50:00 to 52:06'>2</button>.</span></p>",
      "</div>",
      "<div class='block' data-section='payoff'>",
      "<div class='side notes' role='group' aria-label='Notes from the talk'>",
      "<p class='notes__label'>From the talk</p>",
      "<ol>",
      "<li class='note'><span class='note__num'>3</span><p class='note__text'>Non-engineers ship fixes via Grok Bot, which she attributes to the strict architecture.</p><button class='note__open' type='button' data-lesson-source='l7-cost-and-adoption:3' data-num='3' aria-label='Open note 3 in the recording, said from 54:31 to 56:42'>54:31–56:42 · said</button></li>",
      "<li class='note'><span class='note__num'>4</span><p class='note__text'>A model release announced in the session; she hedges the pricing statement.</p><button class='note__open' type='button' data-lesson-source='l7-cost-and-adoption:2' data-num='4' aria-label='Open note 4 in the recording, said at 52:29'>52:29 · said</button></li>",
      "</ol>",
      "</div>",
      "<h2 class='h3 para-head' id='l7-payoff' tabindex='-1'>The claimed payoff</h2>",
      "<p class='para'>She credits the strict architecture with letting product managers and designers ship fixes through Grok Bot’s chat-style interface, which she likens to a messaging app with named <span class='nobr'>agents<button class='cite' type='button' data-lesson-source='l7-cost-and-adoption:3' aria-label='Note 3, said from 54:31 to 56:42'>3</button>.</span> During the session she also announced a new model release, a Grok model numbered 4.6 that she believed kept the previous per-token price, and hedged that statement <span class='nobr'>herself<button class='cite' type='button' data-lesson-source='l7-cost-and-adoption:2' aria-label='Note 4, said at 52:29'>4</button>.</span> Treat it as dated: the Grok Bot overview captured on 11 October 2026 already links a later model version.</p>",
      "</div>",
      "<div class='block' data-section='order'>",
      "<h2 class='h3 para-head' id='l7-order' tabindex='-1'>Order over scale</h2>",
      "<p class='para'>For a home cluster, the order matters more than the scale. It is lesson 1’s climb, turned into an adoption plan:</p>",
      "<ol class='num-list'>",
      "<li>Require verification evidence for every agent task.<span class='num-list__where'><a href='#lesson/l2-verification'>Lesson 2</a> · Verify</span></li>",
      "<li>Convert repeated review comments into checks.<span class='num-list__where'><a href='#lesson/l5-agent-friendly-architecture'>Lesson 5</a> · Checks</span></li>",
      "<li>Add isolation and claims for parallel work.<span class='num-list__where'><a href='#lesson/l6-fleet-operations'>Lesson 6</a> · Claim · Worktree</span></li>",
      "<li>Only then consider unattended agents, and keep the promotion boundary human.<span class='num-list__where'><a href='#lesson/l1-trust-curve'>Lesson 1</a> · Merge · Promote</span></li>",
      "</ol>",
      "<p class='para'>The experiments put rough numbers on the same trade.</p>",
      "</div>",
      "<div class='block'>",
      "<div class='side side--quiet' role='note'><p>Our table of the five experiments’ scripted outcomes, in abstract units. None of it is a measured cost.</p></div>",
      "<figure class='figure' aria-labelledby='l7-fig-title'>",
      "<p class='figure__title' id='l7-fig-title'>What each control cost in the experiments</p>",
      "<table class='compare costs'>",
      "<caption class='visually-hidden'>Scripted cost units with each control off and on, and what the difference bought</caption>",
      "<thead><tr><th scope='col'>Experiment · control</th><th scope='col' class='num'>Cost, off → on</th><th scope='col'>What it bought</th></tr></thead>",
      "<tbody>",
      "<tr><td><a href='#practice/s2-plausible-vs-verified'>Done, or verified?</a> · verification gate</td><td class='num'>9 → 12</td><td>The non-fix stays off main: defects on main fall from 1 to 0.</td></tr>",
      "<tr><td><a href='#practice/s4-naive-retry'>Retry without a claim</a> · atomic claim</td><td class='num'>6 → 3</td><td>No duplicate PR: wasted units fall from 3 to 0.</td></tr>",
      "<tr><td><a href='#practice/s5-architecture-gate'>The shortcut import</a> · CI check</td><td class='num'>3 → 4</td><td>Caught by CI at tick 2, not by a user at tick 8.</td></tr>",
      "<tr><td><a href='#practice/s1-shared-vs-isolated'>Two agents, one file</a> · worktrees</td><td class='num'>6 → 6</td><td>The lost edit becomes a conflict a reviewer sees.</td></tr>",
      "<tr><td><a href='#practice/s3-review-backlog'>The reviewer is the bottleneck</a> · hard checks</td><td class='num is-empty'>not counted</td><td>With four agents, the peak review queue falls from 10 to 6.</td></tr>",
      "</tbody>",
      "</table>",
      "<p class='figure__note'>The model counts work, not what a defect costs once it reaches users, so the cheaper control-off figures leave out the price of what they let through.</p>",
      "</figure>",
      "</div>",
      "<section class='block section-block' data-section='breaks' aria-labelledby='l7-breaks'>",
      "<h2 class='h2' id='l7-breaks' tabindex='-1'>Where the analogy breaks</h2>",
      "<ul class='dash-list'>",
      "<li>Infrastructure cost is predictable per resource; agent cost varies with task difficulty and failure loops.</li>",
      "</ul>",
      "</section>",
      "<section class='block section-block' data-section='further' aria-labelledby='l7-further'>",
      "<h2 class='h2' id='l7-further' tabindex='-1'>Going further</h2>",
      "<p class='para'>Estimate cost per verified, merged change rather than per agent run: wasted runs, failed verifications and duplicates are all cost. The table above shows the shape in miniature: gates shift spending from rework to checks.</p>",
      "<details class='limits' data-depth-open='deep'>",
      "<summary>Limits of the evidence · 3</summary>",
      "<ul class='limits__list'>",
      "<li>The model release and its price are dated, and she hedged them herself. The <a href='https://docs.x.ai/build/overview' rel='noreferrer'>Grok Build overview ↗</a>, docs.x.ai, retrieved 11 October 2026, names grok-4.7 as the latest model and gives no prices, so her pricing remark stays as she said it. Its install uses a piped download script, which this guide’s lab deliberately avoids.</li>",
      "<li>One phrase near the end of note 2’s stretch is unclear in the recording, and we do not interpret it.</li>",
      "<li>An on-screen caption calls her a software engineer at SpaceXAI; in speech she says she joined Cursor about five months earlier and works at an AI lab. We report both and do not resolve her role or employer.</li>",
      "</ul>",
      "</details>",
      "</section>",
      "<section class='block section-block' data-section='check' aria-labelledby='l7-check'>",
      "<h2 class='h2' id='l7-check' tabindex='-1'>Check yourself</h2>",
      "<form class='quiz' data-lesson-quiz='l7-cost-and-adoption:0' novalidate>",
      "<fieldset class='choices'>",
      "<legend>Which context does the speaker give about her token use?</legend>",
      "<label class='choice'><input type='radio' name='q-l7-cost-and-adoption-0' value='0' /><span>Strictly budgeted<span class='choice__verdict'></span></span></label>",
      "<label class='choice'><input type='radio' name='q-l7-cost-and-adoption-0' value='1' /><span>Effectively unlimited, so not a template to copy exactly<span class='choice__verdict'></span></span></label>",
      "<label class='choice'><input type='radio' name='q-l7-cost-and-adoption-0' value='2' /><span>Free for everyone<span class='choice__verdict'></span></span></label>",
      "<label class='choice'><input type='radio' name='q-l7-cost-and-adoption-0' value='3' /><span>Not mentioned<span class='choice__verdict'></span></span></label>",
      "</fieldset>",
      "<div class='quiz__actions'><button class='btn' type='submit'>Check</button></div>",
      "<div class='quiz__feedback' role='status'></div>",
      "</form>",
      "</section>",
      "<section class='block section-block' data-section='rehearse' aria-labelledby='l7-rehearse'>",
      "<h2 class='h2' id='l7-rehearse' tabindex='-1'>Rehearse it</h2>",
      "<div class='rehearse__line'><pre><code>PROMOTION: git diff main promote -- contains only promotion.json</code></pre></div>",
      "<p class='para'><strong>Lab step 7 · Rehearse the promotion boundary · 8 min.</strong> The script commits only promotion.json on a separate branch and proves it is the only difference from main: source and activation never travel together. This is the boundary that stays human however far you climb.</p>",
      "<a class='btn' href='#lab/lab-6-promotion'>Open lab step 7</a>",
      "</section>",
      "<section class='block section-block adopt' data-section='adopt' aria-labelledby='l7-adopt'>",
      "<h2 class='h2' id='l7-adopt' tabindex='-1'>Your adoption decision</h2>",
      "<p class='para adopt__intro'>Answer these for your own setup before you add a single agent. Your answers stay in this browser. Download them as Markdown, or move them with your progress in Settings.</p>",
      "<ol class='adopt__list'>",
      "<li class='adopt__item'><label class='adopt__prompt' for='adopt-0'><span class='adopt__num' aria-hidden='true'>1</span>Which agent tasks will require attached verification evidence, and what counts as evidence for each?</label><p class='adopt__from meta' id='adopt-0-from'>From <a href='#lesson/l2-verification'>lesson 2</a> · Verify</p><textarea class='adopt__field' id='adopt-0' data-adoption='0' rows='3' aria-describedby='adopt-0-from'></textarea></li>",
      "<li class='adopt__item'><label class='adopt__prompt' for='adopt-1'><span class='adopt__num' aria-hidden='true'>2</span>Which review comments have I written more than twice, and what check will replace each one?</label><p class='adopt__from meta' id='adopt-1-from'>From <a href='#lesson/l5-agent-friendly-architecture'>lesson 5</a> · Checks</p><textarea class='adopt__field' id='adopt-1' data-adoption='1' rows='3' aria-describedby='adopt-1-from'></textarea></li>",
      "<li class='adopt__item'><label class='adopt__prompt' for='adopt-2'><span class='adopt__num' aria-hidden='true'>3</span>Which invariant will I make impossible by construction first?</label><p class='adopt__from meta' id='adopt-2-from'>From <a href='#lesson/l5-agent-friendly-architecture'>lesson 5</a> · Checks</p><textarea class='adopt__field' id='adopt-2' data-adoption='2' rows='3' aria-describedby='adopt-2-from'></textarea></li>",
      "<li class='adopt__item'><label class='adopt__prompt' for='adopt-3'><span class='adopt__num' aria-hidden='true'>4</span>How will each agent get an isolated workspace, and how are tasks claimed so a retry cannot duplicate work?</label><p class='adopt__from meta' id='adopt-3-from'>From <a href='#lesson/l6-fleet-operations'>lesson 6</a> · Claim · Worktree</p><textarea class='adopt__field' id='adopt-3' data-adoption='3' rows='3' aria-describedby='adopt-3-from'></textarea></li>",
      "<li class='adopt__item'><label class='adopt__prompt' for='adopt-4'><span class='adopt__num' aria-hidden='true'>5</span>Which credentials, contexts and networks must an agent never see? How do I prove they cannot?</label><p class='adopt__from meta' id='adopt-4-from'>From <a href='#lesson/l6-fleet-operations'>lesson 6</a> · Worktree</p><textarea class='adopt__field' id='adopt-4' data-adoption='4' rows='3' aria-describedby='adopt-4-from'></textarea></li>",
      "<li class='adopt__item'><label class='adopt__prompt' for='adopt-5'><span class='adopt__num' aria-hidden='true'>6</span>Where does agent autonomy stop: branch, PR, merge, or never beyond PR? Why?</label><p class='adopt__from meta' id='adopt-5-from'>From <a href='#lesson/l1-trust-curve'>lesson 1</a> · Merge</p><textarea class='adopt__field' id='adopt-5' data-adoption='5' rows='3' aria-describedby='adopt-5-from'></textarea></li>",
      "<li class='adopt__item'><label class='adopt__prompt' for='adopt-6'><span class='adopt__num' aria-hidden='true'>7</span>The digest promotion stays human. Who approves it, and what must they check?</label><p class='adopt__from meta' id='adopt-6-from'>From <a href='#lesson/l6-fleet-operations'>lesson 6</a> · Promote</p><textarea class='adopt__field' id='adopt-6' data-adoption='6' rows='3' aria-describedby='adopt-6-from'></textarea></li>",
      "<li class='adopt__item'><label class='adopt__prompt' for='adopt-7'><span class='adopt__num' aria-hidden='true'>8</span>How will I measure escaped defects, for example reverts per landed change, before raising agent count?</label><p class='adopt__from meta' id='adopt-7-from'>From <a href='#lesson/l1-trust-curve'>lesson 1</a> · Review</p><textarea class='adopt__field' id='adopt-7' data-adoption='7' rows='3' aria-describedby='adopt-7-from'></textarea></li>",
      "<li class='adopt__item'><label class='adopt__prompt' for='adopt-8'><span class='adopt__num' aria-hidden='true'>9</span>What is my monthly token budget, and what cost per verified merged change is acceptable?</label><p class='adopt__from meta' id='adopt-8-from'>From this lesson · the whole path</p><textarea class='adopt__field' id='adopt-8' data-adoption='8' rows='3' aria-describedby='adopt-8-from'></textarea></li>",
      "<li class='adopt__item'><label class='adopt__prompt' for='adopt-9'><span class='adopt__num' aria-hidden='true'>10</span>When I change a skill or model, what eval or rerun confirms behaviour did not regress?</label><p class='adopt__from meta' id='adopt-9-from'>From <a href='#lesson/l4-pstack-evals'>lesson 4</a> · Agent</p><textarea class='adopt__field' id='adopt-9' data-adoption='9' rows='3' aria-describedby='adopt-9-from'></textarea></li>",
      "</ol>",
      "<div class='adopt__actions'><button class='btn' type='button' data-adoption-export>Download as Markdown</button><p class='adopt__status meta' role='status' data-adoption-status></p></div>",
      "</section>",
      "<div class='lesson-end'>",
      "<div class='lesson-end__finish'><button class='btn finish' type='button' aria-pressed='false' data-finish='l7-cost-and-adoption'><span class='finish__mark' aria-hidden='true'></span><span data-finish-label>Mark lesson as finished</span></button><p class='lesson-end__progress meta' data-progress-count hidden></p></div>",
      "<nav class='lesson-end__nav' aria-label='Lesson navigation'>",
      "<a class='next' href='#lab'><span class='next__label'>Next · On your machine · about 50 min</span><span class='next__title'>The offline lab<span class='next__arrow' aria-hidden='true'>→</span></span></a>",
      "<a class='prev' href='#lesson/l6-fleet-operations'>Previous: Start local, then scale on signals</a>",
      "</nav>",
      "</div>"
    ],
    "notes": [
      {
        "n": 1,
        "source": "l7-cost-and-adoption:0",
        "kind": "said",
        "time": "49:33",
        "range": "49:33–49:52",
        "panelKind": "Our paraphrase · said at 49:33",
        "paraphrase": "She has effectively unlimited tokens at work and cautions against copying her approach exactly.",
        "evidence": {
          "start": 2973.8,
          "end": 2992.4,
          "label": "SAID"
        }
      },
      {
        "n": 2,
        "source": "l7-cost-and-adoption:1",
        "kind": "said-long",
        "time": "50:00–52:06",
        "range": "50:00–52:06",
        "panelKind": "A longer stretch · said from 50:00 to 52:06",
        "paraphrase": "Up-front token spend is an ROI decision that lets weaker agents and fewer people do good work.",
        "evidence": {
          "start": 3000.3,
          "end": 3126.8,
          "label": "SAID"
        }
      },
      {
        "n": 3,
        "source": "l7-cost-and-adoption:3",
        "kind": "said-long",
        "time": "54:31–56:42",
        "range": "54:31–56:42",
        "panelKind": "A longer stretch · said from 54:31 to 56:42",
        "paraphrase": "Non-engineers ship fixes via Grok Bot, which she attributes to the strict architecture.",
        "paraphraseNormalisation": "Grokbot in the source paraphrase is set in the authored docs spelling, Grok Bot (contentCautions).",
        "evidence": {
          "start": 3271.0,
          "end": 3402.4,
          "label": "SAID"
        }
      },
      {
        "n": 4,
        "source": "l7-cost-and-adoption:2",
        "kind": "said",
        "time": "52:29",
        "range": "52:29–53:12",
        "panelKind": "Our paraphrase · said at 52:29",
        "paraphrase": "A model release announced in the session; she hedges the pricing statement.",
        "evidence": {
          "start": 3149.5,
          "end": 3192.6,
          "label": "SAID"
        }
      }
    ],
    "checks": [
      {
        "index": 0,
        "question": "Which context does the speaker give about her token use?",
        "options": [
          "Strictly budgeted",
          "Effectively unlimited, so not a template to copy exactly",
          "Free for everyone",
          "Not mentioned"
        ],
        "answer": 1,
        "explanationHtml": "She says she works at an AI lab with effectively unlimited tokens, so her approach should not be copied wholesale, though she thinks it can be done without breaking the bank. She says so at <button class='time-link' type='button' data-lesson-source='l7-cost-and-adoption:0' aria-label='Note 1, said at 49:33'>49:33</button>.",
        "status": "question, options and answer verbatim; explanation rewritten without the numeric range"
      }
    ],
    "practice": [],
    "lab": {
      "step": "lab-6-promotion",
      "n": 7,
      "title": "Rehearse the promotion boundary",
      "minutes": 8,
      "outputLine": "PROMOTION: git diff main promote -- contains only promotion.json"
    },
    "supplements": {
      "basics": "The original basics paragraph retained verbatim.",
      "deep": "The original deep paragraph retained in Going further, its last sentence pointing at the cost table instead of the simulator in general. Limits of the evidence holds the dated release and docs entry, the unclear phrase and the role conflict.",
      "practitioner": "All three original paragraphs retained in substance; the third becomes the ordered adoption list, and the cost table is the lesson’s figure. Numeric ranges removed."
    },
    "end": {
      "next": {
        "href": "#lab",
        "label": "Next · On your machine · about 50 min",
        "title": "The offline lab"
      },
      "previous": {
        "href": "#lesson/l6-fleet-operations",
        "text": "Previous: Start local, then scale on signals"
      }
    }
  }
};
