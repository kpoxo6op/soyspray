#!/usr/bin/env python3
import json
import logging
import math
import os
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(message)s",
)

DOMAIN_NAME = os.environ["DOMAIN_NAME"]
CHECK_INTERVAL_SECONDS = int(os.getenv("CHECK_INTERVAL_SECONDS", "21600"))
HTTP_PORT = int(os.getenv("HTTP_PORT", "8080"))
CLOUDFLARE_API_TOKEN = os.environ["CLOUDFLARE_API_TOKEN"]
HEALTHCHECKS_PING_URL = os.environ["HEALTHCHECKS_PING_URL"]
EXPECTED_NAMESERVERS = sorted(
    ns.strip().rstrip(".").lower()
    for ns in os.environ["EXPECTED_NAMESERVERS"].split(",")
    if ns.strip()
)
USER_AGENT = "soyspray-domain-health/1.0"

if not EXPECTED_NAMESERVERS:
    raise RuntimeError("EXPECTED_NAMESERVERS must not be empty")


METRIC_HELP = {
    "domain_health_check_success": "Whether the named check completed successfully.",
    "domain_health_last_check_timestamp_seconds": "Unix timestamp of the most recent check attempt.",
    "domain_health_last_success_timestamp_seconds": "Unix timestamp of the most recent successful check.",
    "domain_health_rdap_expiry_timestamp_seconds": "Unix timestamp of the domain RDAP expiry date.",
    "domain_health_rdap_expiry_days": "Remaining whole days until domain expiry.",
    "domain_health_cloudflare_zone_exists": "Whether the Cloudflare zone exists.",
    "domain_health_cloudflare_zone_active": "Whether the Cloudflare zone status is active.",
    "domain_health_cloudflare_nameservers_match": "Whether Cloudflare nameservers match the expected values.",
    "domain_health_public_dns_nameservers_match": "Whether public DNS NS answers match the expected values.",
}


class MetricsState:
    def __init__(self):
        self._lock = threading.Lock()
        self._samples = {}
        self._last_run_ok = False
        self._last_run_finished = 0.0

    def set_metric(self, name, labels, value):
        key = (name, tuple(sorted(labels.items())))
        with self._lock:
            self._samples[key] = float(value)

    def get_health(self):
        with self._lock:
            if self._last_run_finished == 0:
                return False
            return self._last_run_ok and (time.time() - self._last_run_finished) < (CHECK_INTERVAL_SECONDS * 2)

    def finish_run(self, ok):
        with self._lock:
            self._last_run_ok = ok
            self._last_run_finished = time.time()

    def render_prometheus(self):
        with self._lock:
            grouped = {}
            for (name, labels), value in self._samples.items():
                grouped.setdefault(name, []).append((labels, value))

        lines = []
        for name in sorted(grouped):
            lines.append(f"# HELP {name} {METRIC_HELP.get(name, name)}")
            lines.append(f"# TYPE {name} gauge")
            for labels, value in sorted(grouped[name]):
                rendered_labels = ",".join(
                    f'{k}="{str(v).replace(chr(92), chr(92) * 2).replace(chr(34), chr(92) + chr(34))}"'
                    for k, v in labels
                )
                metric = f"{name}{{{rendered_labels}}}" if rendered_labels else name
                if math.isnan(value) or math.isinf(value):
                    continue
                lines.append(f"{metric} {value}")
        lines.append("")
        return "\n".join(lines).encode("utf-8")


STATE = MetricsState()


def request_json(url, headers=None):
    req = Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
            **(headers or {}),
        },
    )
    with urlopen(req, timeout=20) as response:
        return json.load(response)


def parse_timestamp(value):
    cleaned = value.strip()
    if cleaned.endswith("Z"):
        cleaned = cleaned[:-1] + "+00:00"
    return datetime.fromisoformat(cleaned).astimezone(timezone.utc).timestamp()


def extract_rdap_expiry_timestamp(payload):
    direct_keys = [
        "expirationDate",
        "expiryDate",
        "expires",
        "registryExpiryDate",
        "paid_till",
    ]
    for key in direct_keys:
        value = payload.get(key)
        if isinstance(value, str):
            return parse_timestamp(value)

    for event in payload.get("events", []):
        action = str(event.get("eventAction", "")).strip().lower()
        when = event.get("eventDate")
        if not isinstance(when, str):
            continue
        if action in {"expiration", "expiry", "expiration date", "registered until"}:
            return parse_timestamp(when)

    raise RuntimeError("Unable to find RDAP expiry timestamp")


