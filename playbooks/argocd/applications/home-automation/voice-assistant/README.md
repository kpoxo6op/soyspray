# Home Assistant local voice starter

This package runs local English speech processing for Home Assistant Assist.
Argo CD owns Speech-to-Phrase, Piper, their services, network policies, model
bootstrap Job, and model storage. The services have no Ingress or
LoadBalancer.

The starter controls the existing `light.top`, `light.middle`, and
`light.bottom` entities. Home Assistant already marks these entities for
Assist exposure. They initially have no Area assignment.

## Git and runtime ownership

Git stores all Kubernetes resources, immutable model inputs, and this
procedure. Ansible stores one runtime-only Home Assistant token in the
`voice-assistant-ha-token` Kubernetes Secret. The token is never committed. It
is mounted as a file. The Speech-to-Phrase process does not receive it through
a container environment variable or kernel command line.

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

For a model update, pin the new upstream revision and checksums. Create new
versioned PVC names, point the new Job and Deployments at those PVCs, and
increment the Job name. Keep the old PVC manifests for one validation and
rollback commit. Remove them in a later cleanup commit. Do not use a mutable
`main` model URL.

If a model PVC is lost while the completed Job still exists, change the Job
run suffix in Git and commit the change. Argo CD will then run a new controlled
bootstrap. Do not delete the live Job as an undocumented repair.

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
source soyspray-venv/bin/activate
make voice-assistant VOICE_ASSISTANT_REVISION="$(git branch --show-current)"
unset VOICE_ASSISTANT_HA_TOKEN
```

Later reconciliations preserve the existing Secret when
`VOICE_ASSISTANT_HA_TOKEN` is empty. Set the variable again only as part of the
rotation procedure below.

If the `GI Speech` password is unavailable, an owner can reset it under
**Settings > People > Users**. A password reset does not replace the live
long-lived token. Use the new password only to sign in for token rotation.

Verify the GitOps resources and model bootstrap:

```bash
kubectl get application -n argocd voice-assistant
kubectl wait -n home-automation --for=condition=complete \
  job/voice-model-bootstrap-v1 --timeout=30m
kubectl wait -n home-automation --for=condition=available \
  deployment/speech-to-phrase deployment/piper-en --timeout=15m
kubectl exec -n home-automation deployment/speech-to-phrase -- \
  test -f /data/train/en_US-rhasspy/training_info.json
kubectl get deploy,job,svc,pvc,networkpolicy -n home-automation \
  -l app.kubernetes.io/part-of=home-assistant-voice
kubectl get pod -n home-automation \
  -l 'app in (speech-to-phrase,piper-en)'
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
6. Open **Settings > Voice assistants**.
7. Add an assistant named `GI`.
8. Pronounce the name `Gee Ai`.
9. Select language `English` and conversation agent `Home Assistant`.
10. Select Speech-to-Phrase for speech-to-text.
11. Select Piper with voice `en_US-lessac-medium` for text-to-speech.
12. Keep `light.top`, `light.middle`, and `light.bottom` enabled for Assist exposure.
13. Assign the three lights to their physical Area.
14. On a phone with Bluetooth, open **Settings > Devices & services** in the
    Home Assistant app.
15. Add the discovered `ha-voice-pe-0a9b95` **Improv via BLE** entry and
    provision it on the home Wi-Fi.
16. When prompted, press the large round button on top of the Voice PE once.
17. If automatic ESPHome discovery does not appear, add **ESPHome** manually
    with host `home-assistant-voice-0a9b95` and port `6053`. OpenWrt DNS tracks
    this DHCP hostname, so do not store its temporary lease address.
18. Rename the device and satellite to `GI`.
19. Assign `GI` to the Area where it is installed.
20. Select the `GI` Assist pipeline for the satellite.

The setup photo identifies the unit as Home Assistant Voice Preview Edition,
model `NC-VK-9727`. Before a voice test, move its physical microphone switch
so that red is not visible.

## Name and wake word

`GI` is the reproducible Home Assistant assistant, device, and satellite name.
The supported starter wake phrase remains `Okay Nabu`. Voice Preview Edition
also includes `Hey Jarvis` and `Hey Mycroft`.

`Gee Ai` is not a bundled on-device wake word. A reliable custom wake word
needs a tested microWakeWord model and custom ESPHome firmware. Do not replace
the supported firmware with an unmeasured model. When a model passes false-wake
and missed-wake tests, commit its model manifest, checksum, firmware package,
and recovery procedure before selecting it.

## Wyoming transcription and light checks

Run the deterministic Piper-to-Speech-to-Phrase audio check. It synthesizes a
phrase, sends the audio to Speech-to-Phrase, and checks the transcript. It does
not operate a light.

```bash
kubectl exec -i -n home-automation deployment/home-assistant \
  -c home-assistant -- python3 -I - < scripts/ha_voice_smoke.py
```

Then use the Voice Preview Edition for the complete wake-word, intent, light,
and reply check. For each command, open the Assist pipeline debug view and
confirm that the trace uses Speech-to-Phrase, contains the expected transcript,
calls the expected light service, and completes Piper output.

- `Okay Nabu, turn on top.`
- `Okay Nabu, turn off top.`
- Repeat the checks for `middle` and `bottom`.
- After Area assignment, test `Okay Nabu, turn on the lights.`
- Confirm that only the lights in the satellite Area change.

Manual light controls and existing automations must continue to work during a
voice-service outage.

## Rollback and retirement

Before merge, point the Argo CD Application at the pushed topic branch. After
merge, run the Ansible command again with
`VOICE_ASSISTANT_REVISION=HEAD`.

To roll back a bad release, revert its Git commit and let Argo CD sync. Do not
delete the Home Assistant PVC or edit `.storage`.

To retire the complete voice stack, run:

```bash
source soyspray-venv/bin/activate
make voice-assistant VOICE_ASSISTANT_ENABLED=false
```

This disables Argo CD automation, removes the `voice-assistant` Application,
prunes the two voice model PVCs, and removes the token Secret. It does not
remove the Home Assistant PVC or the light entities. Remove the Wyoming
entries and `GI` pipeline through the Home Assistant UI only if they are no
longer required.
