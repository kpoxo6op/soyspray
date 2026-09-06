#!/bin/sh
set -eu
root="$(CDPATH='' cd -- "$(dirname -- "$0")/../../.." && pwd)"
cd "$root"
exec "$root/soyspray-venv/bin/python" -m apps.immich.recovery.run "$@"
