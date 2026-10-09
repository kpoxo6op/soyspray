#!/usr/bin/env bash
set -euo pipefail
mode=${1:?}; voice_pid=${2:?}; birth=${3:?}; seconds=${4:-0}; test_id=${5:-restore}
[[ $voice_pid =~ ^[0-9]+$ && $voice_pid -gt 1 && $birth =~ ^[0-9]+$ ]] || exit 2
same_process() {
  [[ -r /proc/$voice_pid/stat ]] && [[ $(awk '{print $22}' "/proc/$voice_pid/stat") == "$birth" ]]
}
restore() {
  if same_process; then
    kill -CONT "$voice_pid"
    printf 'VOICE_CONT id=%s utc=%s\n' "$test_id" "$(date -u +%FT%TZ)"
  else
    printf 'VOICE_RESTORE_SKIPPED identity_changed id=%s\n' "$test_id"
  fi
}
if [[ $mode == restore ]]; then restore; exit; fi
[[ $mode == freeze && $seconds =~ ^[0-9]+$ && $seconds -ge 240 && $seconds -le 420 && $test_id =~ ^[A-Za-z0-9-]+$ ]] || exit 2
same_process || { printf 'Refusing changed process identity\n' >&2; exit 3; }
unit="soyspray-gi-$test_id"
systemd-run --quiet --collect --unit="$unit-restore" --on-active="${seconds}s" \
  -- /bin/bash "$(realpath "$0")" restore "$voice_pid" "$birth" 0 "$test_id"
systemctl is-active --quiet "$unit-restore.timer"
printf 'VOICE_RESTORE_ARMED id=%s utc=%s\n' "$test_id" "$(date -u +%FT%TZ)"
trap restore EXIT
same_process || exit 3
kill -STOP "$voice_pid"
printf 'VOICE_STOP id=%s utc=%s\n' "$test_id" "$(date -u +%FT%TZ)"
sleep "$seconds"
