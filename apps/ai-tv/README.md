# AI TV app

A small Android TV app for AI-made television, full screen in the TV's
WebView. It carries three networks:

- **fal.live**: live AI channels (Anime, Chaos, Sitcom, Soap Opera and
  Wildlife World; the password-protected Popcorn is skipped).
- **Flow TV**: Google Labs' channels of Veo clips.
- **Nothing, Forever**: the endless AI sitcom, through Twitch's embedded
  player.

Up and down (or channel up and down) change channel, left and right change
network, and a pill at the bottom names what is on. OK presses the Enter button
on fal.live's age and terms dialog, which appears once after each install;
fal.live's "Enter with sound" and Flow TV's mute are pressed automatically.
Back leaves, and leaving stops the stream. The app reopens the network and
channel that were on last.

It replaces the Infinite Slop app, whose event ended in October 2026 with a
pointer to fal.live.

## How it works on the TV

The TV's WebView is Chrome 98, which ignores every rule inside CSS `@layer`.
fal.live is built with Tailwind 4, which puts all of its styles there, so the
site rendered unstyled. `app/src/main/assets/kiosk.js` fetches each stylesheet
again and adds it with the layer wrappers removed and `dvh` units mapped to
`vh`, which also fixes Flow TV's player. The same script reads the channel
names from the sites' own buttons, shows only the video on Flow TV, and reloads
a page whose video has stopped for 90 seconds, at most every ten minutes.

Twitch only plays its embed inside a page from the domain named as `parent`,
so the app loads the embed in a page with the base URL `https://soyspray.vip/`.
Main-frame navigation is limited to the three networks' hosts.

WebView debugging is on so Chrome DevTools can attach over adb when a site
changes:

```bash
pid=$(adb -s 192.168.20.232:5555 shell pidof vip.soyspray.aitv)
adb -s 192.168.20.232:5555 forward tcp:9333 localabstract:webview_devtools_remote_$pid
curl -s http://127.0.0.1:9333/json
```

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

Confirm that each network fills the screen with sound, and that up and down
change channel.

## Limits

fal.live streams over WebRTC and Flow TV plays clip files from Google, so the
WebView plays them; neither has a feed to play natively. Channel names, button
labels and Flow TV's links are the sites' markup, not a stable API: if a site
changes them, the page still plays but may stop changing channel. fal.live
channels go offline at times and show "The director is reconnecting" until
they return. Vercel sometimes shows fal.live a short browser check, which
passes by itself.
