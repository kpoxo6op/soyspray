#!/bin/sh
set -eu
case "${PACK_HASH:-}" in
  *[!a-f0-9]*|'') echo 'PACK_HASH must be configured' >&2; exit 1;;
esac
test "${#PACK_HASH}" = 64
printf '{"packHash":"%s"}\n' "$PACK_HASH" > /tmp/site-config.json
exec nginx -g 'daemon off;'
