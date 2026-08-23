# Private GI models

This file lists the two GI wake models that we keep. Model files, voice
recordings, calculated audio data, and training output stay outside Git.

| Purpose | ConfigMap | Private file | SHA-256 |
| --- | --- | --- | --- |
| Current | `openwakeword-gi-model-v7b` | `~/pCloudDrive/docs/soyspray/home-assistant-voice/gi-v7.tflite` | `e61dd9f2880f226b05b8f9885c053fa7ec7805170c3f3b4d56427c6294cb4be0` |
| Rollback | `openwakeword-gi-model-v2` | `~/pCloudDrive/docs/soyspray/home-assistant-voice/gi-v2.tflite` | `4b89c92d8500243404a77af30a7d8f8a618718403a355a3564e18108bc8f9739` |

An immutable ConfigMap cannot change after creation. Its checksum annotation
and the SHA-256 of its decoded `gi.tflite` file must match this table.

## How detection works

The service uses GI v7b with a score threshold of `0.65` and a trigger level of
`2`. It needs two scores above `0.65` in a row. A lower score resets the count.
An audio chunk with a 16-bit sample of `12` or higher starts a two-second timer.
The service ignores high model scores when that timer has reached zero.

Before the pod becomes Ready, its startup check confirms these facts:

- The model file matches the expected SHA-256.
- The running handler contains our patch.
- Built-in wake words are absent.
- The model reports 16 input windows.
- One model prediction completes.

The handler logs `GI_CANDIDATE` and `GI_DETECTION` metadata. It does not log
audio or transcripts.

## Test results

GI v7b detected GI in 8 of 10 initial live Voice PE attempts. In a later
10-attempt session, it detected GI eight times, and seven requested light
changes succeeded. Soft speech and speech directed away from the device caused
the misses.

Four later activations were confirmed while the room was empty. Each event
stopped in the listening state. None reached conversation, a service call, or
a device action.

During one overnight check, the model produced single scores of `0.685` and
`0.714`. Neither score caused a wake because the service requires two high
scores in a row. No wake occurred, so the temporary private recorder wrote no
file.

Keep issue [#199](https://github.com/kpoxo6op/soyspray/issues/199) open and add
new confirmed false wakes. Only Boris can test spoken GI with the real Home
Assistant Voice PE or identify sound in a recording. Automated checks can check
the model file, deployment, and event times only.

## Training and replacement

Use `scripts/train_gi_personalized.py` to train another model. It uses a private
recording of repeated GI speech, fixed public feature files, non-GI feature
files, and one exact openWakeWord source version.

We trained v7b with these values:

| Setting | Value |
| --- | --- |
| Seed | `20260820` |
| Width | `64` |
| Steps | `5000` |
| Maximum negative weight | `32` |
| Selection threshold | `0.65` |
| Selected checkpoint | `3200` |
| Private held-out recall | `1.0` |
| Generic threshold crossings | `0` in `6000` windows |

These numbers describe training and file format only. They do not replace the
live Voice PE test. Do not use a new model unless it still detects normal GI
speech and reduces confirmed false wakes.

Keep the input name `x` when you convert the selected ONNX model. One conversion
changed the input layout from `16 x 96` to `96 x 16`; the startup check rejected
that file.

## Add a model through GitOps

Use a new immutable ConfigMap name for a new model.

1. Update the model name and checksum in
   `roles/apps/voice-assistant/defaults/main.yml`.
2. Set `VOICE_ASSISTANT_GI_MODEL_PATH` to the private file whose checksum you
   checked.
3. Push the branch.
4. Run `make voice-assistant VOICE_ASSISTANT_REVISION="$(git rev-parse HEAD)"`.
5. Update the Deployment volume and startup-probe checksum.
6. Push and deploy the second commit.
7. Run the live Voice PE recall and false-wake check.

Ansible creates and checks the new ConfigMap before Argo CD uses it.

## GI v2 rollback

Keep the v2 private file and immutable ConfigMap available. To roll back:

1. Set the role defaults, Deployment volume, and startup-check checksum to the
   v2 name and checksum in the table.
2. Commit and push one small rollback change.
3. If the immutable ConfigMap is absent, set
   `VOICE_ASSISTANT_GI_MODEL_PATH` to the private v2 file.
4. Run `make voice-assistant VOICE_ASSISTANT_REVISION="$(git rev-parse HEAD)"`.
5. Check that Argo CD reports `Synced` and `Healthy`.
6. Check that the new pod is Ready with zero restarts.
7. Confirm the live model checksum.
8. Run the physical Voice PE check with Boris.

Do not delete either ConfigMap while issue #199 is open.
