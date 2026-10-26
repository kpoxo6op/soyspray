# Living-room Android TV

`sync-android-tv.yml` brings the living-room Sony KD-65X8500G (Android TV 10)
to the state declared in `living-room-tv.yml`: Sony and Google advertising,
tracking, remote-support and voice packages off, privacy settings, Remote
start, our own home screen (`apps/tv-home`), and pinned SmartTube, Moonfin, Jellyfin,
SmartTwitchTV, AI TV (`apps/ai-tv`) and Crossover (`apps/crossover-tv`) builds.
Crossover's view is sent separately by `make -f apps/gi/Makefile tv`, and again
after any reinstall, which clears it. Retired apps listed in
`android_tv_removed_packages` are uninstalled. On OpenWrt it reserves the TV's
address and keeps the TV's DNS on the router. Change the TV by editing
`living-room-tv.yml` and running the playbook; do not change it by hand.

## Normal use

Run from the laptop, whose ADB key the TV trusts:

```bash
source soyspray-venv/bin/activate
ansible-playbook playbooks/operations/android-tv/sync-android-tv.yml
```

The run is safe to repeat. A second run reports no changes. It wakes the
screen, walks a few settings screens with the D-pad, then returns home. While
someone is watching, add `--skip-tags screens`: apps, packages, settings and the
router are still enforced, and the screen is left alone.

To upgrade an app, replace its `version_name`, `url`, `sha256` and, only if the
publisher changed its key, `signer_sha256`. SmartTube comes from F-Droid because
its README warns that some upstream builds may have been compromised; F-Droid
builds it from source and signs it with the pinned key. Jellyfin comes from the
official GitHub release, whose API publishes the SHA-256.

## Checks

The playbook fails when the address answers as a different product, a download
or its signing certificate differs from the pin, a declared package is still
enabled, or any app crashes within 20 seconds of the changes.

```bash
adb connect 192.168.20.232:5555
adb -s 192.168.20.232:5555 shell pm list packages -d
adb -s 192.168.20.232:5555 exec-out screencap -p > tv.png
```

## Access

ADB stays enabled so the laptop and Home Assistant can control the TV. Each
client key needs one "Allow USB debugging?" approval on the TV with "Always
allow" ticked; a client that already has ADB can press it with
`tv_ui.py SERIAL switch '*' on` and `tv_ui.py SERIAL select ALLOW`.
Revoke keys in Developer options if a client is retired.

LAN-only devices reach `*.soyspray.vip` through OpenWrt's LAN ingress hairpin;
see `../networking/set-lan-ingress-hairpin.yml`.

## Network

The firewall rule `firewall.sony_tv_dns` rejects the TV's DNS (port 53) and
DNS over TLS (853) to the internet, matched by MAC so it covers the TV's IPv6
addresses too. Every app therefore resolves through the router, which answers
`*.soyspray.vip` locally; a resolver hard-coded in an app falls back to the
router at once. With the Sony and Samba TV services disabled, the TV's own
traffic is Google Play services and the Chromecast receiver, which stay
allowed so casting keeps working.

## Limits

AirPlay is a persistent Sony app that starts even when disabled and crash-loops
without the Vewd engine, so both stay enabled. No other launcher is installed:
if the home screen app breaks, `adb shell pm enable com.google.android.tvlauncher`
brings Google's home screen back.
Sony firmware updates may rename screens; `tv_ui.py` then fails with the visible
texts. A factory reset needs the remote for setup, Developer options and the
first ADB approval before this playbook can run again.

## Rollback

`adb shell pm enable PACKAGE` re-enables a package, `adb uninstall PACKAGE`
removes an app, `uci delete dhcp.sony_tv && uci commit dhcp` on the router
drops the reservation, and `uci delete firewall.sony_tv_dns && uci commit
firewall && fw4 reload` drops the DNS rule. Revert the commit so the next run
does not reapply it.

## USB fastboot incident

Before trying USB fastboot or rooting, read the [26 October attempt and recovery](usb-fastboot-recovery.md). A bootloader reboot with the C-to-A connection left this TV at the Sony logo and required a physical factory reset. An A-to-A connection remains untested.

## Moonfin appearance and sign-in

Moonfin 2.7.0 opens the same Jellyfin library at https://tv.soyspray.vip.
Approve its fresh Quick Connect code from a signed-in Jellyfin browser. The
code expires; reopen the client sign-in flow to request another one.

After sign-in, choose Left Sidebar, Banner home header, Modern rows, Modern
details and Glass theme in the setup wizard. Then set Settings →
Personalization → General Style → Glass Quality to **Reduced**. Auto quality
crashed in the Sony Mali graphics driver during the first Live TV launch;
Reduced passed the subsequent channel playback check. Keep this setting when
repeating setup, and test both a library title and Live TV before switching the
launcher tile. These display preferences live in the client and need repeating
after clearing its data or a factory reset; the playbook pins the APK but does
not restore private client preferences or authentication.

The official Jellyfin client remains installed and signed in as a fallback.
The home-screen Guide continues to use it for indirect streams. To roll back
the library tile, restore its org.jellyfin.androidtv target in Tiles.java,
release and promote that home-screen build through the normal workflow.
