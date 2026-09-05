from __future__ import annotations

import gzip
import json
import os
import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).parent
SIGNED = re.compile(r"(?:token|signature|expires|policy|key-pair-id)=", re.I)
EPG_LITE_URL = "https://iptvx.one/EPG_LITE"
EPG_CACHE_SECONDS = 6 * 60 * 60
EPG_FAILURE_RETRY_SECONDS = 5 * 60
GUIDE_CACHE = {"expires_at": 0.0, "retry_at": 0.0, "xml": None, "programmes": None}
GUIDE_LOCK = threading.Lock()
GUIDE_REFRESH_LOCK = threading.Lock()
GUIDE_REFRESHING = False


class GuideUnavailable(RuntimeError):
    pass


def validate_catalog(catalog: dict) -> None:
    seen = {"slug": set(), "number": set(), "guide id": set()}
    for channel in catalog["channels"]:
        if channel["delivery"] != "dispatcharr":
            raise ValueError(f"unsupported delivery: {channel['delivery']}")
        values = {
            "slug": channel["slug"],
            "number": channel["number"],
            "guide id": channel["guide"]["id"],
        }
        for label, value in values.items():
            if value in seen[label]:
                raise ValueError(f"duplicate {label}: {value}")
            seen[label].add(value)
        for source in channel["sources"]:
            if source["type"] not in {"direct_hls", "streamlink_page"}:
                raise ValueError(f"unsupported source: {source['type']}")
            if SIGNED.search(source["url"]):
                raise ValueError(f"signed URL is not allowed: {channel['slug']}")


def load_catalog(path: Path = ROOT / "channels.json") -> dict:
    catalog = json.loads(path.read_text(encoding="utf-8"))
    validate_catalog(catalog)
    return catalog


def dispatcharr_channels(catalog: dict) -> list[dict]:
    return [c for c in catalog["channels"] if c["enabled"] and c["delivery"] == "dispatcharr"]


def build_playlist(catalog: dict, base_url: str) -> str:
    lines = ['#EXTM3U x-tvg-url="%s/xmltv.xml"' % base_url]
    for channel in dispatcharr_channels(catalog):
        guide_id = channel["guide"]["id"]
        identity = (
            f'#EXTINF:-1 tvg-id="{guide_id}" tvg-chno="{channel["number"]}" '
            f'tvg-logo="{channel["logo"]}" group-title="{channel["groups"][0]}",{channel["name"]}'
        )
        for source in channel["sources"]:
            lines += [identity, source["url"]]
    return "\n".join(lines) + "\n"


def build_xmltv(catalog: dict, programmes: dict[str, list[dict]]) -> str:
    tv = ET.Element("tv", {"generator-info-name": "media-helper"})
    for channel in dispatcharr_channels(catalog):
        guide_id = channel["guide"]["id"]
        node = ET.SubElement(tv, "channel", {"id": guide_id})
        ET.SubElement(node, "display-name").text = channel["name"]
        if channel["logo"]:
            ET.SubElement(node, "icon", {"src": channel["logo"]})
        for item in programmes.get(channel["slug"], []):
            show = ET.SubElement(tv, "programme", {"channel": guide_id, **item["times"]})
            ET.SubElement(show, "title").text = item["title"]
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(tv, encoding="unicode")


def epg_channels(catalog: dict) -> list[dict]:
    return [
        channel
        for channel in dispatcharr_channels(catalog)
        if channel["guide"]["source"] == "iptvx_epg_lite"
    ]


def parse_epg_lite(source, catalog: dict) -> dict[str, list[dict]]:
    selected = {channel["guide"]["id"]: channel["slug"] for channel in epg_channels(catalog)}
    programmes = {slug: [] for slug in selected.values()}
    with gzip.GzipFile(fileobj=source) as uncompressed:
        events = ET.iterparse(uncompressed, events=("start", "end"))
        _, root = next(events)
        for event, element in events:
            if event != "end" or element.tag != "programme":
                continue
            slug = selected.get(element.get("channel"))
            title = element.findtext("title")
            start = element.get("start")
            stop = element.get("stop")
            if slug and title and start and stop:
                programmes[slug].append(
                    {"times": {"start": start, "stop": stop}, "title": title.strip()}
                )
            element.clear()
            root.clear()
    return programmes


