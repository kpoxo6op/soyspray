#!/usr/bin/env bash
# Record one command without interpreting it or choosing the next operation.
set -euo pipefail
umask 077
if (( $# < 3 )); then
    echo 'Usage: record.sh PRIVATE_DIRECTORY STEP COMMAND [ARGUMENT ...]' >&2
    exit 2
fi
drill_dir=$1
drill_step=$2
shift 2
if [[ $drill_dir != /* || ! $drill_step =~ ^[a-zA-Z0-9_-]+$ ]]; then
    echo 'Use an absolute private directory and a simple unique step name.' >&2
    exit 2
fi
mkdir -p -- "$drill_dir"
chmod 700 -- "$drill_dir"
drill_log="$drill_dir/$drill_step.log"
# Refuse a reused step instead of replacing the evidence from a failed attempt.
(set -o noclobber; : > "$drill_log") || exit 2
drill_started=$(date -u +%FT%TZ)
{
    printf '%s\tSTART\t%s\t' "$drill_started" "$drill_step"
    printf '%q ' "$@"
    printf '\n'
} >> "$drill_dir/journal.tsv"
if "$@" > "$drill_log" 2>&1; then
    drill_rc=0
else
    drill_rc=$?
fi
printf '%s\tEND\t%s\trc=%s\n' "$(date -u +%FT%TZ)" "$drill_step" "$drill_rc" >> "$drill_dir/journal.tsv"
printf '%s rc=%s log=%s\n' "$drill_step" "$drill_rc" "$drill_log"
exit "$drill_rc"
