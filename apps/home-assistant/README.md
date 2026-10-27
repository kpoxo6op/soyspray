# Home Assistant

Use `make check APP=home-assistant` to check the manifests and saved-state
restore contract. Use `make diff APP=home-assistant` for a read-only live
comparison. `make restore-check APP=home-assistant` restores the latest
Longhorn backup in an isolated namespace and privately validates the saved
pipeline, devices, entities, areas, and Assist exposure settings. Merge to
`main` for Argo CD delivery.

Home Assistant is an open-source home automation platform that puts local control and privacy first. It integrates with a wide range of smart home devices and services.

## Features

- Local-first architecture for privacy and reliability
- Extensive device and service integrations
- Powerful automation engine
- Web-based user interface
- Mobile apps for iOS and Android
- MQTT integration for Zigbee and other IoT devices

## Integration

Home Assistant connects to the MQTT broker to discover and control devices:
- Automatically discovers Zigbee devices via MQTT discovery from Zigbee2MQTT
- Subscribes to MQTT topics for device states and events
- Publishes MQTT commands to control devices
- Provides unified interface for all home automation devices

## Runtime Device Entries

Home Assistant stores UI-added integration config entries in the
`home-assistant-config` PVC. These are persistent HA runtime state rather than
Kubernetes manifests.

Current TP-Link Smart Home entries added through Home Assistant:

- Tapo L530 bulbs: `light.top`, `light.middle`, `light.bottom`
- Tapo H100 hub at `192.168.20.154`, exposing:
  - `binary_sensor.tapo_t100_motion`
  - `binary_sensor.tapo_t100_cloud_connection`
  - `sensor.tapo_t100_signal_level`
  - `siren.tapo_h100`

The living-room Sony TV at `192.168.20.232` uses the Android Debug Bridge
integration as device `Living Room TV` in the Living Room area, with
`media_player.living_room_tv` and `remote.living_room_tv`. Home Assistant keeps
its own ADB key in the PVC; the TV approved it once with "Always allow". If the
PVC is restored elsewhere or the TV is reset, approve the new prompt on the TV
as described in `playbooks/operations/android-tv/README.md`.

The bootstrap ConfigMap keeps HA's declarative automations, scripts, and scenes
that depend on these entities, including the Tapo Relax light behavior.

The PVC is protected from Argo pruning and Application deletion. Restore checks
must preserve the production claim and volume identity and remove their scratch
namespace. A successful synthetic voice check does not prove room recognition.

The Dreame L10s Ultra robot vacuum is visible on the LAN as
`dreame_vacuum_r2228o` at `192.168.20.170`. Home Assistant does not ship a
built-in Dreamehome integration, so the Deployment installs the pinned
`Tasshack/dreame-vacuum` beta custom component into the HA config PVC on pod
start. The beta line is intentional because the stable `v1.x` flow only supports
Xiaomi Home accounts, while this vacuum is paired to a Dreamehome account. The
actual Dreame account/device config entry is still HA runtime state in the PVC
after login.

## Fellow Stagg EKG Pro

The Deployment installs the unofficial `bramboe/stagg-ekg-plus-ha` custom
component (v1.3.6) at a fixed Git revision, checking the downloaded archive checksum
before replacing only `/config/custom_components/fellow_stagg`. It uses the
kettle's local HTTP CLI; Bluetooth is optional for discovery.

Connect the kettle to the home 2.4 GHz Wi-Fi with Fellow's EKG Updater app.
In Home Assistant, choose Settings → Devices & services → Add integration →
Fellow Stagg EKG Pro (HTTP CLI), and enter its local HTTP URL. Find the address
in the router's client list. Reconfigure the integration if DHCP changes it;
this preserves entities and history. The config entry belongs to the HA PVC,
so Wi-Fi credentials and private device addresses do not belong in Git.

Firmware 1.2.26 returns an empty form from the legacy CLI. The integration
detects its native HTTP status/settings interface and preserves existing entity
IDs. Reliable power control on this firmware requires a reachable active
Bluetooth adapter or ESPHome proxy and Automatic/Bluetooth connection mode;
Wi-Fi-only power controls are unavailable. Do not infer an off state from an
empty CLI response or send blind heating commands. Firmware flashing and
partition switching are separate deliberate operations.

The integration exposes temperature, heating state, power, and schedule
controls according to the detected firmware and connection capabilities. It does not measure water quantity. Confirm water and placement
before starting heat; installation does not create a heating schedule or
expose the kettle to Assist automatically. The local HTTP interface has no authentication,
so keep it on the trusted LAN and do not forward its HTTP port externally.
Fellow does not officially support remote control, and firmware changes may
remove this interface.

Run `make check APP=home-assistant`, `make full-check`, and
`make diff APP=home-assistant`. After GitOps delivery, confirm the integration
loads and its reported temperature matches a fresh read from the kettle.
The existing PVC backup/isolated restore contract includes its runtime entry.
To roll back, remove the HA config entry and revert the installer commit;
the component files remain on the PVC until explicitly removed. Existing
integrations, credentials, and schedules are preserved.

## Tapo firmware compatibility

If bulbs remain reachable but return HTTP 403 to `handshake1`, use python-kasa
discovery to check the advertised encryption. `TPAP` is unsupported by the
installed driver. Enable Third-Party Compatibility in the Tapo app (toggle it
off/on if already enabled), then verify discovery advertises `KLAP` and all
three light entities recover. Reload existing entries if needed; preserve
their identities and credentials. A healthy HA pod does not prove device access.
