"""Configure DeepSeek through a supported Home Assistant config flow."""

import aiohttp
import voluptuous as vol
from homeassistant.config_entries import ConfigFlow
from homeassistant.const import CONF_API_KEY
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import API, CONF_LIGHTS, DEFAULT_LIGHTS, DOMAIN, MODEL


class GiVoiceConfigFlow(ConfigFlow, domain=DOMAIN):
    """One explicit light allowlist, no automatic exposure or pipeline changes."""

    VERSION = 1

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
