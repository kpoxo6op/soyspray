"""Validate interpretations before any Home Assistant intent is called."""

import re
from dataclasses import dataclass

FIELDS = {"kind", "intent", "targets", "brightness_pct", "question"}
INTENTS = {"turn_on": "HassTurnOn", "turn_off": "HassTurnOff", "set_brightness": "HassLightSet"}
NO_ACTION = re.compile(
    r"\b(don['’]?t|do not|never|not|no|stop|cancel|unless|except|without|"
    r"tomorrow|later|kettle|siren|heater|vacuum|door|lock|alarm)\b",
    re.IGNORECASE,
)
CONTEXTUAL = re.compile(r"\b(it|them|those|that|again|brighter|dimmer|more|less)\b", re.I)


@dataclass(frozen=True)
class Interpretation:
    kind: str
    intent: str | None
    targets: tuple[str, ...]
    brightness_pct: int | None
    question: str | None


def validate(value, eligible):
    """Reject malformed, unsupported or out-of-catalog actions."""
    if not isinstance(value, dict) or set(value) != FIELDS:
        raise ValueError("Invalid interpretation fields")
    kind = value["kind"]
    if kind not in {"action", "clarify", "none"}:
        raise ValueError("Invalid interpretation kind")
    targets = value["targets"]
    if (
        not isinstance(targets, list)
        or any(not isinstance(target, str) for target in targets)
        or len(targets) != len(set(targets))
        or len(targets) > 4
    ):
        raise ValueError("Invalid targets")
    if kind == "action":
        if value["intent"] not in INTENTS or not targets or value["question"] is not None:
            raise ValueError("Invalid action")
        if any(target not in eligible or not target.startswith("light.") for target in targets):
            raise ValueError("Ineligible target")
        brightness = value["brightness_pct"]
        if value["intent"] == "set_brightness":
            if type(brightness) is not int or not 1 <= brightness <= 100:
                raise ValueError("Invalid brightness")
        elif brightness is not None:
            raise ValueError("Unexpected brightness")
    else:
        if targets or value["intent"] is not None or value["brightness_pct"] is not None:
            raise ValueError("Non-action carries an action")
        question = value["question"]
        if kind == "clarify":
            if not isinstance(question, str) or not 1 <= len(question) <= 140:
                raise ValueError("Invalid clarification")
        elif question is not None:
            raise ValueError("Unexpected question")
    return Interpretation(
        kind, value["intent"], tuple(targets), value["brightness_pct"], value["question"]
    )
