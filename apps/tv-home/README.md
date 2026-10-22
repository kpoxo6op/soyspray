# TV home screen

The living-room TV's home screen: a large thin clock, three big tiles (Jellyfin,
SmartTube and Infinite Slop) and two small buttons for all apps and settings,
over a dark background with a soft glow that slides to the focused tile and
takes its colour. It replaces the Google home screen and Couchy, which stays
installed as a fallback.

Design: one screen, no rows of recommendations, no network calls, no images to
load. Tiles and glyphs are drawn in code. Focus lifts a tile with scale, shadow
and an outline, the way tvOS and Projectivy do, and only GPU-side view
properties animate, so focus moves stay at 60 fps on the TV's MediaTek chip.
The app has no libraries and starts in well under a second.

## Use

Left and right move between tiles, OK opens one, Up reaches the Apps and
Settings buttons. The remote's Settings key opens Settings and Menu opens the
app drawer. Back does nothing on the home screen.

Change the tiles in `Tiles.java` (`ROW`): title, subtitle, package and colours.
A missing app makes its tile shake instead of opening.

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
adb -s 192.168.20.232:5555 shell dumpsys gfxinfo vip.soyspray.home framestats
```

Confirm the clock and date, that focus moves without dropped frames
(`Janky frames` near zero in `gfxinfo`), and that each tile opens its app.

## Limits

The clock follows the TV's time zone and 12- or 24-hour setting. The drawer
lists apps with a TV launcher entry only.
