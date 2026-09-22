#!/usr/bin/env python3
"""Collect bounded, read-only incident evidence inside the cluster.

Raw log lines stay in Loki and in this process. Only allowlisted, normalized
records leave this module, and only the sanitized pack is written to disk. A line
whose format cannot be checked is not exported: it becomes an explicit evidence
gap instead.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen

MAX_TARGETS = 6
MAX_LINES_PER_TARGET = 40
# Aggregate bounds, not per-target bounds. A per-target allowance multiplies.
MAX_TOTAL_LINES = 120
MAX_SAMPLES_PER_TARGET = 8
MAX_MESSAGE_CHARS = 200
MAX_SOURCE_CHARS = 64
MAX_RAW_LINE_CHARS = 4096
MAX_RAW_BYTES = 512 * 1024
# Reject an oversized remote response before parsing it.
MAX_RAW_RESPONSE_BYTES = 1024 * 1024
MAX_PACK_BYTES = 24 * 1024
MAX_STORED_PACKS = 20
DEFAULT_WINDOW_SECONDS = 900
MAX_WINDOW_SECONDS = 3600
DEFAULT_TIMEOUT_SECONDS = 20
DEFAULT_LOKI_URL = "http://loki.monitoring.svc.cluster.local:3100"
DEFAULT_ALERTMANAGER_URL = "http://alertmanager-operated.monitoring.svc.cluster.local:9093"
DEFAULT_PROMETHEUS_URL = "http://kube-prometheus-stack-prometheus.monitoring.svc.cluster.local:9090"

SAFE_SELECTOR_VALUE = re.compile(r"[a-zA-Z0-9_.:/-]{1,253}")
CRI_PREFIX = re.compile(r"^\d{4}-\d{2}-\d{2}T[\d:.]+Z (?:stdout|stderr) [FP] ")
RFC3339_PREFIX = re.compile(
    r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:[.,]\d+)?(?:Z|[+-]\d{2}:?\d{2})?\s*"
)
LOGFMT_LINE = re.compile(r'^\s*(?:[A-Za-z_][A-Za-z0-9_.-]*=(?:"[^"]*"|[^\s"]*)\s*)+$')

LEVEL_VALUES = {
    "trace": "trace",
    "debug": "debug",
    "info": "info",
    "information": "info",
    "notice": "notice",
    "warn": "warning",
    "warning": "warning",
    "err": "error",
    "error": "error",
    "eror": "error",
    "fatal": "fatal",
    "panic": "fatal",
    "critical": "fatal",
    "crit": "fatal",
    "emerg": "fatal",
    "alert": "fatal",
}
LEVEL_KEYS = ("level", "lvl", "severity", "loglevel", "log_level", "log.level")
MESSAGE_KEYS = ("msg", "message", "error", "err", "reason", "detail", "cause", "event")
SOURCE_KEYS = ("logger", "component", "caller", "module", "subsystem", "service", "source")

# Bounded signal vocabulary. It mirrors the Alloy log and event signals so the
# same names appear in Prometheus, in Loki, and in an incident narrative.
SIGNALS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "mount-failure",
        re.compile(
            r"failedmount|failedattachvolume|volumeattachmentfailed"
            r"|unable to attach or mount volumes|mountvolume\.setup failed",
            re.I,
        ),
    ),
    ("disk-full", re.compile(r"no space left on device|enospc|disk full", re.I)),
    (
        "dns-failure",
        re.compile(
            r"no such host|server misbehaving|temporary failure in name resolution"
            r"|lookup [^\s]+ on [\d.]+:53",
            re.I,
        ),
    ),
    ("connection-refused", re.compile(r"connection refused|connection reset by peer", re.I)),
    (
        "network-timeout",
        re.compile(
            r"i/o timeout|context deadline exceeded|\btimed? ?out\b|deadline exceeded", re.I
        ),
    ),
    (
        "auth-denied",
        re.compile(
            r"accessdenied|access denied|403 forbidden|unauthorized|invalid credentials"
            r"|authentication failed|expiredtoken|invalidaccesskeyid|signaturedoesnotmatch",
            re.I,
        ),
    ),
    (
        "permission-failure",
        re.compile(r"permission denied|operation not permitted|read-only file system", re.I),
    ),
    (
        "resource-exhaustion",
        re.compile(
            r"out of memory|oomkill|cannot allocate memory|too many open files"
            r"|resource temporarily unavailable",
            re.I,
        ),
    ),
    (
        "crash-loop",
        re.compile(
            r"back-off restarting failed container|crashloopbackoff|panic:"
            r"|fatal error:|segmentation fault|core dumped",
            re.I,
        ),
    ),
    (
        "backup-failure",
        re.compile(
            r"(?:backup|snapshot|archive|restic|barman|pg_basebackup|wal|sync)[^\n]{0,40}"
            r"(?:fail|error|refus|denied|abort)"
            r"|archive_command[^\n]{0,20}(?:failed|returned)"
            r"|backofflimitexceeded|failed to (?:backup|upload|sync|push)",
            re.I,
        ),
    ),
    ("checksum-mismatch", re.compile(r"checksum|integrity|corrupt|truncated", re.I)),
    (
        "saturation",
        re.compile(
            r"quota exceeded|rate limit|429 too many requests|throttl|slowdown"
            r"|requesttimetooskewed|time skew",
            re.I,
        ),
    ),
    (
        "certificate-failure",
        re.compile(r"certificate (?:has expired|is not valid|expired)|x509:|tls handshake", re.I),
    ),
    ("evicted", re.compile(r"\bevicted\b|preempt|node affinity|outofcpu|outofmemory", re.I)),
    (
        "unhealthy",
        re.compile(r"unhealthy|probe failed|liveness|readiness|not ready", re.I),
    ),
)

# Shapes that must never leave this module, whatever else the line contains.
UNSAFE_MESSAGE = re.compile(
    r"(?i)(?:"
    r"[a-z][a-z0-9+.-]*://[^/\s]*@"
    r"|(?:password|passwd|passphrase|secret|token|api[_-]?key|apikey|authorization"
    r"|credential|private[_-]?key|client[_-]?secret)\s*(?:[:=]|\bis\b|\bwas\b)"
    r"|\bbearer\s+\S"
    r"|-----begin[^-]{0,32}private key"
    r"|\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"
    r"|\beyJ[A-Za-z0-9_-]{10,}"
    r"|[\w.+-]+@[\w-]+\.[\w.]{2,}"
    r"|\b(?:\d[ -]?){12,}\b"
    r")"
)
LONG_TOKEN = re.compile(r"[A-Za-z0-9+/=_-]{40,}")
CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")
SENSITIVE_FIELD = re.compile(
    r"(?i)(?:password|passwd|secret|token|api[_-]?key|apikey|authorization|credential"
    r"|private[_-]?key|access[_-]?key|session|cookie|auth)"
)


# Loki keeps the searchable raw evidence. The collector reads only these fields.
def _now() -> datetime:
    return datetime.now(timezone.utc)


def _truncate(value: str, limit: int) -> str:
    return value if len(value) <= limit else value[:limit]


def normalize_line(raw: str) -> str:
    """Strip transport prefixes so the same message hashes the same way."""
    text = raw.rstrip("\n")
    text = CRI_PREFIX.sub("", text)
    text = RFC3339_PREFIX.sub("", text)
    return text.strip()


def signals_in(text: str) -> list[str]:
    return sorted(name for name, pattern in SIGNALS if pattern.search(text))


def _unsafe_text(text: str, limit: int) -> bool:
    """Reject anything that could carry a credential, a record or an object dump."""
    if not text or len(text) > limit:
        return True
    if CONTROL_CHARS.search(text):
        return True
    if UNSAFE_MESSAGE.search(text):
        return True
    if any(len(token) >= 40 and not token.isdigit() for token in LONG_TOKEN.findall(text)):
        return True
    # A serialized object can carry an environment or record dump.
    return text.count('"') > 2 or text.startswith(("{", "["))


def _as_text(value: Any) -> str | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        return value.strip()
    return None


def safe_message(value: Any) -> str | None:
    """Return a message only when it is a recognized operational fact.

    Prose that no signal vocabulary recognizes never leaves this module. That
    covers personal records, application payloads and injected instructions,
    which no secret pattern can enumerate. The rejected line still contributes
    its level, source and signal names.
    """
    text = _as_text(value)
    if text is None or _unsafe_text(text, MAX_MESSAGE_CHARS):
        return None
    if not signals_in(text):
        return None
    return text


def safe_source(value: Any) -> str | None:
    text = _as_text(value)
    if text is None or _unsafe_text(text, MAX_SOURCE_CHARS):
        return None
    return text if re.fullmatch(r"[A-Za-z0-9_.:/-]{1,%d}" % MAX_SOURCE_CHARS, text) else None


def _parse_logfmt(text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for match in re.finditer(r'([A-Za-z_][A-Za-z0-9_.-]*)=("([^"]*)"|[^\s"]*)', text):
        key = match.group(1)
        value = match.group(3) if match.group(3) is not None else match.group(2)
        if len(fields) < 64:
            fields[key] = value
    return fields


def accepted_fields(fields: dict[str, Any]) -> tuple[dict[str, str], bool]:
    """Keep allowlisted, safe fields and report whether prose was held back."""
    selected: dict[str, str] = {}
    dropped = False
    for key in LEVEL_KEYS:
        value = fields.get(key)
        if isinstance(value, str) and value.strip().lower() in LEVEL_VALUES:
            selected["level"] = LEVEL_VALUES[value.strip().lower()]
            break
    for key in MESSAGE_KEYS:
        if key not in fields:
            continue
        if SENSITIVE_FIELD.search(key):
            dropped = True
            continue
        message = safe_message(fields[key])
        if message is not None:
            selected["message"] = message
            break
        dropped = True
    for key in SOURCE_KEYS:
        source = safe_source(fields.get(key))
        if source is not None:
            selected["source"] = source
            break
    return selected, dropped


def sanitize_line(raw: str) -> dict[str, Any]:
    """Turn one raw log line into a bounded, allowlisted record.

    The raw line is never returned. Free text is counted, not exported.
    """
    text = normalize_line(raw)
    record: dict[str, Any] = {"format": "text", "signals": signals_in(text), "level": "unknown"}
    if not text:
        return record
    fields: dict[str, Any] = {}
    if text.startswith("{"):
        try:
            parsed = json.loads(text)
        except (ValueError, TypeError):
            parsed = None
        if isinstance(parsed, dict):
            fields = parsed
            record["format"] = "json"
    elif LOGFMT_LINE.match(text):
        fields = _parse_logfmt(text)
        record["format"] = "logfmt"
    if fields:
        selected, dropped = accepted_fields(fields)
        record.update(selected)
        record.setdefault("level", "unknown")
        record["message_held_back"] = dropped and "message" not in selected
    return record


def _line_messages(
    streams: Iterable[Any], *, line_budget: int, byte_budget: int
) -> tuple[list[str], int, bool]:
    """Flatten Loki streams in time order inside the remaining incident budget.

    Returns the lines, the bytes they used, and whether a budget stopped the
    read. The caller passes what is left for the whole incident, so the bounds
    stay aggregate instead of multiplying per target.
    """
    collected: list[tuple[str, str]] = []
    used = 0
    truncated = False
    for stream in streams:
        if not isinstance(stream, dict):
            continue
        for value in stream.get("values") or []:
            if not isinstance(value, list) or len(value) != 2:
                continue
            timestamp, line = value
            if not isinstance(timestamp, str) or not isinstance(line, str):
                continue
            size = len(line.encode("utf-8", "ignore"))
            if used + size > byte_budget or len(collected) >= line_budget:
                truncated = True
                break
            used += size
            collected.append((timestamp, _truncate(line, MAX_RAW_LINE_CHARS)))
        if truncated:
            break
    return [item[1] for item in sorted(collected)], used, truncated


def build_target(symptom: str, target: dict[str, str]) -> dict[str, str] | None:
    """Build one bounded Loki selector from validated alert labels."""
    namespace = target.get("namespace", "")
    if not SAFE_SELECTOR_VALUE.fullmatch(namespace or ""):
        return None
    matchers = [f'namespace="{namespace}"']
    container = target.get("container", "")
    pod = target.get("pod", "")
    if container and SAFE_SELECTOR_VALUE.fullmatch(container):
        matchers.append(f'container="{container}"')
    elif pod and SAFE_SELECTOR_VALUE.fullmatch(pod):
        matchers.append(f'pod="{pod}"')
    selector = "{" + ", ".join(matchers) + "}"
    if not pod and not container:
        selector += ' |~ "(?i)(error|fail|fatal|warn|denied|refused|timeout|mount|backup)"'
    return {"id": symptom, "selector": selector, "query": selector}


MAX_NODE_TARGETS = 3


def build_targets(
    summary: dict[str, Any],
    node_pods: dict[str, list[tuple[str, str]]] | None = None,
) -> tuple[list[dict[str, str]], list[dict[str, Any]]]:
    """Select bounded evidence targets for an incident and record explicit gaps."""
    targets: list[dict[str, str]] = []
    gaps: list[dict[str, Any]] = []
    seen: set[str] = set()
    symptoms = summary.get("symptoms") or []
    for symptom in symptoms:
        if len(targets) >= MAX_TARGETS:
            gaps.append({"reason": "target-limit", "target": symptom.get("name", "")})
            continue
        if symptom.get("state") != "firing":
            continue
        name = str(symptom.get("name", "symptom"))
        labels = symptom.get("labels") or {}
        target = {
            key: str(labels.get(key))
            for key in ("namespace", "app_namespace", "pvc_namespace", "pod", "container", "node")
            if labels.get(key)
        }
        if "namespace" not in target:
            for alias in ("app_namespace", "pvc_namespace"):
                if alias in target:
                    target["namespace"] = target[alias]
                    break
        if not target.get("namespace") and target.get("node"):
            # A node incident has no namespace. Read the pods the node owns.
            selected = (node_pods or {}).get(target["node"], [])[:MAX_NODE_TARGETS]
            if not selected:
                gaps.append({"reason": "no-log-selector", "target": name})
                continue
            for namespace, pod in selected:
                built = build_target(f"{name}[{pod}]", {"namespace": namespace, "pod": pod})
                if built is None or built["selector"] in seen:
                    continue
                seen.add(built["selector"])
                targets.append(built)
            continue
        built = build_target(name, target)
        if built is None:
            reason = "no-log-selector" if not target.get("namespace") else "unsafe-selector"
            gaps.append({"reason": reason, "target": name})
            continue
        if built["selector"] in seen:
            continue
        seen.add(built["selector"])
        targets.append(built)
    return targets[:MAX_TARGETS], gaps


def pack_bytes(pack: dict[str, Any]) -> int:
    return len(json.dumps(pack, separators=(",", ":"), ensure_ascii=True).encode())


def trim_pack(pack: dict[str, Any]) -> dict[str, Any]:
    """Shrink the pack to its byte budget without inventing evidence."""
    while pack_bytes(pack) > MAX_PACK_BYTES:
        candidates = [
            (index, len(json.dumps(target.get("samples", []))))
            for index, target in enumerate(pack["targets"])
        ]
        if not candidates:
            break
        index = max(candidates, key=lambda item: item[1])[0]
        samples = pack["targets"][index].get("samples", [])
        if samples:
            samples.pop()
            pack["totals"]["samples"] = sum(
                len(target.get("samples", [])) for target in pack["targets"]
            )
            continue
        pack["targets"].pop(index)
    if pack_bytes(pack) > MAX_PACK_BYTES:
        pack["targets"] = []
        pack["gaps"].append({"reason": "pack-limit", "target": "incident"})
    return pack


def loki_transport(url: str, timeout: float) -> tuple[int, Any]:
    """One bounded Loki read. The URL carries only validated label values."""
    try:
        with urlopen(url, timeout=timeout) as response:
            body = response.read(MAX_RAW_RESPONSE_BYTES + 1)
            if len(body) > MAX_RAW_RESPONSE_BYTES:
                return response.status, None
            return response.status, json.loads(body)
    except HTTPError as error:
        return error.code, None
    except (URLError, TimeoutError, OSError, ValueError):
        return 0, None


def query_url(base: str, selector: str, start: datetime, end: datetime, limit: int) -> str:
    return (
        base.rstrip("/")
        + "/loki/api/v1/query_range?"
        + urlencode(
            {
                "query": selector,
                "start": str(int(start.timestamp() * 1_000_000_000)),
                "end": str(int(end.timestamp() * 1_000_000_000)),
                "limit": str(limit),
                "direction": "backward",
            }
        )
    )


def collect_evidence(
    summary: dict[str, Any],
    *,
    transport: Callable[[str, float], tuple[int, Any]] = loki_transport,
    loki_url: str = DEFAULT_LOKI_URL,
    now: datetime | None = None,
    window_seconds: int = DEFAULT_WINDOW_SECONDS,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    node_pods: dict[str, list[tuple[str, str]]] | None = None,
) -> dict[str, Any]:
    """Read bounded log evidence for one incident from Loki.

    The query is built only from charset-validated label values, and the read is
    bounded before it is parsed, so neither alert text nor log content can widen
    the request or the payload.
    """
    observed_at = now or _now()
    window_seconds = max(60, min(int(window_seconds), MAX_WINDOW_SECONDS))
    pack: dict[str, Any] = {
        "status": "unavailable",
        "collected_at": observed_at.isoformat(),
        "window_seconds": window_seconds,
        "targets": [],
        "gaps": [],
        "totals": {"lines": 0, "exported": 0, "dropped": 0, "samples": 0, "bytes": 0},
        "limits": {
            "targets": MAX_TARGETS,
            "lines_per_target": MAX_LINES_PER_TARGET,
            "total_lines": MAX_TOTAL_LINES,
        },
    }
    targets, gaps = build_targets(summary, node_pods)
    pack["gaps"].extend(gaps)
    if not targets:
        pack["status"] = "no-evidence"
        return pack

    start = observed_at - timedelta(seconds=window_seconds)
    line_budget = MAX_TOTAL_LINES
    byte_budget = MAX_RAW_BYTES
    observed_any = False
    for target in targets:
        if line_budget <= 0 or byte_budget <= 0:
            pack["gaps"].append({"reason": "incident-budget-reached", "target": target["id"][:80]})
            continue
        url = query_url(loki_url, target["query"], start, observed_at, MAX_LINES_PER_TARGET)
        try:
            status, response = transport(url, timeout)
        except Exception:  # noqa: BLE001 - any transport fault is an evidence gap
            pack["gaps"].append({"reason": "collector-unavailable", "target": target["id"][:80]})
            continue
        if status != 200 or not isinstance(response, dict):
            pack["gaps"].append({"reason": "query-failed", "target": target["id"][:80]})
            continue
        observed_any = True
        streams = response.get("data", {}).get("result") if isinstance(response, dict) else None
        if not isinstance(streams, list):
            pack["gaps"].append({"reason": "query-malformed", "target": target["id"][:80]})
            continue
        lines, used, truncated = _line_messages(
            streams, line_budget=line_budget, byte_budget=byte_budget
        )
        line_budget -= len(lines)
        byte_budget -= used
        pack["totals"]["bytes"] = pack["totals"].get("bytes", 0) + used
        if truncated:
            pack["gaps"].append({"reason": "incident-budget-reached", "target": target["id"][:80]})
        if not lines:
            pack["gaps"].append({"reason": "no-lines-in-window", "target": target["id"][:80]})
            continue
        records = [sanitize_line(line) for line in lines]
        text_lines = sum(1 for record in records if record["format"] == "text")
        held_back = sum(1 for record in records if record.get("message_held_back"))
        if text_lines:
            pack["gaps"].append(
                {
                    "reason": "text-format-not-exported",
                    "target": target["id"][:80],
                    "lines": text_lines,
                }
            )
        if held_back:
            pack["gaps"].append(
                {"reason": "message-held-back", "target": target["id"][:80], "lines": held_back}
            )
        exported = [record for record in records if record["format"] != "text"]
        for record in exported:
            record.pop("message_held_back", None)
        pack["targets"].append(
            {
                "id": target["id"][:80],
                "selector": target["selector"][:200],
                "lines": len(records),
                "exported": len(exported),
                "dropped": len(records) - len(exported),
                "levels": _histogram(record.get("level", "unknown") for record in records),
                "signals": _histogram(
                    signal for record in records for signal in record.get("signals", [])
                ),
                "samples": _samples(exported),
            }
        )
        pack["totals"]["lines"] += len(records)
        pack["totals"]["exported"] += len(exported)
        pack["totals"]["dropped"] += len(records) - len(exported)
    pack["totals"]["samples"] = sum(len(target["samples"]) for target in pack["targets"])
    pack["status"] = "observed" if observed_any else "unavailable"
    if not pack["targets"] and observed_any:
        pack["status"] = "no-evidence"
    return trim_pack(pack)


def _histogram(values: Iterable[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        if isinstance(value, str) and value:
            counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:16])


def _samples(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Deduplicate exported records so repeated lines are not sent or billed twice."""
    unique: dict[str, dict[str, Any]] = {}
    for record in records:
        key = json.dumps(record, sort_keys=True)
        if key not in unique:
            unique[key] = record
    ordered = list(unique.values())
    return ordered[:MAX_SAMPLES_PER_TARGET]


