APP_NAME := redis
DIFF_MODE := --pushed
APP_TESTS := tests/test_durable_restore.py
RESTORE_TARGET := redis-data-redis-master-0
include $(dir $(lastword $(MAKEFILE_LIST)))../gitops.mk
