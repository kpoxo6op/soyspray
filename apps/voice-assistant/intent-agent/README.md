# GI voice agents

GI Everyday adds exact local sentences for lights, Android TV, catalog channels and
Dreame room cleaning. Its device catalog comes from current Assist exposure and
HA areas. It chooses one matching device in the satellite room, or the only
matching exposed device elsewhere. Ambiguity asks for a name or room and never
broadcasts. App launch packages are fixed; device IDs are not. Vacuum segment
names are resolved in the selected map. A sleeping TV uses the MAC from its HA
device registry for Wake-on-LAN, then refreshes its ADB connection. Set
`GI_VOICE_BROADCAST_ADDRESS` to the LAN broadcast when HA runs behind a pod network.
No TV address or MAC is built into command code. The original GI and GI Flex remain
separate pipelines.

The `GiControl` intent script calls a bounded local service. Negation, future
requests and reported speech decline before interpretation. Bare pronouns have
their own non-action sentences. GI Everyday must have **prefer local intents
disabled**, so its guard sees every transcript before any action. Its STT streams to local open speech recognition, retaining negation and future
qualifiers that constrained decoding can discard. Exact recognized commands use
the local sentence matcher, including numeric percentage notation such as `30%`.
Turns with no successful transcript retry the same bounded audio with
`stt.gi_whisper`, then optionally cloud speech. A nonempty open transcript goes
to interpretation unchanged; unfamiliar wording is not evidence that a second
English decoder would be more accurate. The Whisper service refreshes its
vocabulary from HA exposure; no device list is built into the recognizer.
Everyday cloud audio stays off unless explicitly enabled. Real microphone tests
are required; neither recognition nor a wake word authenticates the speaker.

Speech-to-Phrase and the promoted custom sentence bundle remain available for
comparison, but are not trusted as the first action-producing recognizer after
acoustic tests showed dropped negation and changed on/off words.

`phrase_server.py` uses pinned Speech-to-Phrase 1.4.3. It checks the upstream
handler checksum, serializes turns against vocabulary replacement, closes an old
cached decoder before training a changed vocabulary, and retains a warm decoder
when the vocabulary agrees. Training happens on connection, not during an active
turn. New exposed devices are picked up without a code change.

Unmatched text gets one bounded DeepSeek interpretation. A successful action
produces a private audit record. After observing the real device, export that
record with `verified: true` and compile its exact wording offline:

```sh
python apps/voice-assistant/intent-agent/learn.py --receipt /private/verified.json \
  --output apps/voice-assistant/intent-agent/custom_components/gi_voice/sentences/en/gi_learned.yaml
```

Use the HA test environment for this command. Review the sentence diff, merge its
source PR, then promote the new image digest to both HA and Speech-to-Phrase.
No runtime code change or LLM call is needed for the learned wording. Rejected,
failed and unverified records cannot be compiled. Repeated sentences with a
different action fail rather than overwrite. Never commit private audit files.

Configure a parallel **GI Everyday** pipeline with `conversation.gi_everyday`,
`stt.gi_everyday_speech`, existing GI wake and Piper, and local-intent preference
off. Select it on the Voice PE only after real-device checks. Set the preferred
pipeline to it for phone Assist; a second satellite supplies its HA room normally.
Rollback is selecting **GI** in the Voice PE Assistant selector (and preferred
pipeline for the phone). Binary rollback reverts the HA/STP promotion digest.

## Original GI Flex


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
local. With cloud speech explicitly enabled, all other post-wake audio gets one OpenAI
`gpt-transcribe` retry using that same audio and the measured fixed name prompt.
This is an exact phrase gate, not Home Assistant intent matching. No fuzzy name
repair or cross-turn audio lookup is used. The conversation agent is unchanged.

Cloud speech is **off by default**. In GI Flex's integration options, select the
existing Parakeet STT entity and enter the OpenAI API key. The options form checks
model access without sending audio. Enable cloud only after the owner agrees
that all non-exact post-wake speech, other requests, clarification replies, other
household voices and false-wake background speech may go to OpenAI. Polite variants
and spelled-out numbers can also take this route. Selecting this STT entity in GI
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
interpretation cache. GI Flex has no fuzzy cache or learned mapping. GI Everyday uses only the
reviewed exact sentence file described above. Jev is not enabled.

The guarded `check-ha-voice-installer.yml` operation runs only inside an existing
isolated Home Assistant restore. It checks scratch ownership, separate volume
identity and deny-all network policy before installing PR source twice with HA
UID/GID, resolving one custom integration and exercising saved GI intent handling.
It does not boot device integrations or prove microphone/cloud execution. Use the
shared restore runner for namespace/PVC cleanup; never target production.
