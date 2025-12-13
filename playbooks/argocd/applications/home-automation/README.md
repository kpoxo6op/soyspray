# Home Automation Stack

Complete home automation stack for managing Zigbee sensors and devices through Kubernetes, using GitOps principles.

## Overview

The stack consists of three core applications working together to provide local, self-hosted home automation:

- **Mosquitto**: MQTT message broker that acts as the central communication hub
- **Zigbee2MQTT**: Zigbee coordinator bridge that connects Zigbee devices to MQTT
- **Home Assistant**: Automation platform with web UI for device management and automations

## Architecture

The stack uses a Sonoff ZBDongle-P Zigbee coordinator (USB dongle) as the hub for Zigbee sensors. Data flows from sensors through the coordinator to Zigbee2MQTT, which publishes to Mosquitto, and Home Assistant subscribes to MQTT topics for automation and control.

```
Zigbee Sensors (Aqara/Tuya)
    ↓
Sonoff ZBDongle-P (USB Coordinator)
    ↓
Zigbee2MQTT
    ↓
Mosquitto (MQTT Broker)
    ↓
Home Assistant
```

## Components

### Mosquitto

MQTT message broker providing the messaging infrastructure for all components. Acts as the central message bus for sensor data and automation commands.

### Zigbee2MQTT

Bridges Zigbee devices to MQTT. Connects to the Sonoff ZBDongle-P USB coordinator via serial passthrough and translates Zigbee protocol messages to MQTT topics. Supports Aqara and Tuya sensors out of the box.

### Home Assistant

Home automation platform that subscribes to MQTT topics for device discovery and control. Provides web UI for managing devices, creating automations, and monitoring sensor states.

## Deployment

All applications are deployed as ArgoCD applications in the `home-automation` namespace, following GitOps principles. Each application has its own directory with Kubernetes manifests and configuration.

## Storage

All applications use Longhorn persistent volumes for configuration and data persistence, ensuring state survives pod restarts and cluster updates.

