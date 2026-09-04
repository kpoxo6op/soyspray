# Jellyfin

Jellyfin provides cartoons and native Live TV at `https://tv.soyspray.vip`. It runs the official digest-pinned Jellyfin image and its stock Web interface. There is no local Web patch.

## Normal use

Use Jellyfin Web for administration, browser playback, SSO, and Quick Connect approval. Browser users select the Authentik sign-in option. Native clients use Quick Connect or the local playback account.

The bootstrap adds `Cartoons` at `/media/Русские мультфильмы`, preserves unknown libraries, configures Intel Quick Sync, and connects Jellyfin to Dispatcharr and Media Helper. It does not rewrite Home sections or other display preferences.

Jellyfin gets the Live TV lineup from Dispatcharr's HDHomeRun interface. Programme data and static channel artwork come from Media Helper XMLTV. Open Jellyfin's native `Live TV` and `Guide` screens to browse channels and schedules.

The future television client is the official Android TV application. See [the Android TV plan](../../../../../soydocs/android-tv/README.md). Do not add television-specific UI code before a real device is available.

## Access and storage

The pinned Community SSO plugin supplies Authentik OIDC. Members of `media-users` can play media and Live TV. Only `cluster-admins` receive Jellyfin administrator rights. Secrets stay outside Git. Local accounts remain available for recovery.

The ingress accepts only LAN, Tailscale, and cluster traffic. It does not use Authentik forward authentication because native-client APIs must remain available.

The protected `jellyfin-config-v2` claim stores configuration. The database uses node-0 storage at `/srv/media/jellyfin-data`. The `media-downloads` claim is read-only. Jellyfin receives only `/dev/dri/renderD128` for Intel transcoding.

## Checks

```bash
kubectl kustomize playbooks/argocd/applications/media/jellyfin
kubectl -n argocd get application jellyfin
kubectl -n media get deployment,pod,pvc,service,ingress
```

Confirm that the pod runs on `node-0`, the image is digest-pinned, and `/dev/dri/renderD128` is present. Test Authentik login, Quick Connect, cartoon scanning, direct play, one lower-bitrate transcode, channel playback, and the native Guide.

Run the bootstrap twice. Confirm that it does not duplicate libraries, tuners, guide sources, or accounts and does not delete unknown configuration.

## Limits

The official Web and Android TV clients control their own layouts. This repository does not patch either client. Programme text is unavailable when the upstream guide has no matching entry. Lower playback quality can reduce client bitrate through Intel transcoding, but it cannot repair a broken upstream stream.

The SSO plugin is a pinned beta community component. Local login remains the recovery path. The node-local database and render group ID are specific to `node-0`.

## Shutdown and rollback

```bash
LIVE_TV_ENABLED=false LIVE_TV_REVISION=HEAD make live-tv
```

This removes the runtime applications but keeps the configuration and shared media. Roll back by reverting the relevant commits on a topic branch, pushing it, and deploying that revision through `make live-tv`.
