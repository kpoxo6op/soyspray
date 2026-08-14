# Home Assistant local voice starter

This package runs local English speech processing for Home Assistant Assist.
Argo CD owns Speech-to-Phrase, Piper, the `GI` openWakeWord service, their
services, network policies, model bootstrap Job, and model storage. The
services have no Ingress or LoadBalancer.

The starter controls the existing `light.top`, `light.middle`, and
`light.bottom` entities. Home Assistant already marks these entities for
Assist exposure. They initially have no Area assignment.

## Git and runtime ownership

Git stores all Kubernetes resources, model checksums, training records, and
this procedure. Ansible stores one runtime-only Home Assistant token in the
`voice-assistant-ha-token` Kubernetes Secret and the private GI model in the
immutable `openwakeword-gi-model-v2` ConfigMap. Neither value is committed to
this public repository. The token is mounted as a file. The Speech-to-Phrase
process does not receive it through a container environment variable or kernel
command line.

Home Assistant stores the Wyoming integration entries, Assist pipeline,
ESPHome adoption, entity aliases, Assist exposure, and Area assignments in its
PVC. These items are `.storage` runtime state. Do not generate or edit
`.storage` files. Reproduce them with the procedure below.

## Immutable model bootstrap

The versioned `voice-model-bootstrap-v1` Job downloads and verifies these
artifacts before either runtime Deployment starts:

| Artifact | Upstream revision | SHA-256 |
| --- | --- | --- |
| Speech-to-Phrase `en_US-rhasspy.tar.gz` | `a17c6ed2bbbb09176164e81cd3161b264d0fb2ba` | `3dbf8c16b2d08767eba4866a444f075d0a5b1304c73ca366d2c60346b28759e7` |
| Piper `en_US-lessac-medium.onnx` | `ea046e8458f6acd997706d6e6066a022b42f6fb1` | `5efe09e69902187827af646e1a6e9d269dee769f9877d17b16b1b46eeaaf019f` |
| Piper voice configuration | `ea046e8458f6acd997706d6e6066a022b42f6fb1` | `efe19c417bed055f2d69908248c6ba650fa135bc868b0e6abb3da181dab690a0` |

Only the bootstrap Job has WAN HTTPS egress. It has no Home Assistant token.
The Speech-to-Phrase pod can reach only Home Assistant on TCP port 8123. It
uses the Kubernetes service-link address and does not need DNS. The Piper pod
has no egress. This separation makes runtime restarts independent of WAN
access. A first sync with empty PVCs also proves this path: Argo CD waits for
the bootstrap Job, then starts both WAN-blocked runtime Deployments.

The private `gi.tflite` file is checksum-pinned in Git. Ansible verifies it and
creates an immutable, versioned ConfigMap before Argo CD can start the
openWakeWord pod. The pod repeats the checksum and real-inference checks at
startup. It has no WAN or DNS egress.

For a Speech-to-Phrase or Piper model update, pin the new upstream revision and
checksums. Create new versioned PVC names, point the new Job and Deployments at
those PVCs, and increment the Job name. Keep the old PVC manifests for one
validation and rollback commit. Remove them in a later cleanup commit. Do not
use a mutable `main` model URL.

If a model PVC is lost while the completed Job still exists, change the Job
run suffix in Git and commit the change. Argo CD will then run a new controlled
bootstrap. Do not delete the live Job as an undocumented repair.

## GI model provenance

The training configuration and record are in `models/`. The record pins the
public openWakeWord notebook, source revisions, training phrase, parameters,
compatibility changes, and private model checksum. The binary stays in private
pCloud storage because this GitHub repository is public and the mixed training
datasets permit non-commercial personal use only.

The model label comes from the filename `gi.tflite`. The synthesized training
phrase is `gee eye`; do not train the three-sound text `Gee Ai`. Re-run the
model smoke test after any model or threshold change.

## Initial deployment

Create the token with a dedicated Home Assistant user. Do not use Boris's
account. Speech-to-Phrase v1.4.3 reads the admin-only Assist exposure list, so
this separate account requires Administrator. Home Assistant does not scope a
long-lived token to selected WebSocket commands. The runtime network policy
limits the token-bearing pod to Home Assistant TCP port 8123, but the token can
still administer Home Assistant. Revoke it if the speech workload is
compromised.

1. In Home Assistant, open **Settings > People > Users**.
2. Add a local user named `GI Speech`.
3. Enable **Administrator** for this dedicated account.
4. Set a strong generated password. Do not put it in Git.
5. Sign in as `GI Speech` and open its **Security** profile page.
6. Create a long-lived access token named `Soyspray Speech-to-Phrase`.
7. Keep the token only for the next Ansible command.
8. Commit and push the topic branch.
9. Run `make go`.
10. Deploy the pushed branch:

