APP_NAME := qbittorrent
DIFF_MODE := --package apps/qbittorrent/manifests
APP_TESTS := tests/test_sso_home_assistant_qbittorrent.py tests/test_durable_restore.py
RESTORE_TARGET := qbittorrent-config
include $(dir $(lastword $(MAKEFILE_LIST)))../gitops.mk
