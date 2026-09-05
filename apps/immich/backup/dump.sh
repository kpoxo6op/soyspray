#!/bin/sh
set -eu
umask 077
mkdir -p /backup/database
date -u '+%Y-%m-%d %H:%M:%S' > /backup/database/started-at
psql -X -q -A -t -0 -v ON_ERROR_STOP=on -f "$(dirname "$0")/dump.sql"
pg_restore --list /backup/database/immich.dump > /dev/null
