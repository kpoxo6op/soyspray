APP_NAME := lazylibrarian
DIFF_MODE := --package apps/lazylibrarian/manifests
APP_TESTS := tests/test_sso_legacy_proxy.py tests/test_durable_restore.py
RESTORE_TARGET := lazylibrarian-books lazylibrarian-config
include $(dir $(lastword $(MAKEFILE_LIST)))../gitops.mk
