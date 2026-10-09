# Home Assistant local GI voice control

This package provides local voice control for `light.top`, `light.middle`, and
`light.bottom`. The code defines `light.peanut` as a group that controls all
three lights.
Home Assistant Voice PE streams audio to Home Assistant.
Home Assistant uses these local Wyoming services:

- Speech-to-Phrase for speech-to-text.
- Piper for text-to-speech.
- An openWakeWord service that lists only the installed GI model. It checks the
  SHA-256 of `handler.py` before it applies our patch, and stops if it differs.

The services have no Ingress or LoadBalancer. Only Home Assistant can connect
to their Wyoming ports.

## Ownership and private data

Git stores the Kubernetes manifests, exact image and model checksums, the wake
handler patch, and these instructions.

Ansible creates two objects that do not belong in Git:

- `voice-assistant-ha-token`, which contains a dedicated Home Assistant token.
- An immutable ConfigMap that contains the private `gi.tflite` model.

Home Assistant stores Wyoming integrations, the GI Assist pipeline, Assist
exposure, device names, and Area assignments in its persistent `.storage`
data. Configure this state through the Home Assistant UI or supported API. Do
not edit `.storage` files.

Keep all voice recordings, packet captures, calculated audio data, model files,
and training output outside Git. [models/README.md](manifests/models) lists the
model names and checksums.

## Deployment

Create a dedicated Home Assistant administrator named `GI Speech`. Create one
long-lived token for Speech-to-Phrase. The pod needs administrator access to
read the Assist exposure list. Its network policy permits access only to Home
Assistant on TCP port `8123`.

The current private model file is:

```text
~/.config/soyspray/recovery/voice-models/gi-v7.tflite
```

Bootstrap private inputs only when the working tree is clean:

```bash
read -rsp 'Home Assistant voice token: ' VOICE_ASSISTANT_HA_TOKEN
export VOICE_ASSISTANT_HA_TOKEN
export VOICE_ASSISTANT_GI_MODEL_PATH="${HOME}/.config/soyspray/recovery/voice-models/gi-v7.tflite"
source soyspray-venv/bin/activate
make -f apps/voice-assistant/Makefile bootstrap
unset VOICE_ASSISTANT_HA_TOKEN VOICE_ASSISTANT_GI_MODEL_PATH
```

If the Secret and model ConfigMap already exist, leave both environment
variables empty. Ansible will reuse them.

The bootstrap Job downloads the expected Speech-to-Phrase and Piper models and
checks their SHA-256 values. Only that Job can use HTTPS to reach the internet.
During normal use, Speech-to-Phrase can reach Home Assistant. Piper and
openWakeWord cannot open outbound connections.

Verify the deployment:

```bash
kubectl get application -n argocd voice-assistant
kubectl wait -n home-automation --for=condition=complete   job/voice-model-bootstrap-v1 --timeout=30m
kubectl wait -n home-automation --for=condition=available   deployment/speech-to-phrase deployment/piper-en   deployment/openwakeword-gi --timeout=15m
kubectl get pod -n home-automation   -l 'app in (speech-to-phrase,piper-en,openwakeword-gi)'
```

Confirm that Argo CD shows the pushed revision and the `Synced` and `Healthy`
states. Confirm that every voice pod is Ready and has zero restarts.

## Home Assistant setup

The bootstrap configuration sets
`internal_url: http://192.168.20.33:8123`. Voice PE uses this LAN address for
audio. Do not use a pod address.

Add three Wyoming Protocol integrations:

| Service | Host | Port |
| --- | --- | --- |
| Speech-to-Phrase | `speech-to-phrase.home-automation.svc.cluster.local` | `10300` |
| Piper | `piper-en.home-automation.svc.cluster.local` | `10200` |
| openWakeWord | `openwakeword-gi` | `10400` |

Create an Assist pipeline named `GI` with these settings:

- Language: English.
- Conversation agent: Home Assistant.
- Speech-to-text: Speech-to-Phrase.
- Text-to-speech: Piper `en_US-lessac-medium`.
- Streaming wake word: `gi`.
- Prefer local intents: enabled.

Keep `light.top`, `light.middle`, `light.bottom`, and `light.peanut` exposed to
Assist. Use `turn on peanut` or `turn off peanut` to control all three lights.
Assign the Voice PE and the lights to the correct Area. Select the GI pipeline
for the satellite. The global preferred pipeline can remain different.

Adopt the Voice PE through ESPHome. Use host
`home-assistant-voice-0a9b95` and port `6053` if discovery does not find it.

## Voice PE firmware

The build script uses one exact Voice PE source commit. It removes `Okay Nabu`,
`Hey Jarvis`, and `Hey Mycroft`. It keeps the local Stop model for long replies
and timers. The device streams microphone audio while it waits for Home
Assistant to detect GI.

Render and compile the firmware:

```bash
make voice-pe-check
make voice-pe-compile
```

Upload only after `make voice-pe-check` and `make check` pass:

```bash
make voice-pe-upload
```

### Listening recovery and diagnostics

Every continuous-listening start now uses one queued stop/wait/start script.
The wait is bounded at five seconds. This prevents a start during a previous
stop from being silently discarded. The pinned ESPHome `on_start` callback
records Home Assistant's run acknowledgement.

