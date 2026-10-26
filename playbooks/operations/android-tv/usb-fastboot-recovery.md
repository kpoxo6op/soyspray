# USB fastboot attempt and recovery — 26 October 2026

The KD-65X8500G stopped at the Sony logo after `adb reboot bootloader`.
No USB device appeared on the laptop. Removing USB and cycling power did not
restore Android. A physical forced factory reset got it past the Sony logo
to the Android animation and Welcome screen, erasing its configuration.

## Device and connection

- Sony KD-65X8500G, product `BRAVIA_UR2_4K_PA`, MediaTek MT5893.
- Android 10, build `662301` / `QTG3.200305.006.S97`, security patch
  `2026-02-01`, kernel 4.19.75, locked verified boot (`green`).
- Working network ADB before the attempt; unprivileged `shell` account.
- USB-A at the TV, USB-C at the Linux laptop. All three TV ports were tried
  while Android ran; the final bootloader attempt used the top USB 1 port.
- `lsusb` detected no TV; Android's `/sys/class/udc` was empty. Neither
  observation proves that the bootloader lacks a USB device interface.

## What went wrong

We ran `adb -s 192.168.20.232:5555 reboot bootloader` before establishing a
usable USB fastboot connection or a verified exit path. Network ADB disappeared,
`fastboot devices` remained empty (also as root), and the TV stayed at the Sony
logo across power cycles. No unlock, partition flash, or erase command was run
from the laptop. The subsequent physical factory reset was deliberately approved.

The precise stalled mode was not observable. Related MT5893 research shows
that the bootloader reboot command writes a fastboot marker to `misc`; persistent
bootloader entry is a plausible explanation, not a confirmed diagnosis here.
Repeated USB scans while Android ran could not answer whether fastboot would
work. We also overstated that changing ports could not help and that an A-to-A
cable would be sufficient. Both claims exceeded the evidence.

## Recovery that worked

With USB disconnected:

1. Disconnect AC power.
2. Hold **Power + Volume Down on the TV itself**, then reconnect AC while holding.
3. Sony instructs releasing when the front LED turns green, normally after
   10–30 seconds. Do not interrupt the reset and subsequent restarts.
4. The observed result was Android's coloured startup animation, then Welcome.
   Sony says 2019 models may show Welcome twice; complete setup on the second.
5. Complete initial setup, enable Developer options by selecting Build seven
   times, turn on ADB debugging, and authorize platt with **Always allow**.
6. Restore the declared configuration with the [normal sync operation](README.md).
   Restore Crossover's private view with `make -f apps/gi/Makefile tv` and
   reauthorize Home Assistant's ADB key and Jellyfin Quick Connect as necessary.

Source: [Sony forced factory reset instructions, including X85G](https://www.sony.com.au/electronics/support/articles/00159906).

## Before another attempt with an A-to-A cable

The [X8000H research](https://github.com/liliangxu/bravia-x8000h-downgrade/blob/master/docs/research.md#port-and-cable)
reports USB fastboot on a **different TV and region** with the same SoC and
build number. It reports a USB 2.0 gadget port and a working computer-host
connection through a dock/OTG adapter plus an A-to-A cable; a plain C-to-A
cable selected the wrong direction on its Mac. This is a lead, not proof of
KD-65X8500G compatibility or of the electrical suitability of any A-to-A cable.

- Confirm the intended cable wiring, computer host role and TV bootloader port
  from reliable model-specific evidence. Do not assume every A-to-A cable is
  suitable for joining two powered USB-A ports.
- Have fastboot installed, USB detection logging ready, and the stock firmware
  and restoration procedure identified before rebooting. Preserve recoverable
  app configuration and account access; the previous reset erased both.
- Treat another bootloader reboot as potentially requiring another physical
  reset. Establish an exit/recovery plan and explicit acceptance of that risk.
- Start with device enumeration and read-only identity/state queries. Confirm a
  working return to Android before considering unlock or flash operations.
- Do not copy the other model's images or rollback indices. An unlock can erase
  data; altered verified boot can affect DRM and standby. Cable detection is
  not evidence that a rooting or downgrade procedure is compatible.

The A-to-A route has **not been tested on this TV**, and the TV has not been
rooted. Recovery and restoration take priority over another rooting attempt.
