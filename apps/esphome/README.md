# ESPHome devices

Local-only ESP32 boards for Home Assistant: the bathroom scale, an IR bridge
that replaces the air conditioner and fan remotes, and mmWave presence sensors.
Nothing here runs in the cluster and Argo CD does not deploy it. Each board is
flashed from the laptop and then talks to Home Assistant over the LAN through
the ESPHome native API. No vendor cloud and no phone apps.

Status (17 November 2026): the scale bridge runs on hardware and is in Home
Assistant as device "Scale bridge" (`sensor.scale_bridge_weight`). It publishes
one settled weight per weigh-in (the value the display held longest) and blanks
the sensor for a second first, so equal weights on different days still reach
Home Assistant. Home Assistant's side is in `apps/home-assistant` (Bathroom scale). The IR and
presence configs validate with `esphome config` but have not run on hardware.

## Why

- **Scale.** A cheap AliExpress body-fat scale. A BLE scan from the laptop
  found that it broadcasts every reading in the clear as `Yoda0`, weight in
  bytes 0-1 of the manufacturer data (big-endian, hundredths of a kg). The
  company ID field is a rolling counter (`0x1AC0`, `0x1DC0`, ...), so the
  decoder matches the name instead. The
  decoding notes are at the top of [`devices/scale.yaml`](devices/scale.yaml).
  The Home Assistant pod has no Bluetooth, so an ESP32 near the scale listens
  for those packets.
- **IR.** The air conditioner and the fan only have IR remotes. One ESP32 with
  an IR receiver learns the codes once, and an IR LED then sends them for Home
  Assistant.
- **Presence.** HLK-LD2410C 24 GHz radars report "someone is here" even when
  the person sits still, unlike the existing Tapo T100 motion sensor.

## Parts

| Part | Qty | Used by |
| --- | --- | --- |
| ESP32 DevKit (ESP-WROOM-32, USB-C; the scale board has a CP2102) | 3 | scale, IR, presence |
| HLK-LD2410C mmWave radar | 2 | presence |
| 38 kHz IR transmitter + receiver module set | 1 | IR |
| Dupont jumper leads, 20 cm | 120 | all wiring |

Wiring is written at the top of each device file. Nothing needs soldering.

## Files

- `devices/common.yaml`: board, Wi-Fi, API encryption, OTA and the Wi-Fi signal
  sensor. Every device includes it.
- `devices/scale.yaml`: passive BLE decoder for the scale, plus a Bluetooth proxy.
- `devices/ir-remote.yaml`: IR receiver in learning mode and the transmitter.
  The climate and fan entities are placeholders until the codes are learned.
- `devices/presence.yaml`: LD2410C over UART. Flash one copy per room with a
  different `name`.
- `devices/secrets.example.yaml`: copy it to `devices/secrets.yaml`, which Git
  ignores, and fill it in. Never commit the real file.

## Flash and add to Home Assistant

```sh
cd apps/esphome/devices
cp secrets.example.yaml secrets.yaml   # then edit
uvx esphome config scale.yaml          # validate
uvx esphome run scale.yaml             # first flash over USB, later over Wi-Fi
uvx esphome logs scale.yaml            # watch packets and learned IR codes
```

For a second presence board:
`uvx esphome -s name presence-bedroom -s friendly_name "Bedroom presence" run presence.yaml`.

Home Assistant runs in a pod without host networking, so mDNS discovery will
not see the boards. Add each one in Settings → Devices & services → Add
integration → ESPHome, using the board's IP address (give it a DHCP
reservation on the router) and the API key from `secrets.yaml`. That config
entry lives in the `home-assistant-config` PVC, like the Tapo entries.

## Next steps

1. Weigh someone barefoot to confirm what bytes 2-3 (impedance) mean.
2. Flash the IR bridge, learn the AC and fan codes, note the AC brand, and pick
   a native climate platform or template buttons.
3. Flash the presence boards, place them, and tune the gates with the LD2410
   sensors.
4. Add the devices to Home Assistant by IP and update its README with the
   entity names.

## Limits

- The scale reports body weight only. Body-fat numbers need the impedance
  formula and the user's height, age and sex. That is not done here.
- Only the scale config has been compiled and run. Some of these boards'
  charge-only USB cables carry no data; use a data cable for the first flash.
  On Linux the CP2102 port needs `dialout` access (or a temporary ACL).
- esptool may misreport the crystal as 26 MHz at 460800 baud. It is 40 MHz;
  do not set `CONFIG_XTAL_FREQ_26`. Flash at 115200 if the stub fails.
- Give each board a DHCP reservation on the router so its HA entry keeps
  working; the scale bridge has one.
