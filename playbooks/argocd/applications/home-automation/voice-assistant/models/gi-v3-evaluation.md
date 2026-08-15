# GI v3 evaluation

Status: **rejected on 2026-08-15**. Version 3 did not activate on any of the
six held-out target bursts. Do not promote or deploy this model. Version 2
remains the deployment artifact.

## Frozen candidate

| Item | Value |
| --- | --- |
| Final bundle, 1,105,920 bytes | `eab6184e9418a93061cae1724b3b5978b68a739873b2863bab003253d7b7af3a` |
| Bundle metadata | `62e9038bdb7d5dfd8485e02140be2f27a549da76646b04d4f46a79d2978849ca` |
| Bundle manifest | `edaff9033594e65486b2e6f8de83313f37948d01962972ee04abbeb80d330a9f` |
| Training configuration | `411d067731a7bbb6e1e1c61c36e9387f3e5f59fefa65abfe8a97b224ee28ec04` |
| Training driver | `c39c171ff4bcd25809b8c7700e4dc324433522f13e1547405c22ec48c00d0e94` |
| Training dependency lock | `7ac50c40e00272209872af31da70f8ea7819d0b35296d6dbd7638c409ecce12d` |
| Conversion dependency lock | `0b0a21a97d9c15dd5af9b27cf9bda9ce26ec3591a5cfa5954d533d8c80e83dd2` |
| ONNX model, 206,248 bytes | `4902fc23beb7b52ee2ca8b1338f79dfdd6cca3d12fe29f4f6d4d5bef87d3edf0` |
| Version 3 TFLite model, 206,952 bytes | `6707f121883a24729a7afa80416fd53cd5c3c1d367c9790cf4fedc719aa8fda6` |
| Version 2 comparison model, 207,084 bytes | `4b89c92d8500243404a77af30a7d8f8a618718403a355a3564e18108bc8f9739` |

The held-out evaluator used `pyopen-wakeword==1.1.0`, `numpy==2.2.6`,
`ai-edge-litert==2.1.2`, `onnx2tf==2.6.8`, and `onnxruntime==1.26.0`.
It used fresh model state for each file and 1,280-sample streaming chunks.
The operational comparison was strict score `>0.65`.

The ONNX/TFLite conversion passed. Its 32 seeded comparisons had maximum
absolute error `6.556510925292969e-07` and cosine similarity
`0.9999999999999667`. Conversion is not the cause of the rejection.

## Synthetic validation

The frozen TFLite model was evaluated on the saved 2,000 positive and 2,000
adversarial-negative feature examples.

| Threshold | TP | FN | FP | TN | Recall | Accuracy |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `0.5` | 1,043 | 957 | 3 | 1,997 | `0.5215` | `0.76` |
| `0.65` | 993 | 1,007 | 1 | 1,999 | `0.4965` | `0.748` |

The training log reported accuracy `0.7599999904632568`, recall
`0.5214999914169312`, and `2.8318583965301514` false positives per hour.
The last value is 32 false positives in the fixed 11.3-hour validation set.
It exceeds the configured target of `0.2` false positives per hour.

Positive scores had median `0.6198877096176147` and maximum
`0.9609709978103638`. Adversarial-negative scores had median
`0.0007752096280455589`, 99th percentile `0.0028096348978579044`, and
maximum `0.9287893772125244`.

## Private held-out regression set

No audio, transcript, personal path, or private content is in Git. The source
recording and derived WAV files remain private. Human audio was not used for
training or checkpoint selection. This record contains only media facts,
SHA-256 values, and model outputs.

The private source is mono Opus at 48 kHz. Its duration is `9.060000` seconds
and its SHA-256 is
`d4c30f86ec219ba303ac47a837aa03dde0e47d82570568eda2c0b112c5403e2b`.
The canonical evaluation files are mono 16 kHz, 16-bit PCM WAV files.

