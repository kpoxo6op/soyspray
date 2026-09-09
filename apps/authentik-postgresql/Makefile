APP_NAME := authentik-postgresql
DIFF_MODE := --package apps/authentik-postgresql/manifests
APP_TESTS := tests/test_authentik_postgresql_metrics.py tests/test_cnpg_migration.py
include $(dir $(lastword $(MAKEFILE_LIST)))../gitops.mk
