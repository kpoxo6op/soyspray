# Ask an agent

You do not need to translate a question into Kubernetes commands. Ask for the
outcome and require current evidence.

## Useful requests

- “Check the cluster and explain anything that needs attention.”
- “Is Vaultwarden healthy, backed up, and recently restore-tested?”
- “Explain how Immich works in plain language, then show the authoritative
  repository folders.”
- “Prepare a pull request for this change. Do not deploy or merge it.”
- “Show what would change before running this operation.”
- “Update the human guide and technical README with this change.”

## What an answer should contain

An agent should lead with the result, name the live or repository evidence it
checked, and separate facts from unknowns. It should state any action that still
needs confirmation.

For a change, the agent should use a branch and pull request, run the maintained
checks, preserve data and ownership boundaries, and update the affected human
and technical documentation together.

For destructive work, the agent must resolve the exact target, check current
backup and recovery evidence, and follow the maintained operation. General
permission to inspect the system is not permission to delete or rebuild it.

