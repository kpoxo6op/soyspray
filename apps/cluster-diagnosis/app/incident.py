#!/usr/bin/env python3
"""Group Alertmanager alerts into operational incidents and track their lifecycle.

An incident is one thing an operator would investigate. Related symptoms keep one
identity. Independent failures keep separate identities. The model reads this
module's output, so every value that crosses into a prompt passes an allowlist.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timedelta
from typing import Any, Iterable
from urllib.parse import urlsplit, urlunsplit

# Only alerts that can reach a human are operational incidents. Watchdog and
# InfoInhibitor are synthetic bookkeeping alerts at severity none, and info
# alerts never page, so tracking them would show a permanently open incident.
TRACKED_SEVERITIES = frozenset({"critical", "warning"})
# Symptoms that arrive inside this window belong to the same incident.
CORRELATION_WINDOW = timedelta(minutes=30)
# An incident with no firing symptom is closed after this grace period. The grace
# absorbs a resolve and refire inside one Alertmanager resolve timeout.
RECOVERY_GRACE = timedelta(minutes=3)
# One symptom that stops being reported is closed after this grace period, even
# while a sibling symptom keeps the incident's anchor visible.
SYMPTOM_GRACE = timedelta(minutes=5)
# A silent incident is discarded after this long, even if a symptom never closed.
STALE_AFTER = timedelta(hours=12)
# A reopened anchor keeps the generation chain only inside this window.
REOPEN_WINDOW = timedelta(hours=6)
# Bounded memory for one incident and for the private state file.
MAX_SYMPTOMS = 24
MAX_ATTEMPTS_PER_GENERATION = 3
MAX_CLOSED_INCIDENTS = 40
MAX_ACTIVE_INCIDENTS = 40

STATE_VERSION = 2

SAFE_LABEL = re.compile(r"[a-zA-Z0-9_.:/-]{1,253}")
SECRET_KEY_MARKERS = (
    "password",
    "secret",
    "token",
    "credential",
    "authorization",
    "api_key",
    "apikey",
    "private_key",
    "access_key",
)

# Labels that name the owned resource. These select evidence for the incident.
RESOURCE_LABELS = (
    "namespace",
    "app_namespace",
    "pvc_namespace",
    "pod",
    "container",
    "node",
    "pvc",
    "persistentvolumeclaim",
    "deployment",
    "statefulset",
    "daemonset",
    "job",
    "cronjob",
    "job_name",
    "service",
    "instance",
    "reason",
    "kubernetes_event_involved_object_name",
    "kubernetes_event_involved_object_kind",
)

# Labels that may reach the model prompt.
PROMPT_LABELS = (
    "alertname",
    "severity",
    "namespace",
    "app_namespace",
    "pvc_namespace",
    "pod",
    "container",
    "deployment",
    "statefulset",
    "daemonset",
    "job",
    "cronjob",
    "job_name",
    "node",
    "pvc",
    "service",
    "reason",
    "kubernetes_event_involved_object_name",
    "kubernetes_event_involved_object_kind",
)


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _safe_value(value: Any) -> Any:
    if isinstance(value, dict):
        return safe_map(value)
    if isinstance(value, list):
        return [_safe_value(item) for item in value]
    if not isinstance(value, str):
        return value
    lowered = value.lower()
    if any(marker in lowered for marker in SECRET_KEY_MARKERS):
        return "[redacted]"
    if "@" in value and "://" in value:
        parsed = urlsplit(value)
        if parsed.username or parsed.password:
            host = parsed.hostname or ""
            if parsed.port:
                host += f":{parsed.port}"
            return urlunsplit(parsed._replace(netloc=f"<redacted>@{host}"))
    return value


def safe_map(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    return {
        str(key): "[redacted]"
        if any(marker in str(key).lower() for marker in SECRET_KEY_MARKERS)
        else _safe_value(item)
        for key, item in value.items()
    }


def redacted_url(url: str) -> str:
    parsed = urlsplit(url)
    if parsed.username or parsed.password:
        host = parsed.hostname or ""
        if parsed.port:
            host += f":{parsed.port}"
        parsed = parsed._replace(netloc=f"<redacted>@{host}")
    return urlunsplit(parsed)


def parse_time(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else None


def safe_label(value: Any) -> str:
    """Return a label value only when it matches the shared safe charset."""
    if isinstance(value, str) and SAFE_LABEL.fullmatch(value):
        return value
    return ""


def alert_fingerprint(alert: dict[str, Any]) -> str:
    fingerprint = str(alert.get("fingerprint", "")).strip()
    if fingerprint:
        return fingerprint
    source = {"labels": alert.get("labels", {}), "generatorURL": alert.get("generatorURL", "")}
    return hashlib.sha256(_json(source).encode()).hexdigest()[:32]


def alert_hash(alert: dict[str, Any]) -> str:
    """Hash incident meaning, excluding Alertmanager refresh timestamps."""
    status = alert.get("status", {}) or {}
    value = {
        "labels": safe_map(alert.get("labels", {})),
        "annotations": safe_map(alert.get("annotations", {})),
        "status": {
            "state": status.get("state", ""),
            "silencedBy": status.get("silencedBy", []),
            "inhibitedBy": status.get("inhibitedBy", []),
        },
        "startsAt": alert.get("startsAt", ""),
    }
    return hashlib.sha256(_json(value).encode()).hexdigest()


def alert_state(alert: dict[str, Any], now: datetime) -> str:
    """Classify one Alertmanager alert as firing, resolved, suppressed or pending."""
    status = alert.get("status", {}) or {}
    if status.get("silencedBy") or status.get("inhibitedBy"):
        return "suppressed"
    if status.get("state") != "active":
        return "pending"
    starts = parse_time(alert.get("startsAt"))
    if starts is None or starts > now:
        return "pending"
    ends = parse_time(alert.get("endsAt"))
    if ends is not None and ends <= now:
        return "resolved"
    return "firing"


def severity(alert: dict[str, Any]) -> str:
    value = str((alert.get("labels") or {}).get("severity", "")).lower()
    return value if value in {"critical", "warning", "info", "none"} else "unknown"


def anchor(alert: dict[str, Any]) -> tuple[str, str]:
    """Return the (kind, key) ownership anchor for one alert.

    A namespaced alert belongs to its application. A node alert without a
    namespace belongs to the node. Anything else falls back to its named
    resource, then to the alert name.
    """
    labels = alert.get("labels") or {}
    namespace = safe_label(labels.get("namespace")) or safe_label(labels.get("app_namespace"))
    if not namespace:
        namespace = safe_label(labels.get("pvc_namespace"))
    node = safe_label(labels.get("node"))
    alertname = safe_label(labels.get("alertname"))
    if namespace:
        return "app", namespace
    if node:
        return "node", node
    for key, kind in (
        ("pvc", "volume"),
        ("persistentvolumeclaim", "volume"),
        ("service", "service"),
        ("instance", "target"),
        ("job", "job"),
    ):
        value = safe_label(labels.get(key))
        if value:
            return kind, value
    return "alert", alertname or "unknown"


def anchor_id(kind: str, key: str) -> str:
    return f"{kind}:{key}" if key else kind


SYMPTOM_KEYS = (
    "pod",
    "container",
    "pvc",
    "persistentvolumeclaim",
    "kubernetes_event_involved_object_name",
    "node",
    "instance",
    "job",
)


def symptom_name(alert: dict[str, Any]) -> str:
    """Name one symptom by every discriminating label it carries.

    Two containers in one pod are two symptoms, and an event-derived alert keeps
    the object it is about. Sharing a name would let a resolved sibling hide a
    firing failure.
    """
    labels = alert.get("labels") or {}
    alertname = safe_label(labels.get("alertname")) or "Alert"
    parts = [value for key in SYMPTOM_KEYS if (value := safe_label(labels.get(key)))]
    return f"{alertname}({', '.join(parts)})" if parts else alertname


def prompt_labels(alert: dict[str, Any]) -> dict[str, str]:
    """Return only the allowlisted, charset-safe labels that may enter a prompt."""
    labels = alert.get("labels") or {}
    return {key: value for key in PROMPT_LABELS if (value := safe_label(labels.get(key)))}


def evidence_targets(alert: dict[str, Any]) -> dict[str, str]:
    """Return the bounded resource selection used to gather incident evidence."""
    labels = alert.get("labels") or {}
    target = {key: value for key in RESOURCE_LABELS if (value := safe_label(labels.get(key)))}
    if "namespace" not in target:
        for alias in ("app_namespace", "pvc_namespace"):
            if alias in target:
                target["namespace"] = target[alias]
                break
    return target


def qualifying(alert: dict[str, Any], now: datetime, *, minimum_severity: str = "critical") -> bool:
    """An alert may start incident work only when it fires and can page a human."""
    if alert_state(alert, now) != "firing":
        return False
    if minimum_severity == "warning":
        return severity(alert) in {"critical", "warning"}
    return severity(alert) == "critical"


def visible_symptoms(alert: dict[str, Any], now: datetime) -> bool:
    """Return True when an alert should keep an incident open, at any severity."""
    return alert_state(alert, now) in {"firing", "pending"}


def incident_key(kind: str, key: str) -> str:
    return hashlib.sha256(f"{kind}|{key}".encode()).hexdigest()[:16]


class Incident:
    """One tracked incident and its symptoms."""

    def __init__(self, record: dict[str, Any]):
        self.record = record

    @property
    def id(self) -> str:
        return self.record["id"]

    @property
    def anchor_id(self) -> str:
        return self.record["anchor"]

    @property
    def kind(self) -> str:
        return self.record["kind"]

    @property
    def key(self) -> str:
        return self.record["key"]

    @property
    def generation(self) -> int:
        return int(self.record.get("generation", 1))

    @property
    def state(self) -> str:
        return self.record.get("state", "open")

    @property
    def symptoms(self) -> dict[str, Any]:
        return self.record.setdefault("symptoms", {})

    def active_symptoms(self) -> list[dict[str, Any]]:
        return [item for item in self.symptoms.values() if item.get("state") == "firing"]

    def active_symptom_names(self) -> list[str]:
        return [name for name, item in self.symptoms.items() if item.get("state") == "firing"]

    def highest_severity(self) -> str:
        order = {"critical": 3, "warning": 2, "info": 1, "none": 0, "unknown": 0}
        values = [item.get("severity", "unknown") for item in self.active_symptoms()]
        return max(values, key=lambda item: order.get(item, 0), default="unknown")

    def content_hash(self) -> str:
        """Hash the material meaning of the incident, ignoring refresh timestamps."""
        value = {
            "generation": self.generation,
            "anchor": self.anchor_id,
            # Consequences are part of the parent's meaning: a new one must make
            # the parent eligible for an update, not hide it.
            "consequences": sorted(self.record.get("consequences") or []),
            "symptoms": sorted(
                (
                    {
                        "name": name,
                        "state": item.get("state"),
                        "severity": item.get("severity"),
                        "hash": item.get("hash"),
                    }
                    for name, item in self.symptoms.items()
                ),
                key=lambda item: item["name"],
            ),
        }
        return hashlib.sha256(_json(value).encode()).hexdigest()

    def attempt_count(self) -> int:
        return len(self.record.get("attempts", []))


def new_incident(kind: str, key: str, now: datetime, *, generation: int = 1) -> Incident:
    stamp = now.isoformat()
    return Incident(
        {
            "id": incident_key(kind, key),
            "anchor": anchor_id(kind, key),
            "kind": kind,
            "key": key,
            "generation": generation,
            "state": "open",
            "opened_at": stamp,
            "last_firing_at": stamp,
            "updated_at": stamp,
            "closed_at": None,
            "symptoms": {},
            "attempts": [],
            "notified_hash": None,
            "delivery_pending": None,
            "pending_since": None,
            "close_reason": None,
            "reopened_from": None,
        }
    )


def _empty_state() -> dict[str, Any]:
    return {
        "version": STATE_VERSION,
        "source": None,
        "incidents": {},
        "closed": [],
        "attempts": {},
        "quota": {},
        "metrics": {},
        "classifier_cache": {},
    }


def load_incident_state(store_load: Any) -> dict[str, Any]:
    """Load incident state through a caller-supplied loader, tolerating old files."""
    value = store_load()
    if not isinstance(value, dict) or value.get("version") != STATE_VERSION:
        return _empty_state()
    for name, default in _empty_state().items():
        value.setdefault(name, default() if callable(default) else default)
    return value


def apply_alerts(
    state: dict[str, Any],
    alerts: Iterable[dict[str, Any]],
    now: datetime,
) -> dict[str, Any]:
    """Fold one Alertmanager read into incident state and report the transitions.

    Returns a report with the incidents that changed materially. The caller decides
    which transition spends an attempt; this function never spends one.
    """
    incidents: dict[str, dict[str, Any]] = state["incidents"]
    observed: dict[str, list[tuple[str, dict[str, Any]]]] = {}
    for alert in alerts:
        if not isinstance(alert, dict):
            continue
        if severity(alert) not in TRACKED_SEVERITIES:
            continue
        kind, key = anchor(alert)
        observed.setdefault(anchor_id(kind, key), []).append((kind, alert))

    transitions: list[dict[str, Any]] = []
    for anchor_value, group in sorted(observed.items()):
        kind = group[0][0]
        key = anchor_value.split(":", 1)[1] if ":" in anchor_value else anchor_value
        record = incidents.get(incident_key(kind, key))
        is_new = record is None
        if is_new:
            if not any(alert_state(alert, now) in {"firing", "pending"} for _, alert in group):
                # Alertmanager still lists resolved alerts for one resolve
                # timeout. A page of history must not open a new incident.
                continue
            closed = _take_closed(state, anchor_value)
            generation = 1
            reopened_from = None
            if closed is not None and now - (parse_time(closed.get("closed_at")) or now) <= (
                REOPEN_WINDOW
            ):
                generation = int(closed.get("generation", 1)) + 1
                reopened_from = closed.get("closed_at")
            record = new_incident(kind, key, now, generation=generation).record
            record["reopened_from"] = reopened_from
            incidents[record["id"]] = record

        incident = Incident(record)
        before = incident.content_hash()
        was_open = incident.state == "open"
        changed = False
        seen_names: set[str] = set()
        for _, alert in group:
            name = symptom_name(alert)
            seen_names.add(name)
            current = alert_state(alert, now)
            existing = incident.symptoms.get(name)
            if current == "firing":
                incident.record["last_firing_at"] = now.isoformat()
            if existing is None:
                if current not in {"firing", "pending"}:
                    continue
                if len(incident.symptoms) >= MAX_SYMPTOMS:
                    if not _make_room(incident, severity(alert)):
                        incident.record["symptom_overflow"] = (
                            int(incident.record.get("symptom_overflow", 0)) + 1
                        )
                        continue
                existing = {"first_seen": now.isoformat()}
                incident.symptoms[name] = existing
                changed = True
            existing.update(
                {
                    "state": "firing" if current == "firing" else existing.get("state", "pending"),
                    "last_seen": now.isoformat(),
                    "severity": severity(alert),
                    "hash": alert_hash(alert),
                    "targets": evidence_targets(alert),
                    "labels": prompt_labels(alert),
                }
            )
            if current in {"resolved", "suppressed"} and existing.get("state") == "firing":
                existing["state"] = "closed"
                existing["closed_at"] = now.isoformat()
                existing["close_reason"] = current
                changed = True
            elif current == "pending" and existing.get("state") == "firing":
                existing["state"] = "pending"
                changed = True
            elif current == "firing" and existing.get("state") != "firing":
                existing["state"] = "firing"
                existing.pop("closed_at", None)
                existing.pop("close_reason", None)
                changed = True

        # B5: reconcile symptoms that this poll did not report at all. Without
        # this a vanished symptom stays firing while a sibling keeps the anchor
        # visible, and the incident never resolves.
        for name, item in incident.symptoms.items():
            if name in seen_names:
                continue
            last_seen = parse_time(item.get("last_seen")) or now
            if item.get("state") in {"firing", "pending"} and now - last_seen > SYMPTOM_GRACE:
                item["state"] = "closed"
                item["closed_at"] = now.isoformat()
                item["close_reason"] = "not-observed"
                changed = True

        incident.record["updated_at"] = now.isoformat()
        if incident.state == "open":
            last_firing = parse_time(incident.record.get("last_firing_at")) or now
            if not incident.active_symptoms() and now - last_firing > RECOVERY_GRACE:
                _close(state, incident, now)
                transitions.append(
                    {
                        "transition": "recovered",
                        "incident": incident,
                        "reason": incident.record["close_reason"],
                    }
                )
                continue
        after = incident.content_hash()
        if changed or before != after:
            if was_open:
                if is_new:
                    opening = "reopened" if incident.generation > 1 else "opened"
                else:
                    opening = "updated"
                transitions.append({"transition": opening, "incident": incident})
            if incident.record.get("pending_since") is None:
                incident.record["pending_since"] = now.isoformat()

    for incident in _close_absent(state, observed, now):
        transitions.append(
            {
                "transition": "recovered",
                "incident": incident,
                "reason": incident.record["close_reason"],
            }
        )
    _prune(state, now)
    return {"transitions": transitions, "observed_anchors": sorted(observed)}


def _make_room(incident: Incident, incoming: str) -> bool:
    """Free one symptom slot, and never let a critical alert be dropped.

    The oldest non-firing symptom goes first. A firing non-critical symptom only
    goes when something critical needs the slot.
    """
    closed = [name for name, item in incident.symptoms.items() if item.get("state") != "firing"]
    if closed:
        incident.symptoms.pop(
            min(closed, key=lambda name: incident.symptoms[name].get("first_seen") or "")
        )
        return True
    if incoming != "critical":
        return False
    order = {"critical": 3, "warning": 2, "info": 1, "none": 0, "unknown": 0}
    evictable = [
        name for name, item in incident.symptoms.items() if order.get(item.get("severity"), 0) < 3
    ]
    if not evictable:
        return False
    incident.symptoms.pop(
        min(evictable, key=lambda name: incident.symptoms[name].get("first_seen") or "")
    )
    return True


def _close(state: dict[str, Any], incident: Incident, now: datetime) -> None:
    incident.record["state"] = "closed"
    incident.record["closed_at"] = now.isoformat()
    incident.record["close_reason"] = _close_reason(incident.symptoms)
    for item in incident.symptoms.values():
        if item.get("state") in {"firing", "pending"}:
            item["state"] = "closed"
            item["closed_at"] = now.isoformat()
            item["close_reason"] = "not-observed"
    _retire(state["incidents"], state, incident)


def _close_reason(symptoms: dict[str, Any]) -> str:
    """Report the strongest evidence for why an incident stopped firing.

    Only Alertmanager's own resolution counts as recovery. A silence or an
    inhibition is a separate outcome and must not be described as one.
    """
    reasons = {item.get("close_reason") for item in symptoms.values() if item.get("close_reason")}
    if reasons == {"resolved"}:
        return "resolved"
    if "suppressed" in reasons:
        return "suppressed"
    if reasons:
        return sorted(reasons)[0]
    return "not-observed"


def _take_closed(state: dict[str, Any], anchor_value: str) -> dict[str, Any] | None:
    for index, record in enumerate(state["closed"]):
        if record.get("anchor") == anchor_value:
            return state["closed"].pop(index)
    return None


def _retire(incidents: dict[str, Any], state: dict[str, Any], incident: Incident) -> None:
    incidents.pop(incident.id, None)
    closed = state["closed"]
    closed.append(incident.record)
    del closed[:-MAX_CLOSED_INCIDENTS]


def _close_absent(
    state: dict[str, Any], observed: dict[str, list[tuple[str, dict[str, Any]]]], now: datetime
) -> list[Incident]:
    """Close open incidents whose anchor Alertmanager no longer reports at all."""
    closed: list[Incident] = []
    for record in list(state["incidents"].values()):
        if record.get("anchor") in observed:
            continue
        incident = Incident(record)
        last_firing = parse_time(record.get("last_firing_at")) or now
        if now - last_firing <= RECOVERY_GRACE:
            continue
        _close(state, incident, now)
        closed.append(incident)
    return closed


def _prune(state: dict[str, Any], now: datetime) -> None:
    incidents = state["incidents"]
    for record in list(incidents.values()):
        last_firing = parse_time(record.get("last_firing_at")) or now
        if now - last_firing > STALE_AFTER:
            _close(state, Incident(record), now)
    active = list(incidents.values())
    if len(active) <= MAX_ACTIVE_INCIDENTS:
        return
    order = sorted(active, key=lambda item: item.get("opened_at") or "")
    for record in order[: len(active) - MAX_ACTIVE_INCIDENTS]:
        incidents.pop(record["id"], None)


def inventory(state: dict[str, Any]) -> dict[str, Any]:
    """Return the bounded incident inventory used for metrics and prompts."""
    open_incidents = sorted(
        (Incident(record) for record in state["incidents"].values()),
        key=lambda item: item.record.get("opened_at") or "",
    )
    return {
        "open": [summarize(incident) for incident in open_incidents],
        "recently_closed": [
            {
                "anchor": record.get("anchor"),
                "generation": record.get("generation"),
                "closed_at": record.get("closed_at"),
                "reason": record.get("close_reason"),
            }
            for record in state["closed"][-5:]
        ],
    }


def summarize(incident: Incident) -> dict[str, Any]:
    """Return the sanitized incident shape supplied to prompts and delivery."""
    return {
        "anchor": incident.anchor_id,
        "kind": incident.kind,
        "generation": incident.generation,
        "state": incident.state,
        "opened_at": incident.record.get("opened_at"),
        # Symptoms of other incidents that this incident owns. They are not
        # investigated separately while this incident stays open.
        "consequences": list(incident.record.get("consequences") or []),
        "symptom_overflow": int(incident.record.get("symptom_overflow", 0)),
        "symptoms": [
            {
                "name": name,
                "state": item.get("state"),
                "severity": item.get("severity"),
                "labels": item.get("labels", {}),
            }
            for name, item in sorted(incident.symptoms.items())
        ],
    }


def related_to_node(
    app: Incident,
    node: Incident,
    node_pods: dict[str, list[tuple[str, str]]],
    now: datetime,
    *,
    precede_window: timedelta = timedelta(minutes=5),
) -> bool:
    """Report whether an application incident is a bounded consequence of a node incident.

    The test is deliberately narrow. Every firing symptom that names a pod must
    sit on the failing node, and the application incident must start around the
    node incident. An older or partly unrelated failure stays independent.
    """
    pods = set(node_pods.get(node.key, []))
    if not pods:
        return False
    opened = parse_time(app.record.get("opened_at"))
    node_opened = parse_time(node.record.get("opened_at"))
    if opened is None or node_opened is None:
        return False
    if opened < node_opened - precede_window or opened > node_opened + CORRELATION_WINDOW:
        return False
    named: list[tuple[str, str]] = []
    for name in app.active_symptom_names():
        item = app.symptoms[name]
        labels = item.get("labels") or {}
        pod = labels.get("pod")
        if not pod:
            # A symptom that names no pod cannot be shown to belong to the node.
            # It keeps its own investigation instead of hiding inside the parent.
            return False
        namespace = labels.get("namespace") or labels.get("app_namespace") or ""
        named.append((namespace, pod))
    return bool(named) and all(item in pods for item in named)
