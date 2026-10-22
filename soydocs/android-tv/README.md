# Android TV

The living-room television is a 2019 Sony Bravia KD-65X8500G (65-inch, Android
TV 10), bought second-hand in October 2026. It needs only power and ethernet.
It has no Google account. The laptop and Home Assistant control it over network
ADB, and its desired state is code in
[the Android TV operation](../../playbooks/operations/android-tv).

## Device

- Address `192.168.20.232`, reserved on OpenWrt as `sony-tv`.
- ADB on port 5555 for the laptop and Home Assistant. Each key was approved once
  on the TV with "Always allow".
- Sony web API on port 80. Power status and model answer without authentication.
- Chromecast built-in stays available for casting.
- Remote start is on, so the TV stays reachable in standby and ADB can wake it.

The operation disables Sony and Google advertising, Samba TV viewing analytics,
Sony remote support and cloud agents, Google Assistant, diagnostics and the
store. It also turns off location scanning, usage reporting and the screensaver,
and opts out of advertising personalisation.

## Apps

The home screen (`apps/tv-home`), SmartTube, the official Jellyfin client,
SmartTwitchTV and AI TV (`apps/ai-tv`) are pinned in
`playbooks/operations/android-tv/living-room-tv.yml` by version, SHA-256 and
signing certificate. SmartTwitchTV is the TV-remote Twitch client; ReVanced
Twitch is built for phones. SmartTube comes from F-Droid because the upstream README
warns that some upstream builds may have been compromised. Recheck that notice
before upgrading. Do not automate Google login or store Google credentials.

Jellyfin connects to `https://tv.soyspray.vip`. LAN-only devices need OpenWrt's
LAN ingress hairpin (`playbooks/operations/networking/set-lan-ingress-hairpin.yml`).
Sign in with Quick Connect:

1. Open Jellyfin on the TV and enter `https://tv.soyspray.vip`.
2. Select Add account and keep the Quick Connect code on screen.
3. Approve the code at Jellyfin Web > user menu > Quick Connect in a browser
   signed in through Authentik.
4. Keep the native playback account as the recovery option.
5. Play one cartoon and one Live TV channel.

The official client has its own native interface. Use its Home settings to
choose and order sections, and its native Guide for Live TV. Do not maintain a
custom Web client or Android TV fork before the real device shows a specific
limitation.

## Home Assistant

The Android Debug Bridge integration controls the TV as device `Living Room TV`
in the Living Room area, with `media_player.living_room_tv` and
`remote.living_room_tv`. It provides power, volume, key presses, current app and
ADB commands. Its config entry is Home Assistant runtime state.

## After a factory reset

1. With the remote, finish setup without a Google account and choose Home mode.
2. Settings > System > About: press OK on Build seven times.
3. Settings > System > Developer options: turn on ADB debugging.
4. Run the operation from the laptop and approve its key on the TV.
5. Sign in to Jellyfin with Quick Connect and re-add the Home Assistant
   integration, approving its key on the TV.

## Limits

AirPlay and the Vewd engine stay enabled
because AirPlay is a persistent app that crash-loops without Vewd. Live TV
plays one selected channel at a time. If playback buffers, choose a lower
quality in the Jellyfin client; Jellyfin can transcode with Intel Quick Sync,
but a lower bitrate cannot repair a broken upstream stream.

## Rollback

`adb shell pm enable PACKAGE` restores a disabled package, and
`adb uninstall app.smarttube.fdroid` or `adb uninstall org.jellyfin.androidtv`
removes an app. Factory-reset the TV before resale.
