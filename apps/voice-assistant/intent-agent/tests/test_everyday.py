"""Real HA conversation -> YAML script -> device service boundary.

Existing light-only tests do not own TV packages, vacuum segments, room routing,
or a teacher's learned sentences. These checks catch cross-room dispatch and
silent expansion from a room clean to a whole-house clean without running hardware.
"""

import json
from pathlib import Path

import pytest
import yaml
from custom_components.gi_voice.const import API, DOMAIN
from homeassistant.components import conversation
from homeassistant.components.homeassistant.exposed_entities import async_expose_entity
from homeassistant.core import Context
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry


@pytest.fixture
async def everyday(hass):
    await async_setup_component(hass, "homeassistant", {})
    entry = MockConfigEntry(domain=DOMAIN, data={"api_key": "test", "lights": ["light.top"]})
    entry.add_to_hass(hass)
    areas = ar.async_get(hass)
    bedroom = areas.async_create("Bedroom")
    living = areas.async_create("Living Room")
    entities, devices = er.async_get(hass), dr.async_get(hass)
    definitions = [
        ("media_player", "androidtv", "TV", living.id, {"device_class": "tv"}),
        (
            "vacuum",
            "dreame_vacuum",
            "vacuum",
            living.id,
            {
                "selected_map": "Map 1",
                "rooms": {
                    "Map 1": [
                        {"id": 1, "name": "Dining Hall"},
                        {"id": 2, "name": "Bathroom"},
                        {"id": 3, "name": "Living Room"},
                    ]
                },
            },
        ),
        ("light", "test", "Top", bedroom.id, {}),
        ("light", "test", "Middle", bedroom.id, {}),
    ]
    ids = {}
    for domain, platform, name, area, attrs in definitions:
        device = devices.async_get_or_create(
            config_entry_id=entry.entry_id, identifiers={(DOMAIN, name)}
        )
        devices.async_update_device(device.id, area_id=area)
        entity = entities.async_get_or_create(
            domain,
            platform,
            name,
            suggested_object_id=name,
            original_name=name,
            device_id=device.id,
        )
        hass.states.async_set(entity.entity_id, "on", {"friendly_name": name, **attrs})
        async_expose_entity(hass, "conversation", entity.entity_id, True)
        ids[name] = entity.entity_id
    satellite = devices.async_get_or_create(
        config_entry_id=entry.entry_id, identifiers={(DOMAIN, "satellite")}
    )
    devices.async_update_device(satellite.id, area_id=bedroom.id)
    assert await hass.config_entries.async_setup(entry.entry_id)
    config = await hass.async_add_executor_job(
        lambda: yaml.safe_load(
            (Path(__file__).parents[1] / "custom_components/gi_voice/intents.yaml").read_text()
        )
    )
    assert await async_setup_component(hass, "intent_script", {"intent_script": config})
    calls = []

    async def capture(call):
        calls.append((call.domain, call.service, dict(call.data)))

    for domain, services in {
        "light": ["turn_on", "turn_off"],
        "media_player": ["turn_on", "turn_off", "volume_mute"],
        "androidtv": ["adb_command"],
        "vacuum": ["start", "stop", "return_to_base"],
        "dreame_vacuum": ["vacuum_clean_segment"],
    }.items():
        for service in services:
            hass.services.async_register(domain, service, capture)
    await hass.async_block_till_done()
    for _domain, _platform, name, _area, attrs in definitions:
        hass.states.async_set(ids[name], "on", {"friendly_name": name, **attrs})
    return entry, ids, satellite.id, calls


async def say(hass, text, device=None):
    return await conversation.async_converse(
        hass,
        text,
        None,
        Context(),
        language="en",
        agent_id="conversation.gi_everyday",
        device_id=device,
    )


