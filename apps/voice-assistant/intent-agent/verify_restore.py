"""Verify PR source on a disposable HA restore with all network traffic denied."""

import asyncio
import json
import os
import sys
import tarfile
from pathlib import Path
from types import MappingProxyType

from homeassistant import loader
from homeassistant.components import conversation
from homeassistant.components.assist_pipeline.pipeline import (
    PipelineRun,
    PipelineStage,
    async_get_pipelines,
)
from homeassistant.config_entries import ConfigEntries, ConfigEntry
from homeassistant.core import Context, HomeAssistant
from homeassistant.helpers import chat_session
from homeassistant.setup import async_setup_component

sys.path.insert(0, "/test")
from install import install


async def main():
    config = Path("/config")
    owner = config.stat()
    assert (os.getuid(), os.getgid()) == (owner.st_uid, owner.st_gid)
    source = Path("/tmp/component")
    with tarfile.open("/test/component.tar") as archive:
        archive.extractall(source, filter="data")
    revision = os.environ["SOURCE_REVISION"]
    install(source, config, revision)
    install(source, config, revision)
    manifests = [
        p
        for p in (config / "custom_components").glob("*/manifest.json")
        if json.loads(p.read_text()).get("domain") == "gi_voice"
    ]
    assert len(manifests) == 1
    assert manifests[0].parent.name == "gi_voice"
    assert (
        json.loads((config / ".gi_voice/installed.json").read_text())["source_revision"] == revision
    )
    hass = HomeAssistant(str(config))
    hass.config_entries = ConfigEntries(hass, {})
    loader.async_setup(hass)
    assert await async_setup_component(hass, "homeassistant", {})
    assert await async_setup_component(hass, "assist_pipeline", {})
    domains = await loader.async_get_custom_components(hass)
    assert domains["gi_voice"].file_path == config / "custom_components/gi_voice"
    gi = next(p for p in async_get_pipelines(hass) if p.name == "GI")
    before = gi.to_json()
    entry = ConfigEntry(
        version=1,
        minor_version=1,
        domain="gi_voice",
        title="GI Flex isolated check",
        data={"api_key": "isolated-no-network", "lights": ["light.peanut"]},
        options={},
        source="user",
        unique_id="isolated-check",
        discovery_keys=MappingProxyType({}),
        subentries_data=(),
    )
    await hass.config_entries.async_add(entry)
    await hass.async_block_till_done()
    result = await conversation.async_converse(
        hass,
        "Do not turn on Peanut",
        None,
        Context(),
        language="en",
        agent_id=entry.runtime_data.entity_id,
    )
    assert result.response.speech["plain"]["speech"] == "I haven't changed anything."
    run = PipelineRun(
        hass, Context(), gi, PipelineStage.INTENT, PipelineStage.INTENT, lambda event: None
    )
    with chat_session.async_get_chat_session(hass, None) as session:
        await run.prepare_recognize_intent(session)
        speech, _ = await run.recognize_intent(
            "Do not turn on Peanut", session.conversation_id, None
        )
    assert speech
    assert gi.to_json() == before
    await hass.async_stop()
    print(
        json.dumps(
            {
                "source_revision": revision,
                "installer_runs": 2,
                "discoverable_gi_voice_domains": 1,
                "custom_agent_answers": True,
                "saved_gi_intent_answers": True,
                "saved_gi_pipeline_unchanged": True,
                "uid": os.getuid(),
                "gid": os.getgid(),
                "scope": "disposable restore, isolated core/intent check; no device/cloud/microphone proof",
            }
        )
    )


if __name__ == "__main__":
    asyncio.run(main())
