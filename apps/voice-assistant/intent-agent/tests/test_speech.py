"""Exercise HA's speech boundary; conversation tests do not process audio."""

import asyncio
import io
import wave
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import aiohttp
import pytest
from aiohttp import web
from custom_components.gi_voice import stt as speech
from custom_components.gi_voice.const import CLOUD_ENABLED, DOMAIN, LOCAL_STT, OPENAI_KEY
from homeassistant.components import stt
from homeassistant.components.homeassistant.exposed_entities import async_expose_entity
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

META = stt.SpeechMetadata(
    "en",
    stt.AudioFormats.WAV,
    stt.AudioCodecs.PCM,
    stt.AudioBitRates.BITRATE_16,
    stt.AudioSampleRates.SAMPLERATE_16000,
    stt.AudioChannels.CHANNEL_MONO,
)
PCM = b"\x01\x00" * 1600


async def chunks(data=PCM):
    yield data[:100]
    yield data[100:]


@pytest.fixture
async def engine(hass):
    await async_setup_component(hass, "homeassistant", {})
    lights = []
    for name in ["Top", "Middle", "Bottom", "Peanut"]:
        eid = "light." + name.lower()
        lights.append(eid)
        hass.states.async_set(eid, "off", {"friendly_name": name})
        async_expose_entity(hass, "conversation", eid, True)
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"api_key": "deepseek-test", "lights": lights},
        options={CLOUD_ENABLED: True, OPENAI_KEY: "private-test-key", LOCAL_STT: "stt.local"},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    entity = stt.async_get_speech_to_text_entity(hass, "stt.gi_flex_speech")
    assert entity is not None
    return entity


def decoder(text="Turn on button."):
    async def recognize(metadata, stream):
        assert metadata == META
        assert b"".join([part async for part in stream]) == PCM
        return stt.SpeechResult(text, stt.SpeechResultState.SUCCESS)

    return SimpleNamespace(async_process_audio_stream=AsyncMock(side_effect=recognize))


@pytest.mark.parametrize(
    "text,accepted",
    [
        ("Turn on the Top.", True),
        ("switch Peanut off!", True),
        ("Bottom", True),
        ("Set Middle brightness to 40%", True),
        ("Set Top to 100 percent", True),
        ("Don't turn Peanut on", False),
        ("Turn Top on tomorrow", False),
        ("My friend said turn Top on", False),
        ("Turn on button", False),
        ("Set Top to 140 percent", False),
        ("Turn it off", False),
    ],
)
def test_exact_gate_keeps_qualifiers_and_unknown_names_out(text, accepted):
    assert speech.local_command(text) is accepted


async def test_known_command_uses_local_audio_without_http(engine, aioclient_mock):
    local = decoder("Turn off Top.")
    with patch.object(stt, "async_get_speech_to_text_engine", return_value=local):
        result = await engine.internal_async_process_audio_stream(META, chunks())
    assert result.text == "Turn off Top."
    local.async_process_audio_stream.assert_awaited_once()
    assert aioclient_mock.call_count == 0


async def test_unclear_audio_sent_once_as_valid_wav(engine, aiohttp_server, socket_enabled, caplog):
    received = []

    async def transcribe(request):
        reader = await request.multipart()
        fields = {}
        async for part in reader:
            fields[part.name] = await part.read()
        received.append((request.headers.get("Authorization"), fields))
        return web.json_response({"text": "Turn on Bottom."})

    app = web.Application()
    app.router.add_post("/transcribe", transcribe)
    server = await aiohttp_server(app)
    with (
        patch.object(speech, "API", str(server.make_url("/transcribe"))),
        patch.object(stt, "async_get_speech_to_text_engine", return_value=decoder()),
    ):
        result = await engine.internal_async_process_audio_stream(META, chunks())
    assert result.text == "Turn on Bottom."
    assert len(received) == 1
    authorization, fields = received[0]
    assert authorization == "Bearer private-test-key"
    assert fields["model"] == b"gpt-transcribe"
    assert fields["languages[]"] == b"en"
    assert fields["prompt"] == b"Top, Middle, Bottom, Peanut"
    with wave.open(io.BytesIO(fields["file"])) as wav:
        assert (wav.getframerate(), wav.getsampwidth(), wav.getnchannels()) == (16000, 2, 1)
        assert wav.readframes(wav.getnframes()) == PCM
    assert all(
        value not in caplog.text
        for value in ["private-test-key", "Turn on button", "Turn on Bottom"]
    )


