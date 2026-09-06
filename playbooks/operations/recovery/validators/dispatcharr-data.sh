#!/bin/sh
set -eu
export PATH=/usr/lib/postgresql/17/bin:$PATH
rm -f /data/db/postmaster.pid
printf 'local all all trust\n' > /tmp/hba
pg_ctl -D /data/db -l /tmp/postgres.log -o "-c listen_addresses='' -c unix_socket_directories=/tmp -c hba_file=/tmp/hba" -w start
trap 'pg_ctl -D /data/db -m fast -w stop' EXIT
psql -h /tmp -U dispatch -d postgres -Atc 'SELECT count(*) FROM pg_database'
pg_amcheck -h /tmp -U dispatch --all --install-missing
