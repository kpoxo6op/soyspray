# TV home screen

The living-room TV's home screen. ОТВ Прим plays live behind everything, muted,
with what is on now (title, times and a progress line) and what is next. Below
sit seven tiles: Watch live, Guide, Jellyfin, YouTube (SmartTube), Twitch
(SmartTwitchTV), AI TV (fal.live) and Crossover (`apps/crossover-tv`). The row
shrinks in proportion when its tiles would not fit between the margins. The Jellyfin tile opens Moonfin, a customizable client for the same server.
The official Jellyfin app stays in Apps and handles the guide fallback. A
clock and small Apps and Settings buttons sit top right. It replaces the Google home screen, which stays
disabled.

Watch live hides everything and turns the sound on; up and down (or channel
up and down) change between the channels with a direct stream, and Back
returns home. Guide opens a full-screen programme guide over the video:
channels down the side, three hours across and a red line at the current time.
OK on a channel with a direct stream plays it full screen; other channels open
Jellyfin, which plays them through Dispatcharr. The remote's Guide, Settings
and Menu keys open the guide, Settings and the app drawer.

The lineup and guide come from Media Helper at `https://guide.soyspray.vip`
(`/api/v1/channels` and `/xmltv.xml`), the same catalog Jellyfin uses, so a
channel added there appears here too. The last copy is cached, so the screen
works at once after a restart. The guide refreshes every 20 minutes.

Design: one screen, no recommendation rows, plain Android views and canvas
drawing. Only GPU-side view properties animate on focus, and ExoPlayer draws
the video on its own surface, so focus moves stay at 60 fps on the TV's
MediaTek chip. The video stops while another app is open.

## Use

Change the tiles in `Tiles.java` (`ROW`) and the featured channel in
`Live.java` (`FEATURED`, a catalog slug). A missing app makes its tile shake.

Voice control can open a direct catalog channel full screen with sound:

```bash
adb shell am start -n vip.soyspray.home/.HomeActivity --es play_channel otv-prim
```

`play_channel` accepts a catalog slug or exact name, on both cold start and an
already running home screen. Unknown names and indirect streams do nothing.
Media Play/Pause keys pause and resume full-screen live playback; channel keys
step through the direct catalog. HA wakes the TV before sending the intent.

## Build and release

`.github/workflows/tv-home.yml` builds the package on pull requests and
publishes the GitHub release `tv-home-1.RUN` from `main`, with its SHA-256 and
signing certificate. Pin a release in
`playbooks/operations/android-tv/living-room-tv.yml` (`android_tv_apps` and
`android_tv_home`) in a separate pull request, then run the TV operation.

## Checks

```bash
adb -s 192.168.20.232:5555 shell input keyevent KEYCODE_HOME
adb -s 192.168.20.232:5555 exec-out screencap -p > home.png
adb -s 192.168.20.232:5555 shell dumpsys gfxinfo vip.soyspray.home
```

Confirm the live picture and now/next text, focus moves without dropped frames
(`Janky frames` near zero), Watch live with sound, the guide, and each tile.

## Limits

Only channels with a `direct_hls` source play on the home screen; Streamlink
channels play in Jellyfin. Without the guide host and without a cached copy,
the screen shows no live picture. Times show in the TV's time zone.
