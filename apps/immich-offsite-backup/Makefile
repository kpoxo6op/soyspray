APP_NAME := immich-offsite-backup
DIFF_MODE := --package apps/immich-offsite-backup/manifests
APP_TESTS := apps/immich-offsite-backup/tests --ignore=apps/immich-offsite-backup/tests/test_backup.py
include $(dir $(lastword $(MAKEFILE_LIST)))../gitops.mk
