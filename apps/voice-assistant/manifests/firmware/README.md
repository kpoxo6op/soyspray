# Voice PE firmware inputs

`stop.json` and `stop.tflite` contain the spoken Stop model from the
[`kahrendt/microWakeWord`](https://github.com/kahrendt/microWakeWord) `stop`
release. We keep copies here so a rebuild does not depend on a download that can
change or disappear.

| File | Upstream URL | SHA-256 |
| --- | --- | --- |
| `stop.json` | `https://github.com/kahrendt/microWakeWord/releases/download/stop/stop.json` | `bd13aeb1b83852649dc4fb6135cb160ff68716d14612b06f6a405342c57447aa` |
| `stop.tflite` | `https://github.com/kahrendt/microWakeWord/releases/download/stop/stop.tflite` | `b5a18c4ad681a89950dfade31011e1631bdcb333e93c84519a1a63ff4f071146` |

The source repository uses the Apache License 2.0. The build script checks both
SHA-256 values before it copies the files. This model is not a wake phrase. It
listens for `Stop` only during long replies and timers.
