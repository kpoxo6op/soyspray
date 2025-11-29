#!/usr/bin/env bash
#
# Usage:
#   ./argocd-list.sh "Name Status Health"
# or via make:
#   make argocd-list COLS="Name Status Health"
#
# Common fields -> JSON path:
#   Name         -> .metadata.name
#   Namespace    -> .spec.destination.namespace
#   Status       -> .status.sync.status
#   Health       -> .status.health.status
#   SyncPolicy   -> .spec.syncPolicy
#   Repo         -> .spec.source.repoURL
#   Path         -> .spec.source.path
#   Target       -> .spec.source.targetRevision

set -euo pipefail

# If no columns given, default to something small
COLS="${1:-Name Namespace Status}"

# Mapping short field names to actual JSON paths
declare -A MAP=(
  [Name]=".metadata.name"
  [Namespace]=".spec.destination.namespace"
  [Status]=".status.sync.status"
  [Health]=".status.health.status"
  [SyncPolicy]=".spec.syncPolicy"
  [Repo]=".spec.source.repoURL"
  [Path]=".spec.source.path"
  [Target]=".spec.source.targetRevision"
)

# Convert COLS into an array of JSON paths
IFS=' ' read -ra FIELDS <<< "$COLS"

# Query Argo CD in JSON
APPS_JSON="$(argocd app list -o json)"

# Print header
echo -n "#"
for field in "${FIELDS[@]}"; do
  width=20
  if [[ "$field" == "Name" ]]; then
    width=35
  fi
  printf " %-${width}s" "$field"
done
echo ""

# Loop over each item in the JSON array
echo "$APPS_JSON" | jq -c '.[]' | while read -r row; do
  echo -n " "
  for field in "${FIELDS[@]}"; do
    path="${MAP[$field]:-}"
    if [[ -z "$path" ]]; then
      # If user provided an unknown column name, just show blank
      printf "%-20s " "-"
      continue
    fi
    # Extract the value
    value="$(echo "$row" | jq -r "$path // \"\"")"

    # Dynamic width based on field
    width=20
    if [[ "$field" == "Name" ]]; then
      width=35
    fi

    # Print formatted column (truncated to width)
    printf "%-${width}s " "$(echo "$value" | cut -c1-$width)"
  done
  echo ""
done

