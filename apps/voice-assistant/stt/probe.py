"""Require complete Wyoming metadata after the model has loaded."""

import asyncio

from wyoming.client import AsyncTcpClient
from wyoming.info import Describe, Info


async def probe():
    async with asyncio.timeout(4):
        async with AsyncTcpClient("127.0.0.1", 10300) as client:
            await client.write_event(Describe().event())
            event = await client.read_event()
            if event is None or not Info.is_type(event.type) or event.payload:
                raise ValueError("Invalid Wyoming metadata")
            programs = Info.from_event(event).asr
            if not any(p.installed and any(m.installed for m in p.models) for p in programs):
                raise ValueError("No installed ASR model")


if __name__ == "__main__":
    asyncio.run(probe())
