#!/bin/bash
# Run under systemd so controller/SSH loss cannot cancel recovery.
set -euo pipefail
interface=${1:?interface required}
duration=${2:?duration required}
unit=${3:?unit required}
[[ $interface =~ ^[a-zA-Z0-9_-]+$ && $duration =~ ^[0-9]+$ && $unit =~ ^soyspray-network-[a-zA-Z0-9_-]+$ ]]
(( duration >= 10 && duration <= 120 ))

# A second systemd unit restores the interface even if this process is killed.
systemd-run --unit="${unit}-restore" --on-active="${duration}s" \
    --timer-property=AccuracySec=100ms ip link set dev "$interface" up
systemctl is-active --quiet "${unit}-restore.timer"
trap 'ip link set dev "$interface" up' EXIT
date -u '+NETWORK_DOWN %FT%TZ'
ip link set dev "$interface" down
sleep "$duration"
ip link set dev "$interface" up
date -u '+NETWORK_UP %FT%TZ'
