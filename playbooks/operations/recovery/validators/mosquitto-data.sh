#!/bin/sh
set -eu
printf 'listener 1883 127.0.0.1\nallow_anonymous true\npersistence true\npersistence_location /data/\nlog_dest stdout\n' > /tmp/mosquitto.conf
mosquitto -c /tmp/mosquitto.conf -v >/tmp/mosquitto.log 2>&1 &
pid=$!
trap 'kill "$pid" 2>/dev/null || true; wait "$pid" || true' EXIT
sleep 10
kill -0 "$pid"
cat /tmp/mosquitto.log
if grep -iE 'error|corrupt|unsupported' /tmp/mosquitto.log; then exit 1; fi
