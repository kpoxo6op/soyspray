# Infinite Slop TV app

A small Android TV app that gives https://infiniteslop.ai/ its own tile on the
living-room TV's home screen. It opens the site full screen in the TV's
WebView, starts the stream with sound, hides the chat and queue panels, and
keeps the screen awake. OK on the remote shows or hides the panels; Back leaves.

It reloads the page when no video has advanced for a minute, retries ten
seconds after a failed load, and restarts itself if the WebView renderer dies.
Leaving the app stops the stream; opening it again starts fresh.

## Build and release

`.github/workflows/infinite-slop-tv.yml` builds the package on pull requests.
A merge to `main` publishes the GitHub release `infinite-slop-tv-1.RUN` with
the package and its SHA-256 and signing certificate. Each build uses a
throwaway signing key, so no key is stored anywhere.

Promote a release in a separate pull request by pinning its URL, `sha256`,
`signer_sha256` and version name in
`playbooks/operations/android-tv/living-room-tv.yml`, then run the TV
operation. Because every build has a new key, the operation reinstalls the app
when the certificate changes; the app keeps no data worth preserving.

## Checks

```bash
adb -s 192.168.20.232:5555 shell monkey -p vip.soyspray.infiniteslop -c android.intent.category.LEANBACK_LAUNCHER 1
adb -s 192.168.20.232:5555 exec-out screencap -p > slop.png
```

Confirm that video plays with sound within ten seconds, OK toggles the panels,
and Back returns to the home screen.

## Limits

The site announces that Infinite Slop has ended and points to fal.live, though
it still streams. If it stops, point `URL` in `MainActivity.java` elsewhere.
The page's element IDs (`splash`, `mute`, `chattoggle`) are not a stable API;
if the site changes them, the stream still loads but may start muted or with
the panels open. The TV's built-in WebView is version 98 and is not updated.
