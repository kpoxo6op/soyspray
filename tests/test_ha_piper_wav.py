from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import wave
from importlib.util import module_from_spec, spec_from_file_location
from io import BytesIO
from types import ModuleType, SimpleNamespace

from conftest import ROOT

SCRIPT = ROOT / "scripts/ha_piper_wav.py"


def load_script():
    spec = spec_from_file_location("ha_piper_wav", SCRIPT)
    assert spec and spec.loader
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def install_fake_wyoming(monkeypatch, events, *, read_delay=0):
    class EventType:
        event_type = ""

        @classmethod
        def is_type(cls, event_type):
            return event_type == cls.event_type

    class AudioStart(EventType):
        event_type = "audio-start"

        @staticmethod
        def from_event(event):
            return SimpleNamespace(**event.data)

    class AudioChunk(EventType):
        event_type = "audio-chunk"

        @staticmethod
        def from_event(event):
            return SimpleNamespace(audio=event.payload, **event.data)

    class AudioStop(EventType):
        event_type = "audio-stop"

    class Synthesize:
        def __init__(self, text):
            self.text = text

        def event(self):
            return SimpleNamespace(type="synthesize", data={"text": self.text})

    class AsyncTcpClient:
        instances = []

        def __init__(self, host, port):
            self.host = host
            self.port = port
            self.events = list(events)
            self.writes = []
            self.instances.append(self)

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def write_event(self, event):
            self.writes.append(event)

        async def read_event(self):
            if read_delay:
                await asyncio.sleep(read_delay)
            return self.events.pop(0)

    modules = {
        "wyoming": ModuleType("wyoming"),
        "wyoming.audio": ModuleType("wyoming.audio"),
        "wyoming.client": ModuleType("wyoming.client"),
        "wyoming.tts": ModuleType("wyoming.tts"),
    }
    modules["wyoming.audio"].AudioStart = AudioStart
    modules["wyoming.audio"].AudioChunk = AudioChunk
    modules["wyoming.audio"].AudioStop = AudioStop
    modules["wyoming.client"].AsyncTcpClient = AsyncTcpClient
    modules["wyoming.tts"].Synthesize = Synthesize
    for name, module in modules.items():
        monkeypatch.setitem(sys.modules, name, module)

    return AsyncTcpClient


def test_phrase_is_required_before_writing_stdout() -> None:
    env = os.environ.copy()
    env.pop("PHRASE", None)

    result = subprocess.run(
        [sys.executable, SCRIPT],
        cwd=ROOT,
        env=env,
        check=False,
        capture_output=True,
    )

    assert result.returncode != 0
    assert result.stdout == b""
    assert b"PHRASE is required" in result.stderr


def test_write_wav_emits_a_valid_mono_stream() -> None:
    script = load_script()
    output = BytesIO()
    audio = b"\x00\x00\x01\x00"

    script.write_wav(output, audio, rate=16000, width=2, channels=1)

    assert output.getvalue().startswith(b"RIFF")
    with wave.open(BytesIO(output.getvalue()), "rb") as wav_file:
        assert wav_file.getparams()[:4] == (1, 2, 16000, 2)
        assert wav_file.readframes(2) == audio


def test_synthesize_collects_one_complete_piper_stream(monkeypatch) -> None:
    events = [
        SimpleNamespace(type="audio-start", data={"rate": 16000, "width": 2, "channels": 1}),
        SimpleNamespace(
            type="audio-chunk",
            data={"rate": 16000, "width": 2, "channels": 1},
            payload=b"\x01\x00",
        ),
        SimpleNamespace(
            type="audio-chunk",
            data={"rate": 16000, "width": 2, "channels": 1},
            payload=b"\x02\x00",
        ),
        SimpleNamespace(type="audio-stop", data={}),
    ]
    client_class = install_fake_wyoming(monkeypatch, events)
    script = load_script()

    result = asyncio.run(script.synthesize("turn on the lights"))

    assert result == (16000, 2, 1, b"\x01\x00\x02\x00")
    assert (client_class.instances[0].host, client_class.instances[0].port) == (
        "piper-en.home-automation.svc.cluster.local",
        10200,
    )
    assert client_class.instances[0].writes[0].data == {"text": "turn on the lights"}


def test_synthesize_reports_a_bounded_piper_timeout(monkeypatch) -> None:
    import pytest

    install_fake_wyoming(monkeypatch, [], read_delay=1)
    script = load_script()
    script.TIMEOUT = 0.001

    with pytest.raises(RuntimeError, match="Timed out waiting for Piper audio"):
        asyncio.run(script.synthesize("turn on the lights"))
