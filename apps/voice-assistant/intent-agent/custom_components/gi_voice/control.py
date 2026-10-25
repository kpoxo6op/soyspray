"""Resolve one currently exposed device and execute a bounded local command."""

import re

import voluptuous as vol
from homeassistant.components.homeassistant.exposed_entities import async_should_expose
from homeassistant.core import SupportsResponse
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

APPS = {
    "youtube": "app.smarttube.fdroid",
    "jellyfin": "org.jellyfin.androidtv",
    "twitch": "com.fgl27.twitch",
}
ACTIONS = {
    "light_on",
    "light_off",
    "brightness",
    "tv_on",
    "tv_off",
    "pause",
    "resume",
    "louder",
    "quieter",
    "mute",
    "next",
    "previous",
    "app",
    "channel",
    "vacuum_room",
    "vacuum_all",
    "vacuum_stop",
    "vacuum_home",
}
BLOCKED = re.compile(
    r"\b(don['’]?t|do not|never|not|tomorrow|later|unless|except|without|"
    r"said|says|saying|if|would happen|could happen|might|yesterday)\b",
    re.I,
)


def normalize(value):
    return " ".join(re.sub(r"[^\w\s]", " ", value.casefold()).split())


def catalog(hass):
    """No saved device allowlist: names, areas and eligibility come from HA."""
    entities, devices = er.async_get(hass), dr.async_get(hass)
    result = {}
    for state in hass.states.async_all():
        domain = state.domain
        if domain not in {"light", "vacuum", "media_player"}:
            continue
        if domain == "media_player" and state.attributes.get("device_class") != "tv":
            continue
        if not async_should_expose(hass, "conversation", state.entity_id):
            continue
        entry = entities.async_get(state.entity_id)
        device = devices.async_get(entry.device_id) if entry and entry.device_id else None
        if not isinstance(state.name, str):
            continue
        result[state.entity_id] = {
            "name": state.name,
            "aliases": sorted(a for a in entry.aliases if isinstance(a, str)) if entry else [],
            "domain": domain,
            "area_id": (entry.area_id if entry else None) or (device.area_id if device else None),
            "platform": entry.platform if entry else None,
        }
    return result


def resolve(hass, action, target_name="", preferred_area_id="", area=""):
    domain = (
        "light"
        if action.startswith("light_") or action == "brightness"
        else ("vacuum" if action.startswith("vacuum_") else "media_player")
    )
    candidates = {eid: item for eid, item in catalog(hass).items() if item["domain"] == domain}
    if target_name:
        wanted = normalize(target_name)
        candidates = {
            eid: item
            for eid, item in candidates.items()
            if wanted in {normalize(n) for n in [item["name"], *item["aliases"]]}
        }
    if area:
        registry = ar.async_get(hass)
        matches = [
            a.id
            for a in registry.areas.values()
            if normalize(area) in {normalize(a.name), *(normalize(x) for x in a.aliases)}
        ]
        candidates = {eid: item for eid, item in candidates.items() if item["area_id"] in matches}
    elif preferred_area_id:
        nearby = {
            eid: item for eid, item in candidates.items() if item["area_id"] == preferred_area_id
        }
        if nearby:
            candidates = nearby
    if len(candidates) != 1:
        raise HomeAssistantError("Say the device name or room; I cannot choose one safely.")
    return next(iter(candidates))


async def execute(hass, data, context):
    action = data["command"]
    if action not in ACTIONS:
        raise HomeAssistantError("Unsupported voice action")
    eid = resolve(
        hass,
        action,
        data.get("target_name", ""),
        data.get("preferred_area_id", ""),
        data.get("area", ""),
    )
    value = data.get("value", "")
    domain, service, payload = None, None, {"entity_id": eid}
    if action in {"light_on", "light_off", "brightness"}:
        domain, service = "light", "turn_off" if action == "light_off" else "turn_on"
        if action == "brightness":
            if (
                isinstance(value, bool)
                or not str(value).replace(".", "", 1).isdigit()
                or not float(value).is_integer()
                or not 1 <= float(value) <= 100
            ):
                raise HomeAssistantError("Choose brightness from 1 to 100 percent.")
            payload["brightness_pct"] = int(float(value))
    elif action.startswith("vacuum_"):
        domain = "vacuum"
        service = {
            "vacuum_all": "start",
            "vacuum_stop": "stop",
            "vacuum_home": "return_to_base",
        }.get(action)
        if action == "vacuum_room":
            state = hass.states.get(eid)
            room = normalize(str(value))
            room = {"dining room": "dining hall", "lounge": "living room"}.get(room, room)
            rooms = state.attributes.get("rooms", {}).get(state.attributes.get("selected_map"), [])
            segments = [r["id"] for r in rooms if normalize(r["name"]) == room]
            if len(segments) != 1 or catalog(hass)[eid]["platform"] != "dreame_vacuum":
                raise HomeAssistantError("That vacuum room is not available.")
            domain, service = "dreame_vacuum", "vacuum_clean_segment"
            payload["segments"] = segments
    elif action in {"tv_on", "tv_off", "mute"}:
        domain = "media_player"
        service = {"tv_on": "turn_on", "tv_off": "turn_off", "mute": "volume_mute"}[action]
        if action == "mute":
            payload["is_volume_muted"] = True
    else:
        if catalog(hass)[eid]["platform"] != "androidtv":
            raise HomeAssistantError("This TV does not support these Android TV commands.")
        domain, service = "androidtv", "adb_command"
        keys = {
            "pause": 127,
            "resume": 126,
            "louder": 24,
            "quieter": 25,
            "next": 166,
            "previous": 167,
        }
        if action in keys:
            payload["command"] = "input keyevent " + str(keys[action])
        elif action == "app":
            if str(value).casefold() not in APPS:
                raise HomeAssistantError("That TV app is not supported.")
            payload["command"] = (
                "monkey -p "
                + APPS[str(value).casefold()]
                + " -c android.intent.category.LEANBACK_LAUNCHER 1"
            )
        elif action == "channel":
            if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,79}", str(value)):
                raise HomeAssistantError("Invalid catalog channel")
            payload["command"] = (
                "am start -n vip.soyspray.home/.HomeActivity --es play_channel " + str(value)
            )
        if action in {"app", "channel"} and hass.states.get(eid).state == "off":
            await hass.services.async_call(
                "media_player", "turn_on", {"entity_id": eid}, blocking=True, context=context
            )
    # Exposure and identity may change during a wake-up call.
    if eid not in catalog(hass):
        raise HomeAssistantError("The device is no longer exposed to voice.")
    await hass.services.async_call(domain, service, payload, blocking=True, context=context)
    return {"speech": "Done.", "entity_id": eid, "command": action}


def setup_service(hass):
    async def handle(call):
        try:
            return await execute(hass, call.data, call.context)
        except HomeAssistantError as error:
            return {"speech": str(error), "error": True}

    hass.services.async_register(
        "gi_voice",
        "command",
        handle,
        schema=vol.Schema(
            {
                vol.Required("command"): vol.In(ACTIONS),
                vol.Optional("target_name", default=""): str,
                vol.Optional("preferred_area_id", default=""): str,
                vol.Optional("area", default=""): str,
                vol.Optional("value", default=""): vol.Any(str, int, float),
            }
        ),
        supports_response=SupportsResponse.ONLY,
    )
