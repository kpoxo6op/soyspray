include $(dir $(lastword $(MAKEFILE_LIST)))../common.mk
.PHONY: check diff restore-check

check:
	cd $(ROOT) && $(PYTHON) -m pytest -q apps/immich/tests --ignore=apps/immich/tests/test_backup.py

diff:
	cd $(ROOT) && $(PYTHON) -m scripts.app_diff --app immich --pushed

restore-check:
	cd $(ROOT) && $(PYTHON) -m apps.immich.recovery.run