```bash
read -rsp 'Home Assistant voice token: ' VOICE_ASSISTANT_HA_TOKEN
export VOICE_ASSISTANT_HA_TOKEN
PCLOUD_DRIVE="${HOME}/pCloudDrive"
export VOICE_ASSISTANT_GI_MODEL_PATH="${PCLOUD_DRIVE}/docs/soyspray/home-assistant-voice/gi-v2.tflite"
source soyspray-venv/bin/activate
make voice-assistant VOICE_ASSISTANT_REVISION="$(git branch --show-current)"
unset VOICE_ASSISTANT_HA_TOKEN VOICE_ASSISTANT_GI_MODEL_PATH PCLOUD_DRIVE
```

Later reconciliations preserve the existing Secret when
`VOICE_ASSISTANT_HA_TOKEN` is empty and preserve the immutable GI ConfigMap when
`VOICE_ASSISTANT_GI_MODEL_PATH` is empty. Set either variable again only for
its documented rotation procedure.

If the `GI Speech` password is unavailable, an owner can reset it under
**Settings > People > Users**. A password reset does not replace the live
long-lived token. Use the new password only to sign in for token rotation.

Verify the GitOps resources and model bootstrap:

```bash
kubectl get application -n argocd voice-assistant
kubectl wait -n home-automation --for=condition=complete \
  job/voice-model-bootstrap-v1 --timeout=30m
kubectl wait -n home-automation --for=condition=available \
  deployment/speech-to-phrase deployment/piper-en \
  deployment/openwakeword-gi --timeout=15m
kubectl exec -n home-automation deployment/speech-to-phrase -- \
  test -f /data/train/en_US-rhasspy/training_info.json
kubectl get deploy,job,svc,pvc,configmap,networkpolicy -n home-automation \
  -l app.kubernetes.io/part-of=home-assistant-voice
kubectl get pod -n home-automation \
  -l 'app in (speech-to-phrase,piper-en,openwakeword-gi)'
```

The Speech-to-Phrase readiness probe checks both the Wyoming socket and
`training_info.json`. A TCP listener alone is not sufficient.

### Token rotation

Speech-to-Phrase reads the token only when its process starts. Rotate it with
this two-phase GitOps rollout. The order prevents Argo CD from restarting the
pod with the old Secret value.

1. Create a replacement token in the `GI Speech` profile.
2. Create a new rotation branch from the exact revision that the live
   Application uses. Do not change `deployments.yaml` yet.
3. Push this unchanged rotation branch.
4. Run the initial deployment command with the replacement token and the
   unchanged rotation branch. Ansible stores the replacement token before it
   points Argo CD at that branch. The unchanged tree causes no rollout.
   The replacement Secret therefore exists before the annotation change can
   start a new pod.
5. Increment `voice.soyspray.vip/token-revision` in `deployments.yaml`.
6. Commit and push the annotation change to the rotation branch. Argo CD now
   restarts Speech-to-Phrase with the replacement token.
7. Wait for `deployment/speech-to-phrase` to become available.
8. Run `scripts/ha_voice_smoke.py` with the command below.
9. Revoke the old token only after the annotation change, new pod, and smoke
   check succeed.

### GI model rotation

The private model ConfigMap is immutable. Use a new versioned name for every
model. The two-phase order prevents Argo CD from starting a pod before Ansible
has stored the new private binary.

1. Train and validate the replacement model. Save its canonical copy in the
   documented private pCloud directory.
2. Create a rotation branch from the live Application revision.
3. Update only `voice_assistant_gi_model_configmap_name`,
   `voice_assistant_gi_model_sha256`, and the model training record. Do not
   change the Deployment volume yet.
4. Commit and push that first change.
5. Set `VOICE_ASSISTANT_GI_MODEL_PATH` to the replacement private file and run
   the deployment command. Ansible verifies the bytes and creates the new
   immutable ConfigMap. The old Deployment continues to use the old version.
6. Change the Deployment volume and startup-probe checksum to the new version.
7. Commit and push the second change. Argo CD now rolls the pod onto the model
   that already exists.
8. Run the GI positive, negative, fallback, human voice, and light checks.
9. After rollback is no longer required, add the old name to
   `voice_assistant_gi_model_retired_configmaps`, commit and push, then run the
   deployment command. Remove the retired name from the list in a later
   cleanup commit. Do not delete it manually during the rollout.

## Home Assistant runtime setup

Perform these steps after both voice Deployments are ready.

The Home Assistant bootstrap configuration owns
`internal_url: http://192.168.20.33:8123`. This matches the Home Assistant
LoadBalancer service. A Voice PE on the LAN can use this address to fetch
audio. Do not use a Kubernetes pod address for `internal_url`.

