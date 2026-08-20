# GI v7 personalized model

GI v7 uses the 17 live GI v6 clips and the eight earlier GI v5 live clips as
private personalized training evidence. The corpus contains 25 utterances: 23
for training and two for checkpoint selection. The recordings and derived
features remain outside Git and Kubernetes.

The trainer is `scripts/train_gi_personalized.py` at Git commit `79cc75d`.
Training ran on node-2 with the pinned GI v4 public feature arrays and these
fixed values:

| Setting | Value |
| --- | --- |
| Seed | `20260820` |
| Model width | `64` |
| Steps | `5000` |
| Maximum negative weight | `32` |
| Production threshold | `0.65` |
| Selected checkpoint | step `3200` |
| Private held-out recall | `1.0` |
| Generic false positives | `0` in `6000` windows |
| Synthetic balanced accuracy | `0.7734375` |

The selected checkpoint is the eligible checkpoint with the fewest generic
false positives. Eligibility requires private held-out recall of at least
`0.90`.

## Private artifact record

| Artifact | SHA-256 |
| --- | --- |
| Private training WAV | `a4689adb3f00c5ed1ce33e81b33ec56405747c6925036fc6845f2f55a95cec5c` |
| Original ONNX model | `c28074ef69b110349eb748a0c03d47fe8c0479f95378c73d0cb3d6061c6d8a60` |
| Training report | `264aa25a5c49d52dcff2e031e85cc27064c49abe6a8beb79d48ac3c78a709dbd` |
| Float32 TFLite model | `e61dd9f2880f226b05b8f9885c053fa7ec7805170c3f3b4d56427c6294cb4be0` |
| Float16 TFLite model | `0b13e713c64ede214179236bceb23509f4977145d6431b9cb229f68046ec184e` |
| Converter report | `c8808345fb6a4a92d14f8dfa66f527c372577875364fbc6f2bac8ac7a51e9abe` |

The canonical deployment file is private:

```text
~/pCloudDrive/docs/soyspray/home-assistant-voice/gi-v7.tflite
```

The first TFLite conversion changed the model input layout from `16 x 96` to
`96 x 16`. The workload startup check rejected that model before it became
Ready. The corrected conversion preserved input `x` with `-kat x`. Production
startup then loaded the exact pinned bytes, confirmed 16 input windows, and ran
one normal inference window. Immutable ConfigMap
`openwakeword-gi-model-v7b` contains the corrected model.

## Live acceptance

GI v7 passed a 12-minute silent-room soak with no wake event. The primary user
then completed ten live Voice PE tests with natural speech. The model detected
8 of 10 tests. The first seven normal-use tests all passed, including soft
speech at one metre, normal speech at three metres, and speech with the user
facing away at two metres.

Both misses occurred at three metres while the user was turned sideways. A
control test at the same distance passed when the user faced the speaker. The
primary user then spoke naturally in Russian for two minutes without a false
wake and accepted the result.

GI v7 is accepted for current use. Its measured limit is soft or sideways
speech at three metres. Keep GI v2 and the corrected GI v7 model ConfigMaps for
rollback. The voice Argo application uses no automatic retry after a failed
rollout so a rejected model cannot hold a long retry cycle.
