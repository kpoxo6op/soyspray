"""Render the incident loop's state as Prometheus text.

Only numbers and bounded labels are exposed. No log text or alert prose
reaches this endpoint, and an absent value stays absent so the
dashboard shows unknown instead of a false zero.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

MAX_INCIDENT_ANCHORS = 40
MAX_LABEL = 80
SAFE_LABEL = re.compile(r"[^A-Za-z0-9_.:/ -]")

HELP = (
    ("soyspray_diagnosis_up", "gauge", "Whether the incident loop is running."),
    (
        "soyspray_diagnosis_last_poll_timestamp_seconds",
        "gauge",
        "Completion time of the last Alertmanager poll.",
    ),
    (
        "soyspray_diagnosis_state_usable",
        "gauge",
        "Whether incident and delivery state could be read.",
    ),
    (
        "soyspray_diagnosis_outbox_pending",
        "gauge",
        "Diagnosis messages waiting for delivery.",
    ),
    ("soyspray_diagnosis_delivery_total", "counter", "Delivery attempts by result."),
    ("soyspray_diagnosis_outcome_total", "counter", "Diagnosis outcomes since start."),
    (
        "soyspray_diagnosis_suppressed_total",
        "counter",
        "Incidents the loop examined and stayed silent about.",
    ),
    (
        "soyspray_diagnosis_last_success_timestamp_seconds",
        "gauge",
        "Time of the last message delivered to Telegram, of any outcome.",
    ),
    (
        "soyspray_diagnosis_outbox_oldest_seconds",
        "gauge",
        "Age of the oldest message waiting for Telegram.",
    ),
    (
        "soyspray_diagnosis_alertmanager_source_ok",
        "gauge",
        "Whether the last Alertmanager read succeeded.",
    ),
    ("soyspray_incident_open", "gauge", "Incidents currently open."),
    (
        "soyspray_incident_opened_timestamp_seconds",
        "gauge",
        "Open time of a tracked incident.",
    ),
    (
        "soyspray_incident_consequence",
        "gauge",
        "Application incident owned by an open node incident.",
    ),
    (
        "soyspray_incident_overflow_total",
        "gauge",
        "Symptoms dropped because an incident was full.",
    ),
    ("soyspray_evidence_collector_observed", "gauge", "Whether the last incident produced a pack."),
    ("soyspray_evidence_lines_read_total", "gauge", "Log lines read for the last incident."),
    ("soyspray_evidence_lines_exported_total", "gauge", "Log lines exported after allowlisting."),
    ("soyspray_evidence_gap_total", "gauge", "Evidence gaps by reason."),
)


def bounded(value: object) -> str:
    return SAFE_LABEL.sub("_", str(value))[:MAX_LABEL]


def _labels(labels: dict[str, str]) -> str:
    if not labels:
        return ""
    body = ",".join(f'{key}="{value}"' for key, value in sorted(labels.items()))
    return "{" + body + "}"


def _number(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


class Renderer:
    """Collects series and emits a complete exposition."""

    def __init__(self) -> None:
        self.lines: list[str] = []

    def metric(self, name: str, value: object, labels: dict[str, str] | None = None) -> None:
        number = _number(value)
        if number is None:
            return
        self.lines.append(f"{name}{_labels(labels or {})} {number}")

    def info(self, name: str, value: object, labels: dict[str, str]) -> None:
        self.metric(name, value, {key: bounded(item) for key, item in labels.items()})

    def text(self) -> str:
        body = [f"# HELP {name} {help_text}" for name, _kind, help_text in HELP]
        body += [f"# TYPE {name} {kind}" for name, kind, _help in HELP]
        return "\n".join(body + self.lines) + "\n"


def render(
    state: dict[str, Any],
    *,
    now: datetime,
    source_ok: bool,
    state_usable: bool,
    poll_seconds: int,
) -> str:
    out = Renderer()
    out.metric("soyspray_diagnosis_up", 1)
    out.metric("soyspray_diagnosis_state_usable", int(state_usable))
    out.metric("soyspray_diagnosis_alertmanager_source_ok", int(source_ok))

    metrics = state.get("metrics") or {}
    out.metric(
        "soyspray_diagnosis_last_poll_timestamp_seconds",
        metrics.get("last_poll_timestamp_seconds"),
    )
    out.metric(
        "soyspray_diagnosis_last_success_timestamp_seconds",
        metrics.get("last_success_timestamp_seconds"),
    )
    for outcome, count in list((metrics.get("outcomes") or {}).items())[:32]:
        out.info("soyspray_diagnosis_outcome_total", count, {"outcome": outcome})
    for reason, count in list((metrics.get("suppressed") or {}).items())[:8]:
        out.info("soyspray_diagnosis_suppressed_total", count, {"reason": reason})
    for result, count in list((metrics.get("deliveries") or {}).items())[:16]:
        out.info("soyspray_diagnosis_delivery_total", count, {"result": result})
    outbox = [entry for entry in (state.get("outbox") or []) if isinstance(entry, dict)]
    out.metric("soyspray_diagnosis_outbox_pending", len(outbox))
    oldest = oldest_outbox_seconds(outbox, now)
    if oldest is not None:
        out.metric("soyspray_diagnosis_outbox_oldest_seconds", oldest)

    for item in (state.get("incidents") or {}).values():
        anchor = bounded(item.get("anchor", "unknown"))
        kind = bounded(item.get("kind", "unknown"))
        out.metric("soyspray_incident_open", 1, {"anchor": anchor, "kind": kind})
        opened = incident_time(item.get("opened_at"))
        if opened:
            out.metric(
                "soyspray_incident_opened_timestamp_seconds",
                opened,
                {"anchor": anchor, "kind": kind},
            )
        overflow = item.get("symptom_overflow")
        if isinstance(overflow, int) and overflow > 0:
            out.metric("soyspray_incident_overflow_total", overflow, {"anchor": anchor})
        for consequence in (item.get("consequences") or [])[:MAX_INCIDENT_ANCHORS]:
            out.metric(
                "soyspray_incident_consequence",
                1,
                {"anchor": bounded(consequence), "parent": anchor},
            )

    collector = state.get("collector") or {}
    if collector.get("status") not in (None, "unknown"):
        status = str(collector.get("status"))
        out.metric("soyspray_evidence_collector_observed", int(status in {"observed", "partial"}))
        out.metric("soyspray_evidence_lines_read_total", collector.get("lines"))
        out.metric("soyspray_evidence_lines_exported_total", collector.get("exported"))
        for reason, count in list((collector.get("gaps") or {}).items())[:32]:
            out.info("soyspray_evidence_gap_total", count, {"reason": reason})

    return out.text()


def oldest_outbox_seconds(outbox: list[dict[str, Any]], now: datetime) -> float | None:
    """Age of the oldest queued message, or nothing when the outbox is empty."""
    queued = [
        float(entry["queued_at"])
        for entry in outbox
        if isinstance(entry.get("queued_at"), (int, float))
        and not isinstance(entry.get("queued_at"), bool)
    ]
    if not queued:
        return None
    return max(0.0, now.timestamp() - min(queued))


def incident_time(value: object) -> float | None:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    return parsed.timestamp() if parsed.tzinfo else None
