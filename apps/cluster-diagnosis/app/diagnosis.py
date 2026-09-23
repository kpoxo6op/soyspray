#!/usr/bin/env python3
"""Run the incident loop inside the cluster.

One poll every poll_seconds: read Alertmanager, fold related alerts into one
incident, collect bounded evidence from Loki, and deliver only new factual
observations to Telegram. State and delivery are persisted across restarts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import signal
import sys
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

import evidence as evidence_module
import incident as incident_module
import metrics as metrics_module
import store as store_module
import telegram as telegram_module
from incident import summarize

AUCKLAND = ZoneInfo("Pacific/Auckland")
ALERTMANAGER_TIMEOUT = 20.0
MAX_ALERT_BYTES = 512 * 1024
METRIC_QUERIES = {
    "pod_nodes": "max by (node, namespace, pod) (kube_pod_info)",
}
METRIC_QUERY_LIMITS = {"pod_nodes": 600}


def log(event: str, **fields: Any) -> None:
    record = {"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"), "event": event}
    record.update(fields)
    print(json.dumps(record, sort_keys=True), flush=True)


def read_secret(path: str | None) -> str:
    """Read a mounted secret without ever logging or echoing its value."""
    if not path:
        return ""
    try:
        return Path(path).read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def fetch_alerts(url: str, timeout: float = ALERTMANAGER_TIMEOUT) -> list[dict[str, Any]]:
    request = Request(url.rstrip("/") + "/api/v2/alerts", headers={"Accept": "application/json"})
    with urlopen(request, timeout=timeout) as response:
        body = response.read(MAX_ALERT_BYTES + 1)
    if len(body) > MAX_ALERT_BYTES:
        raise ValueError("Alertmanager response was too large")
    value = json.loads(body)
    if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
        raise ValueError("Alertmanager response was not an alert list")
    return value


def prometheus_query(base: str, query: str, timeout: float = 10.0) -> dict[str, Any] | None:
    url = base.rstrip("/") + "/api/v1/query?" + urlencode({"query": query})
    try:
        with urlopen(url, timeout=timeout) as response:
            value = json.load(response)
    except (HTTPError, URLError, TimeoutError, OSError, ValueError):
        return None
    data = value.get("data") if isinstance(value, dict) else None
    result = data.get("result") if isinstance(data, dict) else None
    return result if isinstance(result, list) else None


def metric_evidence(base: str) -> dict[str, Any]:
    """Read the pod-to-node map used only for deterministic correlation."""
    series: dict[str, Any] = {}
    observed = False
    for name, query in METRIC_QUERIES.items():
        rows = prometheus_query(base, query)
        if rows is None:
            series[name] = {"status": "unavailable"}
            continue
        observed = True
        limit = METRIC_QUERY_LIMITS[name]
        selected = []
        for row in rows[:limit]:
            if not isinstance(row, dict):
                continue
            sample = row.get("value")
            if not isinstance(sample, list) or len(sample) != 2:
                continue
            try:
                timestamp, value = float(sample[0]), float(sample[1])
            except (TypeError, ValueError):
                continue
            if abs(datetime.now(timezone.utc).timestamp() - timestamp) > 300:
                continue
            labels = {
                key: item
                for key, item in (row.get("metric") or {}).items()
                if key
                in {
                    "node",
                    "pvc",
                    "pvc_namespace",
                    "app_namespace",
                    "namespace",
                    "job",
                    "pod",
                    "container",
                    "volume",
                }
                and isinstance(item, str)
                and incident_module.safe_label(item)
            }
            selected.append({"labels": labels, "value": value})
        series[name] = selected
    return {"status": "observed" if observed else "unavailable", "series": series}


# One line per related symptom beyond the first, and no more.
MAX_RELATED_LINES = 3
ICONS = {
    "opened": "\N{FIRE}",
    "reopened": "\N{FIRE}",
    "updated": "\N{CLOCKWISE RIGHTWARDS AND LEFTWARDS OPEN CIRCLE ARROWS}",
    "recovered": "\N{WHITE HEAVY CHECK MARK}",
}
TITLES = {
    "opened": "FIRING",
    "reopened": "FIRING AGAIN",
    "updated": "UPDATE",
    "recovered": "RESOLVED",
}


def symptom_identity(item: dict[str, Any]) -> tuple[str, str]:
    """Return the alert name and the object it names, short enough to read."""
    labels = item.get("labels") or {}
    name = str(item.get("name", ""))
    alert = str(labels.get("alertname") or name.split("(", 1)[0] or "Alert")
    namespace = str(labels.get("namespace") or "")
    target = next(
        (
            str(labels[key])
            for key in (
                "pod",
                "node",
                "deployment",
                "statefulset",
                "daemonset",
                "job",
                "pvc",
                "persistentvolumeclaim",
                "service",
            )
            if labels.get(key)
        ),
        "",
    )
    container = str(labels.get("container") or "")
    where = "/".join(part for part in (namespace, target) if part)
    if container and container != target:
        where = f"{where} ({container})" if where else container
    return alert, where


def age_label(seconds: Any) -> str:
    if isinstance(seconds, bool) or not isinstance(seconds, (int, float)):
        return ""
    minutes = int(seconds) // 60
    if minutes < 1:
        return "under a minute"
    if minutes < 60:
        return f"{minutes}m"
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h{minutes:02d}m" if minutes else f"{hours}h"


def synthetic_check(summary: dict[str, Any]) -> bool:
    """Respect explicit test provenance in the alert already sent to Telegram."""
    for item in summary.get("symptoms") or []:
        name = str(item.get("name") or "").lower()
        annotations = item.get("annotations") or {}
        description = str(annotations.get("description") or "").lower()
        if (
            "acceptanceprobe" in name
            or "loopverification" in name
            or "synthetic trigger" in description
            or "no meaning about the cluster" in description
        ):
            return True
    return False


def new_signal_counts(summary: dict[str, Any], pack: dict[str, Any]) -> dict[tuple[str, str], int]:
    """Keep a sampled failure tied to the alert target that produced it."""
    firing = [item for item in summary.get("symptoms") or [] if item.get("state") == "firing"]
    by_name = {str(item.get("name") or ""): item for item in firing}
    implicit = {
        "crash-loop": ("crashloop", "podcrash"),
        "mount-failure": ("mountfail", "volumemount"),
        "backup-failure": ("backupfail",),
        "disk-full": ("diskfull", "filesystemfull"),
        "unhealthy": ("unhealthy", "readiness", "liveness"),
    }
    counts: dict[tuple[str, str], int] = {}
    for target in pack.get("targets") or []:
        item = by_name.get(str(target.get("id") or ""))
        if item is None and len(firing) == 1 and len(pack.get("targets") or []) == 1:
            item = firing[0]
        if item is None:
            continue
        alert, where = symptom_identity(item)
        source = where or alert
        for name, count in (target.get("signals") or {}).items():
            if not isinstance(count, int) or count <= 0:
                continue
            if any(term in alert.lower() for term in implicit.get(name, ())):
                continue
            key = (source, str(name))
            counts[key] = counts.get(key, 0) + count
    return counts


def finding_shape(summary: dict[str, Any], pack: dict[str, Any]) -> str:
    """Describe what kind of observation this is, without its drifting numbers.

    The counts come from a sliding window, so the same situation reports 40 lines
    and then 44. What matters for a second message is a different kind of
    observation, not a different count of the same one.
    """
    signals = new_signal_counts(summary, pack)
    if signals:
        return "signals:" + ",".join(f"{source}:{name}" for source, name in sorted(signals))
    related = correlated_symptoms(summary)
    if related:
        return f"related:{related[0]}"
    return ""


def finding_line(summary: dict[str, Any], pack: dict[str, Any]) -> str:
    """Return what this loop knows that the alert itself does not say.

    An empty string means the message would only repeat the alert, and the loop
    stays silent: Alertmanager has already told the operator the alert exists.
    """
    window = age_label(pack.get("window_seconds")) or "the window"
    signals = new_signal_counts(summary, pack)
    if signals:
        top = sorted(signals.items(), key=lambda item: (-item[1], item[0]))[:2]
        detail = ", ".join(
            f"{source}: {name} ({count} sampled log lines)" for (source, name), count in top
        )
        return f"Loki, last {window}: {detail}."
    related = correlated_symptoms(summary)
    if related:
        first, rest = related
        return (
            f"{len(rest)} alerts name {first}: {', '.join(rest[:2])}"
            + (f" and {len(rest) - 2} more" if len(rest) > 2 else "")
            + "."
        )
    return ""


def _finding_signature(candidate: incident_module.Incident, shape: str) -> str:
    """Identify one kind of finding so the same news is never delivered twice."""
    payload = {
        "anchor": candidate.anchor_id,
        "generation": candidate.generation,
        "shape": shape,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:32]


def correlated_symptoms(summary: dict[str, Any]) -> tuple[str, list[str]] | None:
    """Return the shared object and the alerts that name it, when there are two."""
    firing = [item for item in summary.get("symptoms", []) if item.get("state") == "firing"]
    if len(firing) < 2:
        return None
    seen: dict[str, list[str]] = {}
    for item in firing:
        labels = item.get("labels") or {}
        target = next(
            (
                f"{key}={labels[key]}"
                for key in ("pod", "deployment", "statefulset", "daemonset", "pvc", "node")
                if labels.get(key)
            ),
            "",
        )
        if not target:
            continue
        alert, _ = symptom_identity(item)
        seen.setdefault(target, []).append(alert)
    for target, alerts in sorted(seen.items()):
        if len(alerts) >= 2:
            return target.split("=", 1)[1], alerts
    return None


def incident_header(transition: str, summary: dict[str, Any], reason: str = "") -> str:
    title = TITLES.get(transition, transition)
    if transition == "recovered" and reason not in {"resolved", ""}:
        # Only Alertmanager's own resolution is a recovery. A silence, an
        # inhibition or a vanished alert is a close, and it says why.
        title = "CLOSED"
    firing = [item for item in summary["symptoms"] if item.get("state") == "firing"]
    shown = firing or list(summary["symptoms"])
    if not shown:
        return f"{ICONS.get(transition, '-')} {TITLES.get(transition, transition)}"
    alert, where = symptom_identity(shown[0])
    severity = (
        "critical"
        if any(item.get("severity") == "critical" for item in summary["symptoms"])
        else "warning"
    )
    age = age_label(shown[0].get("firing_seconds")) if firing else ""
    icon = "\N{WHITE CIRCLE}" if title == "CLOSED" else ICONS.get(transition, "-")
    head = f"{icon} {title} [{severity}] {alert}"
    if where:
        head += f" {where}"
    if len(shown) > 1:
        head += f" +{len(shown) - 1}"
    if age:
        head += f" \N{MIDDLE DOT} firing {age}"
    lines = [head]
    for item in shown[1 : MAX_RELATED_LINES + 1]:
        other, other_where = symptom_identity(item)
        lines.append(f"  {other} {other_where}".rstrip())
    if len(shown) > MAX_RELATED_LINES + 1:
        lines.append(f"  +{len(shown) - MAX_RELATED_LINES - 1} more")
    if reason == "resolved":
        lines.append("  Alertmanager reports this alert resolved.")
    elif reason == "not-observed":
        lines.append("  Alertmanager no longer reports it; recovery is unverified.")
    elif reason == "suppressed":
        lines.append("  Alertmanager suppressed it; recovery is unverified.")
    elif reason:
        lines.append(f"  Alertmanager closed it ({reason}); recovery is unverified.")
    return "\n".join(lines)


def render_update(
    transition: str,
    summary: dict[str, Any],
    *,
    reason: str = "",
    changes: str = "",
    finding: str = "",
) -> str:
    """Render only observed identity, a new finding and a material change."""
    lines = [incident_header(transition, summary, reason)]
    if finding:
        lines.append(finding)
    if changes and transition == "updated":
        lines.append(changes)
    return telegram_module.bounded_message(lines)


def changed_symptoms(before: dict[str, Any], summary: dict[str, Any]) -> str:
    previous = {name: state for name, state in (before or {}).items()}
    current = {item["name"]: item.get("state") for item in summary.get("symptoms", [])}
    added = [name for name in current if name not in previous]
    resolved = [
        name
        for name, state in current.items()
        if previous.get(name) == "firing" and state != "firing"
    ]
    parts = []
    if added:
        parts.append("new: " + ", ".join(sorted(added)[:4]))
    if resolved:
        parts.append("cleared: " + ", ".join(sorted(resolved)[:4]))
    return "; ".join(parts)


SEVERITY_RANK = {"critical": 3, "warning": 2, "info": 1, "none": 0, "unknown": 0}
ENRICHMENT_COOLDOWN_SECONDS = 600


def owns_critical_work(state: dict[str, Any], record: dict[str, Any]) -> bool:
    """A critical incident, or a node incident owning a critical consequence."""
    if incident_module.Incident(record).highest_severity() == "critical":
        return True
    anchors = set(record.get("consequences") or [])
    for other in state["incidents"].values():
        if other.get("anchor") in anchors and (
            incident_module.Incident(other).highest_severity() == "critical"
        ):
            return True
    return False


def eligible(record: dict[str, Any]) -> bool:
    current = incident_module.Incident(record)
    return (
        current.state == "open"
        and bool(current.active_symptoms())
        and not record.get("consequence_of")
    )


def select_candidate(
    state: dict[str, Any], now: datetime
) -> tuple[incident_module.Incident | None, list[str]]:
    candidates: list[incident_module.Incident] = []
    notes: list[str] = []
    for record in state["incidents"].values():
        if not eligible(record):
            continue
        if not owns_critical_work(state, record):
            continue
        current = incident_module.Incident(record)
        candidates.append(current)
    if not candidates:
        return None, notes
    candidates.sort(
        key=lambda item: (
            item.record.get("last_examined_at") or "",
            item.record.get("pending_since") or item.record.get("opened_at") or "",
            -SEVERITY_RANK.get(item.highest_severity(), 0),
            -len(item.record.get("consequences") or []),
            item.anchor_id,
        )
    )
    return candidates[0], notes


def mark_consequences(
    state: dict[str, Any], node_pods: dict[str, list[tuple[str, str]]], now: datetime
) -> list[str]:
    nodes = {
        record["anchor"]: record
        for record in state["incidents"].values()
        if record.get("kind") == "node"
    }
    notes: list[str] = []
    attached: dict[str, list[str]] = {anchor: [] for anchor in nodes}
    for record in state["incidents"].values():
        if record.get("kind") != "app":
            continue
        current = incident_module.Incident(record)
        previous_attachment = record.get("consequence_of")
        record["consequence_of"] = None
        if current.state != "open" or not current.active_symptoms() or not node_pods:
            continue
        for anchor, node_record in sorted(nodes.items()):
            if incident_module.related_to_node(
                current, incident_module.Incident(node_record), node_pods, now
            ):
                record["consequence_of"] = anchor
                attached.setdefault(anchor, []).append(current.anchor_id)
                if previous_attachment != anchor:
                    notes.append(f"consequence:{current.anchor_id}")
                break
    for anchor, node_record in nodes.items():
        previous = node_record.get("consequences") or []
        consequences = sorted(set(attached.get(anchor, [])))
        if previous and consequences != previous:
            notes.append(f"consequences-changed:{anchor}")
        node_record["consequences"] = consequences
    return notes


class Handler(BaseHTTPRequestHandler):
    server_version = "soyspray-cluster-diagnosis"

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/metrics":
            body = self.server.supplier().encode("utf-8")  # type: ignore[attr-defined]
            self._respond(200, body, "text/plain; version=0.0.4")
            return
        if self.path == "/healthz":
            usable, _detail = self.server.usability()  # type: ignore[attr-defined]
            self._respond(200 if usable else 503, b"ok\n" if usable else b"state-unusable\n")
            return
        self._respond(404, b"not found\n")

    def _respond(self, status: int, body: bytes, content_type: str = "text/plain") -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args: Any) -> None:
        return


class Diagnosis:
    """The poll loop, with every external call injectable for tests."""

    def __init__(
        self,
        *,
        state_path: Path,
        lock_path: Path,
        alertmanager_url: str,
        loki_url: str,
        prometheus_url: str,
        telegram: telegram_module.Telegram,
        poll_seconds: int = 120,
        fetch: Callable[[str], list[dict[str, Any]]] = fetch_alerts,
        collect: Callable[..., dict[str, Any]] = evidence_module.collect_evidence,
        metrics_source: Callable[[str], dict[str, Any]] = metric_evidence,
        now: Callable[[], datetime] | None = None,
        port: int | None = None,
    ):
        self.store = store_module.StateStore(Path(state_path), Path(lock_path))
        self.alertmanager_url = alertmanager_url
        self.loki_url = loki_url
        self.prometheus_url = prometheus_url
        self.telegram = telegram
        self.poll_seconds = poll_seconds
        self.fetch = fetch
        self.collect = collect
        self.metrics_source = metrics_source
        self.now = now or (lambda: datetime.now(AUCKLAND))
        self.port = port if port is not None else int(os.environ.get("METRICS_PORT", "9911"))
        self.stop = threading.Event()
        self.state: dict[str, Any] = store_module.empty_state()
        self.state_usable = False
        self.source_ok = False
        self.last_metrics = ""
        self._lock = threading.Lock()

    # -- state ---------------------------------------------------------------

    def reload_state(self) -> str:
        try:
            self.state = self.store.load()
        except store_module.StateUnusable as error:
            self.state_usable = False
            return str(error)
        self.state_usable = True
        # The state records whether the last Alertmanager read succeeded. A
        # reader such as --print-metrics has not polled, so it reports the
        # recorded answer instead of a fresh process's empty one.
        source = self.state.get("source")
        if isinstance(source, dict) and "ok" in source:
            self.source_ok = bool(source["ok"])
        return ""

    def save(self) -> None:
        if not self.state_usable:
            # The state could not be read. Writing over it would lose incident
            # and delivery history and might repeat updates.
            return
        self.store.save(self.state)

    # -- delivery ------------------------------------------------------------

    def deliver_outbox(self) -> None:
        now = time.time()
        pending = list(self.state.get("outbox") or [])
        keep: list[dict[str, Any]] = []
        for entry in pending:
            if entry.get("format") != "factual-v1":
                # Native alerts already sent; queued provider prose must not
                # emerge from the retained volume after this runtime starts.
                self._count("deliveries", "legacy-dropped")
                continue
            if telegram_module.expired(entry, now):
                self._count("deliveries", "expired")
                continue
            if not self.telegram.healthy():
                keep.append(entry)
                continue
            result = self.telegram.send(str(entry.get("message", "")))
            if result["status"] == "sent":
                self._count("deliveries", "sent")
                self.state.setdefault("metrics", {})["last_success_timestamp_seconds"] = int(
                    self.now().timestamp()
                )
                self._record_delivery(entry)
            else:
                self._count("deliveries", "failed")
                keep.append(entry)
        self.state["outbox"] = keep

    def _record_delivery(self, entry: dict[str, Any]) -> None:
        """Mark that this incident's own message reached the chat.

        An incident is only worth a closing message when the chat heard about it
        in the first place, so delivery, not queueing, is the evidence.
        """
        record = self._record_for(str(entry.get("incident_id") or ""))
        if record is None:
            return
        record["delivered_generation"] = int(
            entry.get("generation") or record.get("generation") or 1
        )
        record["delivered_format"] = "factual-v1"
        record["delivered_at"] = self.now().isoformat()
        # Only a message that actually arrived counts as news the operator has
        # seen, so the same finding is never sent twice.
        if entry.get("signature"):
            record["delivered_signature"] = str(entry["signature"])
        record["delivered_text"] = str(entry.get("message") or "")[:280]

    def _record_for(self, incident_id: str) -> dict[str, Any] | None:
        """Find an incident record, open or closed, by its identifier."""
        if not incident_id:
            return None
        record = (self.state.get("incidents") or {}).get(incident_id)
        if isinstance(record, dict):
            return record
        for candidate in self.state.get("closed") or []:
            if isinstance(candidate, dict) and str(candidate.get("id") or "") == incident_id:
                return candidate
        return None

    def enqueue(
        self,
        message: str,
        *,
        incident_id: str = "",
        generation: int = 0,
        signature: str = "",
    ) -> None:
        self.state["outbox"] = telegram_module.enqueue(
            self.state.setdefault("outbox", []),
            {
                "message": message,
                "queued_at": time.time(),
                "incident_id": incident_id,
                "generation": int(generation),
                "signature": signature,
                "format": "factual-v1",
            },
        )

    def _close_notice(
        self, incident: incident_module.Incident, incident_id: str, generation: int, reason: str
    ) -> None:
        incident.record["recovery_notified"] = True
        incident.record["close_pending"] = None
        self.enqueue(
            render_update("recovered", summarize(incident), reason=reason),
            incident_id=incident_id,
            generation=generation,
        )

    def flush_close_notices(self) -> list[str]:
        """Send the holds whose opening message has now been delivered.

        A close held because its opening update was queued is sent as
        soon as that update arrives. When the opening message is gone for
        good, the hold is dropped instead of arriving out of nowhere.
        """
        outcomes: list[str] = []
        for record in list(self.state.get("closed") or []):
            if not isinstance(record, dict) or not record.get("close_pending"):
                continue
            incident_id = str(record.get("id") or "")
            generation = int(record.get("generation") or 1)
            delivered = (
                int(record.get("delivered_generation") or 0) == generation
                and record.get("delivered_format") == "factual-v1"
            )
            if not delivered and self._pending_for(incident_id, generation):
                continue
            if not delivered:
                record["close_pending"] = None
                record["recovery_notified"] = True
                outcomes.append("close-suppressed")
                continue
            self._close_notice(
                incident_module.Incident(record),
                incident_id,
                generation,
                str(record.get("close_pending")),
            )
            self._count("outcomes", "recovered")
            outcomes.append("recovered")
        return outcomes

    def _pending_for(self, incident_id: str, generation: int) -> bool:
        return any(
            str(entry.get("incident_id") or "") == incident_id
            and int(entry.get("generation") or 0) == int(generation)
            for entry in (self.state.get("outbox") or [])
        )

    def _count(self, bucket: str, key: str) -> None:
        counters = self.state.setdefault("metrics", {}).setdefault(bucket, {})
        counters[key] = int(counters.get(key, 0)) + 1

    # -- one iteration -------------------------------------------------------

    def iterate(self) -> str:
        timestamp = self.now()
        if not self.state_usable:
            # Refuse to work on unreadable state: overwriting it would lose
            # delivery history and could repeat messages.
            return "state-unusable"
        self.deliver_outbox()

        def finish(outcome: str) -> str:
            """Deliver anything queued this iteration, then persist and report."""
            self.state.setdefault("metrics", {})["last_poll_timestamp_seconds"] = int(
                timestamp.timestamp()
            )
            self.deliver_outbox()
            self.save()
            return outcome

        try:
            alerts = self.fetch(self.alertmanager_url)
        except (HTTPError, URLError, TimeoutError, OSError, ValueError) as error:
            self.source_ok = False
            self.state["source"] = {"ok": False, "error": type(error).__name__}
            return finish("source-failed")
        self.source_ok = True
        self.state["source"] = {"ok": True}

        report = incident_module.apply_alerts(self.state, alerts, timestamp)
        node_pods: dict[str, list[tuple[str, str]]] = {}
        if any(
            record.get("kind") == "node" and record.get("state") == "open"
            for record in self.state["incidents"].values()
        ):
            series = self.metrics_source(self.prometheus_url).get("series", {})
            for row in series.get("pod_nodes", []) if isinstance(series, dict) else []:
                labels = row.get("labels", {}) if isinstance(row, dict) else {}
                node, namespace, pod = (
                    labels.get("node"),
                    labels.get("namespace"),
                    labels.get("pod"),
                )
                if node and namespace and pod:
                    node_pods.setdefault(node, []).append((namespace, pod))
        mark_consequences(self.state, node_pods, timestamp)

        outcomes: list[str] = []
        for transition in report["transitions"]:
            if transition["transition"] != "recovered":
                continue
            current = transition["incident"]
            if current.record.get("recovery_notified"):
                continue
            incident_id = str(current.record.get("id") or "")
            generation = int(current.record.get("generation") or 1)
            if (
                int(current.record.get("delivered_generation") or 0) != generation
                or current.record.get("delivered_format") != "factual-v1"
            ):
                # Nothing about this incident has reached the chat yet. Hold the
                # close: it must follow the opening message, never overtake it,
                # and it is not news when no opening message ever arrived.
                current.record["close_pending"] = str(transition.get("reason", ""))
                continue
            self._close_notice(current, incident_id, generation, str(transition.get("reason", "")))
            self._count("outcomes", "recovered")
            outcomes.append("recovered")

        outcomes.extend(self.flush_close_notices())

        candidate, notes = select_candidate(self.state, timestamp)
        outcomes.extend(notes)
        if candidate is None:
            return finish(",".join(outcomes) if outcomes else "unchanged")

        summary = summarize(candidate, timestamp)
        if synthetic_check(summary):
            candidate.record["last_examined_at"] = timestamp.isoformat()
            self._count("outcomes", "no-finding")
            self._count("suppressed", "synthetic-check")
            return finish("no-finding")
        pack = self.collect(
            summary,
            loki_url=self.loki_url,
            now=timestamp,
            node_pods=node_pods,
        )
        self.state["collector"] = {
            "status": pack.get("status", "unknown"),
            "gaps": _gap_counts(pack),
            "lines": pack.get("totals", {}).get("lines", 0),
            "exported": pack.get("totals", {}).get("exported", 0),
        }
        candidate.record["last_examined_at"] = timestamp.isoformat()

        # The loop speaks only when it knows something the alert does not say.
        # Alertmanager has already delivered the alert itself, so a message that
        # repeats it is an interruption. Test alerts already explain their own
        # provenance and have no service-outage meaning.
        finding = finding_line(summary, pack)
        if not finding:
            self._count("outcomes", "no-finding")
            self._count("suppressed", "no-finding")
            outcomes.append("no-finding")
            return finish(",".join(outcomes))

        signature = _finding_signature(candidate, finding_shape(summary, pack))
        if self._pending_for(candidate.id, candidate.generation):
            self._count("outcomes", "delivery-pending")
            return finish("delivery-pending")
        if candidate.record.get(
            "delivered_format"
        ) == "factual-v1" and signature == candidate.record.get("delivered_signature"):
            self._count("outcomes", "no-news")
            self._count("suppressed", "no-news")
            outcomes.append("no-news")
            return finish(",".join(outcomes))
        last_message = (
            incident_module.parse_time(candidate.record.get("delivered_at"))
            if candidate.record.get("delivered_format") == "factual-v1"
            else None
        )
        if (
            last_message
            and (timestamp - last_message).total_seconds() < ENRICHMENT_COOLDOWN_SECONDS
        ):
            # One incident, one message, then quiet for a while: a second message
            # a minute later reads as noise whatever it says. The finding is not
            # marked as delivered, so it can go out after the cooldown.
            self._count("outcomes", "cooldown")
            self._count("suppressed", "cooldown")
            outcomes.append("cooldown")
            return finish(",".join(outcomes))

        previous = (
            candidate.record.get("notified_symptoms") or {}
            if candidate.record.get("delivered_format") == "factual-v1"
            else {}
        )
        changes = changed_symptoms(previous, summary)
        transition = "updated" if previous else "reopened" if candidate.generation > 1 else "opened"
        message = render_update(transition, summary, changes=changes, finding=finding)
        self.enqueue(
            message,
            incident_id=str(candidate.record.get("id") or ""),
            generation=candidate.generation,
            signature=signature,
        )
        candidate.record["notified_symptoms"] = {
            name: item.get("state") for name, item in candidate.symptoms.items()
        }
        candidate.record["pending_since"] = None
        self._count("outcomes", "factual")
        outcomes.append("factual")
        return finish(",".join(outcomes))

    # -- metrics -------------------------------------------------------------

    def render_metrics(self) -> str:
        now = self.now()
        return metrics_module.render(
            self.state,
            now=now,
            source_ok=self.source_ok,
            state_usable=self.state_usable,
            poll_seconds=self.poll_seconds,
        )

    def usability(self) -> tuple[bool, str]:
        return self.state_usable, "" if self.state_usable else "state-unusable"

    # -- process -------------------------------------------------------------

    def run_forever(self) -> int:
        if not self.store.acquire():
            log("lock-held")
            return 1
        try:
            detail = self.reload_state()
            if detail:
                log("state-unusable", detail=detail)
            if not self.state_usable:
                self.state = store_module.empty_state()
            server = ThreadingHTTPServer(("0.0.0.0", self.port), Handler)  # noqa: S104 - pod network
            server.supplier = self.render_metrics  # type: ignore[attr-defined]
            server.usability = self.usability  # type: ignore[attr-defined]
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            log("started", poll_seconds=self.poll_seconds)
            while not self.stop.is_set():
                try:
                    detail = self.reload_state() if not self.state_usable else ""
                    if detail:
                        log("state-unusable", detail=detail)
                    outcome = self.iterate()
                    self.last_metrics = self.render_metrics()
                    log("iteration", outcome=outcome, state_usable=self.state_usable)
                except Exception as error:  # noqa: BLE001 - the loop must survive one bad poll
                    log("iteration-failed", error=type(error).__name__)
                self.stop.wait(self.poll_seconds)
            server.shutdown()
            server.server_close()
            return 0
        finally:
            self.store.release()


def _gap_counts(pack: dict[str, Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for gap in pack.get("gaps", []):
        reason = str(gap.get("reason", "unknown"))
        counts[reason] = counts.get(reason, 0) + 1
    return counts


def build_from_environment() -> Diagnosis:
    state_root = Path(os.environ.get("CLUSTER_DIAGNOSIS_STATE_ROOT", "/state"))
    return Diagnosis(
        state_path=state_root / "state.json",
        lock_path=state_root / "state.lock",
        alertmanager_url=os.environ.get(
            "ALERTMANAGER_URL", evidence_module.DEFAULT_ALERTMANAGER_URL
        ),
        loki_url=os.environ.get("LOKI_URL", evidence_module.DEFAULT_LOKI_URL),
        prometheus_url=os.environ.get("PROMETHEUS_URL", evidence_module.DEFAULT_PROMETHEUS_URL),
        telegram=telegram_module.Telegram(
            read_secret(os.environ.get("TELEGRAM_BOT_TOKEN_FILE")),
            os.environ.get("TELEGRAM_CHAT_ID", ""),
        ),
        poll_seconds=int(os.environ.get("POLL_SECONDS", "120")),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true", help="Run one iteration and exit.")
    parser.add_argument(
        "--reset-state",
        action="store_true",
        help="Replace incident and delivery state. Stop the workload first.",
    )
    parser.add_argument(
        "--print-metrics", action="store_true", help="Print the current metrics and exit."
    )
    args = parser.parse_args(argv)
    diagnosis = build_from_environment()
    if args.reset_state:
        if not diagnosis.store.acquire():
            print("another instance holds the state lock", file=sys.stderr)
            return 1
        try:
            diagnosis.store.reset()
            print("state reset")
        finally:
            diagnosis.store.release()
        return 0
    if args.print_metrics:
        detail = diagnosis.reload_state()
        if detail:
            diagnosis.state = store_module.empty_state()
        print(diagnosis.render_metrics(), end="")
        return 0
    if args.once:
        if not diagnosis.store.acquire():
            print("busy")
            return 1
        try:
            detail = diagnosis.reload_state()
            if detail:
                print(detail, file=sys.stderr)
                return 1
            print(diagnosis.iterate())
        finally:
            diagnosis.store.release()
        return 0

    def terminate(_signum: int, _frame: Any) -> None:
        diagnosis.stop.set()

    signal.signal(signal.SIGTERM, terminate)
    signal.signal(signal.SIGINT, terminate)
    return diagnosis.run_forever()


if __name__ == "__main__":
    raise SystemExit(main())
