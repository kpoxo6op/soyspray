# GI Flex intent agent

This Home Assistant conversation integration interprets unfamiliar English light
commands through one non-thinking DeepSeek Flash request. HA handles known
commands first when the pipeline prefers local intents. The integration never
changes a pipeline, satellite selection, room, alias or exposure automatically.

The explicit allowlist is intersected with current Assist exposure. Only
HassTurnOn, HassTurnOff and absolute HassLightSet requests are supported.
Names must be unique among exposed lights, and exposure is checked again after
the provider returns. Unsupported, malformed, truncated, negated, delayed or
risky commands do not execute. A clarification can continue for one turn.
Provider timeout is 2.5 seconds without a retry. Replies describe HA
successes and failures, including partially completed requests. No arbitrary services, toggles, scripts, state values or non-light
entities are sent to or accepted from the provider.

The API key enters a supported HA config flow from private Vault inputs. It is
kept in the HA config entry and existing protected PVC, never in an image or
public Git. `gi_voice.audit.*` is bounded private HA Store data used to assess
latency and recurring paraphrases; it contains transcripts. The audit text and config-entry API key are included in HA volume backups.
The current S3 store encrypts objects at rest with AES256; authorized backup
readers can still read their contents. Removing the integration deletes its
current audit through HA Store and cancels pending saves. Historical backups
remain under the backup tool's existing retention. Diagnostics redact
transcripts and credentials. No microphone recording is performed here.

## Checks and release

Use Python 3.14.2 and the pinned HA 2026.5.4 test environment:

```sh
python -m pip install -r apps/voice-assistant/intent-agent/requirements-tests.txt
python -m pytest -c apps/voice-assistant/intent-agent/pytest.ini \
  -q apps/voice-assistant/intent-agent/tests
```

The real HA loader/conversation tests protect single-call routing, restricted
execution, exposure revocation during inference, duplicate names, malformed or
truncated replies, bounded clarification, provider failure and private diagnostics.
The existing voice manifest tests do not run an HA integration or a provider
request. Installer tests protect unrelated/private files, a failed replacement,
and symlink refusal; the existing installers do not own this component path.
The native intent test observes the actual HA light-service dispatch without
controlling a physical device.

`gi-voice-image.yml` tests and publishes an immutable source bundle after merge.
A source-only merge changes no live code. A separate promotion must reference its
tested GHCR digest in an HA init container mounting only the existing config PVC.
The installer replaces only `custom_components/gi_voice` and retains the previous
component under `/config/.gi_voice/previous`, outside HA integration discovery.
Installation failure preserves existing files and allows HA to start; verify
`/config/.gi_voice/installed.json` against the promoted source revision. No runtime dependency installation is needed.

Before promotion, prove a completed HA backup and isolated restore, export
pipeline/satellite/exposure/alias settings through supported APIs, and check the
native local intent behavior for generic and negated commands. Configure a
parallel GI Flex pipeline; preserve GI, Speech-to-Phrase, GI wake/firmware,
identities and data. Flexible spoken commands need an open-vocabulary STT engine;
adding this integration after Speech-to-Phrase cannot recover rejected speech.
Synthetic/text tests do not prove real Voice PE recognition or latency. Select
the new satellite pipeline only after its gates and user acceptance are met.

Rollback: reselect GI, remove the new config entry, and revert the promoted
installer digest. Restore settings through the supported HA API; never edit
`.storage`. The private audit is disposable and never replayed as a command.
Repeated successful unmatched commands can justify a separately tested exact
interpretation cache. No fuzzy cache, learned mapping or Jev provider is enabled
by this source package.

The guarded `check-ha-voice-installer.yml` operation runs only inside an existing
isolated Home Assistant restore. It checks scratch ownership, separate volume
identity and deny-all network policy before installing PR source twice with HA
UID/GID, resolving one custom integration and exercising saved GI intent handling.
It does not boot device integrations or prove microphone/cloud execution. Use the
shared restore runner for namespace/PVC cleanup; never target production.
