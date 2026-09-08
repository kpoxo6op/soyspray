include $(dir $(lastword $(MAKEFILE_LIST)))../common.mk
.PHONY: check diff bootstrap

check:
	cd $(ROOT) && $(PYTHON) -m pytest -q apps/domain-health/tests
	cd $(ROOT) && $(PYTHON) -m ansiblelint apps/domain-health/*.yml
	cd $(ROOT) && kubectl kustomize apps/domain-health/argocd >/dev/null

diff:
	cd $(ROOT) && $(PYTHON) -m scripts.app_diff --app domain-health --package apps/domain-health

bootstrap:
	cd $(ROOT) && $(ANSIBLE) apps/domain-health/bootstrap.yml

.DEFAULT:
	@printf 'unknown: domain-health has no maintained %s operation yet.\n' "$@" >&2
	@exit 2
