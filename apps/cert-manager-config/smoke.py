"""Read certificate readiness and validate retained HTTPS endpoints without credentials."""

import hashlib
import json
import socket
import ssl
import subprocess
from datetime import UTC, datetime

HOSTS = ("vault.soyspray.vip", "obsidian.soyspray.vip", "headlamp.soyspray.vip")


def timestamp(value):
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("Timestamp has no timezone.")
    return result


def resource_check(resource, now):
    kind = resource["kind"]
    name = resource["metadata"]["name"]
    result = {"target": f"{kind}/{name}"}
    status = resource.get("status", {})
    ready = next((c for c in status.get("conditions", []) if c.get("type") == "Ready"), None)
    if (
        ready is None
        or not isinstance(resource["metadata"].get("generation"), int)
        or ready.get("observedGeneration") != resource["metadata"].get("generation")
    ):
        return {
            **result,
            "status": "unknown",
            "cause": "No readiness observation for the current generation.",
        }
    if ready.get("status") != "True":
        return {**result, "status": "failed", "cause": "The current resource is not Ready."}
    if kind == "Certificate":
        try:
            before, after = timestamp(status["notBefore"]), timestamp(status["notAfter"])
        except (KeyError, TypeError, AttributeError, ValueError):
            return {
                **result,
                "status": "unknown",
                "cause": "Certificate validity dates are missing or invalid.",
            }
        if not before <= now < after:
            return {
                **result,
                "status": "failed",
                "cause": "The certificate is outside its validity period.",
            }
        result["expires_at"] = after.isoformat()
    return {**result, "status": "passed"}


def read_resources(kind, names, namespace=None):
    argv = ["kubectl", "--request-timeout=15s", "get", kind, *names, "-o", "json"]
    if namespace:
        argv += ["-n", namespace]
    value = json.loads(subprocess.check_output(argv, stderr=subprocess.PIPE, timeout=20))
    resources = value["items"]
    if sorted(r["metadata"]["name"] for r in resources) != sorted(names):
        raise ValueError("The API did not return the requested resources.")
    return resources


def tls_check(host):
    context = ssl.create_default_context()
    with socket.create_connection((host, 443), timeout=10) as connection:
        with context.wrap_socket(connection, server_hostname=host) as secured:
            certificate = secured.getpeercert()
            return {
                "target": host,
                "status": "passed",
                "expires_at": datetime.fromtimestamp(
                    ssl.cert_time_to_seconds(certificate["notAfter"]), UTC
                ).isoformat(),
                "sha256": hashlib.sha256(secured.getpeercert(binary_form=True)).hexdigest(),
            }


def run(reader=read_resources, tls=tls_check, now=None):
    now = now or datetime.now(UTC)
    checks = []
    for kind, names, namespace in [
        ("clusterissuers.cert-manager.io", ["letsencrypt-prod", "letsencrypt-staging"], None),
        ("certificates.cert-manager.io", ["prod-cert", "test-cert"], "cert-manager"),
    ]:
        try:
            checks.extend(
                resource_check(resource, now) for resource in reader(kind, names, namespace)
            )
        except (OSError, subprocess.SubprocessError, KeyError, TypeError, ValueError):
            checks.append(
                {
                    "target": kind,
                    "status": "unknown",
                    "cause": "The certificate API read failed or returned incomplete data.",
                }
            )
    for host in HOSTS:
        try:
            checks.append(tls(host))
        except ssl.SSLCertVerificationError:
            checks.append(
                {
                    "target": host,
                    "status": "failed",
                    "cause": "TLS certificate trust, hostname, or validity verification failed.",
                }
            )
        except (OSError, KeyError, ValueError):
            checks.append(
                {
                    "target": host,
                    "status": "unknown",
                    "cause": "A verified TLS connection could not be completed.",
                }
            )
    statuses = {check["status"] for check in checks}
    status = "failed" if "failed" in statuses else "unknown" if "unknown" in statuses else "passed"
    return {
        "application": "cert-manager-config",
        "observed_at": now.isoformat(),
        "status": status,
        "checks": checks,
        "renewal_and_recovery": {
            "status": "unknown",
            "cause": "This read-only check does not issue or restore certificates.",
        },
        "application_login": {
            "status": "unknown",
            "cause": "TLS checks do not sign in to applications.",
        },
    }


def main():
    result = run()
    print(json.dumps(result, indent=2))
    return {"passed": 0, "failed": 1, "unknown": 2}[result["status"]]


if __name__ == "__main__":
    raise SystemExit(main())
