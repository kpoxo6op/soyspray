# GI Flex speech recognition

The official `wyoming-faster-whisper` server supports Parakeet through sherpa-onnx
and Whisper through CTranslate2. This image bakes the checked English model files
into GHCR. Normal operation needs no internet, HA credential or persistent volume.
Only temporary WAV files use `/tmp`; the launcher suppresses upstream transcript
logging. Parakeet is the default; select Whisper with `--stt-library faster-whisper
--model /models/base.en` or `/models/small.en` and `--vad-filter` to suppress
Whisper hallucinations on silence. Keep all other offline arguments.

`gi-stt-image.yml` builds and tests the immutable image, including unchanged default arguments, Wyoming
Describe/Info, silence transcription and checked positive speech with network disabled. It publishes only
after a source merge. Promote the resulting digest separately through Argo CD.
The startup warmup decodes silence before a real command. The probe checks a loaded service's metadata, not microphone accuracy or decoder
performance. The download tests protect checksum rejection and archive confinement;
existing manifest checks do not execute downloaded model handling.

Use a parallel GI Flex pipeline. Preserve GI, its Speech-to-Phrase models, wake
word and satellite selection until real spoken-command acceptance. Compare the
three engines on the actual node, including names, negation and silence, before
choosing the runtime. Synthetic Piper audio measures transport/decoding only.
Rollback selects GI and reverts the new stateless deployment promotion.

Model attribution and license links are in NOTICE.md, which ships in the image.


The pushed `playbooks/operations/recovery/check-gi-stt-node.yml` creates a disposable
`voice-benchmark-<check-id>` namespace on an explicitly selected cluster node. It
has no data PVC, credentials, service account token or device/cloud traffic. Its
bounded job runs the promoted image with the same CPU limit and sandbox as the
service. Stream at most 40 synthetic 16 kHz mono PCM clips as JSON lines to
`python /test/benchmark.py` through the Kubernetes exec channel. Each row has
`case`, `text`, `rate` and base64 `audio`. It measures warmed Wyoming transcription,
peak decoder RSS and cgroup CPU throttling for each candidate. Keep audio and
transcript results private; these are synthetic measurements, not microphone or
HA-action acceptance. Retire the namespace with the same operation's cleanup
phase and its observed namespace UID. A completed idle Job alone is not proof:
require the exec process success and all three benchmark summaries.
