"""Check the Piper to GI wake-word Wyoming path."""

import asyncio

from wyoming.audio import AudioChunk, AudioStart, AudioStop
from wyoming.client import AsyncTcpClient
from wyoming.info import Describe, Info
from wyoming.tts import Synthesize
from wyoming.wake import Detect, Detection, NotDetected

PHRASE = "gee eye"
MODEL = "gi"
NEGATIVE_PHRASES = (
    "okay nabu",
    "hey jarvis",
    "hey mycroft",
    "turn on the top",
    "gee",
    "eye",
)
FALLBACK_REQUESTS = ([], ["okay_nabu"])
TIMEOUT = 180
PIPER = ("piper-en.home-automation.svc.cluster.local", 10200)
WAKE = ("openwakeword-gi.home-automation.svc.cluster.local", 10400)


async def receive(client):
    """Read one event with a bounded wait."""
    event = await asyncio.wait_for(client.read_event(), TIMEOUT)
    if event is None:
        raise RuntimeError("Wyoming service closed the connection")
    if event.type == "error":
        raise RuntimeError(f"Wyoming error: {event.data}")
    return event


async def synthesize(phrase: str) -> list:
    """Synthesize one phrase into Wyoming audio events."""
    saw_start = False
    saw_audio = False
    audio_events = []

    async with AsyncTcpClient(*PIPER) as piper:
        await piper.write_event(Synthesize(phrase).event())

        while True:
            event = await receive(piper)
            valid = any(kind.is_type(event.type) for kind in (AudioStart, AudioChunk, AudioStop))
            if not valid:
                raise RuntimeError(f"Unexpected Piper event: {event.type}")

            saw_start |= AudioStart.is_type(event.type)
            saw_audio |= AudioChunk.is_type(event.type) and bool(event.payload)
            audio_events.append(event)
            if AudioStop.is_type(event.type):
                break

        if not saw_start:
            raise RuntimeError("Piper did not start an audio stream")
        if not saw_audio:
            raise RuntimeError("Piper returned no audio")

    return audio_events


async def describe_models() -> set[str]:
    """Return every wake model advertised by the dedicated service."""
    async with AsyncTcpClient(*WAKE) as wake:
        await wake.write_event(Describe().event())
        event = await receive(wake)
    if not Info.is_type(event.type):
        raise RuntimeError(f"Unexpected wake description: {event.type}")
    info = Info.from_event(event)
    return {model.name for program in (info.wake or []) for model in program.models}


async def detect(audio_events: list, names: list[str]):
    """Send one audio stream to the GI detector and return its result."""
    async with AsyncTcpClient(*WAKE) as wake:
        await wake.write_event(Detect(names=names).event())
        for event in audio_events:
            await wake.write_event(event)
        event = await receive(wake)
    return event


async def main() -> None:
    """Require GI detection and reject known non-GI phrases."""
    models = await describe_models()
    if models != {MODEL}:
        raise RuntimeError(f"GI service advertised unexpected wake models: {models}")

    event = await detect(await synthesize(PHRASE), [MODEL])

    if not Detection.is_type(event.type):
        raise RuntimeError(f"GI wake word was not detected: {event.type}")

    detection = Detection.from_event(event)
    if detection.name != MODEL:
        raise RuntimeError(f"Unexpected wake word: {detection.name}")

    for phrase in NEGATIVE_PHRASES:
        event = await detect(await synthesize(phrase), [MODEL])
        if not NotDetected.is_type(event.type):
            raise RuntimeError(f"False GI detection for {phrase!r}: {event.type}")

    nabu_audio = await synthesize("okay nabu")
    for names in FALLBACK_REQUESTS:
        event = await detect(nabu_audio, names)
        if not NotDetected.is_type(event.type):
            raise RuntimeError(f"GI-only fallback accepted {names!r}: {event.type}")

    print(f"GI wake-word smoke passed: {detection.name}; negatives rejected")


if __name__ == "__main__":
    asyncio.run(main())
