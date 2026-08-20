# GI v6 personalized model

GI v6 is trained for the primary user's pronunciation of `GI`. It includes the
five GI v5 live misses as hard-positive training evidence. A separate private
24.17-second recording produced 17 isolated utterances that were not used for
training or checkpoint selection. They are reserved for the live Voice PE
acceptance test.

The trainer is `scripts/train_gi_personalized.py` at Git commit `3255011`.
Training ran on node-2 with the pinned GI v4 public feature arrays and these
fixed values:

| Setting | Value |
| --- | --- |
| Seed | `20260820` |
| Model width | `64` |
| Steps | `4000` |
| Maximum negative weight | `32` |
| Production threshold | `0.65` |
| Selected checkpoint | step `2000` |
| Private held-out recall | `0.95703125` |
| Generic false positives | `0` in `6000` windows |
| Synthetic balanced accuracy | `0.791015625` |

The selected checkpoint is the eligible checkpoint with the fewest generic
false positives. Eligibility requires private held-out recall of at least
`0.90`.

## Private artifact record

| Artifact | SHA-256 |
| --- | --- |
| Private training WAV | `32b99667ee33d6c584bb2e7ef28f86e7ab62995caef4406b8eae55842557f9d3` |
| Original ONNX model | `b2ab746763fcb96b2cf0b517fd35a2ca456b20011c2a16da2bdd0d4e3b906748` |
| Training report | `0ea539ad43d4cb30dfbad0d59c7a9798ccce436d9867cf5b21d625ba730081ec` |
| Float32 TFLite model | `514b2d09a3c48b16ed8047f268ad8fd604b838a097d10fb9342d1483b7c43573` |
| Float16 TFLite model | `fe72b150a3d37c4aa7c334edc4bbdf78ec3025b6dedf373b01b2462dc301a405` |
| Converter report | `c8808345fb6a4a92d14f8dfa66f527c372577875364fbc6f2bac8ac7a51e9abe` |
| Reserved holdout WAV | `ed7006d0669fe715b33176e19f63975da21943393cb90f6fc7f6c6346ed5519b` |

The canonical deployment file is private:

```text
~/pCloudDrive/docs/soyspray/home-assistant-voice/gi-v6.tflite
```

The Python 3.12 converter used the repository's hash-locked conversion stack.
The model and private derived features are not stored in Git. No automated
acceptance suite was run. Promotion depends on normal workload startup and live
Voice PE playback of the 17 reserved utterances.

Keep immutable ConfigMap `openwakeword-gi-model-v2` available during live
acceptance. Roll back the deployment reference to that ConfigMap and its
recorded SHA-256 if GI v6 causes missed or false wakes.
