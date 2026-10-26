"""Configure DeepSeek through a supported Home Assistant config flow."""

import aiohttp
import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, OptionsFlow
from homeassistant.const import CONF_API_KEY
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    API,
    CLOUD_ENABLED,
    CONF_LIGHTS,
    DEFAULT_LIGHTS,
    DOMAIN,
    LOCAL_STT,
    MODEL,
    OPENAI_KEY,
    SPEECH_MODEL,
)


class GiVoiceConfigFlow(ConfigFlow, domain=DOMAIN):
    """One explicit light allowlist, no automatic exposure or pipeline changes."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return GiSpeechOptionsFlow()

    async def async_step_user(self, user_input=None):
        """Validate the key with a read-only model-list request."""
        errors = {}
        if user_input is not None:
            await self.async_set_unique_id(DOMAIN)
            self._abort_if_unique_id_configured()
            lights = user_input[CONF_LIGHTS]
            if not lights or len(lights) > 4 or any(not e.startswith("light.") for e in lights):
                errors[CONF_LIGHTS] = "invalid_lights"
            else:
                try:
                    session = async_get_clientsession(self.hass)
                    async with session.get(
                        API + "/models",
                        headers={"Authorization": "Bearer " + user_input[CONF_API_KEY]},
                        timeout=aiohttp.ClientTimeout(total=5),
                    ) as response:
                        if response.status == 401:
                            errors["base"] = "invalid_auth"
                        elif response.status != 200:
                            errors["base"] = "cannot_connect"
                        elif MODEL not in {
                            m.get("id") for m in (await response.json()).get("data", [])
                        }:
                            errors["base"] = "model_unavailable"
                except (aiohttp.ClientError, TimeoutError, ValueError):
                    errors["base"] = "cannot_connect"
                if not errors:
                    return self.async_create_entry(title="GI Flex", data=user_input)
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_API_KEY): selector.TextSelector(
                        selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
                    ),
                    vol.Required(CONF_LIGHTS, default=DEFAULT_LIGHTS): selector.EntitySelector(
                        selector.EntitySelectorConfig(domain="light", multiple=True)
                    ),
                }
            ),
            errors=errors,
        )


class GiSpeechOptionsFlow(OptionsFlow):
    """Make cloud audio opt-in and preserve credentials when editing options."""

    async def async_step_init(self, user_input=None):
        errors = {}
        saved = self.config_entry.options
        if user_input is not None:
            values = dict(user_input)
            if "wake_word_source" not in values and saved.get("wake_word_source"):
                values["wake_word_source"] = saved["wake_word_source"]
            values[OPENAI_KEY] = values.get(OPENAI_KEY, "").strip() or saved.get(OPENAI_KEY, "")
            if values[CLOUD_ENABLED]:
                if not values[OPENAI_KEY]:
                    errors["base"] = "openai_key_required"
                else:
                    try:
                        async with async_get_clientsession(self.hass).get(
                            "https://api.openai.com/v1/models/" + SPEECH_MODEL,
                            headers={"Authorization": "Bearer " + values[OPENAI_KEY]},
                            timeout=aiohttp.ClientTimeout(total=5),
                            allow_redirects=False,
                        ) as response:
                            if (
                                response.status != 200
                                or (await response.json()).get("id") != SPEECH_MODEL
                            ):
                                errors["base"] = "openai_unavailable"
                    except (aiohttp.ClientError, TimeoutError, ValueError, AttributeError):
                        errors["base"] = "openai_unavailable"
            if not errors:
                return self.async_create_entry(title="", data=values)
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(CLOUD_ENABLED, default=saved.get(CLOUD_ENABLED, False)): bool,
                    vol.Required(
                        LOCAL_STT, default=saved.get(LOCAL_STT, "stt.faster_whisper")
                    ): selector.EntitySelector(selector.EntitySelectorConfig(domain="stt")),
                    vol.Optional(OPENAI_KEY): selector.TextSelector(
                        selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
                    ),
                    vol.Optional(
                        "wake_word_source", default=saved.get("wake_word_source", vol.UNDEFINED)
                    ): selector.EntitySelector(selector.EntitySelectorConfig(domain="wake_word")),
                }
            ),
            errors=errors,
        )
