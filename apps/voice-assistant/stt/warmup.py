"""Warm decoding on silence before the first real voice command."""

import asyncio

from probe import probe
from wyoming.asr import Transcribe, Transcript
from wyoming.audio import AudioChunk, AudioStart, AudioStop
from wyoming.client import AsyncTcpClient


async def warmup():
    await probe()
    async with asyncio.timeout(12):
        async with AsyncTcpClient("127.0.0.1", 10300) as client:
            await client.write_event(Transcribe(language="en").event())
            await client.write_event(AudioStart(rate=16000, width=2, channels=1).event())
            await client.write_event(
                AudioChunk(rate=16000, width=2, channels=1, audio=bytes(32000)).event()
            )
            await client.write_event(AudioStop().event())
            event = await client.read_event()
            if (
                event is None
                or not Transcript.is_type(event.type)
                or Transcript.from_event(event).text.strip()
            ):
                raise ValueError("Speech decoder did not pass its silence warmup")


if __name__ == "__main__":
    asyncio.run(warmup())
