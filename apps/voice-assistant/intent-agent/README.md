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

During the next English turn of a live clarification, an exact current light
name can complete a canonical `turn`/`switch` on/off request without another
provider call. This covers pronouns and generic light requests, with one leading
or trailing `please`. Names use Unicode normalization, case and punctuation;
aliases, rooms, floors, reserved words and conflicting exposed names decline
the shortcut. Other replies retain the existing provider path. A native-handled
or unrelated intervening turn invalidates the original clarification, as do
expiry and a different conversation, satellite or user. The local route records
`exact_clarification` and zero provider calls in the existing private audit.
It does not repair speech recognition or complete an unknown first target name.

## Optional speech retry

`stt.gi_flex_speech` buffers each turn separately in memory, then uses the selected
local recognizer. Exact on/off, absolute brightness and bare-name phrases stay
local. With cloud speech explicitly enabled, other text gets one OpenAI
`gpt-transcribe` retry using that same audio and the measured fixed name prompt.
This is an exact phrase gate, not Home Assistant intent matching. No fuzzy name
repair or cross-turn audio lookup is used. The conversation agent is unchanged.

Cloud speech is **off by default**. In GI Flex's integration options, select the
existing Parakeet STT entity and enter the OpenAI API key. The options form checks
model access without sending audio. Enable cloud only after the owner agrees
that unclear post-wake speech, clarification replies, other household voices and
false-wake background speech may go to OpenAI. Selecting this STT entity in GI
Flex is a separate supported pipeline update; original GI stays available.

Each buffer is limited to 20 seconds of 16 kHz mono PCM; at most two turns can be
active. Local decoding has a five-second deadline and the cloud request has a
three-second deadline with no retry or redirect. A cloud error or empty response
returns the local result; failure of both decoders reports an STT error. Changed
exposure or names disable cloud retries until the measured catalog is restored.
Disabling cloud reloads the integration and cancels its active audio requests.

The speech component writes no audio files and logs only route and elapsed time
at debug level. Existing Home Assistant pipeline history and the conversation
audit still contain transcripts. The key is stored in HA's supported config
entry options and protected volume backups. It never enters Git, an image or CI.
Revoke cloud access through the options switch or select original GI. A speaker
replay can verify the acoustic path; it is not proof of natural household use.

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

Speech tests use the real HA loader and STT entry point. They cover exact routing
without losing negation/future qualifiers, the actual multipart WAV sent to a
local HTTP server, one-request fallback on provider failures, a real deadline,
audio limits, unload cancellation, disabled/revoked exposure and private logging.
These catch wrong-audio uploads, accidental cloud use and stalled commands;
the conversation and installer tests do not own the audio boundary. Options-flow
coverage verifies explicit enablement, non-audio key validation and key retention.

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
