# Dispatcharr

Dispatcharr owns live stream identifiers, relays, failover, health data, and cached guide data. Its service stays `ClusterIP`. Administrators use `https://dispatcharr.soyspray.vip` from LAN or Tailscale. Authentik first limits access to `cluster-admins`. Dispatcharr then requires its generated local administrator login.

## Normal use

The PostSync job reconciles one M3U account, one guide source, and one Streamlink profile. It keeps automatic channel sync off and creates or patches only channels owned by this managed account. It preserves every group range and custom property. It keeps custom fallback streams, removes stale channels that only this account owns, and requires every catalog name and number to appear exactly once in the final lineup. A second run updates the same objects without duplicates.

The managed Streamlink profile prefers `720p50`, `720p`, `480p50`, and `480p` before `best`. This gives 25 Region a 720p50 preference. The setting selects an upstream rendition. It does not transcode video.

The reconcile job uses that Streamlink profile only when a channel contains a `streamlink_page` source. A channel made only from `direct_hls` sources uses Dispatcharr's locked `ffmpeg` profile. FFmpeg copies the original codecs into MPEG-TS and preserves the timeline across declared HLS discontinuities. This keeps Infinite Slop's separate generated clips continuous for Jellyfin without re-encoding them.

The job requires Dispatcharr's normal URL stream identity setting. It stops with a clear error if that global setting was changed. It does not rewrite global stream identity or the default profile for unmanaged accounts.

`okru.py` is the Streamlink 8.5.0 OK plugin with two small schema changes. OK returns live metadata as either a string or an object. The mounted plugin accepts both forms. See `okru.LICENSE`.

Dispatcharr uses Redis to buffer each active relay and send it to its clients. It keeps an unused channel warm for 15 seconds. A new client starts 20 seconds behind the live edge. The extra delay covers the measured 10 to 14 second upstream gaps without increasing the 60-second Redis retention. These settings reduce reconnect churn and give the player a small complete buffer.

Jellyfin opens one selected channel through the Dispatcharr HDHomeRun interface. Dispatcharr shares one upstream relay between local clients. It does not keep a second browser cache or store expiring media URLs in Git.

## Checks

```bash
kubectl kustomize playbooks/argocd/applications/media/dispatcharr
kubectl -n argocd get application dispatcharr
kubectl -n media get deployment,pod,pvc -l app.kubernetes.io/name=dispatcharr
```

Argo CD deletes the PostSync job after success. If the job fails and remains, read its log with `kubectl -n media logs job/dispatcharr-reconcile`.

Open the administration page and check these managed objects:

- M3U account: `Managed live TV`
- guide source: `Managed live TV guide`
- stream profile: `Managed Streamlink`
- `channel_shutdown_delay`: `15`
- `new_client_behind_seconds`: `20`

Sync the Dispatcharr application twice through Argo CD during an acceptance test. Confirm that the PostSync job does not create duplicate managed objects or remove unmanaged configuration.

Check the HDHomeRun lineup after reconciliation. Confirm that each enabled Dispatcharr channel has one stable channel identity. Restart playback and confirm that a fresh client starts from the relay buffer.

## Limits

The upstream image is pinned to `v0.30.0` and its registry digest. The protected `dispatcharr-data` claim keeps cached data during shutdown and rollback. Authentik is a forward-auth access gate, not native Dispatcharr OIDC. Dispatcharr uses its generated administrator account for administration and internal API reconciliation.

Redis buffering can reduce local reconnects. It cannot repair missing upstream segments, an ended stream, or long packet loss between New Zealand and the source.

A channel with both `streamlink_page` and `direct_hls` sources uses Streamlink because the page source must be resolved before playback. Use only direct HLS sources in a channel that needs FFmpeg discontinuity handling.

Telemiks and 25 Region use the live videos embedded by their official pages. The local plugin fixes the known metadata-format failure. Repeated retries with a capped delay can recover a temporary network or upstream failure.

Media Helper selects only the catalog guide identifiers from IPTVX EPG_LITE. It serves the last complete in-memory snapshot after a refresh failure. Dispatcharr keeps its own guide cache on the protected claim. Do not create a schedule from channel names or expected broadcasts.

## Shutdown and rollback

Stop the complete Live TV stack from a clean, pushed topic branch:

```bash
LIVE_TV_ENABLED=false LIVE_TV_REVISION=HEAD make live-tv
```

The role removes the Argo CD Applications. It does not delete `dispatcharr-data`, Jellyfin configuration, or shared media files.

To roll back Dispatcharr code or settings, revert the applicable commits on a topic branch. Push the branch and run:

```bash
LIVE_TV_ENABLED=true LIVE_TV_REVISION="$(git branch --show-current)" make live-tv
```

After merge, run `LIVE_TV_ENABLED=true LIVE_TV_REVISION=HEAD make live-tv`.
