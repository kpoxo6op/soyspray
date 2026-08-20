# GI v5 personalized model

GI v5 is trained for the primary user's pronunciation of `GI`. It uses ten
utterances detected in one private 14.46-second recording. Eight utterances
produce deterministic augmented training features. Two held-out utterances
produce separate augmented selection features. The recording and derived
features are private and are not stored in this repository or Kubernetes.

The trainer is `scripts/train_gi_personalized.py` at Git commit `50f5ccb`. It
reuses the pinned GI v4 public synthetic feature arrays and the public generic
negative validation features. Training ran on node-2 with these fixed values:

| Setting | Value |
| --- | --- |
| Seed | `20260820` |
| Model width | `64` |
| Steps | `4000` |
| Maximum negative weight | `8` |
| Production threshold | `0.65` |
| Selected checkpoint | step `1200` |
| Private held-out recall | `0.90625` |
| Generic false positives | `4` in `6000` windows |
| Synthetic balanced accuracy | `0.7763671875` |

The selected checkpoint is the eligible checkpoint with the fewest generic
false positives. Eligibility requires private held-out recall of at least
`0.90`.

## Private artifact record

| Artifact | SHA-256 |
| --- | --- |
| Private source WAV | `0f36a00f2c614e628f533002997420c14de12a6e6b1801d47c769472f66af49f` |
| Original ONNX model | `4889fd8ff3ff2de0497db98e70c191bfe31f2a2cf1e05a08424e7d6ed8cfc679` |
| Training report | `9e26b638f997dcaa27f59c3b9e7172f288d47f2719139b4d2af46537a29d3d90` |
| Float32 TFLite model | `bed4311c39eeb28803f8de7df16d923e45f8bde4f4d6b631e882ec9baffe5070` |

The canonical deployment file is private:

```text
~/pCloudDrive/docs/soyspray/home-assistant-voice/gi-v5.tflite
```

The Python 3.12 converter wrote the float32 TFLite model successfully. Its
optional numerical comparison did not complete because an OpenCV import failed
in a child process. No automated acceptance suite was run. Promotion depends
on the normal workload startup check and the live Voice PE test with the
primary user's voice.

Keep immutable ConfigMap `openwakeword-gi-model-v2` available until GI v5
passes the live test. Roll back the deployment reference to that ConfigMap and
its recorded SHA-256 if GI v5 is not reliable.
