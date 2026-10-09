"""Export a fixed set of Voice PE diagnostic entities; never subscribe to audio."""

import asyncio
import math
import os
import time

ENTITIES = {
    "gi_listen_expected": "voice_listen_expected",
    "gi_recovery_exhausted": "voice_recovery_exhausted",
    "gi_pipeline_acknowledged": "voice_pipeline_acknowledged",
    "gi_voice_running": "voice_running",
    "gi_microphone_frame_age": "voice_microphone_frame_age_seconds",
    "gi_recovery_count": "voice_recovery_count",
    "gi_reboot_budget_used": "voice_reboot_budget_used",
    "gi_recovery_reason": "voice_recovery_reason",
    "gi_voice_stage": "voice_stage",
    "gi_uptime": "voice_uptime_seconds",
}


class Metrics:
    def __init__(self):
        self.connected = False
        self.values = {}

    def update(self, object_id, value):
        if object_id in ENTITIES and math.isfinite(float(value)):
            self.values[object_id] = float(value)

    def reset(self):
        self.connected = False
        self.values.clear()

    @property
    def ready(self):
        return self.connected and self.values.keys() >= ENTITIES.keys()

    def render(self):
        values = {
            "voice_device_connected": int(self.connected),
            "voice_diagnostics_ready": int(self.ready),
            **{ENTITIES[key]: value for key, value in self.values.items()},
        }
        return "".join(f"# TYPE {key} gauge\n{key} {value}\n" for key, value in values.items())


async def observe(metrics, host):
    from aioesphomeapi import APIClient, BinarySensorState, SensorState

    while True:
        client = APIClient(host, 6053, "", client_info="GI diagnostics (state only)")
        try:
            stopped = asyncio.Event()

            async def disconnected(_expected, stopped=stopped):
                stopped.set()

            await client.connect(login=True, on_stop=disconnected)
            entities, _ = await client.list_entities_services()
            keys = {e.key: e.object_id for e in entities if e.object_id in ENTITIES}

            def state_changed(state, keys=keys):
                if isinstance(state, (BinarySensorState, SensorState)) and not state.missing_state:
                    metrics.update(keys.get(state.key), state.state)

            client.subscribe_states(state_changed)
            metrics.connected = True
            await stopped.wait()
        except Exception as error:
            # Exception text can contain credentials or unrelated entity values.
            print(f"VOICE_DIAGNOSTICS disconnected error={type(error).__name__}", flush=True)
        finally:
            metrics.reset()
            try:
                await client.disconnect()
            except Exception as error:
                print(f"VOICE_DIAGNOSTICS cleanup error={type(error).__name__}", flush=True)
        await asyncio.sleep(5)


async def serve(metrics, reader, writer):
    try:
        request = await asyncio.wait_for(reader.readline(), timeout=2)
        if request.startswith(b"GET /metrics "):
            status, body = "200 OK", metrics.render()
        elif request.startswith(b"GET /healthz "):
            status, body = (
                ("200 OK", "ready\n")
                if metrics.ready
                else ("503 Service Unavailable", "unavailable\n")
            )
        else:
            status, body = "404 Not Found", "not found\n"
        payload = body.encode()
        writer.write(
            f"HTTP/1.1 {status}\r\nContent-Type: text/plain; version=0.0.4\r\n"
            f"Content-Length: {len(payload)}\r\nConnection: close\r\n\r\n".encode()
            + payload
        )
        await writer.drain()
    except (TimeoutError, ConnectionError, ValueError):
        pass
    finally:
        writer.close()
        await writer.wait_closed()


async def main():
    metrics = Metrics()
    observer = asyncio.create_task(observe(metrics, os.environ["VOICE_PE_HOST"]))
    server = await asyncio.start_server(
        lambda r, w: serve(metrics, r, w), "0.0.0.0", 8080, limit=4096
    )
    print(f"VOICE_DIAGNOSTICS ready timestamp={int(time.time())}", flush=True)
    async with server:
        try:
            await server.serve_forever()
        finally:
            observer.cancel()


if __name__ == "__main__":
    asyncio.run(main())