@pytest.mark.parametrize(
    "reply", [401, 429, 500, "malformed", "empty", "oversized", "timeout", "dns"]
)
async def test_cloud_failure_returns_local_text_once(engine, aioclient_mock, reply):
    if reply in ["timeout", "dns"]:
        aioclient_mock.post(
            speech.API, exc=TimeoutError if reply == "timeout" else aiohttp.ClientConnectionError
        )
    elif reply == "malformed":
        aioclient_mock.post(speech.API, text="not json")
    elif reply == "empty":
        aioclient_mock.post(speech.API, json={"text": ""})
    elif reply == "oversized":
        aioclient_mock.post(speech.API, text="x" * 65537)
    else:
        aioclient_mock.post(speech.API, status=reply)
    with patch.object(stt, "async_get_speech_to_text_engine", return_value=decoder()):
        result = await engine.internal_async_process_audio_stream(META, chunks())
    assert result.text == "Turn on button."
    assert aioclient_mock.call_count == 1


async def test_real_deadline_stops_waiting_for_cloud(engine):
    async def hung(*args, **kwargs):
        await asyncio.sleep(30)

    session = SimpleNamespace(post=lambda *a, **kw: HungRequest())

    class HungRequest:
        __aenter__ = hung

        async def __aexit__(self, *args):
            return False

    with (
        patch.object(stt, "async_get_speech_to_text_engine", return_value=decoder()),
        patch.object(speech, "async_get_clientsession", return_value=session),
    ):
        started = asyncio.get_running_loop().time()
        result = await engine.internal_async_process_audio_stream(META, chunks())
        elapsed = asyncio.get_running_loop().time() - started
    assert result.text == "Turn on button."
    assert 2.8 <= elapsed < 4


async def test_disabled_or_changed_catalog_never_uploads(engine, hass, aioclient_mock):
    with (
        patch.object(stt, "async_get_speech_to_text_engine", return_value=decoder()),
        patch.object(hass.config_entries, "async_reload", new=AsyncMock()),
    ):
        hass.config_entries.async_update_entry(
            engine.entry, options={**engine.entry.options, CLOUD_ENABLED: False}
        )
        await hass.async_block_till_done()
        assert (
            await engine.internal_async_process_audio_stream(META, chunks())
        ).text == "Turn on button."
        hass.config_entries.async_update_entry(
            engine.entry, options={**engine.entry.options, CLOUD_ENABLED: True}
        )
        await hass.async_block_till_done()
        async_expose_entity(hass, "conversation", "light.peanut", False)
        assert (
            await engine.internal_async_process_audio_stream(META, chunks())
        ).text == "Turn on button."
    assert aioclient_mock.call_count == 0


async def test_unloading_cancels_audio_before_any_cloud_call(engine, hass, aioclient_mock):
    entered = asyncio.Event()

    async def unfinished_audio():
        entered.set()
        yield PCM
        await asyncio.sleep(30)

    task = asyncio.create_task(engine.internal_async_process_audio_stream(META, unfinished_audio()))
    await entered.wait()
    assert await hass.config_entries.async_unload(engine.entry.entry_id)
    with pytest.raises(asyncio.CancelledError):
        await task
    assert aioclient_mock.call_count == 0


async def test_audio_limit_never_reaches_a_decoder(engine, aioclient_mock):
    with patch.object(stt, "async_get_speech_to_text_engine") as lookup:
        result = await engine.internal_async_process_audio_stream(
            META, chunks(b"x" * (speech.MAX_AUDIO_BYTES + 1))
        )
    assert result.result == stt.SpeechResultState.ERROR
    lookup.assert_not_called()
    assert aioclient_mock.call_count == 0


async def test_missing_local_engine_never_silently_enables_cloud_for_all(engine, aioclient_mock):
    with patch.object(stt, "async_get_speech_to_text_engine", return_value=None):
        result = await engine.internal_async_process_audio_stream(META, chunks())
    assert result.result == stt.SpeechResultState.ERROR
    assert aioclient_mock.call_count == 0


