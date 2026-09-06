#!/bin/sh
set -eu

if [ "$#" -lt 1 ]; then
  echo "usage: $0 CHECK_ID [ansible-playbook options]" >&2
  exit 2
fi

check_id=$1
shift
playbook_dir="$(cd -- "$(dirname -- "$0")" && pwd)"

cleanup_on_signal() {
  trap - INT TERM
  ansible-playbook "$@" "$playbook_dir/cleanup.yml" -e "recovery_check_id=$check_id" || true
  exit 143
}
trap cleanup_on_signal INT TERM

ansible-playbook "$@" "$playbook_dir/restore.yml" -e "recovery_check_id=$check_id"
