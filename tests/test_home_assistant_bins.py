"""Render the bin collection templates with Home Assistant's Jinja helpers stubbed.

The calendar fixture mirrors what Waste Collection Schedule publishes for
the Auckland Council source: one all-day event per bin for its next date.
The checks protect which bins are announced for which evening, the stale
warning, and that the dashboard only uses entities this config defines.
"""

from __future__ import annotations

import ast
import datetime as dt
import re

import pytest
import yaml
from conftest import load_yaml

jinja2_sandbox = pytest.importorskip("jinja2.sandbox")

REVISION = "67cb32c01a65331cc0acc51eaa4311225a908e90"
TREE = "db613968d04c6ad0237b6382b33e585bfaf0d4c2"
NZDT = dt.timezone(dt.timedelta(hours=13))
CALENDAR = "calendar.bin_collections"


def _bootstrap() -> dict:
    return load_yaml("apps/home-assistant/manifests/configmap-bootstrap.yaml")["data"]


def _events(*items: tuple[str, str]) -> dict:
    return {
        CALENDAR: {
            "events": [
                {"start": day, "end": day, "summary": kind, "description": ""}
                for kind, day in items
            ]
        }
    }


class FakeHass:
    def __init__(self, now: dt.datetime) -> None:
        self.now = now
        self.states: dict[str, tuple[str, dict]] = {
            CALENDAR: ("off", {}),
            "input_datetime.bins_out_for": ("unknown", {}),
        }
        env = jinja2_sandbox.ImmutableSandboxedEnvironment(extensions=["jinja2.ext.loopcontrols"])
        env.globals.update(
            state_attr=lambda e, a: self.states.get(e, (None, {}))[1].get(a),
            states=lambda e: self.states.get(e, ("unknown", {}))[0],
            has_value=lambda e: (
                self.states.get(e, ("unknown", {}))[0] not in ("unknown", "unavailable")
            ),
            strptime=dt.datetime.strptime,
            now=lambda: self.now,
        )
        env.filters["regex_replace"] = lambda value, find="", replace="": re.sub(
            find, replace, value
        )
        self.env = env

    def render(self, template: str, **variables):
        text = self.env.from_string(template).render(**variables).strip()
        try:
            return ast.literal_eval(text)
        except (ValueError, SyntaxError):
            return text

    def read_calendar(self, calendar: dict) -> None:
        block = _templates()[2]
        assert block["action"][0]["action"] == "calendar.get_events"
        variables = {"calendar": calendar}
        for name, template in block["action"][1]["variables"].items():
            variables[name] = self.render(template, **variables)
        sensor = block["sensor"][0]
        attributes = {k: self.render(v, **variables) for k, v in sensor["attributes"].items()}
        self.states["sensor.bins_schedule"] = (
            self.render(sensor["state"], **variables),
            attributes,
        )
        self.refresh()

    def refresh(self) -> None:
        for sensor in _templates()[3]["sensor"]:
            entity = f"sensor.{sensor['unique_id']}"
            if "availability" in sensor and not self.render(sensor["availability"]):
                self.states[entity] = ("unavailable", {})
                continue
            attributes = {k: self.render(v) for k, v in sensor.get("attributes", {}).items()}
            self.states[entity] = (str(self.render(sensor["state"])), attributes)
        # Status reads the sensors above, so render it after they settle.
        status = _templates()[3]["sensor"][-1]
        self.states["sensor.bins_status"] = (self.render(status["state"]), {})


def _templates() -> list[dict]:
    return yaml.safe_load(_bootstrap()["templates.yaml"])


def _automations() -> dict[str, dict]:
    return {a["id"]: a for a in yaml.safe_load(_bootstrap()["automations.yaml"])}


def _scripts() -> dict[str, dict]:
    return yaml.safe_load(_bootstrap()["scripts.yaml"])


def _reminder_due(hass: FakeHass, automation_id: str) -> bool:
    conditions = _automations()[automation_id]["conditions"]
    paused = hass.states.get("input_boolean.bins_reminders_paused", ("off", {}))[0]
    template = next(c for c in conditions if c["condition"] == "template")
    return paused == "off" and hass.render(template["value_template"]) is True


def _notification(hass: FakeHass) -> str:
    step = _scripts()["bins_notify"]["sequence"][1]
    return hass.render(step["data"]["message"])


def test_waste_collection_is_installed_from_a_verified_revision() -> None:
    spec = load_yaml("apps/home-assistant/manifests/deployment.yaml")["spec"]["template"]["spec"]
    init_containers = {item["name"]: item for item in spec["initContainers"]}
    script = init_containers["install-waste-collection"]["command"][-1]

    assert f'revision="{REVISION}"' in script
    assert f'expected_tree="{TREE}"' in script
    assert "rev-parse FETCH_HEAD:custom_components/waste_collection_schedule" in script
    assert "source/aucklandcouncil_govt_nz.py" in script
    assert 'rm -rf "${install_dir}"' in script
    assert "rm -rf /config/custom_components\n" not in script
    copy_script = init_containers["bootstrap-config"]["command"][-1]
    assert "cp /bootstrap/bins-dashboard.yaml /config/dashboards/bins.yaml" in copy_script


