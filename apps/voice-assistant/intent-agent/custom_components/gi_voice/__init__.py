"""Load a conversation agent without changing any pipeline or exposure."""

from homeassistant.const import Platform


async def async_setup_entry(hass, entry):
    """Keep routing and credentials in Home Assistant's supported config entry."""
    await hass.config_entries.async_forward_entry_setups(entry, [Platform.CONVERSATION])
    return True


async def async_unload_entry(hass, entry):
    """Unload without changing the satellite or other conversation agents."""
    return await hass.config_entries.async_unload_platforms(entry, [Platform.CONVERSATION])