def fetch_epg_lite(catalog: dict) -> dict[str, list[dict]]:
    request = urllib.request.Request(
        os.getenv("EPG_LITE_URL", EPG_LITE_URL),
        headers={"User-Agent": "media-helper/1"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return parse_epg_lite(response, catalog)


def guide_snapshot(catalog: dict, now=None) -> tuple[str, dict[str, list[dict]]]:
    clock = time.monotonic() if now is None else now
    with GUIDE_LOCK:
        if GUIDE_CACHE["xml"] is not None and clock < GUIDE_CACHE["expires_at"]:
            return GUIDE_CACHE["xml"], GUIDE_CACHE["programmes"]
        if clock < GUIDE_CACHE["retry_at"]:
            if GUIDE_CACHE["xml"] is not None:
                return GUIDE_CACHE["xml"], GUIDE_CACHE["programmes"]
            raise GuideUnavailable("programme guide is unavailable")
        try:
            programmes = fetch_epg_lite(catalog)
            missing = [
                channel["slug"]
                for channel in epg_channels(catalog)
                if not programmes.get(channel["slug"])
            ]
            if missing:
                raise GuideUnavailable("guide has no programmes for " + ", ".join(missing))
            xml = build_xmltv(catalog, programmes)
        except (
            OSError,
            ValueError,
            gzip.BadGzipFile,
            ET.ParseError,
            urllib.error.URLError,
        ) as error:
            GUIDE_CACHE["retry_at"] = clock + EPG_FAILURE_RETRY_SECONDS
            if GUIDE_CACHE["xml"] is not None:
                return GUIDE_CACHE["xml"], GUIDE_CACHE["programmes"]
            raise GuideUnavailable("programme guide is unavailable") from error
        except GuideUnavailable:
            GUIDE_CACHE["retry_at"] = clock + EPG_FAILURE_RETRY_SECONDS
            if GUIDE_CACHE["xml"] is not None:
                return GUIDE_CACHE["xml"], GUIDE_CACHE["programmes"]
            raise
        GUIDE_CACHE.update(
            {
                "expires_at": clock + EPG_CACHE_SECONDS,
                "retry_at": 0.0,
                "xml": xml,
                "programmes": programmes,
            }
        )
        return xml, programmes


def start_guide_refresh(catalog: dict) -> None:
    global GUIDE_REFRESHING
    with GUIDE_REFRESH_LOCK:
        if GUIDE_REFRESHING:
            return
        GUIDE_REFRESHING = True

    def refresh() -> None:
        global GUIDE_REFRESHING
        try:
            guide_snapshot(catalog)
        except GuideUnavailable:
            pass
        finally:
            with GUIDE_REFRESH_LOCK:
                GUIDE_REFRESHING = False

    threading.Thread(target=refresh, name="guide-refresh", daemon=True).start()


class Handler(BaseHTTPRequestHandler):
    catalog = load_catalog()

    def send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        service_url = os.getenv(
            "MEDIA_HELPER_URL", "http://media-helper.media.svc.cluster.local:8080"
        )
        request_path = urllib.parse.urlsplit(self.path).path
        if request_path == "/healthz":
            return self.send(200, b"ok\n", "text/plain")
        if request_path == "/playlist.m3u":
            playlist = build_playlist(self.catalog, service_url).encode()
            return self.send(200, playlist, "audio/x-mpegurl")
        if request_path == "/xmltv.xml":
            try:
                guide, _ = guide_snapshot(self.catalog)
            except GuideUnavailable:
                return self.send(503, b"programme guide unavailable\n", "text/plain")
            return self.send(200, guide.encode(), "application/xml")
        if request_path == "/api/v1/channels":
            body = json.dumps(self.catalog, ensure_ascii=False).encode()
            return self.send(200, body, "application/json")
        return self.send(404, b"not found\n", "text/plain")

if __name__ == "__main__":
    start_guide_refresh(Handler.catalog)
    ThreadingHTTPServer(("0.0.0.0", 8080), Handler).serve_forever()
