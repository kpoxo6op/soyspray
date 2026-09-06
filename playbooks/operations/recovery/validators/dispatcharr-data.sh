#!/bin/sh
set -eu
export PATH=/usr/lib/postgresql/17/bin:$PATH
rm -f /data/db/postmaster.pid
printf 'local all all trust\n' > /tmp/hba
pg_ctl -D /data/db -l /tmp/postgres.log -o "-c listen_addresses='' -c unix_socket_directories=/tmp -c hba_file=/tmp/hba" -w start
trap 'pg_ctl -D /data/db -m fast -w stop' EXIT
for user in postgres dispatcharr; do
 if psql -h /tmp -U "$user" -d postgres -Atc 'SELECT count(*) FROM pg_database' >/tmp/count 2>/dev/null; then
  cat /tmp/count
  pg_amcheck -h /tmp -U "$user" --all --install-missing
  exit 0
 fi
done
exit 1