def normalize_nameservers(values):
    return sorted(str(value).strip().rstrip(".").lower() for value in values if str(value).strip())


def update_check_status(check_name, ok, now_ts):
    labels = {"domain": DOMAIN_NAME, "check": check_name}
    STATE.set_metric("domain_health_check_success", labels, 1 if ok else 0)
    STATE.set_metric("domain_health_last_check_timestamp_seconds", labels, now_ts)
    if ok:
        STATE.set_metric("domain_health_last_success_timestamp_seconds", labels, now_ts)


def check_rdap(now_ts):
    payload = request_json(f"https://rdap.org/domain/{quote(DOMAIN_NAME)}")
    expiry_ts = extract_rdap_expiry_timestamp(payload)
    expiry_days = math.floor((expiry_ts - now_ts) / 86400)
    labels = {"domain": DOMAIN_NAME}
    STATE.set_metric("domain_health_rdap_expiry_timestamp_seconds", labels, expiry_ts)
    STATE.set_metric("domain_health_rdap_expiry_days", labels, expiry_days)


def check_cloudflare(now_ts):
    headers = {"Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}"}
    payload = request_json(
        f"https://api.cloudflare.com/client/v4/zones?name={quote(DOMAIN_NAME)}",
        headers=headers,
    )
    if not payload.get("success", False):
        raise RuntimeError(f"Cloudflare API error: {payload}")

    zone = None
    for candidate in payload.get("result", []):
        if str(candidate.get("name", "")).lower() == DOMAIN_NAME.lower():
            zone = candidate
            break

    labels = {"domain": DOMAIN_NAME}
    STATE.set_metric("domain_health_cloudflare_zone_exists", labels, 1 if zone else 0)
    if not zone:
        return

    STATE.set_metric(
        "domain_health_cloudflare_zone_active",
        labels,
        1 if str(zone.get("status", "")).lower() == "active" else 0,
    )
    nameservers = normalize_nameservers(zone.get("name_servers", []))
    STATE.set_metric(
        "domain_health_cloudflare_nameservers_match",
        labels,
        1 if nameservers == EXPECTED_NAMESERVERS else 0,
    )


def check_public_dns(now_ts):
    payload = request_json(f"https://dns.google/resolve?name={quote(DOMAIN_NAME)}&type=NS")
    answers = payload.get("Answer", [])
    nameservers = normalize_nameservers(answer.get("data", "") for answer in answers)
    labels = {"domain": DOMAIN_NAME}
    STATE.set_metric(
        "domain_health_public_dns_nameservers_match",
        labels,
        1 if nameservers == EXPECTED_NAMESERVERS else 0,
    )


def ping_healthchecks(suffix=""):
    url = HEALTHCHECKS_PING_URL.rstrip("/") + suffix
    req = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(req, timeout=10) as response:
        response.read()


def run_checks_forever():
    while True:
        now_ts = time.time()
        overall_ok = True
        checks = {
            "rdap": check_rdap,
            "cloudflare_zone": check_cloudflare,
            "cloudflare_nameservers": check_cloudflare,
            "public_dns_nameservers": check_public_dns,
        }

        for check_name, check_fn in checks.items():
            try:
                check_fn(now_ts)
                update_check_status(check_name, True, now_ts)
                logging.info("check succeeded: %s", check_name)
            except Exception as exc:  # noqa: BLE001
                overall_ok = False
                update_check_status(check_name, False, now_ts)
                logging.exception("check failed: %s: %s", check_name, exc)

        update_check_status("overall", overall_ok, now_ts)
        try:
            ping_healthchecks("" if overall_ok else "/fail")
        except (HTTPError, URLError) as exc:
            logging.warning("healthchecks ping failed: %s", exc)

        STATE.finish_run(overall_ok)
        time.sleep(CHECK_INTERVAL_SECONDS)


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/metrics":
            payload = STATE.render_prometheus()
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; version=0.0.4; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return

        if self.path == "/healthz":
            status = 200 if STATE.get_health() else 503
            payload = b"ok\n" if status == 200 else b"stale\n"
            self.send_response(status)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return

        self.send_response(404)
        self.end_headers()

    def log_message(self, fmt, *args):
        logging.debug("http %s", fmt % args)


def main():
    worker = threading.Thread(target=run_checks_forever, daemon=True)
    worker.start()
    server = ThreadingHTTPServer(("0.0.0.0", HTTP_PORT), Handler)
    logging.info("starting exporter on :%s for domain %s", HTTP_PORT, DOMAIN_NAME)
    server.serve_forever()


if __name__ == "__main__":
    main()
