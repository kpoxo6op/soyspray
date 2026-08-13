from __future__ import annotations

import json
from copy import deepcopy

from conftest import ROOT
from test_runtime_tools import load_module


class FakeBetterStack:
    def __init__(self) -> None:
        self.monitors: list[dict] = []
        self.pages: list[dict] = []
        self.resources: dict[str, list[dict]] = {}
        self.mutations: list[tuple[str, str]] = []
        self.next_id = 1

    def request(self, method: str, path: str, payload: dict | None = None) -> dict:
        payload = deepcopy(payload or {})
        if method != "GET":
            self.mutations.append((method, path))
        if path == "/monitors" and method == "GET":
            return {"data": self.monitors}
        if path == "/monitors" and method == "POST":
            item = self._new("monitor", payload)
            self.monitors.append(item)
            return {"data": item}
        if path.startswith("/monitors/") and method == "PATCH":
            return {"data": self._update(self.monitors, path, payload)}
        if path == "/status-pages" and method == "GET":
            return {"data": self.pages}
        if path == "/status-pages" and method == "POST":
            item = self._new("status_page", payload)
            self.pages.append(item)
            self.resources[item["id"]] = []
            return {"data": item}
        if path.count("/") == 2 and path.startswith("/status-pages/") and method == "PATCH":
            return {"data": self._update(self.pages, path, payload)}
        if path.endswith("/resources") and method == "GET":
            return {"data": self.resources[path.split("/")[2]]}
        if path.endswith("/resources") and method == "POST":
            page_id = path.split("/")[2]
            payload["resource_id"] = int(payload["resource_id"])
            item = self._new("status_page_resource", payload)
            self.resources[page_id].append(item)
            return {"data": item}
        if "/resources/" in path and method == "PATCH":
            page_id = path.split("/")[2]
            return {"data": self._update(self.resources[page_id], path, payload)}
        raise AssertionError(f"Unexpected Better Stack request: {method} {path}")

    def _new(self, item_type: str, attributes: dict) -> dict:
        item = {"id": str(self.next_id), "type": item_type, "attributes": attributes}
        self.next_id += 1
        return item

    @staticmethod
    def _update(items: list[dict], path: str, attributes: dict) -> dict:
        item_id = path.rsplit("/", 1)[-1]
        item = next(item for item in items if item["id"] == item_id)
        item["attributes"].update(attributes)
        return item


class FakeCloudflare:
    def __init__(self) -> None:
        self.records: list[dict] = []

    def request(self, method: str, path: str, payload: dict | None = None) -> dict:
        payload = deepcopy(payload or {})
        if path == "/zones?name=soyspray.vip" and method == "GET":
            return {"result": [{"id": "zone-1", "name": "soyspray.vip"}]}
        if path == "/zones/zone-1/dns_records?name=status.soyspray.vip" and method == "GET":
            return {"result": self.records}
        if path == "/zones/zone-1/dns_records" and method == "POST":
            item = {"id": "record-1", **payload}
            self.records.append(item)
            return {"result": item}
        if path == "/zones/zone-1/dns_records/record-1" and method == "PATCH":
            self.records[0].update(payload)
            return {"result": self.records[0]}
        raise AssertionError(f"Unexpected Cloudflare request: {method} {path}")


def test_reconcile_creates_extendable_status_page_without_duplicates() -> None:
    status = load_module("configure_status_page", ROOT / "scripts/configure_status_page.py")
    config = json.loads((ROOT / "platform/public-status.json").read_text())
    config["services"].append(
        {
            "name": "Future service",
            "url": "https://future.soyspray.vip/",
            "keyword": "Future service",
            "explanation": "A second service proves that the list is extendable.",
        }
    )
    better_stack = FakeBetterStack()
    cloudflare = FakeCloudflare()

    first = status.reconcile(config, better_stack, cloudflare)
    mutation_count = len(better_stack.mutations)
    second = status.reconcile(config, better_stack, cloudflare)

    assert (
        first
        == second
        == {
            "custom_url": "https://status.soyspray.vip",
            "fallback_url": "https://soyspray-status.betteruptime.com",
        }
    )
    assert len(better_stack.monitors) == 2
    assert len(better_stack.pages) == 1
    assert len(better_stack.mutations) == mutation_count
    page = better_stack.pages[0]
    assert page["attributes"]["automatic_reports"] is True
    assert page["attributes"]["custom_domain"] == "status.soyspray.vip"
    assert "subscribable" not in page["attributes"]
    assert len(better_stack.resources[page["id"]]) == 2
    autism_monitor = better_stack.monitors[0]["attributes"]
    assert autism_monitor["url"] == "https://autism.soyspray.vip/"
    assert autism_monitor["monitor_type"] == "keyword"
    assert autism_monitor["required_keyword"] == "Detailed autism questionnaire"
    assert cloudflare.records == [
        {
            "id": "record-1",
            "type": "CNAME",
            "name": "status.soyspray.vip",
            "content": "statuspage.betteruptime.com",
            "proxied": False,
            "ttl": 1,
            "comment": "Managed by scripts/configure_status_page.py",
        }
    ]