1. Open **Settings > Devices & services**.
2. Add the **Wyoming Protocol** integration.
3. Add host `speech-to-phrase.home-automation.svc.cluster.local`, port `10300`.
4. Add another **Wyoming Protocol** entry.
5. Add host `piper-en.home-automation.svc.cluster.local`, port `10200`.
6. Add a third **Wyoming Protocol** entry.
7. Add host `openwakeword-gi`, port `10400`. Home Assistant runs in the same
   namespace, so this short service name and
   `openwakeword-gi.home-automation.svc.cluster.local` are equivalent.
8. Open **Settings > Voice assistants**.
9. Add an assistant named `GI`.
10. Say the name as the two letter names: `Gee Eye`.
11. Select language `English` and conversation agent `Home Assistant`.
12. Select Speech-to-Phrase for speech-to-text.
13. Select Piper with voice `en_US-lessac-medium` for text-to-speech.
14. Select `gi` as the **Streaming wake word**.
15. Keep `light.top`, `light.middle`, and `light.bottom` enabled for Assist exposure.
16. Assign the three lights to their physical Area.
17. On a phone with Bluetooth, open **Settings > Devices & services** in the
    Home Assistant app.
18. Add the discovered `ha-voice-pe-0a9b95` **Improv via BLE** entry and
    provision it on the home Wi-Fi.
19. When prompted, press the large round button on top of the Voice PE once.
20. If automatic ESPHome discovery does not appear, add **ESPHome** manually
    with host `home-assistant-voice-0a9b95` and port `6053`. OpenWrt DNS tracks
    this DHCP hostname, so do not store its temporary lease address.
21. Rename the device and satellite to `GI`.
22. Assign `GI` to the Area where it is installed.
23. Select the `GI` Assist pipeline for the satellite.

Home Assistant stores Assist pipelines as runtime data. The UI is the normal
configuration path. If Home Assistant `2026.5.4` shows an empty streaming wake
word picker even though `wake_word.openwakeword` exists, use its supported
WebSocket API from the signed-in administrator browser console. This copies
every required field and changes only the two wake-word fields:

```javascript
const hass = document.querySelector("home-assistant").hass;
const listed = await hass.callWS({ type: "assist_pipeline/pipeline/list" });
const matches = listed.pipelines.filter((item) => item.name === "GI");
if (matches.length !== 1) throw new Error(`Expected one GI pipeline, got ${matches.length}`);
const pipeline = matches[0];
await hass.callWS({
  type: "assist_pipeline/pipeline/update",
  pipeline_id: pipeline.id,
  conversation_engine: pipeline.conversation_engine,
  conversation_language: pipeline.conversation_language,
  language: pipeline.language,
  name: pipeline.name,
  stt_engine: pipeline.stt_engine,
  stt_language: pipeline.stt_language,
  tts_engine: pipeline.tts_engine,
  tts_language: pipeline.tts_language,
  tts_voice: pipeline.tts_voice,
  wake_word_entity: "wake_word.openwakeword",
  wake_word_id: "gi",
  prefer_local_intents: pipeline.prefer_local_intents,
});
```

List the pipelines again and require the `GI` result to contain
`wake_word_entity: wake_word.openwakeword` and `wake_word_id: gi`. Do not edit
Home Assistant `.storage` files.

The setup photo identifies the unit as Home Assistant Voice Preview Edition,
model `NC-VK-9727`. Before a voice test, move its physical microphone switch
so that red is not visible.

## Name and wake word

`GI` is the Home Assistant assistant, device, satellite, pipeline, and wake
model name. The exact two-sound pronunciation and training text is `gee eye`.

`GI` is detected by the local openWakeWord pod. The custom Voice PE firmware
streams microphone audio to Home Assistant while it waits. It contains no
`Okay Nabu`, `Hey Jarvis`, or `Hey Mycroft` activation model. It keeps only the
internal `Stop` microWakeWord model for long replies and timers.

Passive streaming sends 16 kHz, 16-bit mono audio across the home LAN. This is
about 32 KB/s before protocol overhead. The openWakeWord service has no WAN
egress and is available only to the Home Assistant pod.

The phrase has only two syllables. This increases the risk of false wakes. The
starter uses threshold `0.65` and trigger level `2`. Measure household speech,
TV, and music before lowering either value.

Render, validate, and compile the pinned Voice PE `25.5.2` source with ESPHome
`2025.5.1`:

```bash
make voice-pe-check
make voice-pe-compile
```

The live ESPHome entry for this unit has no API password or encryption key.
The renderer therefore preserves its plain `api:` mode. It preserves the
device name, MAC-based identity, saved Wi-Fi credentials, native OTA, and
serial Improv recovery. Do not factory-reset the device.

