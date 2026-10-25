"""Load a conversation agent without changing any pipeline or exposure."""

from homeassistant.const import Platform
from homeassistant.helpers.storage import Store

from .const import DOMAIN

PLATFORMS = [Platform.CONVERSATION, Platform.STT]


async def async_setup_entry(hass, entry):
    """Keep routing and credentials in Home Assistant's supported config entry."""
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    return True


async def async_reload_entry(hass, entry):
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass, entry):
    """Unload without changing the satellite or other conversation agents."""
    agent = getattr(entry, "runtime_data", None)
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded and agent and agent._store:
        await agent._store.async_save({"records": agent.audit})
    return unloaded


async def async_remove_entry(hass, entry):
    """Removing the integration also removes its private transcript audit."""
    agent = getattr(entry, "runtime_data", None)
    store = hass.data.get(DOMAIN, {}).pop(entry.entry_id, None) or Store(
        hass, 1, DOMAIN + ".audit." + entry.entry_id
    )
    await store.async_remove()
    if agent:
        agent.audit.clear()
