# Live TV commands

`make live-tv LIVE_TV_ENABLED=true LIVE_TV_REVISION=<pushed-revision>` runs the existing Ansible role after the full deployment check. Enabling it first reconciles Authentik at the same revision. The default remains disabled; use the existing retirement procedure deliberately.

`make check APP=live-tv` checks the role behavior. This folder owns commands only. Application definitions and ownership remain in their existing locations. See [the live TV runbook](../../roles/apps/live_tv/README.md). Unsupported operations report `unknown` with a cause.
