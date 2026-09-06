include $(dir $(lastword $(MAKEFILE_LIST)))../common.mk
ENABLED ?= true
.PHONY: check diff deploy smoke restore-check

check:
	cd $(ROOT) && $(PYTHON) -m pytest -q apps/boys/tests
	cd $(ROOT)/apps/boys && npm test

diff:
	cd $(ROOT) && $(PYTHON) -m scripts.app_diff --app boys --package apps/boys/manifests

deploy:
	test "$(ENABLED)" = true || { echo 'Retire an adopted app through an explicit operation; this command only deploys.' >&2; exit 1; }
	cd $(ROOT) && $(ANSIBLE) apps/boys/bootstrap.yml
	cd $(ROOT) && $(ANSIBLE) playbooks/bootstrap-apps.yml -e argocd_revision=$(REVISION) \
		-e argocd_preview_application=$(if $(filter HEAD,$(REVISION)),,boys)

smoke:
	@cd $(ROOT) && node apps/boys/smoke.js

restore-check:
	cd $(ROOT) && $(PYTHON) -m apps.boys.restore_check
