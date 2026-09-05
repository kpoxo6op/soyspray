# Media helper

The helper supplies the channel catalog, M3U playlist, and XMLTV guide to
Dispatcharr and Jellyfin. It has no database, browser interface, or playback relay.
The existing [runtime guide](../../playbooks/argocd/applications/media/media-helper/README.md)
explains channel editing, guide caching, and upstream limits.

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

For this adoption only, first run `apps/media-helper/adopt.yml` through the
inventory and privilege options in AGENTS.md, with `--check`, then without it.
The operation requires the known idle Application and removes only Argo cascade
finalizers. It tests resourceVersion and preserves unrelated finalizers. Repeat
it before the native preview to verify that no further change is needed.

Keep the old source definitions until this adoption is deployed and verified.
The runtime still uses its existing ConfigMap in this step. Image packaging and
source colocation follow separately. Rollback restores a reviewed source through
Ansible without deleting the shared namespace or changing the catalog.
