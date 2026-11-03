"""Local sentences first, then a bounded repair of a misheard light name. No cloud."""

import re
import time
from pathlib import Path

import yaml
from hassil import Intents, recognize
from hassil.intents import RangeSlotList, TextSlotList
from hassil.util import merge_dict
from homeassistant.components import conversation
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import intent

from .control import BLOCKED, catalog

# Recognizers put the wake word tail, acknowledgements and politeness around a
# command ("Yeah. Turn on peanut.", "GI, top on", "could you ... for me").
_LEADING = re.compile(
    r"^(?:(?:yeah|yes|yep|yup|okay|ok|so|um+|uh+|er+|erm|ah+|hey|hi|well|and|now|"
    r"right|alright|gi|gee|giant|ji|jai|g|i|please|could you|can you|would you|will you)\s+)+"
)
_TRAILING = re.compile(r"(?:\s+(?:please|thanks|thank you|for me|now|right now))+$")
_TURN = ("turn", "switch")
# Only these words carry an action without a device name.
_ACTION_WORDS = {
    "turn", "switch", "set", "put", "dim", "on", "off", "open", "launch", "watch", "pause",
    "resume", "mute", "louder", "quieter", "volume", "channel", "vacuum", "clean", "stop",
    "send", "tv", "television", "light", "lights", "lamp", "youtube", "jellyfin", "twitch",
}  # fmt: skip
_CYRILLIC = re.compile(r"[Ѐ-ӿ]")
# A repaired name must be this close to one light and clearly closer than any other.
MAX_NAME_DISTANCE = 0.3
MIN_NAME_MARGIN = 0.15


def load_sentences():
    data = {}
    for path in sorted((Path(__file__).parent / "sentences/en").glob("*.yaml")):
        merge_dict(data, yaml.safe_load(path.read_text()))
    return Intents.from_dict(data)


def normalize(text):
    """Case, punctuation, fillers and politeness; never negation or qualifiers."""
    value = text.casefold().replace("’", "'")
    # Open recognizers commonly render spoken percentages as digits plus %.
    value = re.sub(r"(?<=\d)\s*%", " percent", value)
    value = " ".join(re.sub(r"[^\w\s']", " ", value).split())
    value = re.sub(r"\bturn of\b", "turn off", value)
    value = re.sub(r"\bt v\b", "tv", value)
    previous = None
    while value != previous:
        previous = value
        value = _TRAILING.sub("", _LEADING.sub("", value))
    return value


def light_names(devices):
    return {
        eid: [device["name"], *device["aliases"]]
        for eid, device in devices.items()
        if device["domain"] == "light"
    }


def match_command(text, sentences, devices):
    names = [name for values in light_names(devices).values() for name in values]
    return recognize(
        normalize(text),
        sentences,
        slot_lists={
            "name": TextSlotList.from_strings(names, allow_template=False),
            "area": TextSlotList.from_strings(
                sorted({d.get("area", "") for d in devices.values() if d.get("area")}),
                allow_template=False,
            ),
            "brightness": RangeSlotList("brightness", 1, 100, words_language="en"),
        },
        language="en",
    )


_SOUNDS = [
    ("tch", "C"), ("dge", "j"), ("sch", "sk"), ("ph", "f"), ("gh", ""), ("ck", "k"), ("qu", "kw"),
    ("wh", "w"), ("wr", "r"), ("^kn", "n"), ("mb$", "m"), ("sh", "S"), ("ch", "C"), ("th", "T"),
    ("ng", "N"),
]  # fmt: skip
_VOWELS = set("aeiou")
_CLOSE = {frozenset(p) for p in ["pb", "td", "kg", "fv", "sS", "Cj", "mn", "TS", "Td", "tT", "nN"]}


def sound(text):
    """Rough English spelling-to-sound key; enough to compare short names."""
    value = re.sub(r"[^a-z]", "", text.casefold())
    for spelling, key in _SOUNDS:
        value = re.sub(spelling, key, value)
    value = re.sub(r"c(?=[eiy])", "s", value).replace("c", "k").replace("x", "ks")
    value = value.replace("z", "s").replace("q", "k")
    if len(value) > 3:
        value = re.sub(r"(?<=[^aeiouy])e$", "", value)
    value = re.sub(r"ee|ea|ie|ei|ey|i|y", "i", value)
    value = re.sub(r"oo|ou|ow|u", "u", value)
    value = re.sub(r"ai|ay|a", "a", value)
    value = re.sub(r"oa|oe|o", "o", value)
    return re.sub(r"(.)\1+", r"\1", value)


def sound_distance(first, second):
    """Edit distance where similar vowels and voiced pairs cost less, scaled to 0..1."""

    def gap(char):
        return 0.5 if char in _VOWELS else 1.0

    def swap(a, b):
        if a == b:
            return 0.0
        if a in _VOWELS and b in _VOWELS:
            return 0.4
        return 0.5 if frozenset((a, b)) in _CLOSE else 1.0

    previous = [0.0]
    for char in second:
        previous.append(previous[-1] + gap(char))
    for a in first:
        row = [previous[0] + gap(a)]
        for j, b in enumerate(second, 1):
            row.append(min(previous[j] + gap(a), row[j - 1] + gap(b), previous[j - 1] + swap(a, b)))
        previous = row
    return previous[-1] / max(len(first), len(second), 1)


def closest_light(words, devices):
    """One light whose name or alias sounds like the words, or None."""
    heard = sound("".join(words))
    if not heard:
        return None
    scores = sorted(
        (min(sound_distance(heard, sound(name)) for name in names), names[0])
        for names in light_names(devices).values()
    )
    if not scores or scores[0][0] > MAX_NAME_DISTANCE:
        return None
    if len(scores) > 1 and scores[1][0] - scores[0][0] < MIN_NAME_MARGIN:
        return None
    return scores[0][1]


