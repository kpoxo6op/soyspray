"""Preserve command audio consumed while a remote wake detector responds."""

from collections import deque
from dataclasses import replace

from homeassistant.components import wake_word
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er

# Half a second of mono 16 kHz signed 16-bit audio. Retaining it adds no wait.
BUFFER_BYTES = 16000


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([BufferedWakeWord(entry)])


class BufferedWakeWord(wake_word.WakeWordDetectionEntity):
    """Delegate detection unchanged and replay a bounded in-memory audio tail."""

    _attr_name = "GI buffered wake"

    def __init__(self, entry):
        self.entry = entry
        self._attr_unique_id = entry.entry_id + "_buffered_wake"

    def source(self):
        selected = self.entry.options.get("wake_word_source")
        if selected:
            candidates = [selected]
        else:
            candidates = [
                entity.entity_id
                for entity in er.async_get(self.hass).entities.values()
                if entity.domain == "wake_word"
                and entity.platform == "wyoming"
                and not entity.disabled
            ]
        if len(candidates) != 1:
            raise HomeAssistantError("Select the wake detector in GI Flex options")
        source = wake_word.async_get_wake_word_detection_entity(self.hass, candidates[0])
        if source is None or isinstance(source, BufferedWakeWord):
            raise HomeAssistantError("The selected wake detector is unavailable")
        return source

    async def get_supported_wake_words(self):
        try:
            return await self.source().get_supported_wake_words()
        except HomeAssistantError:
            return []

    async def _async_process_audio_stream(self, stream, wake_word_id):
        recent = deque()
        size = 0

        async def capture():
            nonlocal size
            async for audio, timestamp in stream:
                recent.append((audio, timestamp))
                size += len(audio)
                while size > BUFFER_BYTES:
                    first, first_timestamp = recent.popleft()
                    excess = size - BUFFER_BYTES
                    if len(first) > excess:
                        # PCM samples are two bytes; input from HA is aligned.
                        recent.appendleft((first[excess:], first_timestamp + excess / 32))
                        size -= excess
                    else:
                        size -= len(first)
                yield audio, timestamp

        try:
            result = await self.source().async_process_audio_stream(capture(), wake_word_id)
            if result is None:
                return None
            # The delegated provider can return its last prefetched chunk. It
            # already passed capture(), so never play that chunk twice.
            tail = list(recent)
            for audio, timestamp in result.queued_audio or []:
                end = tail[-1][1] + len(tail[-1][0]) / 32 if tail else timestamp
                overlap = max(0, round((end - timestamp) * 32))
                if overlap < len(audio):
                    tail.append((audio[overlap:], timestamp + overlap / 32))
            return replace(result, queued_audio=tail)
        finally:
            recent.clear()
