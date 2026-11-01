#!/bin/sh
# Rebuild data/trays.bin, the node tray mesh, from a RackStack checkout.
# Needs Python 3 with NumPy.
set -e
RACKSTACK=${RACKSTACK:?Set RACKSTACK to the local RackStack checkout}
export RACKSTACK
cd "$(dirname "$0")"
python3 -I pack_meshes.py ../data/trays.bin
