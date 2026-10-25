"""Keep exact local light phrases; retry unclear speech once with consent."""

import asyncio
import io
import json
import logging
import re
import time
import wave

import aiohttp
from homeassistant.components import stt
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import CLOUD_ENABLED, LOCAL_STT, OPENAI_KEY
from .const import SPEECH_MODEL as MODEL

_LOGGER = logging.getLogger(__name__)
API = "https://api.openai.com/v1/audio/transcriptions"
NAME_PROMPT = "Top, Middle, Bottom, Peanut"
MAX_AUDIO_BYTES = 20 * 16000 * 2
REQUEST_TIMEOUT = 3
_NAME = r"(?:top|middle|bottom|peanut)"
_PHRASE = re.compile(
    rf"(?:{_NAME}|(?:turn|switch) (?:on|off) (?:the )?{_NAME}(?: light)?"
    rf"|(?:turn|switch) (?:the )?{_NAME}(?: light)? (?:on|off)"
    rf"|set (?:the )?{_NAME}(?: brightness)? to (?:[1-9]|[1-9][0-9]|100) percent)"
)


def local_command(text):
    """Recognize a small exact grammar; never repair or guess a name."""
    value = re.sub(r"[.,!?]", "", text.casefold()).replace("%", " percent")
    value = " ".join(value.split())
    return _PHRASE.fullmatch(value) is not None


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([GiSpeech(entry), EverydaySpeech(entry)])


class GiSpeech(stt.SpeechToTextEntity):
    """Bind the buffer and both decoder results to one STT invocation."""

    _attr_name = "GI Flex speech"

    def __init__(self, entry):
        self.entry = entry
        self._attr_unique_id = entry.entry_id + "_speech"
        self._active = set()
        self._removed = False

    @property
    def supported_languages(self):
        return ["en"]

    @property
    def supported_formats(self):
        return [stt.AudioFormats.WAV]

    @property
    def supported_codecs(self):
        return [stt.AudioCodecs.PCM]

    @property
    def supported_bit_rates(self):
        return [stt.AudioBitRates.BITRATE_16]

    @property
    def supported_sample_rates(self):
        return [stt.AudioSampleRates.SAMPLERATE_16000]

    @property
    def supported_channels(self):
        return [stt.AudioChannels.CHANNEL_MONO]

    async def async_will_remove_from_hass(self):
        self._removed = True
        tasks = tuple(self._active)
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        await super().async_will_remove_from_hass()

    async def async_process_audio_stream(self, metadata, stream):
        failure = stt.SpeechResult(None, stt.SpeechResultState.ERROR)
        if self._removed or len(self._active) >= 2 or not self.check_metadata(metadata):
            return failure
        task = asyncio.current_task()
        self._active.add(task)
        audio = bytearray()
        local = failure
        started = time.monotonic()
        route = "failed"
        try:
            async with asyncio.timeout(25):
                async for chunk in stream:
                    if len(audio) + len(chunk) > MAX_AUDIO_BYTES:
                        route = "audio_limit"
                        return failure
                    audio.extend(chunk)
            if not audio or len(audio) % 2:
                return failure
            if not any(audio):
                route = "silence"
                return stt.SpeechResult("", stt.SpeechResultState.SUCCESS)

            async def replay():
                for index in range(0, len(audio), 32000):
                    yield bytes(audio[index : index + 32000])

            engine = stt.async_get_speech_to_text_engine(
                self.hass, self.entry.options.get(LOCAL_STT, "stt.faster_whisper")
            )
            if engine is None or isinstance(engine, GiSpeech):
                route = "invalid_local_engine"
                return failure
            try:
                async with asyncio.timeout(5):
                    local = await engine.async_process_audio_stream(metadata, replay())
            except (aiohttp.ClientError, OSError, TimeoutError):
                local = failure
            local_text = local.text if local.result == stt.SpeechResultState.SUCCESS else None
            if local_text and local_command(local_text):
                route = "local"
                return local
            options = self.entry.options
            if not options.get(CLOUD_ENABLED) or not options.get(OPENAI_KEY):
                route = "cloud_disabled"
                return local
            # The measured prompt is valid only for the same currently eligible names.
            catalog = self.entry.runtime_data.catalog()
            if {light["name"] for light in catalog.values()} != set(NAME_PROMPT.split(", ")):
                route = "catalog_changed"
                return local
            output = io.BytesIO()
            with wave.open(output, "wb") as wav:
                wav.setparams((1, 2, 16000, 0, "NONE", "not compressed"))
                wav.writeframes(audio)
            form = aiohttp.FormData()
            form.add_field("model", MODEL)
            form.add_field("languages[]", "en")
            form.add_field("prompt", NAME_PROMPT)
            form.add_field(
                "file", output.getvalue(), filename="command.wav", content_type="audio/wav"
            )
            route = "cloud_fallback"
            try:
                async with asyncio.timeout(REQUEST_TIMEOUT):
                    async with async_get_clientsession(self.hass).post(
                        API,
                        headers={"Authorization": "Bearer " + options[OPENAI_KEY]},
                        data=form,
                        allow_redirects=False,
                    ) as response:
                        if response.status != 200:
                            return local
                        raw = bytearray()
                        async for chunk in response.content.iter_chunked(8192):
                            raw.extend(chunk)
                            if len(raw) > 65536:
                                return local
                        text = json.loads(raw).get("text")
                        if isinstance(text, str) and text.strip() and len(text) <= 8192:
                            route = "cloud"
                            return stt.SpeechResult(text, stt.SpeechResultState.SUCCESS)
            except (aiohttp.ClientError, OSError, TimeoutError, ValueError, AttributeError):
                pass
            return local
        except TimeoutError:
            return failure
        finally:
            audio.clear()
            self._active.discard(task)
            _LOGGER.debug(
                "GI speech route=%s elapsed_ms=%.0f", route, (time.monotonic() - started) * 1000
            )


