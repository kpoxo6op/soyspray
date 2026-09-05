# Media helper

The helper supplies the channel catalog, M3U playlist, and XMLTV guide to
Dispatcharr and Jellyfin. It has no database, browser interface, or playback relay.

The native root owns its existing Application and a dedicated project. Keep the
shared media namespace, service name, selectors, network policy, and channel
catalog. The live-TV role now manages only Dispatcharr and Jellyfin. Stopping
that group does not remove this helper.

```sh
make check APP=media-helper
make diff APP=media-helper
make deploy APP=media-helper REVISION=YOUR_PUSHED_BRANCH
make status APP=media-helper FORMAT=json
```

The standard deployment runs the full gate and native Ansible root operation.
After merge, deploy with no revision override to return to HEAD. Verify the exact
Argo comparison and existing resource UIDs. From an allowed consumer, read
`/healthz`, `/api/v1/channels`, `/playlist.m3u`, and `/xmltv.xml`. Check playlist
identities and current guide programmes. End-user playback is a separate Jellyfin
check. Smoke and restore commands report unknown until maintained operations exist.

The app source and channel catalog are in `app/`; Kubernetes manifests are in
`manifests/`. The helper runs from a pinned GHCR image. Source edits build a tested
image and open a separate digest promotion. They cannot change the running app.
Rollback restores a reviewed image through Ansible without deleting shared media
resources or changing credentials.

## Channels and guide

Edit `app/channels.json` to add, disable, or reorder a channel. Keep stable official
pages, direct streams, or upstream identifiers. Do not commit temporary signed
media URLs. Each enabled channel uses `delivery: dispatcharr`. Catalog logos are
static artwork in XMLTV.

The helper downloads IPTVX EPG_LITE at most once every six hours. It keeps only
selected guide identities and replaces the cache only when every required channel
has programmes. Failed refreshes keep the last complete result. Without one,
`/xmltv.xml` returns 503. Reads use the last complete cache while one background refresh runs. Before the
first successful refresh, the guide and the small `/ready` probe return 503
promptly. Readiness keeps an old ready pod available while a new cache warms.
The guide cache is disposable and rebuilt after restart.

Dispatcharr owns stream resolution, failover and buffering. Jellyfin owns playback
and its visible guide. The helper does not invent schedules or relay playback.
Telemiks and 25 Region use live videos from their official pages. Retries cannot
repair an offline source. Keep client playback checks separate from helper health.

## Build and promote

The Dockerfile keeps the exact upstream Python base digest already deployed and
uses only the standard library. It includes both the code and channel catalog.
The image runs as UID 65532 with no installation patches. GitHub builds and tests
it without external network access, then publishes source changes and opens a
draft digest promotion. A source-only merge does not change the running app.

Promotion changes only the digest. Unknown runtime overrides stop promotion for
review. Service names, selectors, resource limits, probes, temporary storage and
security settings are preserved. The workflow never merges or deploys. Roll back
the reviewed digest through the standard Ansible operation.

`make check APP=media-helper` checks source behavior, cache concurrency, promotion
safety and existing consumer contracts. Docker is needed only for the image and
real-entrypoint checks; GitHub runs them when Docker is unavailable locally.
