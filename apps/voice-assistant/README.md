# Voice commands

`make voice-assistant VOICE_ASSISTANT_REVISION=<pushed-revision>` runs the existing Ansible role after the full deployment check. `VOICE_ASSISTANT_ENABLED` remains true by default.

Use `make voice-pe-render`, `voice-pe-check`, or `voice-pe-compile` for firmware preparation. `make voice-pe-upload VOICE_PE_HOST=<device>` runs the deployment check, renders, validates, compiles, and uploads the firmware. Use the root commands for deployment and upload so their checks run.

`make check APP=voice-assistant` checks voice configuration behavior. This folder owns commands only; it does not migrate application ownership. See [the voice runbook](../../playbooks/argocd/applications/home-automation/voice-assistant/README.md). Unsupported operations report `unknown` with a cause.
