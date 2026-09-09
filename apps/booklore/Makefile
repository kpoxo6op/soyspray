APP_NAME := booklore
DIFF_MODE := --package apps/booklore/manifests
APP_TESTS := tests/test_durable_restore.py
RESTORE_TARGET := booklore-data booklore-config booklore-mariadb
include $(dir $(lastword $(MAKEFILE_LIST)))../gitops.mk
