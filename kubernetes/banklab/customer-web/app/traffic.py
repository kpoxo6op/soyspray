#!/usr/bin/env python3
"""Generate steady, identifiable traffic through the bank-lab gateway."""

from __future__ import annotations

import base64
import hashlib
import hmac
import http.client
import json
import os
import time
from itertools import cycle
from uuid import uuid4

PROXY = os.environ.get(
    "KONG_PROXY_HOST", "banklab-kong-gateway-proxy.platform-kong.svc.cluster.local"
)
INTERVAL = float(os.environ.get("TRAFFIC_INTERVAL_SECONDS", "0.25"))
PROFILES = (
    ("mobile-banking", "accounts", "/accounts/v1/health", "ACCOUNTS_API_KEY"),
    ("payments-processor", "payments", "/payments/v1/health", "PAYMENTS_API_KEY"),
    ("internet-banking", "cards", "/cards/v1/cards", "CARDS_API_KEY"),
    ("internal-crm", "customer-profile", "/customers/v1/health", "CUSTOMERS_API_KEY"),
    ("fraud-platform", "fraud", "/fraud/v1/health", "FRAUD_API_KEY"),
)


def jwt_token() -> str:
    def encode(value: bytes) -> str:
        return base64.urlsafe_b64encode(value).rstrip(b"=").decode()

    header = encode(b'{"alg":"HS256","typ":"JWT"}')
    payload = encode(
        json.dumps(
            {"iss": os.environ["JWT_KEY"], "exp": int(time.time()) + 300}, separators=(",", ":")
        ).encode()
    )
    message = f"{header}.{payload}"
    signature = encode(
        hmac.new(os.environ["JWT_SECRET"].encode(), message.encode(), hashlib.sha256).digest()
    )
    return f"{message}.{signature}"


def event(counter: int, profile: tuple[str, str, str, str]) -> dict:
    client, api, path, key_name = profile
    host = "api.internal.banklab.test"
    headers = {
        "Host": host,
        "User-Agent": f"banklab-{client}",
        "X-Request-ID": f"traffic-{uuid4()}",
        "apikey": os.environ[key_name],
    }
    expected = 200
    scenario = "steady"

    if counter % 41 == 0:
        headers.pop("apikey")
        expected = 401
        scenario = "missing-credential"
    elif counter % 67 == 0:
        path = "/outside-api-prefix"
        expected = 404
        scenario = "unknown-route"
    elif counter % 97 == 0:
        host = "api.external.banklab.test"
        path = "/open-banking/v1/health"
        headers = {
            "Host": host,
            "User-Agent": "banklab-fintech-partner",
            "X-Request-ID": f"traffic-{uuid4()}",
            "Authorization": f"Bearer {jwt_token()}",
        }
        client, api = "fintech-partner", "open-banking"
        scenario = "partner"
    elif counter % 113 == 0:
        path = "/cards/v1/simulate-500"
        headers["apikey"] = os.environ["CARDS_API_KEY"]
        client, api = "internet-banking", "cards"
        expected = 500
        scenario = "planned-backend-error"

    return {
        "client": client,
        "api": api,
        "path": path,
        "headers": headers,
        "expected": expected,
        "scenario": scenario,
    }


def send(item: dict) -> None:
    started = time.monotonic()
    status = 0
    connection = http.client.HTTPConnection(PROXY, 80, timeout=5)
    try:
        connection.request("GET", item["path"], headers=item["headers"])
        response = connection.getresponse()
        status = response.status
        response.read()
    except OSError as exc:
        error = str(exc)
    else:
        error = None
    finally:
        connection.close()

    print(
        json.dumps(
            {
                "event": "banklab-traffic",
                "client": item["client"],
                "api": item["api"],
                "path": item["path"],
                "scenario": item["scenario"],
                "status": status,
                "expected_status": item["expected"],
                "ok": status == item["expected"],
                "latency_ms": round((time.monotonic() - started) * 1000),
                "request_id": item["headers"]["X-Request-ID"],
                "error": error,
            },
            separators=(",", ":"),
        ),
        flush=True,
    )


if __name__ == "__main__":
    for count, profile in enumerate(cycle(PROFILES), start=1):
        send(event(count, profile))
        time.sleep(INTERVAL)
