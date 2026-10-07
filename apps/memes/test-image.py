"""Container HTTP check with generated catalog and no production access."""

import http.cookiejar
import importlib.util
import json
import time
import urllib.error
import urllib.request

from memes.store import Store

assert importlib.util.find_spec("torch") is None
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
base = "http://127.0.0.1:8080"
for _attempt in range(60):
    try:
        health = json.load(opener.open(base + "/healthz"))
        break
    except OSError:
        time.sleep(0.5)
else:
    raise AssertionError("No healthy HTTP server")
assert health["ok"] and health["catalog_count"] == 300
store = Store("/data")
token = store.invite("isolated image fixture")
opener.open(base + "/t/" + token).read()
head = json.load(opener.open(base + "/api/feed"))["items"][0]
assert opener.open(base + head["image"]).headers.get_content_type() == "image/jpeg"
for path, extra in [
    ("render", {}),
    ("action", {"action": "like", "hidden_ms": 0, "client_seq": 1}),
]:
    req = urllib.request.Request(
        base + "/api/" + path,
        json.dumps({"impression_id": head["impression_id"], **extra}).encode(),
        {"Content-Type": "application/json", "Origin": base},
    )
    assert len(json.load(opener.open(req))["items"]) == 3
assert json.load(opener.open(base + "/api/results"))["warmup"]["likes"] == 1
print("IMAGE_HTTP_OK: private image, persisted action, two queued, results")
