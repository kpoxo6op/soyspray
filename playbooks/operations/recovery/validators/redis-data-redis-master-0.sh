#!/bin/sh
set -eu
redis-check-aof /data/appendonlydir/appendonly.aof.manifest
for file in /data/appendonlydir/*.rdb; do redis-check-rdb "$file"; done
