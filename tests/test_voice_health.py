"""Voice recovery bounds and metadata-only export at their public boundaries."""

import asyncio
import importlib.util
import json
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "voice_observer", ROOT / "apps/voice-assistant/health/observer.py"
)
observer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(observer)


def test_export_excludes_unrelated_entities_and_clears_stale_connection():
    metrics = observer.Metrics()
    metrics.connected = True
    for entity in observer.ENTITIES:
        metrics.update(entity, 1)
    metrics.update("private_room_occupancy", 1234)
    metrics.update("gi_uptime", float("nan"))
    assert metrics.ready
    assert "private_room" not in metrics.render()
    assert "nan" not in metrics.render()
    metrics.reset()
    assert not metrics.ready
    assert "voice_device_connected 0" in metrics.render()
    assert "voice_listen_expected" not in metrics.render()


def test_http_metrics_stay_available_when_device_is_unavailable():
    async def check():
        metrics = observer.Metrics()
        server = await asyncio.start_server(
            lambda r, w: observer.serve(metrics, r, w), "127.0.0.1", 0
        )
        try:
            port = server.sockets[0].getsockname()[1]
            for path, status in (("metrics", "200 OK"), ("healthz", "503 Service Unavailable")):
                reader, writer = await asyncio.open_connection("127.0.0.1", port)
                writer.write(f"GET /{path} HTTP/1.1\r\nHost: localhost\r\n\r\n".encode())
                await writer.drain()
                result = await reader.read()
                assert status.encode() in result
                writer.close()
                await writer.wait_closed()
        finally:
            server.close()
            await server.wait_closed()

    asyncio.run(check())


@pytest.mark.parametrize(
    "response,healthy",
    [
        (b'{"type":"info","data":{"wake":[{"models":[{"name":"gi"}]}]}}\n', True),
        (b'{"type":"info","data_length":26}\n' + b'{"wake":[{"models":[{}]}]}', True),
        (b'{"type":"error","data":{}}\n', False),
        (b'{"type":"info","data":{"wake":[]}}\n', False),
        (b'{"type":"info","data_length":20000}\n', False),
        (b'{"type":"info","payload_length":100}\n', False),
        (b'{"type":"info","data_length":100}\n{}', False),
    ],
)
def test_wake_probe_requires_complete_metadata_without_audio(response, healthy):
    async def check():
        async def peer(reader, writer):
            request = json.loads(await reader.readline())
            assert request == {"type": "describe"}
            writer.write(response)
            await writer.drain()
            writer.close()
            await writer.wait_closed()

        server = await asyncio.start_server(peer, "127.0.0.1", 0)
        try:
            assert (
                await observer.probe_wake("127.0.0.1", server.sockets[0].getsockname()[1])
                is healthy
            )
        finally:
            server.close()
            await server.wait_closed()

    asyncio.run(check())


def test_wake_probe_times_out_a_port_that_accepts_but_never_responds():
    async def check():
        release = asyncio.Event()
        finished = asyncio.Event()

        async def stopped_reader(reader, writer):
            try:
                await reader.readline()
                await release.wait()
            finally:
                writer.close()
                await writer.wait_closed()
                finished.set()

        server = await asyncio.start_server(stopped_reader, "127.0.0.1", 0)
        try:
            assert not await asyncio.wait_for(
                observer.probe_wake("127.0.0.1", server.sockets[0].getsockname()[1], timeout=0.05),
                timeout=0.5,
            )
        finally:
            release.set()
            await asyncio.wait_for(finished.wait(), timeout=1)
            server.close()
            await server.wait_closed()

    asyncio.run(check())


@pytest.fixture(scope="session")
def policy_binary(tmp_path_factory):
    directory = tmp_path_factory.mktemp("gi-policy")
    binary = directory / "policy"
    subprocess.run(
        [
            "g++",
            "-std=c++17",
            "-Wall",
            "-Wextra",
            "-Werror",
            "-pthread",
            "-I",
            str(ROOT / "apps/voice-assistant/firmware"),
            str(ROOT / "tests/voice_health_scenarios.cpp"),
            "-o",
            str(binary),
        ],
        check=True,
    )
    return binary


@pytest.mark.parametrize(
    "scenario",
    [
        "quiet",
        "guards",
        "no_ack",
        "idle",
        "stale",
        "budget",
        "wrap",
        "busy_cap",
        "stop_timeout",
        "reconnect",
    ],
)
def test_device_recovery_contract(policy_binary, scenario):
    subprocess.run([str(policy_binary), scenario], check=True, timeout=5)
