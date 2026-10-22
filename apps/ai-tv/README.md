# AI TV app

A small Android TV app for fal.live, a network of AI-generated live channels.
It opens the site full screen in the TV's WebView and turns the remote into a
channel changer: left and right (or channel up and down) switch between
Anime, Chaos, Sitcom, Soap Opera and Wildlife World, and a banner names the
channel for a few seconds. On the first visit OK presses the site's own
"Enter with sound" button, which accepts fal.live's terms; Back leaves.

Once inside, the live stage fills the screen. The page reloads when the video
has not advanced for a minute and retries ten seconds after a failed load; the
app restarts itself if the WebView renderer dies. Leaving stops the stream.

It replaces the Infinite Slop app, whose event ended in October 2026 with a
pointer to fal.live.

## Build and release

`.github/workflows/ai-tv.yml` builds the package on pull requests and publishes
the GitHub release `ai-tv-1.RUN` from `main` with its SHA-256 and signing
certificate, signed with a throwaway key. Pin a release in
`playbooks/operations/android-tv/living-room-tv.yml` in a separate pull
request, then run the TV operation.

## Checks

```bash
adb -s 192.168.20.232:5555 shell monkey -p vip.soyspray.aitv -c android.intent.category.LEANBACK_LAUNCHER 1
adb -s 192.168.20.232:5555 exec-out screencap -p > ai-tv.png
```

Confirm that the stream fills the screen, OK starts sound, and left and right
change channel.

## Limits

fal.live streams over WebRTC, so the TV's WebView plays it; there is no HLS
feed to play natively. The channel names and the stage's `section#live` are
the site's markup, not a stable API; if fal.live changes them, the page still
plays but may stay framed or stop changing channel. The password-protected
Popcorn channel is left out. The TV's built-in WebView is version 98.
