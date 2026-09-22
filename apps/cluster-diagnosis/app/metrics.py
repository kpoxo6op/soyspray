"""Render the incident loop's state as Prometheus text.

Only numbers and bounded labels are exposed. No evidence, prompt or provider
response reaches this endpoint, and an absent value stays absent so the
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
        "Whether the spend guard could be read. 0 stops all model calls.",
    ),
    (
        "soyspray_diagnosis_attempts_today",
        "gauge",
        "Transmissions charged to the current Auckland day.",
    ),
    ("soyspray_diagnosis_attempt_limit", "gauge", "Daily transmission ceiling."),
    ("soyspray_diagnosis_tokens_today", "gauge", "Tokens charged to the current Auckland day."),
    ("soyspray_diagnosis_token_limit", "gauge", "Daily token ceiling."),
    ("soyspray_diagnosis_provider_blocked", "gauge", "1 when the provider rejected the key."),
    (
        "soyspray_diagnosis_outbox_pending",
        "gauge",
        "Diagnosis messages waiting for delivery.",
    ),
    ("soyspray_diagnosis_delivery_total", "counter", "Delivery attempts by result."),
    ("soyspray_diagnosis_outcome_total", "counter", "Diagnosis outcomes since start."),
    (
        "soyspray_diagnosis_last_success_timestamp_seconds",
        "gauge",
        "Time of the last delivered narrative.",
    ),
    (
        "soyspray_diagnosis_model_info",
        "gauge",
        "Serving model and profile of the last request.",
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
    ("soyspray_classifier_up", "gauge", "Whether the classifier returned usable hints."),
    ("soyspray_classifier_failure_total", "counter", "Classifier requests that failed."),
    ("soyspray_classifier_unknown_total", "counter", "Evidence lines left explicitly unknown."),
    (
        "soyspray_classifier_last_success_timestamp_seconds",
        "gauge",
        "Last successful classification.",
    ),
    ("soyspray_classifier_model_info", "gauge", "Serving classifier model."),
    ("soyspray_classifier_result_total", "gauge", "Classifier labels in the last incident."),
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
    blocked: bool,
    attempt_limit: int,
    token_limit: int,
    poll_seconds: int,
    model: str = "",
    profile: str = "",
) -> str:
    out = Renderer()
    out.metric("soyspray_diagnosis_up", 1)
    out.metric("soyspray_diagnosis_state_usable", int(state_usable))
    out.metric("soyspray_diagnosis_alertmanager_source_ok", int(source_ok))
    out.metric("soyspray_diagnosis_provider_blocked", int(blocked))
    out.metric("soyspray_diagnosis_attempt_limit", attempt_limit)
    out.metric("soyspray_diagnosis_token_limit", token_limit)

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
    for result, count in list((metrics.get("deliveries") or {}).items())[:16]:
        out.info("soyspray_diagnosis_delivery_total", count, {"result": result})
    out.metric("soyspray_diagnosis_outbox_pending", len(state.get("outbox") or []))
    if model:
        out.info("soyspray_diagnosis_model_info", 1, {"model": model, "profile": profile})

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

    classifier = state.get("classifier") or {}
    status = str(classifier.get("status", "unknown"))
    if status in {"ok", "cached", "partial", "unavailable", "quota-exhausted"}:
        out.metric("soyspray_classifier_up", int(status in {"ok", "cached", "partial"}))
    if classifier.get("model"):
        out.info("soyspray_classifier_model_info", 1, {"model": classifier["model"]})
    out.metric("soyspray_classifier_failure_total", (metrics.get("classifier_failures") or 0))
    out.metric("soyspray_classifier_unknown_total", (metrics.get("classifier_unknown") or 0))
    out.metric(
        "soyspray_classifier_last_success_timestamp_seconds",
        metrics.get("classifier_last_success_timestamp_seconds"),
    )
    for label, count in list((classifier.get("counts") or {}).items())[:16]:
        out.info("soyspray_classifier_result_total", count, {"label": label})
    return out.text()


def incident_time(value: object) -> float | None:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    return parsed.timestamp() if parsed.tzinfo else None
