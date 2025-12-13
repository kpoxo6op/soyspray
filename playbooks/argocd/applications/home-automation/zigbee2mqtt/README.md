# Zigbee2MQTT

Zigbee2MQTT is an open-source bridge that allows you to use Zigbee devices without the vendor's bridge or gateway. It connects Zigbee devices to an MQTT broker, enabling integration with home automation platforms.

## Features

- Supports a wide range of Zigbee devices from various manufacturers
- Web-based frontend for device management and configuration
- Local control without cloud dependencies
- Automatic device discovery and pairing
- Home Assistant integration via MQTT discovery

## Integration

Zigbee2MQTT bridges Zigbee devices to the MQTT broker:
- Connects to Zigbee coordinator (Sonoff ZBDongle-P) via USB serial passthrough
- Publishes device states and events to MQTT topics
- Subscribes to MQTT commands to control devices
- Home Assistant automatically discovers devices via MQTT discovery

