"""Check an isolated Boys image through its HTTP interface."""

import http.cookiejar
import json
import os
import time
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8080"
client = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))


def request(path, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    request = urllib.request.Request(
        BASE + path,
        data=data,
        headers={"Content-Type": "application/json"} if data else {},
    )
    with client.open(request, timeout=5) as response:
        return json.load(response)


for attempt in range(20):
    try:
        with client.open(BASE + "/ready", timeout=2) as response:
            assert response.status == 200
        break
    except urllib.error.URLError:
        if attempt == 19:
            raise
        time.sleep(0.5)

assert request("/api/session") == {"authenticated": False}
try:
    request("/api/availability")
except urllib.error.HTTPError as error:
    assert error.code == 401
else:
    raise AssertionError("Availability must require a session")

crew = request("/api/crew")
assert len(crew["crew"]) == 9
name = crew["crew"][0]["name"]
request("/api/claim", {"name": name, "seed_pin": os.environ["BOYS_PIN"], "pin": "5678"})
assert request("/api/session") == {"authenticated": True}
assert request("/api/availability")["me"] == name
request("/api/logout", {})
assert request("/api/session") == {"authenticated": False}
request("/api/session", {"name": name, "pin": "5678"})
assert request("/api/availability")["me"] == name
with client.open(BASE + "/", timeout=5) as response:
    assert b"<!doctype html>" in response.read().lower()
print("Boys image: readiness, authentication, claim, login, session, and static assets passed.")
