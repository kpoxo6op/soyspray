include $(dir $(lastword $(MAKEFILE_LIST)))../common.mk
.PHONY: check diff bootstrap

check:
	cd $(ROOT) && $(PYTHON) -m pytest -q apps/autism-traits/tests
	cd $(ROOT)/apps/autism-traits/app && npm run check && npm run test:e2e

diff:
	cd $(ROOT) && $(PYTHON) -m scripts.app_diff --app autism-traits --package apps/autism-traits/manifests

bootstrap:
	cd $(ROOT) && $(ANSIBLE) apps/autism-traits/bootstrap.yml

.DEFAULT:
	@printf 'unknown: autism-traits has no maintained %s operation.\n' '$@'; exit 2
