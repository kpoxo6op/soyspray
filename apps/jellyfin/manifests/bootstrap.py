import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

BASE = "http://jellyfin.media.svc.cluster.local:8096"
DISPATCHARR_LINEUP = "http://dispatcharr.media.svc.cluster.local:9191/hdhr/lineup.json"
AUTH = (
    'MediaBrowser Client="soyspray-bootstrap", Device="argo-job", DeviceId="bootstrap", Version="1"'
)


def call(method, path, body=None, token=None):
    headers = {"Authorization": AUTH + (f', Token="{token}"' if token else "")}
    if token:
        headers["X-Emby-Token"] = token
    data = json.dumps(body).encode() if body is not None else None
    if data:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=30) as response:
        raw = response.read()
        return json.loads(raw) if raw else None


def lineups_match(dispatcharr, jellyfin):
    expected = {(item.get("GuideName"), str(item.get("GuideNumber"))) for item in dispatcharr}
    current = {(item.get("Name"), str(item.get("Number"))) for item in jellyfin}
    return bool(expected) and current == expected


def guide_refresh_required(dispatcharr, jellyfin):
    return not lineups_match(dispatcharr, jellyfin) or any(
        not item.get("ImageTags", {}).get("Primary") for item in jellyfin
    )


def get_dispatcharr_lineup():
    with urllib.request.urlopen(DISPATCHARR_LINEUP, timeout=30) as response:
        return json.load(response)


def qsv_configuration(current):
    desired = dict(current)
    desired.update(
        {
            "HardwareAccelerationType": "qsv",
            "EnableHardwareEncoding": True,
            "QsvDevice": "/dev/dri/renderD128",
        }
    )
    return desired


def scheduled_task(token, key):
    tasks = call("GET", "/ScheduledTasks", token=token)
    return next(item for item in tasks if item.get("Key") == key)


def refresh_guide(token, timeout=900):
    task = scheduled_task(token, "RefreshGuide")
    previous = task.get("LastExecutionResult", {})
    previous_start = previous.get("StartTimeUtc")
    call("POST", f"/ScheduledTasks/Running/{task['Id']}", token=token)
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        task = scheduled_task(token, "RefreshGuide")
        result = task.get("LastExecutionResult") or {}
        if task.get("State") == "Idle" and result.get("StartTimeUtc") != previous_start:
            if result.get("Status") == "Completed":
                return
            raise RuntimeError(result.get("ErrorMessage") or "Jellyfin guide refresh failed")
        time.sleep(2)
    raise RuntimeError("Jellyfin guide refresh timed out")


for attempt in range(60):
    try:
        call("GET", "/System/Info/Public")
        break
    except OSError:
        if attempt == 59:
            raise RuntimeError("Jellyfin did not become ready")
        time.sleep(2)

try:
    call("GET", "/Startup/User")
except urllib.error.HTTPError as error:
    if error.code not in (400, 401, 404):
        raise
else:
    call(
        "POST",
        "/Startup/Configuration",
        {
            "ServerName": "soyspray-jellyfin",
            "UICulture": "ru-RU",
            "MetadataCountryCode": "NZ",
            "PreferredMetadataLanguage": "ru",
        },
    )
    call(
        "POST",
        "/Startup/User",
        {
            "Name": os.environ["JELLYFIN_ADMIN_USER"],
            "Password": os.environ["JELLYFIN_ADMIN_PASSWORD"],
        },
    )
    call("POST", "/Startup/Complete", {})

token = call(
    "POST",
    "/Users/AuthenticateByName",
    {"Username": os.environ["JELLYFIN_ADMIN_USER"], "Pw": os.environ["JELLYFIN_ADMIN_PASSWORD"]},
)["AccessToken"]
encoding = call("GET", "/System/Configuration/encoding", token=token)
desired_encoding = qsv_configuration(encoding)
if desired_encoding != encoding:
    call("POST", "/System/Configuration/encoding", desired_encoding, token=token)
plugin_path = "/Plugins/505ce9d1-d916-42fa-86ca-673ef241d7df/Configuration"
plugin = call("GET", plugin_path, token=token)
if not plugin.get("ManageLoginPageButtons"):
    plugin["ManageLoginPageButtons"] = True
    call("POST", plugin_path, plugin, token)
users = call("GET", "/Users", token=token)
if not any(user["Name"] == os.environ["JELLYFIN_PLAYBACK_USER"] for user in users):
    call(
        "POST",
        "/Users/New",
        {
            "Name": os.environ["JELLYFIN_PLAYBACK_USER"],
            "Password": os.environ["JELLYFIN_PLAYBACK_PASSWORD"],
        },
        token,
    )
    users = call("GET", "/Users", token=token)
folders = call("GET", "/Library/VirtualFolders", token=token)
if not any(folder["Name"] == "Cartoons" for folder in folders):
    query = urllib.parse.urlencode(
        {
            "name": "Cartoons",
            "collectionType": "movies",
            "paths": "/media/Русские мультфильмы",
            "refreshLibrary": "true",
        }
    )
    call(
        "POST",
        "/Library/VirtualFolders?" + query,
        {
            "PreferredMetadataLanguage": "ru",
            "MetadataCountryCode": "RU",
            "EnableRealtimeMonitor": False,
        },
        token,
    )
live_tv = call("GET", "/System/Configuration/livetv", token=token)
tuners = live_tv.get("TunerHosts", [])
providers = live_tv.get("ListingProviders", [])
if not any(
    item.get("Url") == "http://dispatcharr.media.svc.cluster.local:9191/hdhr" for item in tuners
):
    call(
        "POST",
        "/LiveTv/TunerHosts",
        {
            "Type": "hdhomerun",
            "Url": "http://dispatcharr.media.svc.cluster.local:9191/hdhr",
            "FriendlyName": "Dispatcharr",
            "ImportFavoritesOnly": False,
            "AllowHWTranscoding": True,
        },
        token,
    )

if not any(
    item.get("Path") == "http://media-helper.media.svc.cluster.local:8080/xmltv.xml"
    for item in providers
):
    call(
        "POST",
        "/LiveTv/ListingProviders",
        {
            "Type": "xmltv",
            "Path": "http://media-helper.media.svc.cluster.local:8080/xmltv.xml",
            "ListingsId": "Managed live TV guide",
            "EnableAllTuners": True,
        },
        token,
    )

dispatcharr_lineup = get_dispatcharr_lineup()
jellyfin_lineup = call(
    "GET", "/LiveTv/Channels?limit=100&EnableImages=true", token=token
).get("Items", [])
if guide_refresh_required(dispatcharr_lineup, jellyfin_lineup):
    refresh_guide(token)
    jellyfin_lineup = call(
        "GET", "/LiveTv/Channels?limit=100&EnableImages=true", token=token
    ).get("Items", [])
    if not lineups_match(dispatcharr_lineup, jellyfin_lineup):
        raise RuntimeError("Jellyfin did not publish the Dispatcharr channel numbers")
