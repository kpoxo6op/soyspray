"""Write one Piper synthesis result to stdout as WAV audio."""

import asyncio
import os
import sys
import wave
from typing import BinaryIO

PIPER_HOST = "piper-en.home-automation.svc.cluster.local"
PIPER_PORT = 10200
TIMEOUT = 180


async def synthesize(phrase: str) -> tuple[int, int, int, bytes]:
    """Get one complete PCM audio stream from Piper."""
    from wyoming.audio import AudioChunk, AudioStart, AudioStop
    from wyoming.client import AsyncTcpClient
    from wyoming.tts import Synthesize

    start = None
    chunks = []
    async with AsyncTcpClient(PIPER_HOST, PIPER_PORT) as client:
        await client.write_event(Synthesize(phrase).event())
        while True:
            try:
                event = await asyncio.wait_for(client.read_event(), TIMEOUT)
            except TimeoutError as err:
                raise RuntimeError("Timed out waiting for Piper audio") from err
            if event is None:
                raise RuntimeError("Piper closed the connection")
            if event.type == "error":
                raise RuntimeError(f"Piper error: {event.data}")
            if AudioStart.is_type(event.type):
                if start is not None:
                    raise RuntimeError("Piper sent a duplicate AudioStart")
                start = AudioStart.from_event(event)
            elif AudioChunk.is_type(event.type):
                if start is None:
                    raise RuntimeError("Piper sent audio before AudioStart")
                chunk = AudioChunk.from_event(event)
                if (chunk.rate, chunk.width, chunk.channels) != (
                    start.rate,
                    start.width,
                    start.channels,
                ):
                    raise RuntimeError("Piper changed the audio format")
                chunks.append(chunk.audio)
            elif AudioStop.is_type(event.type):
                break
            else:
                raise RuntimeError(f"Unexpected Piper event: {event.type}")

    if start is None or not any(chunks):
        raise RuntimeError("Piper returned no audio")
    return start.rate, start.width, start.channels, b"".join(chunks)


def write_wav(output: BinaryIO, audio: bytes, *, rate: int, width: int, channels: int) -> None:
    """Write PCM audio as one WAV stream."""
    with wave.open(output, "wb") as wav_file:
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(width)
        wav_file.setframerate(rate)
        wav_file.writeframes(audio)


def main() -> int:
    """Run the command."""
    phrase = os.environ.get("PHRASE", "").strip()
    if not phrase:
        print("PHRASE is required", file=sys.stderr)
        return 2

    try:
        rate, width, channels, audio = asyncio.run(synthesize(phrase))
        write_wav(sys.stdout.buffer, audio, rate=rate, width=width, channels=channels)
    except Exception as err:  # The command must keep failure text out of stdout.
        print(err, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
