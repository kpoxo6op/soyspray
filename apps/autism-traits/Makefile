include $(dir $(lastword $(MAKEFILE_LIST)))../common.mk
ENABLED ?= true
.PHONY: check diff deploy

check:
	cd $(ROOT) && $(PYTHON) -m pytest -q apps/autism-traits/tests
	cd $(ROOT)/apps/autism-traits/app && npm run check && npm run test:e2e

diff:
	cd $(ROOT) && $(PYTHON) -m scripts.app_diff --app autism-traits --package apps/autism-traits/manifests

deploy:
	test "$(ENABLED)" = true || { echo 'Retire an adopted app through an explicit operation; this command only deploys.' >&2; exit 1; }
	cd $(ROOT) && $(ANSIBLE) apps/autism-traits/bootstrap.yml
	cd $(ROOT) && $(ANSIBLE) playbooks/bootstrap-apps.yml -e argocd_revision=$(REVISION) \
		-e argocd_preview_application=$(if $(filter HEAD,$(REVISION)),,autism-traits)

.DEFAULT:
	@printf 'unknown: autism-traits has no maintained %s operation.\n' '$@'; exit 2
