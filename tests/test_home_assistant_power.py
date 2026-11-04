"""Render the Power insight templates with Home Assistant's Jinja helpers stubbed.

The fixture is two real Mercury days (1-2 Nov 2026, 1 Nov missing its 00:00
hour as the integration delivered it). The checks protect the money maths
and the once-per-day accounting, not the template text.
"""

from __future__ import annotations

import ast
import datetime as dt
import re

import pytest
import yaml
from conftest import load_yaml

jinja2_sandbox = pytest.importorskip("jinja2.sandbox")

HOURLY = {
    "2026-11-01": [
        None,
        0.76,
        0.36,
        1.18,
        0.88,
        0.23,
        0.76,
        0.27,
        0.38,
        0.82,
        0.25,
        0.27,
        0.26,
        0.26,
        0.26,
        0.26,
        0.80,
        0.38,
        0.44,
        0.48,
        0.31,
        0.95,
        0.38,
        1.39,
    ],
    "2026-11-02": [
        0.30,
        0.21,
        0.77,
        0.21,
        0.22,
        0.22,
        0.24,
        0.45,
        0.81,
        0.21,
        0.22,
        0.26,
        0.32,
        0.25,
        0.36,
        1.17,
        0.87,
        0.51,
        0.45,
        0.42,
        0.46,
        0.97,
        0.39,
        0.39,
    ],
}
DAILY = [
    ("2026-10-27", 11.98, 5.71),
    ("2026-10-28", 10.37, 5.17),
    ("2026-10-29", 11.46, 5.53),
    ("2026-10-30", 10.14, 5.09),
    ("2026-10-31", 13.15, 6.09),
    ("2026-11-01", 13.16, 6.10),
    ("2026-11-02", 10.67, 5.27),
]


def _hours(days: dict[str, list[float | None]]) -> list[dict]:
    return [
        {"datetime": f"{day}T{hour:02d}:00:00+13:00", "consumption": kwh}
        for day, values in days.items()
        for hour, kwh in enumerate(values)
        if kwh is not None
    ]


class FakeHass:
    def __init__(self) -> None:
        self.states: dict[str, tuple[str, dict]] = {
            "sensor.mercury_nz_energy_usage": (
                "11.66",
                {
                    "daily_usage_history": [
                        {"date": f"{d}T00:00:00+13:00", "consumption": k, "cost": c}
                        for d, k, c in DAILY
                    ],
                    "hourly_usage_history": _hours(HOURLY),
                },
            ),
            "sensor.mercury_nz_current_rate": ("0.3327", {}),
        }
        env = jinja2_sandbox.ImmutableSandboxedEnvironment()
        env.globals.update(
            state_attr=lambda e, a: self.states.get(e, (None, {}))[1].get(a),
            states=lambda e: self.states.get(e, ("unknown", {}))[0],
            has_value=lambda e: (
                self.states.get(e, ("unknown", {}))[0] not in ("unknown", "unavailable")
            ),
            strptime=dt.datetime.strptime,
            as_datetime=dt.datetime.fromisoformat,
            now=lambda: dt.datetime(2026, 11, 4, 13, tzinfo=dt.timezone(dt.timedelta(hours=13))),
        )
        env.filters["regex_replace"] = lambda value, find="", replace="": re.sub(
            find, replace, value
        )
        env.tests["search"] = lambda value, pattern: re.search(pattern, value) is not None
        self.env = env

    def render(self, template: str, **variables):
        text = self.env.from_string(template).render(**variables).strip()
        try:
            return ast.literal_eval(text)
        except (ValueError, SyntaxError):
            return text


def _templates() -> list[dict]:
    data = load_yaml("apps/home-assistant/manifests/configmap-bootstrap.yaml")["data"]
    return yaml.safe_load(data["templates.yaml"])


def _run_plan_check(hass: FakeHass, block: dict) -> tuple[str, dict]:
    variables: dict = {}
    for name, template in block["action"][0]["variables"].items():
        variables[name] = hass.render(template, **variables)
    sensor = block["sensor"][0]
    state = hass.render(sensor["state"], **variables)
    attributes = {k: hass.render(v, **variables) for k, v in sensor["attributes"].items()}
    hass.states["sensor.power_plan_check"] = (state, attributes)
    return state, attributes


def test_plain_power_sensors_follow_the_mercury_history() -> None:
    hass = FakeHass()
    sensors = {s["unique_id"]: s for s in _templates()[0]["sensor"]}

    assert hass.render(sensors["power_latest_day"]["state"]) == "2026-11-02"
    hass.states["sensor.power_latest_day"] = ("2026-11-02", {})
    assert hass.render(sensors["power_data_age"]["state"]) == 2
    assert hass.render(sensors["power_last_7_days_cost"]["state"]) == pytest.approx(38.96)
    assert hass.render(sensors["power_last_7_days_usage"]["state"]) == pytest.approx(80.9)
    # Mean of the three quietest hours (0.21 kWh each) is a 210 W floor.
    assert hass.render(sensors["power_always_on"]["state"]) == 210
    assert hass.render(sensors["power_always_on"]["attributes"]["yearly_cost"]) == 612


def test_plan_check_prices_each_complete_day_once() -> None:
    hass = FakeHass()
    block = _templates()[1]

    state, attributes = _run_plan_check(hass, block)
    totals = attributes["totals"]
    flat = sum(k for values in HOURLY.values() for k in values if k) * 0.3327 + 2 * 1.725
    assert attributes["days"] == 2
    assert attributes["last_day"] == "2026-11-02"
    assert totals["Mercury Flat Rates (now)"] == pytest.approx(flat, abs=0.01)
    assert state == min(totals, key=totals.get)
    assert attributes["saving_vs_now"] == pytest.approx(
        totals["Mercury Flat Rates (now)"] - min(totals.values()), abs=0.01
    )

    # A restart re-fires the trigger with the same day: nothing is added.
    _, again = _run_plan_check(hass, block)
    assert again["totals"] == totals and again["days"] == 2

    # A partial day (Mercury still delivering) is not priced yet.
    hours = hass.states["sensor.mercury_nz_energy_usage"][1]
    hours["hourly_usage_history"] = _hours({"2026-11-03": [0.3] * 10})
    _, partial = _run_plan_check(hass, block)
    assert partial["days"] == 2

    # The next complete day adds exactly one day on every plan.
    hours["hourly_usage_history"] = _hours({"2026-11-03": [0.5] * 24})
    _, nxt = _run_plan_check(hass, block)
    assert nxt["days"] == 3
    assert nxt["totals"]["Mercury Flat Rates (now)"] == pytest.approx(
        totals["Mercury Flat Rates (now)"] + 12 * 0.3327 + 1.725, abs=0.01
    )
