# Voice PE firmware inputs

`stop.json` and `stop.tflite` are the internal spoken-stop model from the
[`kahrendt/microWakeWord`](https://github.com/kahrendt/microWakeWord) `stop`
release. They are vendored so a firmware rebuild does not depend on a mutable
release download.

| File | Upstream URL | SHA-256 |
| --- | --- | --- |
| `stop.json` | `https://github.com/kahrendt/microWakeWord/releases/download/stop/stop.json` | `bd13aeb1b83852649dc4fb6135cb160ff68716d14612b06f6a405342c57447aa` |
| `stop.tflite` | `https://github.com/kahrendt/microWakeWord/releases/download/stop/stop.tflite` | `b5a18c4ad681a89950dfade31011e1631bdcb333e93c84519a1a63ff4f071146` |

The upstream repository uses the Apache License 2.0. The renderer verifies both
checksums before it copies these inputs into the generated build directory.
The model is not an activation phrase. It is active only during long replies
and timers so that `Stop` remains available after the Nabu model is removed.
