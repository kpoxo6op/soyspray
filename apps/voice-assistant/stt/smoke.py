"""Exercise the deployed Wyoming boundary without sending a command to HA."""

import asyncio
import re
import wave

from probe import probe
from wyoming.asr import Transcribe, Transcript
from wyoming.audio import AudioChunk, AudioStart, AudioStop
from wyoming.client import AsyncTcpClient


async def smoke():
    for _ in range(60):
        try:
            await probe()
            break
        except (OSError, TimeoutError, ValueError):
            await asyncio.sleep(2)
    else:
        raise RuntimeError("ASR model did not become ready")
    async with asyncio.timeout(30):
        async with AsyncTcpClient("127.0.0.1", 10300) as client:
            await client.write_event(Transcribe(language="en").event())
            await client.write_event(AudioStart(rate=16000, width=2, channels=1).event())
            await client.write_event(
                AudioChunk(rate=16000, width=2, channels=1, audio=bytes(32000)).event()
            )
            await client.write_event(AudioStop().event())
            event = await client.read_event()
            if event is None or not Transcript.is_type(event.type):
                raise ValueError("Missing ASR transcript")
            if Transcript.from_event(event).text.strip():
                raise ValueError("ASR hallucinated speech on silence")
    with wave.open(
        "/models/sherpa-onnx-nemo-parakeet-tdt-0.6b-v2-int8/test_wavs/0.wav", "rb"
    ) as wav:
        assert wav.getframerate() == 16000 and wav.getnchannels() == 1 and wav.getsampwidth() == 2
        audio = wav.readframes(wav.getnframes())
    async with asyncio.timeout(30):
        async with AsyncTcpClient("127.0.0.1", 10300) as client:
            await client.write_event(Transcribe(language="en").event())
            await client.write_event(AudioStart(rate=16000, width=2, channels=1).event())
            await client.write_event(
                AudioChunk(rate=16000, width=2, channels=1, audio=audio).event()
            )
            await client.write_event(AudioStop().event())
            event = await client.read_event()
            if event is None or not Transcript.is_type(event.type):
                raise ValueError("Missing positive ASR transcript")
            words = set(re.findall(r"\w+", Transcript.from_event(event).text.casefold()))
            if not {"wish", "see", "portrait"}.issubset(words):
                raise ValueError("ASR did not recognize the checked speech sample")


if __name__ == "__main__":
    asyncio.run(smoke())
