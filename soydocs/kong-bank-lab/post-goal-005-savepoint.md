# Post Goal 005 Save Point

After `goal-004-auth-rate-limit-security` and
`goal-005-tenancy-rbac-change-control` are implemented, validated, pushed, and
approved by ChatGPT Pro, stop the current long-running conversation loop and
create a fresh-context handoff before starting `goal-006-keycloak-sso-platform-tools`.

Required save point:

- Current branch and latest commit.
- Goal 004 body path, evidence path, validation status, runtime status, and Pro approval status.
- Goal 005 body path, evidence path, validation status, runtime status, and Pro approval status.
- Any corrections Pro asked to carry into goal 006.
- Explicit list of commands that passed for goals 004 and 005.
- Explicit list of cluster mutations performed for goals 004 and 005.
- Current stop condition and whether goal 006 is allowed to start.
- Pointers to the authoritative repo files for continuing from a fresh Codex chat.

ChatGPT Pro must also be asked to create its own wrap-up/save point after goal
005 is approved, so a fresh Pro chat can continue from goal 006 without relying
on the old conversation context.

Do not start goal 006 in the old long conversation unless the user explicitly
overrides this save-point rule.
