"""Packaged-runtime check, run inside the built image with no network access."""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, "/app")
import horoscope  # noqa: E402
from faster_whisper import WhisperModel  # noqa: E402

assert os.geteuid() == 1000, "the image must run as UID 1000"
work = Path(tempfile.mkdtemp())
live = work / "live"
live.mkdir()
for index in range(3):
    subprocess.run(
        ["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "testsrc2=size=1280x720:rate=25",
         "-f", "lavfi", "-i", "sine=frequency=300", "-t", "5", "-c:v", "libx264",
         "-preset", "ultrafast", "-c:a", "aac", "-f", "mpegts",
         str(live / f"20261105T10000{index * 5}Z.ts")],
        check=True,
    )  # fmt: skip
segs = horoscope.segments(live)
samples = horoscope.audio_samples(segs[0][1])
assert 70_000 < len(samples) < 90_000, len(samples)

model = WhisperModel("/models/small", device="cpu", compute_type="int8", local_files_only=True)
pieces, info = model.transcribe(samples, language="ru", vad_filter=True, beam_size=1)
assert list(pieces) == [] or info.language == "ru"

settings = horoscope.Settings("http://127.0.0.1:9/none", work, "", [], segment_seconds=5)
start = segs[0][0] + 1
out = work / "clip.mp4"
assert (
    horoscope.cut(settings, horoscope.covering(segs, start, start + 6), start, start + 6, out) == 6
)
assert out.stat().st_size < settings.max_upload_bytes
print("The image decodes the stream format, runs the baked model offline and cuts a clip.")
