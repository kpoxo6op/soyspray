APP_NAME := mosquitto
DIFF_MODE := --package apps/mosquitto/manifests
APP_TESTS := tests/test_durable_restore.py
RESTORE_TARGET := mosquitto-data
include $(dir $(lastword $(MAKEFILE_LIST)))../gitops.mk