| ID | Samples | Seconds | WAV SHA-256 | v2 max / second | v3 max / second | Crossings `>0.65`, v2 / v3 |
| --- | ---: | ---: | --- | --- | --- | ---: |
| full | 144,856 | `9.053500` | `fe62f214d94426f464a4b17cb48e0817682e3eb9e2a09300f038b4fa6c9555b9` | `0.027940861880779266` / `0.004167395643889904` | `0.017989320680499077` / `0.012577851302921772` | 0 / 0 |
| burst-01 | 24,000 | `1.500000` | `2354139235351ee00d1e5ec1b8d7540600e97883a3a07c1535c100aa296a1a81` | `0.0010351174278184772` / `0.0010080346837639809` | `0.00544473621994257` / `0.0040823426097631454` | 0 / 0 |
| burst-02 | 22,400 | `1.400000` | `284fd6f90e2e85a818e0037dd7e04ebef397b01d864b3eb6667030f3a558c4d9` | `0.0009592820424586535` / `0.0009398740367032588` | `0.0026193188969045877` / `0.0018068177159875631` | 0 / 0 |
| burst-03 | 24,000 | `1.500000` | `99a8f6ef8691f77cf8cd3577009f26326854ed2f7b86b5f26694789c93cf76a6` | `0.0009523782064206898` / `0.0009388134349137545` | `0.0008365907124243677` / `0.0008318693144246936` | 0 / 0 |
| burst-04 | 21,600 | `1.350000` | `e8479d21dcbc17eaecf8344e2f3d831d2cecf7e0467ad3598ae75083209f47bb` | `0.0009121313341893256` / `0.0009098830632865429` | `0.0008421955280937254` / `0.0008368765702471137` | 0 / 0 |
| burst-05 | 23,200 | `1.450000` | `1b993003587355f047ed0f3750c00d833931fa2effe9678cb568dd998b93072c` | `0.0009125040960498154` / `0.0009044937905855477` | `0.0013109067222103477` / `0.0012312311446294188` | 0 / 0 |
| burst-06 | 19,200 | `1.200000` | `33788b431a3f5a8263287c90b8d37354be6a5aecf342f1cca2590819466b4664` | `0.0009330919710919261` / `0.0009328977321274579` | `0.0013497775653377175` / `0.0009997797897085547` | 0 / 0 |

Across the six isolated bursts, the mean maximum rose from
`0.0009507508463381479` to `0.0020672542741522193`. The median rose from
`0.000942735088756308` to `0.0013303421437740326`. Version 3 increased four
of six isolated maxima, but its full-recording maximum fell by
`35.61644319614181%`. Both models detected zero of six bursts. The score
changes are not a functional improvement.

## Minimum version 4 change

Correct these pipeline faults before another training run:

1. Save final training metrics and fail the bundle when recall, accuracy, or
   false-positive targets fail. The version 3 trainer did not apply its
   configured accuracy and recall targets.
2. Run a pinned streaming gate with threshold `0.65` and trigger level `2`.
   Numeric conversion parity alone is not a wake-word test.
3. Use disjoint, seeded Piper speaker conditions for training and validation.
   Version 3 restarted the same speaker-pair and synthesis-setting sequences
   for both sets.
4. Use deterministic sample IDs. Save the text, speaker pair, interpolation
   weight, speed, noise settings, and random seed for each generated clip.
5. Give `gee`, `eye`, `nabu`, `okay nabu`, and normal light commands explicit
   negative quotas. Version 3 added each custom negative only about once or
   twice among approximately 20,000 adversarial samples.
6. Keep `augmentation_rounds: 1` until the trainer allocates feature output
   rows for every requested round.

For the first controlled version 4 candidate, keep the version 3 sample
counts, steps, background data, room impulse responses, batch class counts,
negative weight, and 32-unit layer. Change only the synthetic speech domain:

- Split positive text between `gee eye` and `GI`. Pinned Piper maps `G I` and
  `gee eye` to the same phoneme-ID sequence, so `G I` adds no diversity. It
  maps `GI` to the intended fused letter sounds with a different boundary and
  stress pattern. `G.I.` adds a punctuation token to that fused sequence, so
  leave it for a later one-variable test. Keep `gee eye` as the only
  adversarial-text source.
- Use seeded Piper interpolation weights `(0.0, 0.5, 1.0)` instead of only
  `0.5`. This adds source-speaker endpoints while retaining mixed voices.

Do not lower the runtime threshold or negative weight. If this data-only
candidate fails the synthetic gates, train one separate candidate with a
64-unit layer. Do not combine that capacity test with other tuning.

## Version 4 acceptance gates

Select random seeds and checkpoints only with synthetic data. Freeze the model
before human scoring.

1. With 16 kHz streaming audio, 1,280-sample chunks, strict score `>0.65`,
   and trigger level `2`, detect at least 95% of each positive spelling and
   held-out synthetic speaker group.
2. Detect none of `gee`, `eye`, `nabu`, `okay nabu`, and normal light-command
   negatives. Measure no more than `0.2` generic false positives per hour.
3. Require ONNX/TFLite maximum absolute error at most `0.0001` and cosine
   similarity at least `0.99999`.
4. After the candidate is frozen, require two consecutive scores above `0.65`
   for all six private bursts. Require six events in the full recording and
   zero events in the sealed private negative set.
5. Pass the Wyoming positive and negative smoke tests. Then pass the real
   Voice PE test before promotion.

This evaluation changed no model, GitOps manifest, Home Assistant resource, or
cluster resource. The GitOps startup probe remains pinned to the version 2
model SHA-256 above.
