# Crossover TV app

Crossover on the living-room TV: the date the mortgage is paid off, how much
sooner that is than the scheduled repayments, the loans left with and without
the early repayments, the stages from the cash buffer through mortgage free to
work optional, and the standing transfer, full screen in the TV's WebView. It
is the big-screen form of the private page at `gi.soyspray.vip` (`apps/gi`).
Once there are no loans, work optional leads, with the position against money
needed.

The first screen shows one thing, in one of three layouts: **Date** (the
mortgage-free date alone), **Step** (the stage being worked on, its progress,
the fortnightly transfer and the next stage) or **Line** (the loans falling to
zero against the scheduled repayments). Left and right on the remote change
the layout, and the app keeps the choice. Down shows the full plan described
above; up returns.

Amounts start hidden. OK shows or hides them, and the hint top right says
which. Back leaves, and leaving closes the page, so the next visit starts on
the first screen, hidden again. The page also says how far the date has moved
since the last visit, and turns the data date amber once it is more than 14
days old.

## Data

The app holds no engine and no figures of its own. `make -f apps/gi/Makefile
finance` publishes the private data file to the cluster and then sends the TV
a ready-made view: the private runtime checkout works it out
(`scripts/tv-view.ts`) and ADB delivers it on stdin to `DataReceiver`, which
keeps it in the app's private files. The receiver takes only the view schema
the page draws (3), so the runtime checkout and the installed app must match.
`make -f apps/gi/Makefile tv` sends it again, for example after a reinstall,
which clears those files. The send checks the TV's product name first.

- The app has no `INTERNET` permission, blocks network loads in the WebView,
  and is excluded from backups.
- `DataReceiver` requires the sender to hold `android.permission.DUMP`, which
  only ADB's shell user and the system have, so no installed app can send or
  replace the view.
- The WebView loads only `assets/index.html` with its script, style and B612
  fonts. The page reads the view through the `CrossoverTv` bridge, which also
  keeps the date shown on the last visit.

Remove the view from the TV:

```bash
adb -s 192.168.20.232:5555 shell am broadcast -n vip.soyspray.crossover/.DataReceiver -a vip.soyspray.crossover.CLEAR
```

## Layout

The page sizes everything to the screen width (1rem is a 120th of it), so it
fills the 1920 by 1080 panel at density 2. The colours keep their meaning from
the web page: magenta is the plan, amber asks for attention, ink is a fact. The
TV's WebView is Chrome 98; the page uses nothing newer.

To work on the page in a browser, serve `app/src/main/assets` with a
`view.json` beside `index.html` (from `node scripts/tv-view.ts FILE` in the
runtime checkout) at a 960 by 540 viewport, and delete the file afterwards.

## Build and release

`.github/workflows/crossover-tv.yml` builds the package on pull requests and
publishes the GitHub release `crossover-tv-1.RUN` from `main` with its SHA-256
and signing certificate, signed with a throwaway key. Pin a release in
`playbooks/operations/android-tv/living-room-tv.yml` in a separate pull
request, run the TV operation, then `make -f apps/gi/Makefile tv`.

## Checks

```bash
adb -s 192.168.20.232:5555 shell monkey -p vip.soyspray.crossover -c android.intent.category.LEANBACK_LAUNCHER 1
adb -s 192.168.20.232:5555 exec-out screencap -p > crossover-tv.png
```

Confirm each layout of the first screen (left and right) and the plan (down)
with amounts hidden, that OK shows them, and that Back and a new visit hide
them again.

## Limits

The TV shows the view from the last publish; it does not recalculate. "Days
from today" counts from the TV's own date. Each release is signed with a new
throwaway key, so an upgrade reinstalls the app and clears the stored view
until it is sent again.
