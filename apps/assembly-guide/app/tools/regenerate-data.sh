#!/bin/sh
# Rebuild data/placements.json and data/meshes.bin from a RackStack checkout.
# Needs OpenSCAD and Python 3 with NumPy and SciPy.
set -e
RACKSTACK=${RACKSTACK:?Set RACKSTACK to the local RackStack checkout}
export RACKSTACK
cd "$(dirname "$0")"
OPENSCADPATH="$RACKSTACK" openscad -o "${TMPDIR:-/tmp}/soyspray-transforms.stl" transforms.scad 2>&1 \
  | grep '^ECHO: ' | sed 's/^ECHO: //' > transforms.echo.txt
python3 -I derive.py --json ../data/placements.json
python3 -I pack_meshes.py ../data/meshes.bin
