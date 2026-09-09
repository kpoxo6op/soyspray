APP_NAME := jellyfin
DIFF_MODE := --package apps/jellyfin/manifests
APP_TESTS := tests/test_live_tv.py tests/test_durable_restore.py
RESTORE_TARGET := jellyfin-config-v2
include $(dir $(lastword $(MAKEFILE_LIST)))../gitops.mk
