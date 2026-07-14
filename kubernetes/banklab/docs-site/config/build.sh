#!/bin/sh
set -eu

published_revision=""
mkdir -p /site/releases

while true; do
  if [ ! -L /repo/current ]; then
    sleep 2
    continue
  fi

  revision="$(basename "$(readlink /repo/current)")"
  if [ "$revision" = "$published_revision" ]; then
    sleep 15
    continue
  fi

  work_dir="/site/releases/.${revision}.tmp"
  release_dir="/site/releases/${revision}"
  rm -rf "$work_dir"
  mkdir -p "$work_dir"

  (
    cd /repo/current
    mkdocs build --strict --site-dir "$work_dir"
  )

  rm -rf "$release_dir"
  mv "$work_dir" "$release_dir"
  ln -sfn "releases/${revision}" /site/current
  find /site/releases -mindepth 1 -maxdepth 1 -type d ! -name "$revision" -exec rm -rf {} +

  published_revision="$revision"
  printf 'Published docs revision %s\n' "$revision"
  sleep 15
done
