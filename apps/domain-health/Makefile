include $(dir $(lastword $(MAKEFILE_LIST)))../common.mk
.PHONY: check diff deploy

check:
	cd $(ROOT) && $(PYTHON) -m pytest -q apps/domain-health/tests
	cd $(ROOT) && $(PYTHON) -m ansiblelint apps/domain-health/*.yml
	cd $(ROOT) && kubectl kustomize apps/domain-health/argocd >/dev/null

diff:
	cd $(ROOT) && $(PYTHON) -m scripts.app_diff --app domain-health --package apps/domain-health

deploy:
	cd $(ROOT) && $(ANSIBLE) apps/domain-health/bootstrap.yml
	cd $(ROOT) && $(ANSIBLE) playbooks/bootstrap-apps.yml -e argocd_revision=$(REVISION) \
		-e argocd_preview_application=$(if $(filter HEAD,$(REVISION)),,domain-health)

.DEFAULT:
	@printf 'unknown: domain-health has no maintained %s operation yet.\n' "$@" >&2
	@exit 2
