"""Export routing evidence without private utterances or credentials."""

from .const import DOMAIN, MODEL


async def async_get_config_entry_diagnostics(hass, entry):
    return {
        "domain": DOMAIN,
        "model": MODEL,
        "calls": [
            {k: v for k, v in record.items() if k != "text"} for record in entry.runtime_data.audit
        ],
        "credentials": "redacted",
        "transcripts": "redacted",
    }
