APP_NAME := zigbee2mqtt
DIFF_MODE := --package apps/zigbee2mqtt/manifests
APP_TESTS := tests/test_sso_legacy_proxy.py tests/test_durable_restore.py
RESTORE_TARGET := zigbee2mqtt-data
include $(dir $(lastword $(MAKEFILE_LIST)))../gitops.mk
