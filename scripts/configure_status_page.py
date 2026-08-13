#!/usr/bin/env python3
"""Reconcile the public Better Stack status page and its Cloudflare CNAME."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "platform/public-status.json"
BETTER_STACK_API = "https://uptime.betterstack.com/api/v2"
CLOUDFLARE_API = "https://api.cloudflare.com/client/v4"


class JsonClient:
    def __init__(self, base_url: str, token: str) -> None:
        self.base_url = base_url
        self.token = token

    def request(self, method: str, path: str, payload: dict | None = None) -> dict:
        body = json.dumps(payload).encode() if payload is not None else None
        request = Request(
            f"{self.base_url}{path}",
            data=body,
            method=method,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
                "User-Agent": "soyspray-status-reconciler/1",
            },
        )
        try:
            with urlopen(request, timeout=30) as response:
                result = json.load(response)
        except HTTPError as exc:
            detail = exc.read().decode(errors="replace")
            raise RuntimeError(f"{method} {path} failed with HTTP {exc.code}: {detail}") from exc
        if result.get("success") is False:
            raise RuntimeError(f"{method} {path} failed: {result.get('errors', [])}")
        return result


def validate_config(config: dict) -> None:
    page = config.get("status_page", {})
    dns = config.get("dns", {})
    services = config.get("services", [])
    required_page = {"company_name", "subdomain", "custom_domain"}
    required_dns = {"zone", "name", "target"}
    required_service = {"name", "url", "keyword", "explanation"}

    if missing := required_page - page.keys():
        raise ValueError(f"status_page is missing: {', '.join(sorted(missing))}")
    if missing := required_dns - dns.keys():
        raise ValueError(f"dns is missing: {', '.join(sorted(missing))}")
    if not services:
        raise ValueError("services must contain at least one monitor")
    if page["custom_domain"] != dns["name"]:
        raise ValueError("status_page.custom_domain must match dns.name")
    if not dns["name"].endswith(f".{dns['zone']}"):
        raise ValueError("dns.name must be below dns.zone")
    if dns["target"] != "statuspage.betteruptime.com":
        raise ValueError("dns.target must be statuspage.betteruptime.com")

    urls: set[str] = set()
    for service in services:
        if missing := required_service - service.keys():
            raise ValueError(f"service is missing: {', '.join(sorted(missing))}")
        parsed = urlparse(service["url"])
        if parsed.scheme != "https" or not parsed.netloc:
            raise ValueError(f"service URL must use HTTPS: {service['url']}")
        if service["url"] in urls:
            raise ValueError(f"duplicate service URL: {service['url']}")
        urls.add(service["url"])


def attributes(item: dict) -> dict:
    return item.get("attributes", item)


def changed(item: dict, desired: dict) -> dict:
    current = attributes(item)
    return {key: value for key, value in desired.items() if current.get(key) != value}


def one(items: list[dict], description: str) -> dict | None:
    if len(items) > 1:
        raise RuntimeError(f"More than one {description} exists")
    return items[0] if items else None


def ensure_monitor(api, service: dict) -> str:
    desired = {
        "url": service["url"],
        "pronounceable_name": service["name"],
        "monitor_type": "keyword",
        "required_keyword": service["keyword"],
        "follow_redirects": True,
        "verify_ssl": True,
        "email": True,
        "check_frequency": 180,
    }
    monitors = api.request("GET", "/monitors").get("data", [])
    monitor = one(
        [item for item in monitors if attributes(item).get("url") == service["url"]],
        f"monitor for {service['url']}",
    )
    if monitor is None:
        monitor = api.request("POST", "/monitors", desired).get("data")
    elif updates := changed(monitor, desired):
        monitor = api.request("PATCH", f"/monitors/{monitor['id']}", updates).get("data")
    return str(monitor["id"])


def ensure_page(api, page_config: dict) -> dict:
    desired = dict(page_config)
    pages = api.request("GET", "/status-pages").get("data", [])
    page = one(
        [item for item in pages if attributes(item).get("subdomain") == desired["subdomain"]],
        f"status page for {desired['subdomain']}",
    )
    if page is None:
        response = api.request("POST", "/status-pages", desired)
        page = response.get("data", response)
    elif updates := changed(page, desired):
        response = api.request("PATCH", f"/status-pages/{page['id']}", updates)
        page = response.get("data", response)
    return page


def activate_fallback(config: dict, api) -> dict[str, str]:
    validate_config(config)
    subdomain = config["status_page"]["subdomain"]
    pages = api.request("GET", "/status-pages").get("data", [])
    page = one(
        [item for item in pages if attributes(item).get("subdomain") == subdomain],
        f"status page for {subdomain}",
    )
    if page is None:
        raise RuntimeError(f"Better Stack status page not found: {subdomain}")
    if attributes(page).get("custom_domain"):
        api.request("PATCH", f"/status-pages/{page['id']}", {"custom_domain": ""})
    return {"fallback_url": f"https://{subdomain}.betteruptime.com"}


def ensure_resource(api, page_id: str, monitor_id: str, service: dict, position: int) -> None:
    path = f"/status-pages/{page_id}/resources"
    desired = {
        "resource_id": monitor_id,
        "resource_type": "Monitor",
        "public_name": service["name"],
        "explanation": service["explanation"],
        "position": position,
        "widget_type": "history",
        "mark_as_down_for": "any_incident",
    }
    resources = api.request("GET", path).get("data", [])
    resource = one(
        [
            item
            for item in resources
            if str(attributes(item).get("resource_id")) == monitor_id
            and attributes(item).get("resource_type") == "Monitor"
        ],
        f"status resource for monitor {monitor_id}",
    )
    if resource is None:
        api.request("POST", path, desired)
    else:
        mutable = {key: value for key, value in desired.items() if key != "resource_id"}
        updates = changed(resource, mutable)
    if resource is not None and updates:
        api.request("PATCH", f"{path}/{resource['id']}", updates)


def ensure_dns(api, dns: dict) -> None:
    zone_query = urlencode({"name": dns["zone"]})
    zones = api.request("GET", f"/zones?{zone_query}").get("result", [])
    zone = one(zones, f"Cloudflare zone named {dns['zone']}")
    if zone is None:
        raise RuntimeError(f"Cloudflare zone not found: {dns['zone']}")

    record_query = urlencode({"name": dns["name"]})
    path = f"/zones/{zone['id']}/dns_records"
    records = api.request("GET", f"{path}?{record_query}").get("result", [])
    record = one(records, f"DNS record named {dns['name']}")
    desired = {
        "type": "CNAME",
        "name": dns["name"],
        "content": dns["target"],
        "proxied": False,
        "ttl": 1,
        "comment": "Managed by scripts/configure_status_page.py",
    }
    if record is None:
        api.request("POST", path, desired)
    elif record.get("type") != "CNAME":
        raise RuntimeError(f"Refusing to replace non-CNAME record: {dns['name']}")
    elif updates := changed(record, desired):
        api.request("PATCH", f"{path}/{record['id']}", updates)


def reconcile(config: dict, better_stack, cloudflare) -> dict[str, str]:
    validate_config(config)
    monitors = [ensure_monitor(better_stack, service) for service in config["services"]]
    page = ensure_page(better_stack, config["status_page"])
    pairs = zip(monitors, config["services"], strict=True)
    for position, (monitor_id, service) in enumerate(pairs):
        ensure_resource(better_stack, str(page["id"]), monitor_id, service, position)
    ensure_dns(cloudflare, config["dns"])
    subdomain = config["status_page"]["subdomain"]
    return {
        "custom_url": f"https://{config['status_page']['custom_domain']}",
        "fallback_url": f"https://{subdomain}.betteruptime.com",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--check", action="store_true", help="validate configuration only")
    parser.add_argument(
        "--fallback",
        action="store_true",
        help="activate the Better Stack hostname by removing the custom domain",
    )
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    validate_config(config)
    if args.check:
        print(f"Valid public status configuration: {args.config}")
        return 0

    better_token = os.environ.get("BETTER_STACK_API_TOKEN")
    if not better_token:
        print("Set BETTER_STACK_API_TOKEN.", file=sys.stderr)
        return 2
    if args.fallback:
        result = activate_fallback(config, JsonClient(BETTER_STACK_API, better_token))
        print(json.dumps(result, indent=2))
        return 0

    cloudflare_token = os.environ.get("CLOUDFLARE_API_TOKEN")
    if not cloudflare_token:
        print("Set CLOUDFLARE_API_TOKEN.", file=sys.stderr)
        return 2
    result = reconcile(
        config,
        JsonClient(BETTER_STACK_API, better_token),
        JsonClient(CLOUDFLARE_API, cloudflare_token),
    )
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
