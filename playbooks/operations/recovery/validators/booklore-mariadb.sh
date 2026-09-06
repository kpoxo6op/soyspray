#!/bin/sh
set -eu
mariadbd --no-defaults --datadir=/data/databases --socket=/tmp/mysql.sock --pid-file=/tmp/mysql.pid --skip-networking --skip-grant-tables --log-error=/tmp/mysql.log &
pid=$!
trap 'kill "$pid" 2>/dev/null || true; wait "$pid" || true' EXIT
for n in $(seq 1 60); do mariadb-admin --no-defaults --socket=/tmp/mysql.sock ping >/dev/null 2>&1 && break; kill -0 "$pid"; sleep 2; done
mariadb-check --no-defaults --socket=/tmp/mysql.sock --all-databases
mariadb --no-defaults --socket=/tmp/mysql.sock -N -e "SELECT table_schema,count(*) FROM information_schema.tables WHERE table_schema='booklore' GROUP BY table_schema;"
