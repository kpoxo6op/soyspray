#!/bin/sh
set -eu
umask 077
export TZ=UTC
export RESTIC_HOST=immich
: "${RESTIC_REPOSITORY:?Supply the encrypted repository input}"
: "${RESTIC_PASSWORD_FILE:?Supply the off-cluster recovery key}"

# All three original-content roots are required, including empty directories.
for path in upload library profile; do
  test -d "/usr/src/app/upload/$path"
done
test -s /backup/database/immich.dump
test -s /backup/database/started-at
test -f /backup/database/required-files.raw

restic backup --retry-lock 5m --json --host immich --group-by host \
  --time "$(cat /backup/database/started-at)" --tag pending \
  /backup/database /usr/src/app/upload/upload \
  /usr/src/app/upload/library /usr/src/app/upload/profile > /backup/result.json
snapshot=$(jq -er 'select(.message_type == "summary") | .snapshot_id | select(type == "string" and test("^[a-f0-9]{64}$"))' /backup/result.json)
restic ls --json "$snapshot" > /backup/files.json
# Restic can return success when a file vanished before traversal. Check its saved tree.
jq -se --rawfile required /backup/database/required-files.raw '
  ($required | split("\u0000") | map(select(length > 0)))
  - [.[] | select(.struct_type == "node" and .type == "file") | .path]
  | length == 0
' /backup/files.json > /dev/null
restic tag --retry-lock 5m --add restore-candidate --remove pending "$snapshot"
restic forget --retry-lock 5m --host immich --tag restore-candidate \
  --group-by host --keep-last 48 --keep-daily 30
