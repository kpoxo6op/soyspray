"""Operator-only Wyoming benchmark; stdin is synthetic audio, never device traffic."""

import asyncio
import base64
import json
import math
import os
import re
import statistics
import subprocess
import sys
import time
from pathlib import Path

from wyoming.asr import Transcribe, Transcript
from wyoming.audio import AudioChunk, AudioStart, AudioStop
from wyoming.client import AsyncTcpClient
from wyoming.info import Describe, Info


def normalize(text):
    return re.sub(r"[^a-z0-9 ]", "", text.casefold()).strip()


def cpu_stat():
    return {
        key: int(value)
        for key, value in (
            line.split() for line in Path("/sys/fs/cgroup/cpu.stat").read_text().splitlines()
        )
    }


async def transcribe(audio):
    async with asyncio.timeout(90), AsyncTcpClient("127.0.0.1", 10300) as client:
        await client.write_event(Transcribe(language="en").event())
        await client.write_event(AudioStart(rate=16000, width=2, channels=1).event())
        for index in range(0, len(audio), 32000):
            await client.write_event(
                AudioChunk(
                    rate=16000, width=2, channels=1, audio=audio[index : index + 32000]
                ).event()
            )
        await client.write_event(AudioStop().event())
        start = time.perf_counter()
        event = await client.read_event()
        assert event and Transcript.is_type(event.type)
        return Transcript.from_event(event).text, (time.perf_counter() - start) * 1000


async def main():
    rows = [json.loads(line) for line in sys.stdin if line.strip()]
    assert 1 <= len(rows) <= 40
    assert all(row["rate"] == 16000 and len(row["audio"]) < 500000 for row in rows)
    for candidate in ("parakeet", "base.en", "small.en"):
        library = "sherpa" if candidate == "parakeet" else "faster-whisper"
        model = (
            "sherpa-onnx-nemo-parakeet-tdt-0.6b-v2-int8"
            if candidate == "parakeet"
            else "/models/" + candidate
        )
        command = [
            sys.executable,
            "/app/serve.py",
            "--uri",
            "tcp://0.0.0.0:10300",
            "--data-dir",
            "/models",
            "--download-dir",
            "/models",
            "--local-files-only",
            "--language",
            "en",
            "--stt-library",
            library,
            "--model",
            model,
            "--cpu-threads",
            "2",
            "--beam-size",
            "1",
            "--compute-type",
            "int8",
            "--vad-filter",
        ]
        start = time.perf_counter()
        process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            async with asyncio.timeout(120):
                while True:
                    assert process.poll() is None, "Decoder exited before readiness"
                    try:
                        async with AsyncTcpClient("127.0.0.1", 10300) as client:
                            await client.write_event(Describe().event())
                            event = await client.read_event()
                            if event and Info.is_type(event.type):
                                break
                    except OSError:
                        pass
                    await asyncio.sleep(0.2)
            silence, _ = await transcribe(bytes(32000))
            assert not silence.strip(), "Decoder hallucinated on silence"
            load_ms = (time.perf_counter() - start) * 1000
            before = cpu_stat()
            results = []
            for row in rows:
                text, elapsed = await transcribe(base64.b64decode(row["audio"], validate=True))
                result = {
                    "candidate": candidate,
                    "case": row["case"],
                    "expected": row["text"],
                    "transcript": text,
                    "decode_ms": round(elapsed, 2),
                    "exact_normalized": normalize(text) == normalize(row["text"]),
                    "scope": "node-synthetic; Wyoming, no HA actions or microphone",
                }
                results.append(result)
                print(json.dumps(result), flush=True)
            after = cpu_stat()
            status = Path(f"/proc/{process.pid}/status").read_text().splitlines()
            peak_kib = int(next(line for line in status if line.startswith("VmHWM:")).split()[1])
            times = sorted(result["decode_ms"] for result in results)
            print(
                json.dumps(
                    {
                        "summary": True,
                        "candidate": candidate,
                        "cases": len(rows),
                        "exact": sum(result["exact_normalized"] for result in results),
                        "median_decode_ms": statistics.median(times),
                        "p95_decode_ms": times[math.ceil(0.95 * len(times)) - 1],
                        "peak_rss_mib": round(peak_kib / 1024, 1),
                        "load_ms": round(load_ms, 2),
                        "cpu_delta": {key: after[key] - before[key] for key in before},
                        "node": os.environ["BENCHMARK_NODE"],
                        "scope": "node-synthetic; Wyoming, no HA actions or microphone",
                    }
                ),
                flush=True,
            )
        finally:
            process.terminate()
            process.wait(timeout=15)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    finally:
        Path("/tmp/done").touch()