def sample_texts(pack: dict[str, Any]) -> list[str]:
    """Return the bounded texts that may be sent to the classifier."""
    texts: list[str] = []
    for target in pack.get("targets", []):
        for record in target.get("samples", []):
            parts = [
                f"{key}={record[key]}" for key in ("level", "source", "message") if record.get(key)
            ]
            if record.get("signals"):
                parts.append("signals=" + ",".join(record["signals"]))
            if parts:
                texts.append(" ".join(parts))
    return texts


def store_pack(pack: dict[str, Any], directory: str | Path, name: str) -> str | None:
    """Keep the sanitized pack privately, with bounded retention."""
    root = Path(directory)
    try:
        root.mkdir(mode=0o700, parents=True, exist_ok=True)
        root.chmod(0o700)
        digest = hashlib.sha256(name.encode()).hexdigest()[:12]
        stamp = re.sub(r"[^0-9]", "", str(pack.get("collected_at", "")))[:14]
        descriptor, temporary = tempfile.mkstemp(prefix=f".{digest}.", dir=root)
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(pack, stream, sort_keys=True)
            stream.flush()
            os.fsync(stream.fileno())
        destination = root / f"{stamp}-{digest}.json"
        os.replace(temporary, destination)
        destination.chmod(0o600)
        stored = sorted(root.glob("*.json"))
        for stale in stored[:-MAX_STORED_PACKS]:
            stale.unlink(missing_ok=True)
        return str(destination)
    except OSError:
        return None