@pytest.mark.parametrize(
    "text,domain,service,data",
    [
        ("top on", "light", "turn_on", {"entity_id": "light.top"}),
        (
            "middle to 30 percent",
            "light",
            "turn_on",
            {"entity_id": "light.middle", "brightness_pct": 30},
        ),
        ("TV off", "media_player", "turn_off", {"entity_id": "media_player.tv"}),
        (
            "vacuum the living room",
            "dreame_vacuum",
            "vacuum_clean_segment",
            {"entity_id": "vacuum.vacuum", "segments": [3]},
        ),
        (
            "vacuum the dining room",
            "dreame_vacuum",
            "vacuum_clean_segment",
            {"entity_id": "vacuum.vacuum", "segments": [1]},
        ),
        (
            "vacuum the bathroom",
            "dreame_vacuum",
            "vacuum_clean_segment",
            {"entity_id": "vacuum.vacuum", "segments": [2]},
        ),
        ("vacuum go home", "vacuum", "return_to_base", {"entity_id": "vacuum.vacuum"}),
        (
            "YouTube",
            "androidtv",
            "adb_command",
            {
                "entity_id": "media_player.tv",
                "command": "monkey -p app.smarttube.fdroid -c android.intent.category.LEANBACK_LAUNCHER 1",
            },
        ),
        (
            "oh teh veh prim",
            "androidtv",
            "adb_command",
            {
                "entity_id": "media_player.tv",
                "command": "am start -n vip.soyspray.home/.HomeActivity --es play_channel otv-prim",
            },
        ),
    ],
)
async def test_starters_reach_the_exact_device_service(
    hass, everyday, aioclient_mock, text, domain, service, data
):
    _, _, device, calls = everyday
    result = await say(hass, text, device)
    assert result.response.speech["plain"]["speech"] == "Done."
    assert calls == [(domain, service, data)]
    assert aioclient_mock.call_count == 0


@pytest.mark.parametrize(
    "text",
    [
        "don't turn on top",
        "top on tomorrow",
        "vacuum everywhere later",
        "my friend said TV on",
        "turn it on",
        "turn it off",
    ],
)
async def test_negation_future_and_pronouns_never_dispatch(hass, everyday, aioclient_mock, text):
    await say(hass, text)
    assert everyday[3] == []
    assert aioclient_mock.call_count == 0


async def test_second_room_prefers_its_tv_and_ambiguity_never_broadcasts(
    hass, everyday, aioclient_mock
):
    entry, ids, satellite, calls = everyday
    area = dr.async_get(hass).async_get(satellite).area_id
    entity = er.async_get(hass).async_get_or_create(
        "media_player", "androidtv", "second", suggested_object_id="second_tv", original_name="TV"
    )
    er.async_get(hass).async_update_entity(entity.entity_id, area_id=area)
    hass.states.async_set(entity.entity_id, "on", {"friendly_name": "TV", "device_class": "tv"})
    async_expose_entity(hass, "conversation", entity.entity_id, True)
    await say(hass, "TV off", satellite)
    assert calls[-1][2]["entity_id"] == entity.entity_id
    calls.clear()
    await say(hass, "TV off")
    assert calls == []
    async_expose_entity(hass, "conversation", entity.entity_id, False)
    await say(hass, "TV off", satellite)
    assert calls[-1][2]["entity_id"] == ids["TV"]


async def test_verified_teacher_receipt_becomes_local_without_model_call(
    hass, everyday, aioclient_mock
):
    """Compiler must reproduce a successful action, never learn failed guesses."""
    from custom_components.gi_voice.everyday import match_command
    from hassil import Intents
    from learn import compile_record

    phrase = "give the top light some power"
    aioclient_mock.post(
        API + "/chat/completions",
        json={
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {
                        "content": json.dumps(
                            {"command": "light_on", "target_name": "Top", "value": ""}
                        )
                    },
                }
            ]
        },
    )
    await say(hass, phrase)
    record = everyday[0].runtime_data.audit[-1]
    assert everyday[3][-1] == ("light", "turn_on", {"entity_id": "light.top"})
    assert record["route"] == "deepseek"
    with pytest.raises(ValueError):
        compile_record(record, {})
    learned = compile_record({**record, "verified": True}, {})
    matched = match_command(phrase, Intents.from_dict(learned), {})
    assert matched.intent.name == "GiControl"
    assert {e.name: e.value for e in matched.entities_list} == {
        "command": "light_on",
        "target_name": "Top",
        "value": "",
    }
    assert aioclient_mock.call_count == 1
