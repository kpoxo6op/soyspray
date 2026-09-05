"""Check the real container entrypoint with no external network access."""

import json
import os
import time
import urllib.error
import urllib.request

assert os.geteuid() == 65532
base = "http://127.0.0.1:8080"
for attempt in range(30):
    try:
        with urllib.request.urlopen(base + "/healthz", timeout=2) as response:
            assert response.status == 200
        break
    except urllib.error.URLError:
        if attempt == 29:
            raise
        time.sleep(1)
with urllib.request.urlopen(base + "/api/v1/channels", timeout=2) as response:
    catalog = json.load(response)
with urllib.request.urlopen(base + "/playlist.m3u", timeout=2) as response:
    playlist = response.read().decode()
assert playlist.startswith("#EXTM3U")
for channel in catalog["channels"]:
    if channel["enabled"]:
        assert f'tvg-id="{channel["guide"]["id"]}"' in playlist
for path, status in [("/xmltv.xml", 503), ("/ready", 503), ("/", 404)]:
    try:
        urllib.request.urlopen(base + path, timeout=2)
        raise AssertionError(f"{path} must return {status}")
    except urllib.error.HTTPError as error:
        assert error.code == status
print(
    "Unprivileged entrypoint serves health, catalog and playlist; guide fails promptly without upstream access."
)
