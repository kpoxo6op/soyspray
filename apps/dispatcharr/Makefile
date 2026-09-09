APP_NAME := dispatcharr
DIFF_MODE := --package apps/dispatcharr/manifests
APP_TESTS := tests/test_live_tv.py tests/test_durable_restore.py
RESTORE_TARGET := dispatcharr-data
include $(dir $(lastword $(MAKEFILE_LIST)))../gitops.mk
