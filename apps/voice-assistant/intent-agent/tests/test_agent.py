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
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import chat_session, intent
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import floor_registry as fr
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


async def process(
    agent,
    text="Please illuminate Peanut",
    conversation_id=None,
    *,
    satellite_id=None,
    user_id=None,
    language="en",
):
    user = conversation.ConversationInput(
        text=text,
        context=Context(user_id=user_id),
        conversation_id=conversation_id,
        device_id=None,
        satellite_id=satellite_id,
        language=language,
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
    assert result.response.speech["plain"]["speech"] == "Turned on Peanut."


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
    assert result.response.error_code == response.error_code
    assert result.response.speech["plain"]["speech"] == "I couldn't change Peanut."
    assert result.response.failed_results[0].id == "light.peanut"
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


@pytest.mark.parametrize(
    ("text", "expected_provider_calls"),
    [("turn on Peanut", 0), ("Please illuminate Peanut", 1), ("turn on the lights", 1)],
)
async def test_real_pipeline_prefers_local_control_before_fallback(
    hass, agent, aioclient_mock, text, expected_provider_calls
):
    calls = []

    async def turn_on(call):
        calls.append(call.data)

    hass.services.async_register("light", "turn_on", turn_on)
    generic = text == "turn on the lights"
    value = (
        {
            "kind": "clarify",
            "intent": None,
            "targets": [],
            "brightness_pct": None,
            "question": "Which light?",
        }
        if generic
        else action()
    )
    aioclient_mock.post(API + "/chat/completions", json=provider(value))
    speech = await pipeline_speech(hass, agent, text)
    assert speech
    assert calls == ([] if generic else [{"entity_id": ["light.peanut"]}])
    assert aioclient_mock.call_count == expected_provider_calls


async def pipeline_speech(hass, agent, text, conversation_id=None):
    from homeassistant.components.assist_pipeline.pipeline import (
        Pipeline,
        PipelineRun,
        PipelineStage,
    )

    assert await async_setup_component(hass, "assist_pipeline", {})
    pipeline = Pipeline(
        conversation_engine=agent.entity_id,
        conversation_language="en",
        language="en",
        name="GI Flex test",
        stt_engine=None,
        stt_language=None,
        tts_engine=None,
        tts_language=None,
        tts_voice=None,
        wake_word_entity=None,
        wake_word_id=None,
        prefer_local_intents=True,
    )
    run = PipelineRun(
        hass, Context(), pipeline, PipelineStage.INTENT, PipelineStage.INTENT, lambda event: None
    )
    with chat_session.async_get_chat_session(hass, conversation_id) as session:
        await run.prepare_recognize_intent(session)
        speech, _ = await run.recognize_intent(text, session.conversation_id, None)
    return speech


@pytest.mark.parametrize("fail_top", [False, True])
async def test_pipeline_spells_out_actual_multi_target_and_partial_results(
    hass, agent, aioclient_mock, fail_top
):
    calls = []

    async def turn_on(call):
        target = call.data["entity_id"][0]
        if fail_top and target == "light.top":
            raise HomeAssistantError("Unavailable")
        calls.append(target)

    hass.services.async_register("light", "turn_on", turn_on)
    aioclient_mock.post(
        API + "/chat/completions", json=provider(action(targets=["light.peanut", "light.top"]))
    )
    speech = await pipeline_speech(hass, agent, "Please illuminate Peanut and Top")
    if fail_top:
        assert calls == ["light.peanut"]
        assert speech == "Turned on Peanut. I couldn't change Top."
        assert agent.audit[-1]["outcome"] == "partial"
    else:
        assert calls == ["light.peanut", "light.top"]
        assert speech == "Turned on Peanut and Top."


async def test_remove_entry_deletes_audit_without_delayed_resurrection(hass, agent, hass_storage):
    await agent._store.async_save({"records": [{"text": "private phrase"}]})
    agent._store.async_delay_save(lambda: {"records": [{"text": "pending private phrase"}]}, 5)
    key = agent._store.key
    assert key in hass_storage
    assert await hass.config_entries.async_remove(agent.entry.entry_id)
    assert key not in hass_storage
    await hass.async_stop()
    assert key not in hass_storage


async def test_contextual_action_without_clarification_never_executes(agent, aioclient_mock):
    aioclient_mock.post(API + "/chat/completions", json=provider(action()))
    with patch(
        "custom_components.gi_voice.conversation.intent.async_handle", new=AsyncMock()
    ) as execute:
        result = await process(agent, "Turn it on")
    assert result.continue_conversation
    execute.assert_not_awaited()


async def test_refusals_record_counts_without_transcripts(hass, agent):
    await process(agent, "Don't turn on Peanut")
    async_expose_entity(hass, "conversation", "light.peanut", False)
    async_expose_entity(hass, "conversation", "light.top", False)
    await process(agent, "Please illuminate Peanut")
    assert [r["outcome"] for r in agent.audit] == ["no_action", "no_eligible_lights"]
    assert all("text" not in r for r in agent.audit)


def clarification():
    return action(kind="clarify", intent=None, targets=[], question="Which light?")


ON_OFF_REQUESTS = [
    f"{verb} {reference} {{mode}}"
    for verb in ("turn", "switch")
    for reference in ("it", "them", "light", "lights", "the light", "the lights")
] + [
    f"{verb} {{mode}} {reference}"
    for verb in ("turn", "switch")
    for reference in ("light", "lights", "the light", "the lights")
]


@pytest.mark.parametrize("prior_text", ON_OFF_REQUESTS)
@pytest.mark.parametrize("mode", ["on", "off"])
@pytest.mark.parametrize("answer", ["Peanut!", " peanut. ", "Peanut?"])
async def test_exact_clarification_dispatches_once_without_a_second_provider(
    hass, agent, aioclient_mock, prior_text, mode, answer
):
    """Real intent dispatch owns correct scoped completion; old tests only rejected retries."""
    calls = []

    async def collect(call):
        calls.append((call.service, dict(call.data)))

    hass.services.async_register("light", "turn_" + mode, collect)
    aioclient_mock.post(API + "/chat/completions", json=provider(clarification()))
    first = await process(agent, prior_text.format(mode=mode))
    result = await process(agent, answer, first.conversation_id)
    assert calls == [("turn_" + mode, {"entity_id": ["light.peanut"]})]
    assert aioclient_mock.call_count == 1
    assert not result.continue_conversation
    assert agent.audit[-1]["route"] == "exact_clarification"
    assert agent.audit[-1]["provider_calls"] == 0


@pytest.mark.parametrize(
    "prior_text",
    [
        "Please turn the lights on!",
        "Switch off the light please.",
        "Ｓｗｉｔｃｈ   ｉｔ   ｏｆｆ！",
    ],
)
async def test_exact_clarification_normalizes_politeness_and_current_top(
    hass, agent, aioclient_mock, prior_text
):
    """Polite and normalized speech still chooses the named light, never a fixed example target."""
    calls = []

    async def collect(call):
        calls.append((call.service, dict(call.data)))

    for service in ("turn_on", "turn_off"):
        hass.services.async_register("light", service, collect)
    aioclient_mock.post(API + "/chat/completions", json=provider(clarification()))
    first = await process(agent, prior_text)
    await process(agent, "Ｔｏｐ！", first.conversation_id)
    expected = "turn_on" if " on" in prior_text else "turn_off"
    assert calls == [(expected, {"entity_id": ["light.top"]})]
    assert aioclient_mock.call_count == 1


@pytest.mark.parametrize(
    "collision",
    [
        "alias",
        "area",
        "floor",
        "area_alias",
        "floor_alias",
        "nonlight",
        "normalized_light",
        "reserved",
    ],
)
async def test_exact_clarification_declines_name_collisions(hass, agent, aioclient_mock, collision):
    """A matching light is insufficient when the reply could mean another object or place."""
    aioclient_mock.post(API + "/chat/completions", json=provider(clarification()))
    first = await process(agent, "Turn it off")
    answer = "Peanut"
    if collision == "alias":
        registry = er.async_get(hass)
        other = registry.async_get_or_create("sensor", "test", "shadow")
        registry.async_update_entity(other.entity_id, aliases={"Ｐｅａｎｕｔ!"})
    elif collision == "area":
        ar.async_get(hass).async_create("Ｐｅａｎｕｔ!")
    elif collision == "floor":
        fr.async_get(hass).async_create("Peanut")
    elif collision == "area_alias":
        registry = ar.async_get(hass)
        area = registry.async_create("Kitchen & Dining")
        registry.async_update(area.id, aliases={"Ｐｅａｎｕｔ!"})
    elif collision == "floor_alias":
        registry = fr.async_get(hass)
        floor = registry.async_create("Ground")
        registry.async_update(floor.floor_id, aliases={"Ｐｅａｎｕｔ!"})
    elif collision in ("nonlight", "normalized_light"):
        other = "sensor.other" if collision == "nonlight" else "light.other"
        hass.states.async_set(other, "off", {"friendly_name": "Ｐｅａｎｕｔ!"})
        async_expose_entity(hass, "conversation", other, True)
    else:
        hass.states.async_set("light.peanut", "off", {"friendly_name": "All"})
        answer = "All"
    aioclient_mock.post(
        API + "/chat/completions", json=provider(action(kind="none", intent=None, targets=[]))
    )
    with patch(
        "custom_components.gi_voice.conversation.intent.async_handle", new=AsyncMock()
    ) as execute:
        await process(agent, answer, first.conversation_id)
    execute.assert_not_awaited()
    assert aioclient_mock.call_count == 2


@pytest.mark.parametrize(
    "answer",
    [
        "the Peanut",
        "Peanut please",
        "Peanut light",
        "Peanuts",
        "P-nut",
        "be enough",
        "you",
        "all",
        "",
    ],
)
async def test_exact_clarification_does_not_repair_or_invent_a_reply(agent, aioclient_mock, answer):
    """Neutral and approximate replies cannot acquire a target from the new local path."""
    aioclient_mock.post(API + "/chat/completions", json=provider(clarification()))
    first = await process(agent, "Turn it off")
    aioclient_mock.post(
        API + "/chat/completions", json=provider(action(kind="none", intent=None, targets=[]))
    )
    with patch(
        "custom_components.gi_voice.conversation.intent.async_handle", new=AsyncMock()
    ) as execute:
        await process(agent, answer, first.conversation_id)
    execute.assert_not_awaited()
    assert aioclient_mock.call_count == 2


@pytest.mark.parametrize(
    "prior_text",
    [
        "don't turn it off",
        "turn it off in five minutes",
        "turn it off?",
        "turn it off and on",
        "turn on button",
        "dim it",
        "set it to 50%",
        "please turn it off please",
    ],
)
async def test_exact_clarification_cannot_supply_an_action_from_an_unsupported_request(
    agent, aioclient_mock, prior_text
):
    """A valid light answer cannot erase prior qualifiers or manufacture an on/off request."""
    aioclient_mock.post(API + "/chat/completions", json=provider(clarification()))
    first = await process(agent, prior_text)
    before = aioclient_mock.call_count
    aioclient_mock.post(
        API + "/chat/completions", json=provider(action(kind="none", intent=None, targets=[]))
    )
    with patch(
        "custom_components.gi_voice.conversation.intent.async_handle", new=AsyncMock()
    ) as execute:
        await process(agent, "Peanut", first.conversation_id)
    execute.assert_not_awaited()
    assert aioclient_mock.call_count == before + 1


@pytest.mark.parametrize("age", [59, 61])
async def test_exact_clarification_observes_expiry(agent, aioclient_mock, age):
    """The new provider-free path must not bypass the existing time boundary."""
    aioclient_mock.post(API + "/chat/completions", json=provider(clarification()))
    with patch("custom_components.gi_voice.conversation.time") as clock:
        clock.monotonic.return_value = 100
        first = await process(agent, "Turn it off")
        clock.monotonic.return_value = 100 + age
        aioclient_mock.post(
            API + "/chat/completions", json=provider(action(kind="none", intent=None, targets=[]))
        )
        with patch(
            "custom_components.gi_voice.conversation.intent.async_handle",
            new=AsyncMock(return_value=success()),
        ) as execute:
            await process(agent, "Peanut", first.conversation_id)
    assert execute.await_count == (1 if age == 59 else 0)
    assert aioclient_mock.call_count == (1 if age == 59 else 2)


@pytest.mark.parametrize("different", ["conversation", "satellite", "user", "language"])
async def test_exact_clarification_requires_the_original_caller_and_language(
    agent, aioclient_mock, different
):
    """A recognized name from another caller or language cannot consume the local completion."""
    aioclient_mock.post(API + "/chat/completions", json=provider(clarification()))
    first = await process(agent, "Turn it off", satellite_id="speaker-a", user_id="user-a")
    aioclient_mock.post(
        API + "/chat/completions", json=provider(action(kind="none", intent=None, targets=[]))
    )
    with patch(
        "custom_components.gi_voice.conversation.intent.async_handle", new=AsyncMock()
    ) as execute:
        await process(
            agent,
            "Peanut",
            None if different == "conversation" else first.conversation_id,
            satellite_id="speaker-b" if different == "satellite" else "speaker-a",
            user_id="user-b" if different == "user" else "user-a",
            language="fr" if different == "language" else "en",
        )
    execute.assert_not_awaited()
    assert aioclient_mock.call_count == 2


async def test_exact_clarification_cannot_be_replayed_or_revived(agent, aioclient_mock):
    """Existing one-question tests do not protect local completion after consumption or a third turn."""
    aioclient_mock.post(API + "/chat/completions", json=provider(clarification()))
    first = await process(agent, "Turn it off")
    with patch(
        "custom_components.gi_voice.conversation.intent.async_handle",
        new=AsyncMock(return_value=success()),
    ) as execute:
        await process(agent, "Peanut", first.conversation_id)
        aioclient_mock.post(
            API + "/chat/completions", json=provider(action(kind="none", intent=None, targets=[]))
        )
        await process(agent, "Peanut", first.conversation_id)
    assert execute.await_count == 1
    aioclient_mock.post(API + "/chat/completions", json=provider(clarification()))
    first = await process(agent, "Turn it off")
    second = await process(agent, "you", first.conversation_id)
    assert not second.continue_conversation
    aioclient_mock.post(
        API + "/chat/completions", json=provider(action(kind="none", intent=None, targets=[]))
    )
    with patch(
        "custom_components.gi_voice.conversation.intent.async_handle", new=AsyncMock()
    ) as execute:
        await process(agent, "Peanut", first.conversation_id)
    execute.assert_not_awaited()


@pytest.mark.parametrize("remove", [False, True])
async def test_exact_clarification_rereads_exposure_and_entity_presence(
    hass, agent, aioclient_mock, remove
):
    """The reply cannot act from a catalog saved on the first turn."""
    aioclient_mock.post(API + "/chat/completions", json=provider(clarification()))
    first = await process(agent, "Turn it off")
    if remove:
        hass.states.async_remove("light.peanut")
    else:
        async_expose_entity(hass, "conversation", "light.peanut", False)
    aioclient_mock.post(
        API + "/chat/completions", json=provider(action(kind="none", intent=None, targets=[]))
    )
    with patch(
        "custom_components.gi_voice.conversation.intent.async_handle", new=AsyncMock()
    ) as execute:
        await process(agent, "Peanut", first.conversation_id)
    execute.assert_not_awaited()
    assert aioclient_mock.call_count == 2


async def test_exact_clarification_execution_race_never_falls_back(hass, agent, aioclient_mock):
    """Once locally selected, a revoked target cannot trigger a second provider decision."""
    aioclient_mock.post(API + "/chat/completions", json=provider(clarification()))
    first = await process(agent, "Turn it off")
    original = agent.execute

    async def revoke(*args):
        async_expose_entity(hass, "conversation", "light.peanut", False)
        return await original(*args)

    with (
        patch.object(agent, "execute", side_effect=revoke),
        patch(
            "custom_components.gi_voice.conversation.intent.async_handle", new=AsyncMock()
        ) as execute,
    ):
        result = await process(agent, "Peanut", first.conversation_id)
    execute.assert_not_awaited()
    assert aioclient_mock.call_count == 1
    assert "couldn't change" in result.response.speech["plain"]["speech"]
    assert agent.audit[-1]["provider_calls"] == 0


async def test_native_turn_precedes_and_invalidates_pending_clarification(
    hass, agent, aioclient_mock
):
    """Native handling bypasses this agent; its turn must still invalidate stale local completion."""
    calls = []

    async def collect(call):
        calls.append(dict(call.data))

    hass.services.async_register("light", "turn_on", collect)
    aioclient_mock.post(API + "/chat/completions", json=provider(clarification()))
    first = await process(agent, "Turn it off")
    audit_before = len(agent.audit)
    await pipeline_speech(hass, agent, "turn on Top", first.conversation_id)
    assert calls == [{"entity_id": ["light.top"]}]
    assert len(agent.audit) == audit_before
    assert aioclient_mock.call_count == 1
    aioclient_mock.post(
        API + "/chat/completions", json=provider(action(kind="none", intent=None, targets=[]))
    )
    with patch(
        "custom_components.gi_voice.conversation.intent.async_handle", new=AsyncMock()
    ) as execute:
        await process(agent, "Peanut", first.conversation_id)
    execute.assert_not_awaited()
    assert (
        json.loads(aioclient_mock.mock_calls[-1][2]["messages"][1]["content"])["clarification_of"]
        is None
    )
