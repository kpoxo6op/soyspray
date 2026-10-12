// Presentation labels and placements from the Opus design reference.
// Outcomes and event schedules come exclusively from simulator.js.
export const scenarioPresentation = {
    "s1-shared-vs-isolated": {
        "lesson": [
            "Lesson 6",
            "Start local, then scale on signals",
            "#lesson/l6-fleet-operations"
        ],
        "station": "Worktree",
        "title": "Two agents, one file",
        "setup": "Agents A and B both edit config line 1 in a shared working tree.",
        "question": "What happens to A’s change?",
        "choices": [
            "Git stops B with a merge conflict",
            "CI rejects both edits before they merge",
            "A’s edit is silently overwritten by B",
            "Both edits are kept and merge cleanly"
        ],
        "answer": 2,
        "predictOn": "off",
        "explanation": "In a shared tree the last writer wins with no signal. With per-agent worktrees the same edits surface as a merge conflict at integration, where a reviewer sees them.",
        "control": {
            "legend": "Workspace",
            "off": "Shared tree",
            "on": "Worktrees",
            "colOff": "Shared tree",
            "colOn": "Worktrees",
            "hint": "Now give each agent its own worktree and run again."
        },
        "stations": [
            "Edit",
            "Write",
            "Integrate",
            "Main"
        ],
        "sub": {
            "off": {
                "1": "shared tree",
                "2": "no merge"
            },
            "on": {
                "1": "own worktree"
            }
        },
        "bypass": {
            "off": [
                2
            ],
            "on": []
        },
        "lanes": [
            [
                "T1",
                "A"
            ],
            [
                "T2",
                "B"
            ]
        ],
        "placements": {
            "off": {
                "started": {
                    "lane": "$task",
                    "x": 0
                },
                "written": {
                    "lane": "$task",
                    "x": 1,
                    "m": "written"
                },
                "lost_update": {
                    "lane": "$task",
                    "x": 1,
                    "s": "lost",
                    "m": "lost"
                },
                "merged": {
                    "lane": "$task",
                    "x": 3,
                    "s": "done",
                    "m": "merged"
                }
            },
            "on": {
                "started": {
                    "lane": "$task",
                    "x": 0
                },
                "written": {
                    "lane": "$task",
                    "x": 1,
                    "m": "committed"
                },
                "merged": {
                    "lane": "$task",
                    "x": 3,
                    "s": "done",
                    "m": "merged",
                    "pass": [
                        2
                    ]
                },
                "merge_conflict": {
                    "lane": "$task",
                    "x": 2,
                    "s": "caught",
                    "m": "conflict"
                }
            }
        },
        "comparisonLabels": [
            "Edits on main",
            "Edits lost without a signal",
            "Conflicts shown to a reviewer",
            "Cost, abstract units"
        ]
    },
    "s2-plausible-vs-verified": {
        "lesson": [
            "Lesson 2",
            "Verification closes the loop",
            "#lesson/l2-verification"
        ],
        "station": "Verify",
        "title": "Done, or verified?",
        "setup": "Three agent reports say “fixed”. One change does not fix the symptom.",
        "question": "With the verification gate off, how many fixes reach main?",
        "choices": [
            "None until someone checks them",
            "One, the others are still running",
            "Two, only the real fixes",
            "Three, including the non-fix"
        ],
        "answer": 3,
        "predictOn": "off",
        "explanation": "Without a probe that reproduces the symptom, self-reports are accepted. With the gate on, task T3 fails reproduction-after and returns to the queue. Illustrative outcome, not a measured rate.",
        "control": {
            "legend": "Verification gate",
            "off": "Off",
            "on": "On",
            "colOff": "Gate off",
            "colOn": "Gate on",
            "hint": "Now switch the verification gate on and run again."
        },
        "stations": [
            "Agent",
            "Says done",
            "Verify",
            "Main"
        ],
        "sub": {
            "off": {
                "2": "gate off"
            },
            "on": {}
        },
        "bypass": {
            "off": [
                2
            ],
            "on": []
        },
        "lanes": [
            [
                "T1",
                "T1"
            ],
            [
                "T2",
                "T2"
            ],
            [
                "T3",
                "T3"
            ]
        ],
        "placements": {
            "off": {
                "started": {
                    "lane": "$task",
                    "x": 0
                },
                "reported_done": {
                    "lane": "$task",
                    "x": 1,
                    "m": "“fixed”"
                },
                "accepted": {
                    "lane": "$task",
                    "x": 3,
                    "s": "done",
                    "m": "merged"
                },
                "defect_in_main": {
                    "lane": "$task",
                    "x": 3,
                    "s": "defect",
                    "m": "defect"
                }
            },
            "on": {
                "started": {
                    "lane": "$task",
                    "x": 0
                },
                "reported_done": {
                    "lane": "$task",
                    "x": 1,
                    "m": "“fixed”"
                },
                "verify_pass": {
                    "lane": "$task",
                    "x": 3,
                    "s": "done",
                    "m": "verified",
                    "pass": [
                        2
                    ]
                },
                "verify_fail": {
                    "lane": "$task",
                    "x": 2,
                    "s": "caught",
                    "m": "caught"
                },
                "retry_pending": {
                    "lane": "$task",
                    "x": 0,
                    "s": "pending",
                    "m": "queued"
                }
            }
        },
        "comparisonLabels": [
            "Changes on main",
            "Defects on main",
            "Back in the queue",
            "Cost, abstract units"
        ]
    },
    "s3-review-backlog": {
        "lesson": [
            "Lesson 1",
            "Trust is the throttle on parallelism",
            "#lesson/l1-trust-curve"
        ],
        "station": "Review",
        "title": "The reviewer is the bottleneck",
        "setup": "Each agent opens three PRs at once, and one reviewer clears two per tick. One PR in three has a fault a hard check would catch.",
        "question": "With hard checks on, what changes?",
        "choices": [
            "The review queue shrinks because checks reject faulty PRs first",
            "Nothing changes, since the reviewer still has to read every one",
            "The queue grows, because every PR now has to wait for checks",
            "Agents work faster, so their PRs reach review sooner"
        ],
        "answer": 0,
        "predictOn": "both",
        "explanation": "Adding agents without automated gates only grows the human queue. Hard checks reject the scripted faulty PRs before review, and the more agents you run, the more they save.",
        "control": {
            "legend": "Hard checks",
            "off": "Off",
            "on": "On",
            "colOff": "Checks off",
            "colOn": "Checks on",
            "hint": "Now switch hard checks on and run again."
        },
        "queue": true,
        "placements": {}
    },
    "s4-naive-retry": {
        "lesson": [
            "Lesson 6",
            "Start local, then scale on signals",
            "#lesson/l6-fleet-operations"
        ],
        "station": "Claim",
        "title": "Retry without a claim",
        "setup": "A bug report is delivered twice after a timeout.",
        "question": "With naive retry, how many PRs appear?",
        "choices": [
            "One, the retry is skipped",
            "Two duplicates",
            "One PR with two commits",
            "None, both time out"
        ],
        "answer": 1,
        "predictOn": "off",
        "explanation": "Each delivery spawns its own agent and branch. With an atomic claim keyed by report ID, the second delivery logs skip_already_claimed.",
        "control": {
            "legend": "Retry",
            "off": "Naive",
            "on": "Atomic claim",
            "colOff": "Naive retry",
            "colOn": "Atomic claim",
            "hint": "Now claim the report atomically and run again."
        },
        "stations": [
            "Delivered",
            "Claim",
            "Agent",
            "PR"
        ],
        "sub": {
            "off": {
                "1": "no claim"
            },
            "on": {}
        },
        "bypass": {
            "off": [
                1
            ],
            "on": []
        },
        "lanes": [
            [
                "first",
                "1st"
            ],
            [
                "second",
                "2nd"
            ]
        ],
        "placements": {
            "off": {
                "delivery": {
                    "lane": "first",
                    "x": 0,
                    "m": "R7"
                },
                "started": {
                    "lane": "first",
                    "x": 2,
                    "m": "agent"
                },
                "redelivery": {
                    "lane": "second",
                    "x": 0,
                    "m": "R7 again"
                },
                "duplicate_started": {
                    "lane": "second",
                    "x": 2,
                    "m": "agent"
                },
                "ready": {
                    "lane": "first",
                    "x": 3,
                    "s": "done",
                    "m": "PR-a"
                },
                "duplicate_pr": {
                    "lane": "second",
                    "x": 3,
                    "s": "defect",
                    "m": "duplicate"
                }
            },
            "on": {
                "delivery": {
                    "lane": "first",
                    "x": 0,
                    "m": "R7"
                },
                "claim": {
                    "lane": "first",
                    "x": 1,
                    "m": "claimed"
                },
                "redelivery": {
                    "lane": "second",
                    "x": 0,
                    "m": "R7 again"
                },
                "skip_already_claimed": {
                    "lane": "second",
                    "x": 1,
                    "s": "stopped",
                    "m": "skipped"
                },
                "ready": {
                    "lane": "first",
                    "x": 3,
                    "s": "done",
                    "m": "PR-a",
                    "pass": [
                        1
                    ]
                }
            }
        },
        "comparisonLabels": [
            "PRs opened for report R7",
            "Wasted cost units",
            "Cost, abstract units"
        ]
    },
    "s5-architecture-gate": {
        "lesson": [
            "Lesson 5",
            "Make the shortest path the right path",
            "#lesson/l5-agent-friendly-architecture"
        ],
        "station": "Checks",
        "title": "The shortcut import",
        "setup": "An agent’s quickest fix imports heavy main-process code into the renderer.",
        "question": "With the boundary check on, where is it caught?",
        "choices": [
            "In production, by a user",
            "At review, if the reviewer notices",
            "At CI, before review",
            "In the agent’s own test run"
        ],
        "answer": 2,
        "predictOn": "on",
        "explanation": "Hard checks fail the build. With soft rules only, catching it depends on the reviewer; the scenario scripts the reviewer missing it, to illustrate the gap, not as a measured miss rate.",
        "control": {
            "legend": "Boundary",
            "off": "Soft rule",
            "on": "CI check",
            "colOff": "Soft rule",
            "colOn": "CI check",
            "hint": "Now replace the soft rule with a CI check and run again."
        },
        "stations": [
            "Agent",
            "CI check",
            "Review",
            "Main",
            "Users"
        ],
        "sub": {
            "off": {
                "1": "soft rule"
            },
            "on": {}
        },
        "bypass": {
            "off": [
                1
            ],
            "on": []
        },
        "lanes": [
            [
                "C1",
                "C1"
            ]
        ],
        "placements": {
            "off": {
                "shortcut_import": {
                    "lane": "$task",
                    "x": 0,
                    "m": "shortcut"
                },
                "soft_rule_ignored": {
                    "lane": "$task",
                    "x": 2,
                    "m": "reviewing"
                },
                "boundary_violation_in_main": {
                    "lane": "$task",
                    "x": 3,
                    "s": "defect",
                    "m": "violation"
                },
                "jank_report": {
                    "lane": "$task",
                    "x": 4,
                    "s": "defect",
                    "m": "jank"
                }
            },
            "on": {
                "shortcut_import": {
                    "lane": "$task",
                    "x": 0,
                    "m": "shortcut"
                },
                "ci_fail": {
                    "lane": "$task",
                    "x": 1,
                    "s": "caught",
                    "m": "blocked"
                },
                "revised": {
                    "lane": "$task",
                    "x": 2,
                    "m": "revised",
                    "pass": [
                        1
                    ]
                },
                "merged": {
                    "lane": "$task",
                    "x": 3,
                    "s": "done",
                    "m": "merged"
                }
            }
        },
        "comparisonLabels": [
            "Where the shortcut is caught",
            "Defects on main",
            "Detection delay, ticks",
            "Cost, abstract units"
        ]
    }
};
