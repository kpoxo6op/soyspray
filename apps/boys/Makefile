include $(dir $(lastword $(MAKEFILE_LIST)))../common.mk
.PHONY: check diff bootstrap smoke restore-check

check:
	cd $(ROOT) && $(PYTHON) -m pytest -q apps/boys/tests
	cd $(ROOT)/apps/boys && npm test

diff:
	cd $(ROOT) && $(PYTHON) -m scripts.app_diff --app boys --package apps/boys/manifests

bootstrap:
	cd $(ROOT) && $(ANSIBLE) apps/boys/bootstrap.yml

smoke:
	@cd $(ROOT) && node apps/boys/smoke.js

restore-check:
	cd $(ROOT) && $(PYTHON) -m apps.boys.restore_check
