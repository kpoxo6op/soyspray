## Adding a Zigbee device

1. Confirm the coordinator is visible on the node:

   * `ls -l /dev/serial/by-id`
   * Identify the `usb-ITead_Sonoff_Zigbee_3.0_USB_Dongle_Plus_...` path

2. Ensure Zigbee2MQTT is using that device path for `serial.port` and the pod has access to it via hostPath passthrough.

3. Open the Zigbee2MQTT UI and enable pairing:

   * Toggle **Permit join** on

4. Put the sensor into pairing mode:

   * Hold the pairing button until the LED blinks

5. Verify it joined:

   * Zigbee2MQTT shows the new device
   * Rename it to a stable, meaningful name

6. Confirm Home Assistant discovery:

   * Home Assistant shows the entity via MQTT discovery
   * Use it in automations and dashboards