class EverydaySpeech(GiSpeech):
    """Keep open speech qualifiers intact; retry unclear audio locally first."""

    _attr_name = "GI Everyday speech"

    def __init__(self, entry):
        super().__init__(entry)
        self._attr_unique_id = entry.entry_id + "_everyday_speech"
        self.sentences = None

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        from .everyday import load_sentences

        self.sentences = await self.hass.async_add_executor_job(load_sentences)

    async def async_process_audio_stream(self, metadata, stream):
        from .control import BLOCKED, catalog
        from .everyday import match_command

        failure = stt.SpeechResult(None, stt.SpeechResultState.ERROR)
        if self._removed or len(self._active) >= 2 or not self.check_metadata(metadata):
            return failure
        task = asyncio.current_task()
        self._active.add(task)
        audio = bytearray()
        route = "failed"
        started = time.monotonic()
        try:

            async def capture():
                async for chunk in stream:
                    if len(audio) + len(chunk) > MAX_AUDIO_BYTES:
                        raise ValueError("Audio limit")
                    audio.extend(chunk)
                    yield chunk

            primary = stt.async_get_speech_to_text_engine(
                self.hass, self.entry.options.get(LOCAL_STT, "stt.faster_whisper")
            )
            if primary is None or isinstance(primary, GiSpeech):
                return failure
            async with asyncio.timeout(25):
                local = await primary.async_process_audio_stream(metadata, capture())
            if local.result == stt.SpeechResultState.SUCCESS and local.text:
                if BLOCKED.search(local.text) or match_command(
                    local.text, self.sentences, catalog(self.hass)
                ):
                    route = "local_fast"
                    return local
            if not audio or len(audio) % 2:
                return failure

            async def replay():
                for index in range(0, len(audio), 32000):
                    yield bytes(audio[index : index + 32000])

            engine = stt.async_get_speech_to_text_engine(self.hass, "stt.gi_whisper")
            needs_retry = (
                local.result != stt.SpeechResultState.SUCCESS or not (local.text or "").strip()
            )
            if (
                needs_retry
                and engine is not None
                and not isinstance(engine, GiSpeech)
                and engine is not primary
            ):
                try:
                    async with asyncio.timeout(3):
                        retry = await engine.async_process_audio_stream(metadata, replay())
                    if retry.result == stt.SpeechResultState.SUCCESS and retry.text:
                        local = retry
                except (aiohttp.ClientError, OSError, TimeoutError):
                    pass
            if local.result == stt.SpeechResultState.SUCCESS and local.text:
                if BLOCKED.search(local.text) or match_command(
                    local.text, self.sentences, catalog(self.hass)
                ):
                    route = "local_retry"
                    return local
            options = self.entry.options
            if not options.get(CLOUD_ENABLED) or not options.get(OPENAI_KEY):
                route = "open_local"
                return local
            output = io.BytesIO()
            with wave.open(output, "wb") as wav:
                wav.setparams((1, 2, 16000, 0, "NONE", "not compressed"))
                wav.writeframes(audio)
            form = aiohttp.FormData()
            form.add_field("model", MODEL)
            form.add_field("languages[]", "en")
            form.add_field("languages[]", "ru")
            form.add_field(
                "prompt",
                ", ".join(sorted({item["name"] for item in catalog(self.hass).values()}))
                + ", OTV Prim, ОТВ Прим, YouTube, Jellyfin, Twitch",
            )
            form.add_field(
                "file", output.getvalue(), filename="command.wav", content_type="audio/wav"
            )
            route = "cloud_attempt"
            try:
                async with asyncio.timeout(REQUEST_TIMEOUT):
                    async with async_get_clientsession(self.hass).post(
                        API,
                        headers={"Authorization": "Bearer " + options[OPENAI_KEY]},
                        data=form,
                        allow_redirects=False,
                    ) as response:
                        if response.status == 200:
                            raw = await response.content.read(65537)
                            if len(raw) <= 65536:
                                text = json.loads(raw).get("text")
                                if isinstance(text, str) and text.strip() and len(text) <= 8192:
                                    route = "cloud"
                                    return stt.SpeechResult(text, stt.SpeechResultState.SUCCESS)
            except (aiohttp.ClientError, OSError, TimeoutError, ValueError, AttributeError):
                pass
            return local
        except (aiohttp.ClientError, OSError, TimeoutError, ValueError):
            return failure
        finally:
            audio.clear()
            self._active.discard(task)
            self.hass.bus.async_fire(
                "gi_voice_speech",
                {"route": route, "elapsed_ms": round((time.monotonic() - started) * 1000)},
            )
