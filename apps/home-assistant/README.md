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

## Home dashboard

The default panel, `/dashboard-home`, is a YAML dashboard declared in Git
(`home-dashboard.yaml` in the bootstrap ConfigMap, copied to
`/config/dashboards/home.yaml`). Its tabs are Home, Bins, Power and System;
Remote and Vacuum are subviews opened from the Home tab, so the phone's top
bar fits without scrolling. The sidebar holds only Home and HA's built-in
panels (order set per user in the profile). Change the dashboard in Git; the UI editor cannot save a YAML
dashboard. Notifications open tabs by path (`/dashboard-home/bins`,
`/dashboard-home/power`).

Until 5 November 2026 this dashboard was a UI (storage) dashboard with the
same URL. Its last stored copy is kept privately on the laptop; delete the
storage entry before a YAML dashboard takes over its URL, because removing a
shadowed storage entry later also unregisters the YAML panel until restart.

## Mercury power

The Deployment installs the unofficial `bkintanar/home-assistant-mercury-co-nz`
custom component (v2.1.1) by Git revision. The installer checks both the
commit and the `custom_components/mercury_co_nz` tree hash before replacing
only `/config/custom_components/mercury_co_nz`. It polls Mercury's customer
API (the one the Mercury app uses) about every five minutes. Mercury's data
lags by roughly two days, so "latest day" means the newest day Mercury has.

Sign in once from Settings → Devices & services → Add integration →
Mercury CO NZ with the Mercury app email and password. The config entry and
password live in the HA PVC, never in Git. The integration creates
account sensors as `sensor.mercury_nz_*` and per-ICP sensors on an
`ICP … (primary)` device. Rename those per-ICP sensors once to
`sensor.mercury_nz_<name>` (for example `sensor.mercury_nz_energy_usage`
and `sensor.mercury_nz_current_rate`) so the dashboard finds them.

The **Power** tab of the Home dashboard is declared in Git (see "Home
dashboard" below). It
uses the integration's own cards, which it registers as Lovelace resources at
startup. HA's built-in Energy dashboard reads the
`mercury_co_nz:<account>_energy_consumption` and `_energy_cost` statistics;
choose those under Settings → Dashboards → Energy (not the temporary
email-hash ids). The account number is private and stays out of Git.

To roll back, delete the Mercury config entry and revert the installer and
dashboard commit. The component files remain on the PVC until removed.

### Power insights

`templates.yaml` (bootstrap ConfigMap) turns the Mercury history attributes
into `sensor.power_*`: newest Mercury day and its age, last-7-day cost and
kWh, the always-on load (mean of the three quietest hours of the last 48)
with its yearly cost, and `sensor.power_plan_check`. The plan check prices
every complete hourly day once on the current Mercury Flat Rates low-user
plan and four Auckland alternatives (Mercury Flex Rates, Octopus Flexi,
Electric Kiwi MoveMaster with its free hour, Contact Good Charge). Its state
is the cheapest plan so far; attributes hold the running totals, day count
and the date the rates were checked. Rates are hard-coded and go stale when
retailers reprice; refresh them and the `rates_checked` date together.

Four automations notify `notify.mobile_app_pixel_9_pro_xl` (group `power`):
a day at least 25% and 2 kWh above the previous fortnight's average, with its
biggest hours; a Monday 08:30 digest; a 10:00 warning when Mercury's newest
day is four or more days old (normally two; usually an expired password);
and Mercury's bill note once per billing period (the first summary, then each
new period).
`tests/test_home_assistant_power.py` renders the templates against two real
days. Mercury's hourly cost excludes the daily charge while its daily cost
includes it, so the plan check prices kWh itself and adds each plan's daily
charge.

## Bin collections

The Deployment installs `mampfes/hacs_waste_collection_schedule` (v2.36.0)
by Git revision, checking the commit and the
`custom_components/waste_collection_schedule` tree hash before replacing only
that folder. Its Auckland Council source reads the council's collection-day
page for one property (the assessment number shown by the council's
collection day finder). The council lists only the next date for each bin;
the integration refreshes once a night.

