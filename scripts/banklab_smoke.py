#!/usr/bin/env python3
"""Run the bank lab's read-only request and exposure checks."""

from __future__ import annotations

import base64
import hashlib
import hmac
import http.client
import json
import subprocess
import sys
import time

NAMESPACE = "synthetic-clients"
KEY_ROUTES = (
    ("/accounts/v1/health", "banklab-accounts-ok", "banklab-mobile-banking-app-key-auth"),
    ("/payments/v1/health", "banklab-payments-ok", "banklab-payments-processor-key-auth"),
    ("/cards/v1/health", "banklab-cards-ok", "banklab-internet-banking-web-key-auth"),
    ("/customers/v1/health", "banklab-customer-profile-ok", "banklab-internal-crm-key-auth"),
    ("/fraud/v1/health", "banklab-fraud-decisions-ok", "banklab-fraud-platform-key-auth"),
)


def command(*args: str) -> str:
    result = subprocess.run(args, check=False, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())
    return result.stdout.strip()


def secret(name: str, key: str) -> str:
    encoded = command(
        "kubectl",
        "-n",
        NAMESPACE,
        "get",
        "secret",
        name,
        "-o",
        f"jsonpath={{.data.{key}}}",
    )
    return base64.b64decode(encoded).decode()


def request(
    proxy: str, host: str, path: str, headers: dict[str, str] | None = None
) -> tuple[int, str]:
    connection = http.client.HTTPConnection(proxy, 80, timeout=5)
    connection.request("GET", path, headers={"Host": host, **(headers or {})})
    response = connection.getresponse()
    body = response.read().decode(errors="replace")
    connection.close()
    return response.status, body


def jwt_token(key: str, secret_value: str) -> str:
    def encode(value: bytes) -> str:
        return base64.urlsafe_b64encode(value).rstrip(b"=").decode()

    header = encode(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode())
    payload = encode(
        json.dumps({"iss": key, "exp": int(time.time()) + 300}, separators=(",", ":")).encode()
    )
    message = f"{header}.{payload}"
    signature = encode(hmac.new(secret_value.encode(), message.encode(), hashlib.sha256).digest())
    return f"{message}.{signature}"


def check(
    label: str, actual: int, expected: int, body: str = "", marker: str | None = None
) -> bool:
    passed = actual == expected and (marker is None or marker in body)
    print(f"  {'PASS' if passed else 'FAIL'}  {label} ({actual})")
    return passed


def check_rate_limit(proxy: str, key: str) -> bool:
    """Prove a short burst is limited and the one-second window recovers."""
    time.sleep(1.1)
    statuses = [
        request(
            proxy,
            "api.internal.banklab.test",
            "/accounts/v1/health",
            {"apikey": key},
        )[0]
        for _ in range(4)
    ]
    limited = 200 in statuses and 429 in statuses
    print(
        f"  {'PASS' if limited else 'FAIL'}  rate limit rejects a burst "
        f"({','.join(map(str, statuses))})"
    )

    time.sleep(1.1)
    recovered_status, recovered_body = request(
        proxy,
        "api.internal.banklab.test",
        "/accounts/v1/health",
        {"apikey": key},
    )
    recovered = check(
        "rate limit window recovers",
        recovered_status,
        200,
        recovered_body,
        "banklab-accounts-ok",
    )
    return limited and recovered


def main() -> int:
    try:
        proxy = command(
            "kubectl",
            "-n",
            "platform-kong",
            "get",
            "service",
            "banklab-kong-gateway-proxy",
            "-o",
            "jsonpath={.status.loadBalancer.ingress[0].ip}",
        )
        if not proxy:
            raise RuntimeError("Kong proxy has no LoadBalancer address")

        ok = True
        keys = {}
        print("KONG ROUTES")
        for path, marker, secret_name in KEY_ROUTES:
            route_key = secret(secret_name, "key")
            keys[secret_name] = route_key
            status, body = request(
                proxy,
                "api.internal.banklab.test",
                path,
                {"apikey": route_key},
            )
            ok &= check(path, status, 200, body, marker)

        jwt_key = secret("banklab-external-fintech-partner-jwt", "key")
        jwt_secret = secret("banklab-external-fintech-partner-jwt", "secret")
        status, body = request(
            proxy,
            "api.external.banklab.test",
            "/open-banking/v1/health",
            {"Authorization": f"Bearer {jwt_token(jwt_key, jwt_secret)}"},
        )
        ok &= check("/open-banking/v1/health", status, 200, body, "banklab-open-banking-ok")

        print("\nRATE LIMIT")
        ok &= check_rate_limit(proxy, keys["banklab-mobile-banking-app-key-auth"])

        print("\nBOUNDARIES")
        status, body = request(proxy, "api.internal.banklab.test", "/accounts/v1/health")
        ok &= check("missing API key is rejected", status, 401, body)
        status, body = request(proxy, "api.external.banklab.test", "/accounts/v1/health")
        ok &= check("internal route is absent externally", status, 404, body)

        service = json.loads(
            command("kubectl", "-n", "platform-kong", "get", "service", "-o", "json")
        )
        public_admin = any(
            port.get("port") in {8001, 8444} or "admin" in port.get("name", "")
            for item in service["items"]
            if item["spec"].get("type") in {"LoadBalancer", "NodePort"}
            for port in item["spec"].get("ports", [])
        )
        ok &= check("Admin API has no public Service", 1 if public_admin else 0, 0)

        customer_status = command(
            "curl",
            "--silent",
            "--output",
            "/dev/null",
            "--write-out",
            "%{http_code}",
            "--max-time",
            "5",
            "http://banklab-web.soyspray.vip",
        )
        ok &= check("customer app", int(customer_status), 200)
        return 0 if ok else 1
    except (RuntimeError, ValueError, OSError) as exc:
        print(f"Smoke check failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
