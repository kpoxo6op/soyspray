#!/usr/bin/env python3
"""Classify sanitized incident evidence with the Jev fast classification route.

The classification is a relevance and routing hint. It is never proof of health,
never proof of a root cause, and never authority to suppress a critical alarm or
authorize a change. Every failure mode returns an explicit unknown result and
leaves native alerting and ordinary diagnosis working.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import time
from datetime import datetime, timezone
from typing import Any, Callable, Iterable
from urllib.error import HTTPError
from urllib.request import Request, urlopen

JEV_URL = "https://classifier.dev"
USER_AGENT = "soyspray-incident-diagnosis/1.0"

STORAGE_FAILURE = "storage failure"
NETWORK_FAILURE = "network or DNS failure"
AUTH_FAILURE = "authentication or permission failure"
CRASH_FAILURE = "application crash or resource exhaustion"
NORMAL = "normal or recovered"
UNKNOWN = "unknown or insufficient evidence"

LABELS = (
    STORAGE_FAILURE,
    NETWORK_FAILURE,
    AUTH_FAILURE,
    CRASH_FAILURE,
    NORMAL,
    UNKNOWN,
)

INSTRUCTIONS = (
    "Classify one normalized evidence line from a Kubernetes cluster incident by the "
    "single failure it shows. Use storage failure for volume, disk or backup storage "
    "faults. Use network or DNS failure for connectivity, name resolution and timeout "
    "faults. Use authentication or permission failure for refused, denied or expired "
    "access. Use application crash or resource exhaustion for crashes, restarts, "
    "memory or CPU pressure. Use normal or recovered for lines that report success or "
    "recovery. When the line does not clearly show one of those, or you are unsure, "
    "use unknown or insufficient evidence. Never guess to avoid the unknown label."
)

MIN_CONFIDENCE = 0.6
BATCH_MAX = 64
REQUESTS_PER_RUN = 2
MAX_TEXT_CHARS = 400
MAX_PAYLOAD_BYTES = 32 * 1024
# A response is read up to this size, so a slow or endless body cannot hold the
# adapter lock past the budget.
MAX_RESPONSE_BYTES = 256 * 1024
REQUEST_TIMEOUT = 8.0
MAX_RETRIES = 2
TOTAL_BUDGET_SECONDS = 25.0
MAX_CACHE_ENTRIES = 2000
MAX_CACHE_VALUE_CHARS = 256
DAILY_CLASSIFICATION_LIMIT = 1500
EXPECTED_MODEL_PREFIX = "jev-"

SAFE_TEXT = re.compile(r"[^\x20-\x7e]")


def normalize_text(text: str) -> str:
    """Collapse whitespace and drop non-printable characters before hashing."""
    collapsed = SAFE_TEXT.sub(" ", str(text))
    return re.sub(r"\s+", " ", collapsed).strip()[:MAX_TEXT_CHARS]


def text_key(text: str) -> str:
    return hashlib.sha256(normalize_text(text).encode()).hexdigest()[:32]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def default_client(payload: dict[str, Any], timeout: float) -> tuple[int, Any]:
    """Post one classification request and return its status and decoded body."""
    request = Request(
        JEV_URL,
        data=json.dumps(payload).encode(),
        headers={
            "content-type": "application/json",
            "user-agent": USER_AGENT,
            "accept": "application/json",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            body = response.read(MAX_RESPONSE_BYTES + 1)
            if len(body) > MAX_RESPONSE_BYTES:
                return response.status, None
            return response.status, json.loads(body)
    except HTTPError as error:
        body: Any = None
        try:
            body = json.load(error)
        except Exception:  # noqa: BLE001 - an error body is optional
            body = None
        return error.code, body


def _retry_delay(status: int, body: Any, attempt: int) -> float:
    if isinstance(body, dict):
        value = body.get("retry_after") or body.get("retryAfter")
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return min(float(value), 5.0)
        if isinstance(value, str) and value.isdigit():
            return min(float(value), 5.0)
    return min(0.5 * (2**attempt), 4.0)


class Classifier:
    """Bounded, cached, non-authoritative classifier client."""

    def __init__(
        self,
        state: dict[str, Any],
        *,
        client: Callable[[dict[str, Any], float], tuple[int, Any]] = default_client,
        now: Callable[[], datetime] = _now,
        sleep: Callable[[float], None] = time.sleep,
        budget_seconds: float = TOTAL_BUDGET_SECONDS,
    ):
        self.state = state
        self.client = client
        self.now = now
        self.sleep = sleep
        self.budget = budget_seconds

    def cache(self) -> dict[str, Any]:
        return self.state.setdefault("classifier_cache", {})

    def metrics(self) -> dict[str, Any]:
        return self.state.setdefault("metrics", {})

    def classify(self, texts: Iterable[str]) -> dict[str, Any]:
        report: dict[str, Any] = {
            "status": "ok",
            "model": "",
            "model_substitution": False,
            "counts": {},
            "results": [],
            "classifications": 0,
            "requests": 0,
            "skipped": 0,
            "cause": "",
        }
        cache = self.cache()
        seen: set[str] = set()
        pending: list[str] = []
        for text in texts:
            normalized = normalize_text(text)
            if not normalized:
                continue
            key = text_key(normalized)
            if key in seen:
                continue
            seen.add(key)
            entry = cache.get(key)
            if isinstance(entry, dict) and entry.get("label") in LABELS:
                report["results"].append(
                    {
                        "key": key,
                        "label": entry["label"],
                        "confidence": entry.get("confidence"),
                        "source": "cache",
                        "model": entry.get("model", ""),
                        "escalated": bool(entry.get("escalated")),
                    }
                )
            else:
                pending.append(normalized)

        if pending:
            report["status"] = "cached" if report["results"] else "ok"
            if len(pending) > REQUESTS_PER_RUN * BATCH_MAX:
                report["skipped"] = len(pending) - REQUESTS_PER_RUN * BATCH_MAX
                report["cause"] = "batch-limit"
                pending = pending[: REQUESTS_PER_RUN * BATCH_MAX]
            failure = self._request_batches(pending, report)
            if failure:
                failure = "unavailable" if failure == "partial-budget" else failure
                report["status"] = "partial" if report["classifications"] else failure
                report["cause"] = report["cause"] or failure
                for text in pending:
                    key = text_key(text)
                    if not any(item["key"] == key for item in report["results"]):
                        report["results"].append(_fallback(key))
        elif report["results"]:
            report["status"] = "cached"

        if not report["results"] and not pending:
            # Nothing was classified. Say so instead of reporting success.
            report["status"] = "no-input"
        report["counts"] = _counts(report["results"])
        report["unknown"] = report["counts"].get(UNKNOWN, 0)
        self._record_metrics(report)
        self._prune_cache()
        return report

    def _request_batches(self, pending: list[str], report: dict[str, Any]) -> str:
        started = time.monotonic()
        for start in range(0, len(pending), BATCH_MAX):
            if time.monotonic() - started > self.budget:
                return "unavailable"
            batch = pending[start : start + BATCH_MAX]
            _, used = self._quota()
            remaining = DAILY_CLASSIFICATION_LIMIT - used
            if remaining <= 0:
                return "quota-exhausted"
            # Reserve before dispatch. A request that completes remotely but
            # times out locally is then still counted, and the daily limit stays
            # a bound instead of an estimate.
            batch = batch[:remaining]
            if len(batch) < len(pending[start : start + BATCH_MAX]):
                report["cause"] = "quota-trimmed"
            self.charge(len(batch))
            status, body, cause = self._post(batch, started)
            if status != "ok":
                report["cause"] = cause or status
                return status
            results = _extract_results(body, batch)
            if results is None:
                report["cause"] = "malformed"
                return "unavailable"
            model = str(body.get("model", ""))
            substitutions = [model] if model else []
            # modelsUsed is a list of serving model names. Each result also
            # names its own model, which may differ inside a mixed batch.
            used = body.get("modelsUsed")
            if isinstance(used, list):
                substitutions += [item for item in used if isinstance(item, str)]
            substitutions += [
                item["model"]
                for item in results
                if isinstance(item.get("model"), str) and item["model"]
            ]
            if any(name and not name.startswith(EXPECTED_MODEL_PREFIX) for name in substitutions):
                report["model_substitution"] = True
            report["model"] = model or report["model"]
            for item in results:
                self._cache_item(item, model)
            report["results"].extend(results)
            report["requests"] += 1
            report["classifications"] += len(batch)
            if time.monotonic() - started > self.budget:
                # The socket timeout bounds each read, not the whole exchange.
                # Stop before the next batch once the wall clock is spent.
                return "unavailable" if not report["classifications"] else "partial-budget"
        return ""

    def _post(self, batch: list[str], started: float) -> tuple[str, Any, str]:
        payload = {
            "labels": list(LABELS),
            "inputs": batch,
            "instructions": INSTRUCTIONS,
            "tier": "fast",
        }
        if len(json.dumps(payload).encode()) > MAX_PAYLOAD_BYTES:
            return "unavailable", None, "payload-limit"
        attempt = 0
        while True:
            remaining = self.budget - (time.monotonic() - started)
            if remaining <= 1:
                return "unavailable", None, "budget"
            try:
                status, body = self.client(payload, min(REQUEST_TIMEOUT, max(remaining, 1.0)))
            except Exception:  # noqa: BLE001 - any transport fault is a fallback
                status, body = 0, None
            if status == 200:
                return "ok", body, ""
            if status == 429:
                self.metrics()["classifier_rate_limited"] = (
                    int(self.metrics().get("classifier_rate_limited", 0)) + 1
                )
            if status and status < 500 and status != 429:
                return "unavailable", None, f"http-{status}"
            if attempt >= MAX_RETRIES:
                return "unavailable", None, f"http-{status}" if status else "network"
            delay = _retry_delay(status, body, attempt)
            if time.monotonic() - started + delay > self.budget:
                return "unavailable", None, "budget"
            self.sleep(delay)
            attempt += 1

    def _cache_item(self, item: dict[str, Any], model: str) -> None:
        label = item.get("label")
        if label not in LABELS or item.get("source") != "provider":
            return
        self.cache()[item["key"]] = {
            "label": label,
            "confidence": item.get("confidence"),
            "model": str(item.get("model") or model)[:MAX_CACHE_VALUE_CHARS],
            "escalated": bool(item.get("escalated")),
            "at": self.now().isoformat(),
        }

    def _quota(self) -> tuple[str, int]:
        day = self.now().date().isoformat()
        quota = self.state.setdefault("quota", {})
        used = quota.get(day, 0)
        return day, used if isinstance(used, int) else 0

    def charge(self, count: int) -> None:
        day, used = self._quota()
        self.state["quota"][day] = used + max(0, int(count))

    def _record_metrics(self, report: dict[str, Any]) -> None:
        metrics = self.metrics()
        metrics["classifier_requests_total"] = int(
            metrics.get("classifier_requests_total", 0)
        ) + int(report["requests"])
        metrics["classifier_classifications_total"] = int(
            metrics.get("classifier_classifications_total", 0)
        ) + int(report["classifications"])
        metrics["classifier_unknown_total"] = int(metrics.get("classifier_unknown_total", 0)) + int(
            report["unknown"]
        )
        metrics["classifier_skipped_total"] = int(metrics.get("classifier_skipped_total", 0)) + int(
            report["skipped"]
        )
        if report["status"] in {"unavailable", "quota-exhausted", "partial"}:
            metrics["classifier_failure_total"] = (
                int(metrics.get("classifier_failure_total", 0)) + 1
            )
        if report["status"] in {"ok", "cached", "partial"}:
            metrics["classifier_last_success_timestamp_seconds"] = int(self.now().timestamp())
        if report["model"]:
            metrics["classifier_model"] = str(report["model"])[:64]
        if report["model_substitution"]:
            metrics["classifier_model_substitution_total"] = (
                int(metrics.get("classifier_model_substitution_total", 0)) + 1
            )

    def _prune_cache(self) -> None:
        cache = self.cache()
        if len(cache) <= MAX_CACHE_ENTRIES:
            return
        order = sorted(cache.items(), key=lambda item: str(item[1].get("at", "")))
        for key, _ in order[: len(cache) - MAX_CACHE_ENTRIES]:
            cache.pop(key, None)


def _extract_results(body: Any, batch: list[str]) -> list[dict[str, Any]] | None:
    """Validate one response and never trust a label outside the requested set."""
    if not isinstance(body, dict):
        return None
    results = body.get("results")
    if not isinstance(results, list) or len(results) != len(batch):
        return None
    extracted: list[dict[str, Any]] = []
    for text, item in zip(batch, results, strict=True):
        key = text_key(text)
        if not isinstance(item, dict):
            extracted.append(_fallback(key))
            continue
        label = item.get("label")
        confidence = item.get("confidence")
        model = item.get("model") if isinstance(item.get("model"), str) else ""
        if label not in LABELS:
            extracted.append(_fallback(key))
            continue
        if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
            extracted.append(_fallback(key))
            continue
        if not math.isfinite(float(confidence)) or not 0 <= float(confidence) <= 1:
            extracted.append(_fallback(key))
            continue
        if item.get("unscored") or float(confidence) < MIN_CONFIDENCE:
            extracted.append(
                {
                    "key": key,
                    "label": UNKNOWN,
                    "confidence": float(confidence),
                    "source": "provider",
                    "hint": label,
                    "model": model,
                    "escalated": bool(item.get("escalated")),
                }
            )
            continue
        extracted.append(
            {
                "key": key,
                "label": label,
                "confidence": float(confidence),
                "source": "provider",
                "model": model,
                "escalated": bool(item.get("escalated")),
            }
        )
    return extracted


def _fallback(key: str) -> dict[str, Any]:
    return {
        "key": key,
        "label": UNKNOWN,
        "confidence": None,
        "source": "fallback",
        "model": "",
        "escalated": False,
    }


def _counts(results: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in results:
        label = item.get("label")
        if label in LABELS:
            counts[label] = counts.get(label, 0) + 1
    return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))


def summarize(report: dict[str, Any]) -> dict[str, Any]:
    """Return the bounded classification summary supplied to prompts and delivery."""
    counts = report.get("counts") or {}
    known = {label: count for label, count in counts.items() if label != UNKNOWN}
    dominant = max(known, key=lambda label: known[label]) if known else UNKNOWN
    confidence = None
    for item in report.get("results", []):
        if item.get("label") == dominant and isinstance(item.get("confidence"), (int, float)):
            confidence = max(confidence or 0.0, float(item["confidence"]))
    return {
        "status": report.get("status", "unavailable"),
        "model": report.get("model", ""),
        "model_substitution": bool(report.get("model_substitution")),
        "dominant": dominant,
        "dominant_confidence": confidence,
        "counts": counts,
        "unknown": counts.get(UNKNOWN, 0),
        "classified": len(report.get("results", [])),
        "skipped": int(report.get("skipped", 0)),
        "cause": report.get("cause", ""),
        "authority": "hint-only",
    }
