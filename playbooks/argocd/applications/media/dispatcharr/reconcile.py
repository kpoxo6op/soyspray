import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request


BASE = "http://dispatcharr.media.svc.cluster.local:9191/api"
CATALOG_URL = "http://media-helper.media.svc.cluster.local:8080/api/v1/channels"
MANAGED_ACCOUNT = "Managed live TV"
MANAGED_GUIDE = "Managed live TV guide"
MANAGED_PROFILE = "Managed Streamlink"
TERMINAL_REFRESH_STATES = {"success", "pending_setup"}


def request(path, method="GET", payload=None, token=None, base=BASE, timeout=30):
    data = json.dumps(payload).encode() if payload is not None else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(base + path, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as response:
        raw = response.read()
        return json.loads(raw) if raw else None


def rows(path, token):
    result = request(path, token=token)
    return result.get("results", []) if isinstance(result, dict) else result


def upsert(path, name, payload, token):
    existing = next((row for row in rows(path, token) if row["name"] == name), None)
    if existing:
        return request(f"{path}{existing['id']}/", "PATCH", payload, token)
    return request(path, "POST", {"name": name, **payload}, token)


def refresh_marker(account):
    return account.get("status"), account.get("updated_at"), account.get("last_message")


def refresh_account(account, token, timeout=180):
    before = refresh_marker(account)
    request(f"/m3u/refresh/{account['id']}/", "POST", {}, token)
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        current = request(f"/m3u/accounts/{account['id']}/", token=token)
        status = current.get("status")
        if status == "error":
            raise RuntimeError(current.get("last_message") or "Dispatcharr M3U refresh failed")
        if status in TERMINAL_REFRESH_STATES and refresh_marker(current) != before:
            return current
        time.sleep(2)
    raise RuntimeError("Dispatcharr M3U refresh timed out")


def source_ids(channel):
    streams = channel.get("streams", [])
    return [item["id"] if isinstance(item, dict) else item for item in streams]


def effective(channel, field):
    value = channel.get(f"effective_{field}")
    return channel.get(field) if value is None else value


def channel_values(definition, profile_id):
    return {
        "name": definition["name"],
        "channel_number": definition["number"],
        "tvg_id": definition["guide"]["id"],
        "stream_profile_id": profile_id,
    }


def configure_channel(channel, stream_ids, definition, profile_id, token):
    values = channel_values(definition, profile_id)
    payload = {"streams": list(dict.fromkeys(stream_ids))}
    if channel.get("auto_created"):
        payload["override"] = values
    else:
        payload.update(values)
    return request(f"/channels/channels/{channel['id']}/", "PATCH", payload, token)


def create_channel(stream_ids, matching_streams, definition, account_id, profile_id, token):
    channel_group_id = matching_streams[0].get("channel_group")
    if channel_group_id is None:
        raise RuntimeError(f"Dispatcharr did not assign a group for {definition['slug']}")
    values = {
        "name": definition["name"],
        "channel_number": definition["number"],
        "channel_group_id": channel_group_id,
        "tvg_id": definition["guide"]["id"],
        "streams": list(dict.fromkeys(stream_ids)),
        "auto_created": True,
        "auto_created_by": account_id,
        "override": channel_values(definition, profile_id),
    }
    return request("/channels/channels/", "POST", values, token)


def reconcile_channels(catalog, account, token, profile_ids):
    account_id = account["id"]
    query = urllib.parse.urlencode({"m3u_account": account_id, "page_size": 10000})
    streams = rows(f"/channels/streams/?{query}", token)
    channels = rows(
        "/channels/channels/?include_streams=true&visibility_filter=all&page_size=10000",
        token,
    )
    managed_streams = {stream["id"]: stream for stream in streams}
    expected_stream_ids = set()
    retained_channel_ids = set()
    deleted_channel_ids = set()

    for definition in catalog["channels"]:
        if not definition.get("enabled") or definition.get("delivery") != "dispatcharr":
            continue
        source_types = {source["type"] for source in definition["sources"]}
        profile_key = "streamlink_page" if "streamlink_page" in source_types else "direct_hls"
        profile_id = profile_ids[profile_key]
        expected_urls = [source["url"] for source in definition["sources"]]
        matching = [
            stream
            for url in expected_urls
            for stream in streams
            if stream.get("url") == url
            and stream.get("tvg_id") == definition["guide"]["id"]
            and stream.get("m3u_account") == account_id
            and not stream.get("is_stale")
        ]
        if len(matching) != len(expected_urls):
            raise RuntimeError(f"Dispatcharr did not import every source for {definition['slug']}")

        ordered_ids = [stream["id"] for stream in matching]
        expected = set(ordered_ids)
        expected_stream_ids.update(expected)
        candidates = [
            channel
            for channel in channels
            if channel.get("auto_created_by") == account_id
            and (
                set(source_ids(channel)) & expected
                or effective(channel, "name") == definition["name"]
            )
        ]
        if not candidates:
            created = create_channel(
                ordered_ids,
                matching,
                definition,
                account_id,
                profile_id,
                token,
            )
            retained_channel_ids.add(created["id"])
            continue
        canonical = min(
            candidates,
            key=lambda channel: (
                effective(channel, "channel_number") != definition["number"],
                channel["id"],
            ),
        )
        custom_ids = []
        for candidate in candidates:
            for stream_id in source_ids(candidate):
                if stream_id not in managed_streams and stream_id not in custom_ids:
                    custom_ids.append(stream_id)
        configure_channel(canonical, ordered_ids + custom_ids, definition, profile_id, token)
        retained_channel_ids.add(canonical["id"])

        for extra in candidates:
            if extra["id"] == canonical["id"]:
                continue
            request(f"/channels/channels/{extra['id']}/", "DELETE", token=token)
            deleted_channel_ids.add(extra["id"])

    for channel in channels:
        linked = set(source_ids(channel))
        if (
            channel.get("auto_created_by") == account_id
            and channel["id"] not in retained_channel_ids
            and channel["id"] not in deleted_channel_ids
            and linked
            and linked.isdisjoint(expected_stream_ids)
            and linked <= managed_streams.keys()
            and all(managed_streams[stream_id].get("is_stale") for stream_id in linked)
        ):
            request(f"/channels/channels/{channel['id']}/", "DELETE", token=token)


def disable_group_sync(account, token):
    groups = account.get("channel_groups", [])
    if not groups:
        return
    request(
        f"/m3u/accounts/{account['id']}/group-settings/",
        "PATCH",
        {
            "group_settings": [
                {
                    "channel_group": group["channel_group"],
                    "enabled": group.get("enabled", True),
                    "auto_channel_sync": False,
                    "auto_sync_channel_start": group.get("auto_sync_channel_start"),
                    "auto_sync_channel_end": group.get("auto_sync_channel_end"),
                    "custom_properties": group.get("custom_properties"),
                }
                for group in groups
            ]
        },
        token,
    )


def require_url_hash(stream_settings):
    if stream_settings["value"].get("m3u_hash_key") != "url":
        raise RuntimeError("Dispatcharr must use URL stream identity")


def lineup_matches(catalog, lineup):
    expected = [
        channel
        for channel in catalog["channels"]
        if channel.get("enabled") and channel.get("delivery") == "dispatcharr"
    ]
    for channel in expected:
        named = [item for item in lineup if item.get("GuideName") == channel["name"]]
        numbered = [
            item for item in lineup if str(item.get("GuideNumber")) == str(channel["number"])
        ]
        if len(named) != 1 or len(numbered) != 1 or named[0] is not numbered[0]:
            return False
    return True


def wait_for_lineup(catalog, timeout=120):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(
                "http://dispatcharr.media.svc.cluster.local:9191/hdhr/lineup.json",
                timeout=5,
            ) as response:
                if lineup_matches(catalog, json.load(response)):
                    return
        except (urllib.error.URLError, ValueError):
            pass
        time.sleep(2)
    raise RuntimeError("Dispatcharr did not publish the managed lineup")


def initialize():
    for attempt in range(30):
        try:
            request(
                "/accounts/initialize-superuser/",
                "POST",
                {
                    "username": os.environ["DISPATCHARR_ADMIN_USER"],
                    "password": os.environ["DISPATCHARR_ADMIN_PASSWORD"],
                },
            )
            return
        except urllib.error.HTTPError as error:
            if error.code in (400, 409):
                return
            raise
        except urllib.error.URLError:
            if attempt == 29:
                raise
            time.sleep(2)


def main():
    initialize()
    token = request(
        "/accounts/token/",
        "POST",
        {
            "username": os.environ["DISPATCHARR_ADMIN_USER"],
            "password": os.environ["DISPATCHARR_ADMIN_PASSWORD"],
        },
    )["access"]

    profile = upsert(
        "/core/streamprofiles/",
        MANAGED_PROFILE,
        {
            "command": "streamlink",
            "parameters": (
                "--plugin-dir /opt/streamlink-plugins --stdout "
                "--stream-segment-threads 2 {streamUrl} "
                "720p50,720p,480p50,480p,best"
            ),
            "is_active": True,
        },
        token,
    )
    ffmpeg_profile = next(
        (
            item
            for item in rows("/core/streamprofiles/", token)
            if item["name"] == "ffmpeg" and item.get("locked")
        ),
        None,
    )
    if ffmpeg_profile is None:
        raise RuntimeError("Dispatcharr built-in FFmpeg profile is unavailable")

    settings = rows("/core/settings/", token)
    stream_settings = next(item for item in settings if item["key"] == "stream_settings")
    require_url_hash(stream_settings)
    proxy_settings = next(item for item in settings if item["key"] == "proxy_settings")
    request(
        f"/core/settings/{proxy_settings['id']}/",
        "PATCH",
        {
            "value": {
                **proxy_settings["value"],
                "channel_shutdown_delay": 15,
                "new_client_behind_seconds": 20,
            }
        },
        token,
    )

    account = upsert(
        "/m3u/accounts/",
        MANAGED_ACCOUNT,
        {
            "server_url": "http://media-helper.media.svc.cluster.local:8080/playlist.m3u",
            "is_active": True,
            "max_streams": 0,
            "refresh_interval": 60,
            "account_type": "STD",
            "auto_enable_new_groups_live": True,
        },
        token,
    )
    disable_group_sync(account, token)
    account = refresh_account(account, token)
    disable_group_sync(account, token)
    catalog = request("", base=CATALOG_URL, timeout=90)
    reconcile_channels(
        catalog,
        account,
        token,
        {"direct_hls": ffmpeg_profile["id"], "streamlink_page": profile["id"]},
    )

    upsert(
        "/epg/sources/",
        MANAGED_GUIDE,
        {
            "source_type": "xmltv",
            "url": "http://media-helper.media.svc.cluster.local:8080/xmltv.xml",
            "is_active": True,
            "refresh_interval": 60,
        },
        token,
    )
    wait_for_lineup(catalog)


if __name__ == "__main__":
    main()
