"""HA conversation contracts not exercised by existing manifest checks."""

import json
from unittest.mock import AsyncMock, patch

import pytest
from custom_components.gi_voice.const import API, DOMAIN
from custom_components.gi_voice.diagnostics import async_get_config_entry_diagnostics
from custom_components.gi_voice.policy import Interpretation, validate
from homeassistant.components import conversation
from homeassistant.components.homeassistant.exposed_entities import async_expose_entity
from homeassistant.core import Context
from homeassistant.helpers import intent
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry


def action(**changes):
    return {
        "kind": "action",
        "intent": "turn_on",
        "targets": ["light.peanut"],
        "brightness_pct": None,
        "question": None,
    } | changes


def provider(value, finish="stop"):
    return {"choices": [{"finish_reason": finish, "message": {"content": json.dumps(value)}}]}


@pytest.fixture
async def agent(hass):
    await async_setup_component(hass, "homeassistant", {})
    for eid, name in [("light.peanut", "Peanut"), ("light.top", "Top")]:
        hass.states.async_set(eid, "off", {"friendly_name": name})
        async_expose_entity(hass, "conversation", eid, True)
    entry = MockConfigEntry(
        domain=DOMAIN, data={"api_key": "test-only-key", "lights": ["light.peanut", "light.top"]}
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry.runtime_data


async def process(agent, text="Please illuminate Peanut", conversation_id=None):
    user = conversation.ConversationInput(
        text=text,
        context=Context(),
        conversation_id=conversation_id,
        device_id=None,
        satellite_id=None,
        language="en",
        agent_id=agent.entity_id,
    )
    return await agent.async_process(user)


def success():
    response = intent.IntentResponse(language="en")
    response.async_set_speech("Turned on Peanut.")
    return response


async def test_one_request_then_actual_ha_response(agent, aioclient_mock):
    aioclient_mock.post(API + "/chat/completions", json=provider(action()))
    with patch(
        "custom_components.gi_voice.conversation.intent.async_handle",
        new=AsyncMock(return_value=success()),
    ) as execute:
        result = await process(agent)
    assert result.response.speech["plain"]["speech"] == "Turned on Peanut."
    execute.assert_awaited_once()
    assert execute.call_args.args[2:4] == (
        "HassTurnOn",
        {"name": {"value": "Peanut"}, "domain": {"value": "light"}},
    )
    assert execute.call_args.kwargs["assistant"] == "conversation"
    assert aioclient_mock.call_count == 1
    req = aioclient_mock.mock_calls[0]
    assert req[2]["thinking"] == {"type": "disabled"}
    data = json.loads(req[2]["messages"][1]["content"])
    assert all("state" not in light for light in data["eligible_lights"])


@pytest.mark.parametrize(
    "phrase",
    [
        "Don't turn on Peanut",
        "Do not illuminate Top",
        "Turn on the kettle",
        "Turn on Peanut tomorrow",
        "Cancel that",
    ],
)
async def test_negation_future_and_risky_devices_never_call_or_act(agent, aioclient_mock, phrase):
    with patch(
        "custom_components.gi_voice.conversation.intent.async_handle", new=AsyncMock()
    ) as execute:
        result = await process(agent, phrase)
    assert "haven't changed" in result.response.speech["plain"]["speech"]
    execute.assert_not_awaited()
    assert aioclient_mock.call_count == 0


@pytest.mark.parametrize(
    "value",
    [
        action(targets=["climate.kettle"]),
        action(targets=["light.hidden"]),
        action(intent="toggle"),
        action(brightness_pct=50),
        action(intent="set_brightness", brightness_pct=True),
        action(intent="set_brightness", brightness_pct=101),
        action(extra="execute arbitrary service"),
        action(targets=["light.peanut", "light.peanut"]),
    ],
)
async def test_invalid_decisions_never_execute(agent, aioclient_mock, value):
    aioclient_mock.post(API + "/chat/completions", json=provider(value))
    with patch(
        "custom_components.gi_voice.conversation.intent.async_handle", new=AsyncMock()
    ) as execute:
        result = await process(agent)
    execute.assert_not_awaited()
    assert "can't interpret" in result.response.speech["plain"]["speech"]


async def test_revocation_during_request_blocks_action(hass, agent):
    async def revoke(*args):
        async_expose_entity(hass, "conversation", "light.peanut", False)
        return Interpretation("action", "turn_on", ("light.peanut",), None, None)

    with (
        patch.object(agent, "interpret", side_effect=revoke),
        patch(
            "custom_components.gi_voice.conversation.intent.async_handle", new=AsyncMock()
        ) as execute,
    ):
        result = await process(agent)
    execute.assert_not_awaited()
    assert "can't interpret" in result.response.speech["plain"]["speech"]


async def test_duplicate_names_are_ineligible(hass, agent):
    hass.states.async_set("light.other", "off", {"friendly_name": "Peanut"})
    async_expose_entity(hass, "conversation", "light.other", True)
    assert "light.peanut" not in agent.catalog()


async def test_only_one_clarification_turn(agent, aioclient_mock):
    aioclient_mock.post(
        API + "/chat/completions",
        json=provider(
            {
                "kind": "clarify",
                "intent": None,
                "targets": [],
                "brightness_pct": None,
                "question": "Which light?",
            }
        ),
    )
    first = await process(agent, "Turn on the lights")
    second = await process(agent, "A light", first.conversation_id)
    assert first.continue_conversation is True
    assert second.continue_conversation is False
    assert not agent._pending


async def test_timeout_has_no_retry_or_action(agent):
    with (
        patch.object(agent, "interpret", side_effect=TimeoutError),
        patch(
            "custom_components.gi_voice.conversation.intent.async_handle", new=AsyncMock()
        ) as execute,
    ):
        result = await process(agent)
    execute.assert_not_awaited()
    assert "can't interpret" in result.response.speech["plain"]["speech"]
    assert agent.audit[-1]["outcome"] == "failed"


async def test_truncated_response_does_not_execute(agent, aioclient_mock):
    aioclient_mock.post(API + "/chat/completions", json=provider(action(), "length"))
    with patch(
        "custom_components.gi_voice.conversation.intent.async_handle", new=AsyncMock()
    ) as execute:
        await process(agent)
    execute.assert_not_awaited()


async def test_diagnostics_redact_transcript_and_key(hass, agent, aioclient_mock):
    aioclient_mock.post(
        API + "/chat/completions",
        json=provider(
            {
                "kind": "none",
                "intent": None,
                "targets": [],
                "brightness_pct": None,
                "question": None,
            }
        ),
    )
    await process(agent, "My private utterance")
    result = await async_get_config_entry_diagnostics(hass, agent.entry)
    assert "My private utterance" not in json.dumps(result)
    assert "test-only-key" not in json.dumps(result)
    assert result["calls"][0]["outcome"] == "no_action"


def test_absolute_brightness_percentage():
    assert (
        validate(
            action(intent="set_brightness", brightness_pct=40), {"light.peanut": {}}
        ).brightness_pct
        == 40
    )


async def test_real_native_intent_calls_only_the_eligible_light(hass, agent, aioclient_mock):
    calls = []

    async def turn_on(call):
        calls.append(call.data)

    hass.services.async_register("light", "turn_on", turn_on)
    aioclient_mock.post(API + "/chat/completions", json=provider(action()))
    result = await process(agent)
    assert calls == [{"entity_id": ["light.peanut"]}]
    assert result.response.response_type == intent.IntentResponseType.ACTION_DONE


async def test_native_error_is_spoken_without_claiming_success(agent, aioclient_mock):
    response = intent.IntentResponse(language="en")
    response.async_set_error(
        intent.IntentResponseErrorCode.FAILED_TO_HANDLE, "The light is unavailable."
    )
    aioclient_mock.post(API + "/chat/completions", json=provider(action()))
    with patch(
        "custom_components.gi_voice.conversation.intent.async_handle",
        new=AsyncMock(return_value=response),
    ):
        result = await process(agent)
    assert result.response is response
    assert agent.audit[-1]["outcome"] == "execution_failed"


@pytest.mark.parametrize("body", ["a string", [], {"choices": [None]}])
async def test_malformed_envelope_is_safe(agent, aioclient_mock, body):
    aioclient_mock.post(API + "/chat/completions", json=body)
    with patch(
        "custom_components.gi_voice.conversation.intent.async_handle", new=AsyncMock()
    ) as execute:
        result = await process(agent)
    execute.assert_not_awaited()
    assert "can't interpret" in result.response.speech["plain"]["speech"]


async def test_config_flow_validates_existing_model_without_an_inference_call(hass, aioclient_mock):
    await async_setup_component(hass, "homeassistant", {})
    aioclient_mock.get(API + "/models", json={"data": [{"id": "deepseek-flash"}]})
    flow = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    result = await hass.config_entries.flow.async_configure(
        flow["flow_id"], {"api_key": "test-only-key", "lights": ["light.peanut"]}
    )
    assert result["type"] == "create_entry"
    assert aioclient_mock.call_count == 1
    assert aioclient_mock.mock_calls[0][0] == "GET"
    assert result["data"]["lights"] == ["light.peanut"]


async def test_config_flow_rejects_invalid_credentials(hass, aioclient_mock):
    await async_setup_component(hass, "homeassistant", {})
    aioclient_mock.get(API + "/models", status=401)
    flow = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    result = await hass.config_entries.flow.async_configure(
        flow["flow_id"], {"api_key": "test-only-key", "lights": ["light.peanut"]}
    )
    assert result["type"] == "form"
    assert result["errors"] == {"base": "invalid_auth"}


@pytest.mark.parametrize(
    "text", ["Don't turn on Peanut", "Do not turn on Top", "Never switch Peanut on"]
)
async def test_native_preferred_path_does_not_execute_negated_commands(hass, agent, text):
    calls = []

    async def turn_on(call):
        calls.append(call.data)

    hass.services.async_register("light", "turn_on", turn_on)
    await conversation.async_converse(
        hass, text, None, Context(), language="en", agent_id="conversation.home_assistant"
    )
    assert calls == []
