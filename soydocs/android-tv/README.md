# Android TV plan

Last price check: 31 August 2026. Refresh prices before purchase. Do not keep short-lived listings in this file.

## Purchase guide

The default purchase is a used 55-inch TCL C745 or C755 for NZ$500 to NZ$700. Add a used Google TV Streamer 4K for NZ$100 to NZ$130.

| Tier | Display | Fair used range |
|---|---|---:|
| Best value | TCL C745 or C755, 55 or 65 inch | NZ$500 to NZ$1,000 |
| Safer LED | Sony X90J, X90K, or X90L, 55 or 65 inch | NZ$600 to NZ$1,200 |
| Best picture | LG C2 or C3 OLED, 55 or 65 inch | NZ$800 to NZ$1,500 |

Use a separate streamer even when the display includes Google TV. Select the display for picture quality.

Use the [Google TV Streamer 4K](https://store.google.com/product/google_tv_streamer_specs?hl=en-US) by default. A used NVIDIA Shield TV Pro 2019 costs NZ$220 to NZ$300. It suits high-bit-rate local media and advanced local audio. Use Chromecast with Google TV 4K only as a budget option at NZ$60 to NZ$90. Its memory and storage are more limited.

Check current [Trade Me televisions](https://www.trademe.co.nz/a/marketplace/electronics-photography/tvs) and [Trade Me Chromecast devices](https://www.trademe.co.nz/a/marketplace/electronics-photography/media-streaming/chromecast) before purchase.

Avoid generic Android boxes and old Chromecast receivers. Do not use Fire TV as the main platform. Do not depend only on webOS or Tizen.

## Used hardware checks

1. Check the panel for cracks, pressure damage, lines, and uneven backlight.
2. Show full-screen red, green, blue, white, gray, and black test images.
3. Check for dead pixels and OLED burn-in.
4. Test each High-Definition Multimedia Interface port.
5. Test Ethernet and Wi-Fi.
6. Test all remote buttons.
7. Test a cold start, sleep, and wake.
8. Test High-Definition Multimedia Interface Consumer Electronics Control.
9. Confirm that factory reset is available.
10. Confirm that no account or organization lock remains.
11. Confirm Android TV Remote support before payment.

## Jellyfin setup

1. Install the official Jellyfin client from Google Play.
2. Open `https://tv.soyspray.vip`.
3. Sign in through Authentik in a browser.
4. Select Quick Connect in the television client and approve its code in the signed-in browser.
5. Keep the native playback account as a recovery option.
6. Play one cartoon directly.
7. Open `Live TV` > `Guide` and check the programme rows.
8. Confirm that each Guide row has its channel image.
9. Play each enabled Live TV channel.
10. Restart the streamer and repeat the cartoon and Live TV checks.

The official Android TV client has its own native interface. Use its Home settings to choose and order sections. Open its native Guide for the full Live TV timeline. Jellyfin Web remains a stock administration, browser-playback, and Quick Connect surface. Do not maintain a custom Web client or Android TV fork before the real device shows a specific limitation.

## Native interface plan

Do this only after the real television or streamer is available:

1. Compare the Dark and Muted Purple themes on the television.
2. Test the backdrop disabled and blurred settings.
3. Put the native Live TV section, Continue Watching, and useful Cartoons sections in a practical order.
4. Hide unused audio, book, recording, and empty Home sections.
5. Set library image size and grid direction from normal viewing distance.
6. Set Live TV channel order, favourites, guide colours, and programme indicators.
7. Capture the remaining problems with screenshots and remote-control steps.
8. Classify each problem as a client setting, metadata or artwork problem, upstream Jellyfin defect, or code change.

Use built-in settings and better metadata first. Open an upstream issue for a general defect. Consider a small Android TV patch only when a measured problem has no supported setting. Do not create or maintain a private application fork from a general dislike of the interface.

## SmartTube setup

Recheck the [SmartTube security notice](https://github.com/yuliskov/SmartTube#readme) when the device arrives. Prefer F-Droid package `app.smarttube.fdroid` version `32.10` only if F-Droid still verifies that build.

The pinned F-Droid file is `https://f-droid.org/repo/app.smarttube.fdroid_2400.apk`. Its SHA-256 value is `1fb2da66bcc148f7ae058e42f02dc8161daf414263c451594b8564c5d2e45595`. The F-Droid signing-certificate SHA-256 fingerprint is `33:79:18:72:DA:CC:F6:01:A3:1B:D7:3D:32:92:45:F8:0F:69:04:4F:76:E1:A7:94:58:6F:B8:57:F0:9D:EA:A8`.

Record the downloaded Android Package Kit checksum and signing certificate before installation:

```bash
sha256sum SmartTube.apk
apksigner verify --print-certs SmartTube.apk
```

Do not install the file if either value differs. Refresh the pinned values when F-Droid publishes a new verified version.

Enable network debugging temporarily. Approve the laptop key on the television. Replace `TV_ADDRESS` with the confirmed local address.

```bash
adb connect TV_ADDRESS:5555
adb devices
adb install --replace SmartTube.apk
adb shell pm list packages | grep app.smarttube.fdroid
```

Open one public YouTube video in SmartTube. Check normal playback, seeking, pause, and resume. Do not automate Google login. Do not store Google credentials in this repository.

Remove SmartTube with this command:

```bash
adb uninstall app.smarttube.fdroid
```

Disable network debugging after setup. Run `adb devices` and confirm that the television is not connected.

## Home Assistant setup

Pair the Android TV Remote integration from Home Assistant. Confirm power, navigation, volume, Jellyfin launch, and sleep actions.

The Jellyfin client plays one selected Live TV channel. It does not show several live channels at the same time. Dispatcharr prefers `720p50`, `720p`, `480p50`, and `480p` before `best` for Streamlink sources. A direct source with one rendition keeps that quality.

If playback buffers, first try a lower quality in the Jellyfin client. Jellyfin can use Intel hardware transcoding to reduce the playback bitrate. A lower bitrate can reduce local client load, but it cannot repair missing upstream segments or an offline source.

Do not add a device operations playbook before a real device exists. Add power-on, Jellyfin launch, and session waiting only after the real device passes these checks.

## Shutdown and rollback

Remove SmartTube with `adb uninstall app.smarttube.fdroid`. Remove the Jellyfin client from Android settings. Factory-reset the streamer before resale.

Disable network debugging after every maintenance session. Keep Google credentials outside automation and Git.