The device supervisor waits three minutes after boot and 45 seconds after a
Home Assistant connection. It excludes mute, OTA, backend-error backoff,
normal interactions (up to two minutes), and announcements or timers (up to
15 minutes). While listening is expected, it retries a missing running state,
missing run acknowledgement, or stale microphone callbacks. Quiet audio counts
as progress. Shared-microphone recovery stops both listeners before restarting.
Two retries are separated by 30 seconds; failed stops or repeated failures can
request a native reboot. The device persists the reason and a three-reboot
budget, then stops automatic actions until 30 minutes of healthy listening.

Diagnostic entities expose expected listening, run acknowledgement, running
state, microphone frame age, stage, recovery reason/count, reboot budget and
exhaustion. Reason codes are `1` not running, `2` no acknowledgement, `3` stale
microphone, `4` stop timeout, `5` interaction timeout and `6` manual recovery.
The **Recover GI listening** button runs the same bounded soft recovery.
`GI_RECOVERY` logs contain only these codes and actions. Home Assistant records
the diagnostic entity changes; no audio, transcripts or audio levels are exported.

The microphone callback proves hardware progress, not delivery to Home
Assistant or GI. The diagnostics observer subscribes only to fixed numeric and
binary entities through the existing native API. It never subscribes to voice
audio or sends device commands. Its image is tested and published by
`voice-health-image.yml`; a separate digest promotion is required to deploy it.
Prometheus can compare expected listening with the GI pod's received-byte rate.
An absent diagnostics schema is unavailable evidence, not a healthy stream.

Run `pytest -q tests/test_voice_health.py` for executable recovery-policy and
HTTP export checks. They protect quiet/mute/OTA/backend guards, time limits,
clock wrap, retry/reboot bounds, and stale-state removal. The older renderer
checks do not execute the policy or exercise the exported HTTP boundary.

After native OTA, verify diagnostics and actual HA-to-GI audio flow, then run
the [bounded network operation](../../playbooks/operations/networking/README.md).
A real spoken command remains required to prove wake, action and reply.
Keep the prior compiled binary privately for native OTA rollback. Detection
and bounded recovery do not establish wake accuracy or a permanent root-cause
fix; an acoustic test and longer observation are still needed.

The firmware currently uses the unencrypted ESPHome API and native OTA on the
trusted home LAN. Add API encryption and OTA authentication together in a
separate tested change.

## Verification

Automated checks confirm these facts:

- Kubernetes can render the manifests.
- Image and model checksums match.
- The model has the correct input shape and can make one prediction.
- The network rules allow only the required connections.
- The handler lists no built-in wake words.
- The firmware config contains the required changes.
- The Ansible tasks preserve and validate the private token and model inputs.

Run the local transport checks from the Home Assistant pod:

```bash
kubectl exec -i -n home-automation deployment/home-assistant   -c home-assistant -- python3 -I - < scripts/ha_voice_smoke.py

kubectl exec -i -n home-automation deployment/home-assistant   -c home-assistant -- python3 -I - < scripts/ha_gi_wake_smoke.py
```

The second command uses computer-generated audio. It checks the connection and
model response only. It cannot tell whether Boris can say GI reliably or
whether room sounds cause false wakes.

Only Boris can test speech with the real Home Assistant Voice PE. Test normal,
soft, and distant `GI` speech, including speech directed away from the device.
For each light command, check these separate stages:

1. openWakeWord emits an accepted detection.
2. The satellite enters listening.
3. The Assist pipeline enters processing.
4. Home Assistant records the expected service call.
5. The intended physical light changes.
6. Piper gives the expected reply.

## Recovery after a restart

The wake-word init container recreates its generated package before patching
it, so retrying in the same pod does not leave an old package behind.

If Speech-to-Phrase stays in `ContainerCreating` with `already mounted or mount
point busy`, inspect the attached Longhorn device and multipath users. The
[scoped storage repair](../../playbooks/operations/storage/README.md) excludes
the verified voice disk WWID and releases only its unused map. It preserves
the claim and model files. It refuses a map with users or additional disks;
do not flush every map or recreate the PVC.

A ring flash shows only that the satellite is listening. It does not show that
Home Assistant called a service or changed a device.

Logs use `GI_CANDIDATE` and `GI_DETECTION`. They include the model score, audio
time, audio peaks, recent-audio timer, and remaining trigger count. They contain
no audio or transcript. Compare their times with the Home Assistant recorder.
Keep issue [#199](https://github.com/kpoxo6op/soyspray/issues/199) open and add
confirmed false wakes to it.

## Rotation and rollback

For token rotation:

1. Create a replacement token for `GI Speech`.
2. Store the new token with the input bootstrap command.
3. Increment `voice.soyspray.vip/token-revision` in `deployments.yaml`.
4. Push the annotation change.
5. Wait for the Speech-to-Phrase rollout.
6. Run the transport and live Voice PE checks.
7. Revoke the old token.

For a model change, follow [models/README.md](manifests/models). First, Ansible
creates and checks the new immutable ConfigMap. A second change makes the
Deployment use it.

Keep the stable GI v2 ConfigMap and private file available. Switch to it through
GitOps if an unwanted activation reaches conversation, a service call, or a
device action. If an event stops at listening, record it in issue #199.

After the pull request merges, verify the Application from `main`.

Retirement must use a separate reviewed operation. Preserve the token Secret,
selected model ConfigMap, and Home Assistant persistent data unless the
retirement explicitly includes them.