async def test_overlapping_turns_keep_audio_and_responses_separate(
    engine, aiohttp_server, socket_enabled
):
    both_started = asyncio.Event()
    received = []

    async def transcribe(request):
        parts = await request.multipart()
        async for part in parts:
            if part.name == "file":
                with wave.open(io.BytesIO(await part.read())) as wav:
                    pcm = wav.readframes(wav.getnframes())
        received.append(pcm)
        if len(received) == 2:
            both_started.set()
        await both_started.wait()
        return web.json_response({"text": "Top" if pcm == PCM else "Bottom"})

    app = web.Application()
    app.router.add_post("/transcribe", transcribe)
    server = await aiohttp_server(app)
    local = SimpleNamespace(
        async_process_audio_stream=AsyncMock(
            return_value=stt.SpeechResult("unclear", stt.SpeechResultState.SUCCESS)
        )
    )
    with (
        patch.object(speech, "API", str(server.make_url("/transcribe"))),
        patch.object(stt, "async_get_speech_to_text_engine", return_value=local),
    ):
        top, bottom = await asyncio.gather(
            engine.internal_async_process_audio_stream(META, chunks()),
            engine.internal_async_process_audio_stream(META, chunks(b"\x02\x00" * 1600)),
        )
    assert [top.text, bottom.text] == ["Top", "Bottom"]
    assert len(received) == 2


async def test_options_are_opt_in_validate_without_audio_and_retain_key(
    engine, hass, aioclient_mock
):
    aioclient_mock.get(
        "https://api.openai.com/v1/models/gpt-transcribe", json={"id": "gpt-transcribe"}
    )
    flow = await hass.config_entries.options.async_init(engine.entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        flow["flow_id"],
        user_input={
            CLOUD_ENABLED: True,
            LOCAL_STT: "stt.local",
            OPENAI_KEY: "",
        },
    )
    assert result["type"] == "create_entry"
    assert result["data"][OPENAI_KEY] == "private-test-key"
    assert aioclient_mock.call_count == 1
    assert aioclient_mock.mock_calls[0][0] == "GET"


async def test_everyday_streams_to_phrase_before_the_microphone_finishes(engine, aioclient_mock):
    """The old buffer-first path cannot own the streaming latency contract."""
    everyday = stt.async_get_speech_to_text_entity(engine.hass, "stt.gi_everyday_speech")
    first_seen = asyncio.Event()

    async def microphone():
        yield PCM[:100]
        async with asyncio.timeout(1):
            await first_seen.wait()
        yield PCM[100:]

    async def phrase(metadata, stream):
        collected = bytearray()
        async for part in stream:
            collected.extend(part)
            first_seen.set()
        assert collected == PCM
        return stt.SpeechResult("Top on", stt.SpeechResultState.SUCCESS)

    with patch.object(
        stt,
        "async_get_speech_to_text_engine",
        return_value=SimpleNamespace(async_process_audio_stream=phrase),
    ) as resolve:
        result = await everyday.internal_async_process_audio_stream(META, microphone())
    assert result.text == "Top on"
    assert resolve.call_count == 1
    assert aioclient_mock.call_count == 0


async def test_everyday_rejected_phrase_replays_same_turn_without_cloud_when_disabled(
    engine, aioclient_mock
):
    """New fallback must preserve audio and the everyday cloud-off boundary."""
    everyday = stt.async_get_speech_to_text_entity(engine.hass, "stt.gi_everyday_speech")
    engine.hass.config_entries.async_update_entry(engine.entry, options={LOCAL_STT: "stt.local"})
    await engine.hass.async_block_till_done()
    everyday = stt.async_get_speech_to_text_entity(engine.hass, "stt.gi_everyday_speech")
    phrase, opened = decoder(""), decoder("Please illuminate Top")
    with patch.object(stt, "async_get_speech_to_text_engine", side_effect=[phrase, opened]):
        result = await everyday.internal_async_process_audio_stream(META, chunks())
    assert result.text == "Please illuminate Top"
    opened.async_process_audio_stream.assert_awaited_once()
    assert aioclient_mock.call_count == 0