def repair_light(text, devices):
    """Accept "turn on/off <misheard name>" when the name has one clear match.

    Polarity must be heard as the exact word on/off; only the name is repaired.
    """
    words = normalize(text).split()
    if words[:1] and sound_distance(sound(words[0]), sound("turn")) <= 0.25:
        words[0] = "turn"
    patterns = (
        (r"(?:turn|switch) (on|off) (?:the )?(\S+(?: \S+)?)(?: light| lamp)?", 1, 2),
        (r"(?:turn|switch) (?:the )?(\S+(?: \S+)??)(?: light| lamp)? (on|off)", 2, 1),
        (r"(\S+)(?: light| lamp)? (on|off)", 2, 1),
    )
    value = " ".join(words)
    for pattern, polarity, name in patterns:
        if found := re.fullmatch(pattern, value):
            heard = found.group(name).split()
            if heard[0] in _ACTION_WORDS or heard[-1] in _ACTION_WORDS:
                return None
            if target := closest_light(heard, devices):
                command = "light_on" if found.group(polarity) == "on" else "light_off"
                return {"command": command, "target_name": target}
            return None
    return None


def understand(text, sentences, devices):
    """Classify one transcript: blocked, exact, repaired or None."""
    if not text or not text.strip():
        return None
    if BLOCKED.search(text):
        return "blocked"
    if match_command(text, sentences, devices):
        return "exact"
    if repair_light(text, devices):
        return "repaired"
    return None


def sounds_like_command(text, devices):
    """Whether a heard negation could apply to a command, not to unrelated words."""
    words = set(normalize(text).split())
    names = {normalize(n) for values in light_names(devices).values() for n in values}
    return bool(words & _ACTION_WORDS or words & names)


def compatible(primary, retry):
    """A second recognizer may replace an unmatched first transcript only if it adds detail.

    It must not contradict heard polarity, replace Russian speech or rewrite a long
    unrelated utterance into a command.
    """
    first, second = normalize(primary or "").split(), normalize(retry).split()
    if _CYRILLIC.search(primary or ""):
        return False
    for word, opposite in (("on", "off"), ("off", "on")):
        if word in first and opposite in second and word not in second:
            return False
    # A trailing on/off without "turn" is easy to mishear; it needs corroboration.
    if second[-1:] in (["on"], ["off"]) and not {"turn", "switch"} & set(second):
        return second[-1] in first
    return len(first) <= len(second) + 3


def choose_transcript(primary, retry, sentences, devices):
    """Pick the transcript the agent should act on, and name the route taken."""
    primary_kind = understand(primary, sentences, devices)
    if primary_kind == "exact":
        return primary, "primary"
    if primary_kind == "blocked" and sounds_like_command(primary, devices):
        return primary, "primary_veto"
    retry_kind = understand(retry, sentences, devices)
    if retry_kind == "blocked" and sounds_like_command(retry, devices):
        return retry, "retry_veto"
    if retry_kind == "exact" and compatible(primary, retry):
        return retry, "retry"
    if retry_kind == "repaired" and compatible(primary, retry):
        return retry, "retry_repaired"
    if primary_kind == "repaired":
        return primary, "primary_repaired"
    if primary and primary.strip():
        return primary, "unmatched"
    return retry or "", "unmatched"


class EverydayAgent(conversation.ConversationEntity):
    _attr_name = "GI Everyday"
    _attr_supported_features = conversation.ConversationEntityFeature.CONTROL

    def __init__(self, entry):
        self.entry = entry
        self._attr_unique_id = entry.entry_id + "_everyday"
        self.sentences = None

    @property
    def supported_languages(self):
        return ["en"]

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        self.sentences = await self.hass.async_add_executor_job(load_sentences)

    def area(self, user):
        device_id = user.device_id
        if user.satellite_id:
            entity = er.async_get(self.hass).async_get(user.satellite_id)
            if entity:
                if entity.area_id:
                    return entity.area_id
                device_id = entity.device_id
        device = dr.async_get(self.hass).async_get(device_id) if device_id else None
        return device.area_id if device else None

    async def _async_handle_message(self, user, chat_log):
        started = time.monotonic()
        route = "declined"
        slots = None
        name = "GiDecline"
        text = user.text.strip()
        devices = catalog(self.hass)
        if not BLOCKED.search(text):
            if matched := match_command(text, self.sentences, devices):
                name = matched.intent.name
                slots = {entity.name: entity.value for entity in matched.entities_list}
                route = "local"
            elif repaired := repair_light(text, devices):
                name, slots, route = "GiControl", repaired, "repaired"
        slots = slots or {}
        if area_id := self.area(user):
            slots["preferred_area_id"] = area_id
        response = await intent.async_handle(
            self.hass,
            "conversation",
            name,
            {key: {"value": value} for key, value in slots.items()},
            text_input=text,
            context=user.context,
            language=user.language,
            assistant="conversation",
        )
        # Existing private, bounded audit store of local decisions.
        record = {
            "text": text,
            "route": route,
            "intent": name,
            "slots": slots,
            "elapsed_ms": round((time.monotonic() - started) * 1000),
            "speech": response.speech,
        }
        owner = self.entry.runtime_data
        owner.audit.append(record)
        del owner.audit[:-200]
        if owner._store:
            owner._store.async_delay_save(lambda: {"records": owner.audit}, 5)
        return conversation.ConversationResult(
            response=response, conversation_id=chat_log.conversation_id
        )
