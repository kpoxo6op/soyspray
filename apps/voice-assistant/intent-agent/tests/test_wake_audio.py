"""Wake-to-STT audio handoff, which intent and STT tests cannot exercise.

A delayed detector used to consume the beginning of a fast command. Verify the
actual PCM returned to HA, including its prefetched chunk, rather than detection
success alone. Each turn must own its buffer and release it on cancellation.
"""

import asyncio
from types import SimpleNamespace

import pytest
from custom_components.gi_voice.wake_word import BufferedWakeWord
from homeassistant.components.wake_word import DetectionResult


@pytest.mark.parametrize("sizes", [[3200] * 3, [3200] * 10, [32000]])
async def test_pcm_tail_survives_detection_once(sizes):
    chunks = []
    offset = 0
    for index, size in enumerate(sizes):
        chunks.append((bytes([index + 1]) * size, offset / 32))
        offset += size

    async def audio():
        for chunk in chunks:
            yield chunk

    class Detector:
        async def async_process_audio_stream(self, stream, wake_word_id):
            async for _chunk in stream:
                pass
            return DetectionResult(
                wake_word_id="gi", wake_word_phrase="Gi", timestamp=123, queued_audio=[_chunk]
            )

    entity = BufferedWakeWord(SimpleNamespace(entry_id="test", options={}))
    entity.source = lambda: Detector()
    result = await entity._async_process_audio_stream(audio(), "gi")
    assert b"".join(a for a, _ in result.queued_audio) == b"".join(a for a, _ in chunks)[-16000:]
    assert result.queued_audio[0][1] == max(0, offset - 16000) / 32
    assert result.timestamp == 123
    assert result.wake_word_id == "gi"


async def test_canceled_turn_does_not_contaminate_next_turn():
    waiting = asyncio.Event()

    class Detector:
        async def async_process_audio_stream(self, stream, wake_word_id):
            async for chunk in stream:
                if chunk[0] == b"a" * 3200:
                    waiting.set()
                    await asyncio.Future()
            return DetectionResult(wake_word_id="gi", wake_word_phrase="Gi", timestamp=100)

    entity = BufferedWakeWord(SimpleNamespace(entry_id="test", options={}))
    entity.source = lambda: Detector()

    async def audio(value):
        yield value * 3200, 0

    task = asyncio.create_task(entity._async_process_audio_stream(audio(b"a"), "gi"))
    await waiting.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    result = await entity._async_process_audio_stream(audio(b"b"), "gi")
    assert result.queued_audio == [(b"b" * 3200, 0)]