def test_full_collection_is_announced_the_evening_before() -> None:
    hass = FakeHass(dt.datetime(2026, 11, 10, 18, 30, tzinfo=NZDT))
    hass.read_calendar(
        _events(
            ("rubbish", "2026-11-04"),  # already collected, still in the window
            ("recycling", "2026-11-11"),
            ("food scraps", "2026-11-11"),
            ("rubbish", "2026-11-11"),
        )
    )

    state, attrs = hass.states["sensor.bins_next_collection"]
    assert state == "2026-11-11"
    assert attrs["bins"] == ["Rubbish", "Food scraps", "Recycling"]
    assert attrs["summary"] == "Rubbish, food scraps and recycling"
    assert (attrs["days"], attrs["when"]) == (1, "Tomorrow")
    assert hass.states["sensor.bins_status"][0] == "Put out tonight"
    assert _reminder_due(hass, "bins_evening_reminder")
    assert not _reminder_due(hass, "bins_morning_last_call")
    message = _notification(hass)
    assert "Rubbish, food scraps and recycling tomorrow (Wed 11 Nov)" in message
    assert "🟡 Recycling" in message

    # Pressing "They're out" records the date and silences the 21:00 reminder.
    mark = _scripts()["bins_mark_out"]["sequence"][1]
    hass.states["input_datetime.bins_out_for"] = (hass.render(mark["data"]["date"]), {})
    hass.refresh()
    assert hass.states["sensor.bins_status"][0] == "Out"
    assert not _reminder_due(hass, "bins_evening_reminder")

    hass.states["input_datetime.bins_out_for"] = ("unknown", {})
    hass.states["input_boolean.bins_reminders_paused"] = ("on", {})
    assert not _reminder_due(hass, "bins_evening_reminder")


def test_off_week_leaves_recycling_out_and_morning_call_waits_for_the_day() -> None:
    hass = FakeHass(dt.datetime(2026, 11, 12, 9, tzinfo=NZDT))
    hass.read_calendar(
        _events(
            ("rubbish", "2026-11-18"),
            ("food scraps", "2026-11-18"),
            ("recycling", "2026-11-25"),
            ("garden waste", "2026-11-18"),
        )
    )

    _, attrs = hass.states["sensor.bins_next_collection"]
    # Kinds the council adds later are listed after the usual three.
    assert attrs["bins"] == ["Rubbish", "Food scraps", "Garden waste"]
    assert attrs["summary"] == "Rubbish, food scraps and garden waste"
    assert attrs["when"] == "Wednesday"
    assert hass.states["sensor.bins_recycling"] == (
        "2026-11-25",
        {"when": "In 13 days", "frequency": "Fortnightly"},
    )
    assert not _reminder_due(hass, "bins_evening_reminder")

    hass.now = dt.datetime(2026, 11, 18, 6, 15, tzinfo=NZDT)
    hass.refresh()
    assert hass.states["sensor.bins_status"][0] == "Collection today"
    assert _reminder_due(hass, "bins_morning_last_call")
    assert "Rubbish, food scraps and garden waste today (Wed 18 Nov)" in _notification(hass)


def test_a_frozen_schedule_goes_unavailable_and_warns() -> None:
    hass = FakeHass(dt.datetime(2026, 11, 10, 12, tzinfo=NZDT))
    hass.read_calendar(_events(("rubbish", "2026-11-11"), ("food scraps", "2026-11-11")))
    stale = _automations()["bins_schedule_stale"]["conditions"][0]["value_template"]
    assert hass.render(stale) is False

    # The calendar vanished: the stored dates pass and nothing is announced.
    hass.now = dt.datetime(2026, 11, 12, 10, tzinfo=NZDT)
    hass.refresh()
    assert hass.states["sensor.bins_next_collection"][0] == "unavailable"
    assert hass.states["sensor.bins_status"][0] == "No schedule"
    assert hass.render(stale) is True
    assert not _reminder_due(hass, "bins_evening_reminder")


def test_bins_dashboard_only_uses_entities_this_config_defines() -> None:
    bootstrap = _bootstrap()
    configuration = bootstrap["configuration.yaml"]
    assert "filename: dashboards/bins.yaml" in configuration

    defined = {CALENDAR}
    for block in _templates():
        for sensor in block.get("sensor", []):
            slug = re.sub(r"[^a-z0-9]+", "_", sensor["name"].lower()).strip("_")
            assert slug == sensor["unique_id"]
            defined.add(f"sensor.{slug}")
    defined |= {f"script.{name}" for name in _scripts()}
    for helper in ("bins_reminders_paused", "bins_out_for"):
        assert f"\n  {helper}:\n" in configuration
    defined |= {"input_boolean.bins_reminders_paused", "input_datetime.bins_out_for"}

    dashboard = yaml.safe_load(bootstrap["bins-dashboard.yaml"])
    cards = [card for section in dashboard["views"][0]["sections"] for card in section["cards"]]
    used = {card["entity"] for card in cards if "entity" in card}
    used |= {e for card in cards for e in card.get("entities", [])}
    used |= {b["entity"] for b in dashboard["views"][0]["badges"]}
    assert used and used <= defined


def test_a_reminder_sent_early_names_the_weekday() -> None:
    hass = FakeHass(dt.datetime(2026, 11, 5, 10, tzinfo=NZDT))
    hass.read_calendar(_events(("rubbish", "2026-11-11"), ("food scraps", "2026-11-11")))
    assert "Rubbish and food scraps on Wednesday (Wed 11 Nov)" in _notification(hass)
