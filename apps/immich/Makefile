include $(dir $(lastword $(MAKEFILE_LIST)))../common.mk
.PHONY: check restore-check

check:
	cd $(ROOT) && $(PYTHON) -m pytest -q apps/immich/tests --ignore=apps/immich/tests/test_backup.py

restore-check:
	cd $(ROOT) && $(PYTHON) -m apps.immich.recovery.run