This compatibility mode is not a secure final state. A device on the home LAN
can connect to the unencrypted ESPHome API or use passwordless OTA. It can
control the Voice PE, observe its API traffic, or replace its firmware. The
Kubernetes network policies do not protect these LAN ports.

Migrate to authenticated firmware in a separate tested change:

1. Generate a 32-byte base64 ESPHome API encryption key and a strong OTA
   password. Store the canonical copies in the password manager, outside Git.
2. Extend the pinned renderer so `api.encryption.key` and the native
   `ota.password` use `!secret` values. Create an expendable compile copy at
   `.build/voice-pe/secrets.yaml` from the password-manager values. `make clean`
   deletes this file.
3. Commit and push only the renderer and runbook changes.
4. Compile and upload once with both secrets present.
5. Reconfigure the existing Home Assistant ESPHome entry with the same API
   key when it requests authentication.
6. Rebuild, upload, reconnect, and run the complete wake and light checks.
   Keep both canonical secrets for future API recovery and OTA updates.

Do not add only one key. An API-only change leaves OTA open. An OTA-only change
leaves microphone and control traffic unauthenticated.

After the openWakeWord service is ready and `gi` is selected as the streaming
wake word, upload through native OTA:

```bash
make voice-pe-upload
```

Override `VOICE_PE_HOST` only if local name resolution does not find
`home-assistant-voice-0a9b95.local`. The center button cancels and re-arms
streaming wake detection. It is not push-to-talk in this firmware.

## Wyoming transcription and light checks

Run the deterministic Piper-to-Speech-to-Phrase audio check. It synthesizes a
phrase, sends the audio to Speech-to-Phrase, and checks the transcript. It does
not operate a light.

```bash
kubectl exec -i -n home-automation deployment/home-assistant \
  -c home-assistant -- python3 -I - < scripts/ha_voice_smoke.py
```

Then synthesize the exact wake phrase and require the `gi` model to detect it:

```bash
kubectl exec -i -n home-automation deployment/home-assistant \
  -c home-assistant -- python3 -I - < scripts/ha_gi_wake_smoke.py
```

The helper inserts one second of trailing silence before `AudioStop`. The real
Voice PE sends a continuous microphone stream. A short Piper clip without this
tail can end before the 16-window model emits its final scores.

For the physical Voice PE check, make the laptop speaker say one complete
command with the same pinned Piper service. The helper writes only WAV bytes
to standard output:

```bash
PHRASE='gee eye, turn on top'
kubectl exec -i -n home-automation deployment/home-assistant \
  -c home-assistant -- env PHRASE="${PHRASE}" python3 -I - \
  < scripts/ha_piper_wav.py | pw-play -
```

Repeat with `turn off top`, then with `middle` and `bottom`. Run the same
command with `okay nabu, turn on top` and confirm that no pipeline starts and
the light remains off.

Then use the Voice Preview Edition for the complete wake-word, intent, light,
and reply check. For each command, open the Assist pipeline debug view and
confirm that the trace uses Speech-to-Phrase, contains the expected transcript,
calls the expected light service, and completes Piper output.

- `GI, turn on top.`
- `GI, turn off top.`
- Repeat the checks for `middle` and `bottom`.
- After Area assignment, test `GI, turn on the lights.`
- Confirm that only the lights in the satellite Area change.
- Confirm that `Okay Nabu, turn on top` does not activate the satellite.

Manual light controls and existing automations must continue to work during a
voice-service outage.

## Rollback and retirement

Before merge, point the Argo CD Application at the pushed topic branch. After
merge, run the Ansible command again with
`VOICE_ASSISTANT_REVISION=HEAD`.

To roll back a bad release, revert its Git commit and let Argo CD sync. Do not
delete the Home Assistant PVC or edit `.storage`.

For Voice PE firmware rollback, use the official Home Assistant Voice PE USB-C
installer. Native OTA does not erase Wi-Fi state, but a factory reset does.
If normal USB-C reinstall is unavailable, use the documented bootloader-mode
reinstall. After stock firmware returns, select a bundled wake word in the
satellite and remove the `gi` streaming wake choice. Do not use the 22-second
factory reset as firmware rollback.

To retire the complete voice stack, run:

```bash
source soyspray-venv/bin/activate
make voice-assistant VOICE_ASSISTANT_ENABLED=false
```

This disables Argo CD automation, removes the `voice-assistant` Application,
prunes the two voice model PVCs, and removes the token Secret and current
private GI model ConfigMap. It does not remove the Home Assistant PVC or the
light entities. Remove the Wyoming entries and `GI` pipeline through the Home
Assistant UI only if they are no longer required.