Add it once from Settings → Devices & services → Add integration → Waste
Collection Schedule → New Zealand → Auckland Council, with the property's
assessment number, then rename the calendar entity it creates to
`calendar.bin_collections`. The config entry and number live in the HA PVC,
never in Git, because the number identifies the home address.

`templates.yaml` reads that calendar into `sensor.bins_schedule` and the
countdown sensors `sensor.bins_next_collection`, `sensor.bins_rubbish`,
`sensor.bins_food_scraps`, `sensor.bins_recycling` and `sensor.bins_status`.
The **Bins** tab of the Home dashboard shows them with the calendar, and a
Bins badge appears on the Home tab when the bins should go out.

The phone (`notify.mobile_app_pixel_9_pro_xl`, group and channel `Bins`) is
reminded at 18:30 the evening before a collection, again at 21:00, and at
06:15 on the day, until "They're out" is pressed on the notification or the
dashboard (`input_datetime.bins_out_for`). "In an hour" snoozes once.
`input_boolean.bins_reminders_paused` pauses them. A 10:00 warning fires when
no collection is due within eight days, which means the schedule stopped
updating. `tests/test_home_assistant_bins.py` renders these templates for a
full week, an off-recycling week and a frozen schedule.

Inorganic collection is booked separately and is not on this calendar. To
roll back, delete the config entry and revert the installer and dashboard
commit; the component files remain on the PVC until removed.

## Fellow Stagg EKG Pro

The Deployment installs the unofficial `bramboe/stagg-ekg-plus-ha` custom
component (v1.3.6) at a fixed Git revision, checking the downloaded archive checksum
before replacing only `/config/custom_components/fellow_stagg`. It uses the
kettle's local HTTP interfaces and optional Bluetooth transport.

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
Wi-Fi-only power commands are unsupported and rejected. Do not infer an off state from an
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


### Unattended-update incident, 27 October 2026

The three L530 bulbs moved from the previously recorded 1.1.2 firmware to
1.4.1 Build 260904 Rel.212342. Each advertised unsupported `TPAP` and rejected
HA's KLAP handshake with HTTP 403 while remaining reachable in the Tapo app.
Third-Party Compatibility still displayed **On**. Toggling it off and on
restored KLAP discovery and all three existing entities; a Peanut on/off
command succeeded without recreating integrations or changing credentials.

All three had automatic updates enabled, with a 03:00 start and 120-minute
random window. The observed failures at 03:11, 03:46 and 04:32 fit that window.
Together with the firmware change, this strongly supports unattended firmware
installation as the trigger; no exact installation-event log was recovered.
The confirmed failure was ineffective third-party compatibility despite the
app displaying On. Cluster readiness did not detect this device failure.

Automatic firmware updates were disabled through the existing
`switch.top_auto_update_enabled`, `switch.middle_auto_update_enabled` and
`switch.bottom_auto_update_enabled` entities. Fresh authenticated reads from
each bulb confirmed `enable=false`, firmware 1.4.1 and the lights off. These
settings are stored on the devices, not enforced by this Git repository.

### Firmware change policy

- Keep automatic updates disabled on these three bulbs. Verify the switches
  after provisioning, a factory reset, or any deliberate firmware update.
- Review firmware/security fixes deliberately. Update one bulb first, during
  an attended window; check that its firmware version changed, KLAP discovery
  works, HA polls fresh state, and an on/off command succeeds before updating
  the other two. Restore the prior light state after the check.
- If a candidate update breaks access, stop the remaining updates. Check the
  device's native app and protocol before restarting HA or changing passwords.
  A firmware downgrade is not assumed available or safe.
- Treat a native app's compatibility indicator as configuration, not proof.
  Verify the actual protocol and HA entity states after toggling it. Do not
  delete working device identities, re-pair bulbs, or reset them as a first fix.
- Keep recovery scoped to the reported failure. A deliberately powered-off
  appliance is not evidence of a shared outage. Diagnose device connectivity
  before changing unrelated integrations or restarting the HA server.

The Tapo app may expose a labelled compatibility row plus an unlabelled child
switch. If the guarded phone controller refuses the child, report the exact
refusal and leave the page for the owner; do not bypass it with coordinates.
Successful input delivery alone does not prove the setting changed.
