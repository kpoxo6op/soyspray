"""Test the Wyoming path from Piper to Speech-to-Phrase."""

import asyncio

from wyoming.asr import Transcribe, Transcript
from wyoming.audio import AudioChunk, AudioStart, AudioStop
from wyoming.client import AsyncTcpClient
from wyoming.tts import Synthesize

PHRASE = "turn on the top"
TIMEOUT = 180
PIPER = "piper-en.home-automation.svc.cluster.local"
SPEECH = "speech-to-phrase.home-automation.svc.cluster.local"


async def receive(client):
    """Read one event before the timeout."""
    event = await asyncio.wait_for(client.read_event(), TIMEOUT)
    if event is None:
        raise RuntimeError("Wyoming service closed the connection")
    if event.type == "error":
        raise RuntimeError(f"Wyoming error: {event.data}")
    return event


async def main() -> None:
    """Synthesize a phrase, transcribe it, and check the result."""
    audio_events = []
    async with AsyncTcpClient(PIPER, 10200) as piper:
        await piper.write_event(Synthesize(PHRASE).event())
        while True:
            event = await receive(piper)
            valid = any(kind.is_type(event.type) for kind in (AudioStart, AudioChunk, AudioStop))
            if not valid:
                raise RuntimeError(f"Unexpected Piper event: {event.type}")
            audio_events.append(event)
            if AudioStop.is_type(event.type):
                break

    if not AudioStart.is_type(audio_events[0].type):
        raise RuntimeError("Piper did not start an audio stream")
    if not any(AudioChunk.is_type(event.type) and event.payload for event in audio_events):
        raise RuntimeError("Piper returned no audio")

    async with AsyncTcpClient(SPEECH, 10300) as speech:
        await speech.write_event(Transcribe(name="en_US-rhasspy", language="en").event())
        for event in audio_events:
            await speech.write_event(event)
        event = await receive(speech)

    if not Transcript.is_type(event.type):
        raise RuntimeError(f"Unexpected Speech-to-Phrase event: {event.type}")

    transcript = Transcript.from_event(event).text
    normalized = " ".join(transcript.casefold().split())
    if normalized not in {"turn on top", "turn on the top"}:
        raise RuntimeError(f"Unexpected transcript: {transcript}")

    print(f"Voice path test passed: {transcript}")


asyncio.run(main())
