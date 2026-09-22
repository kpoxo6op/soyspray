include $(dir $(lastword $(MAKEFILE_LIST)))../common.mk
.PHONY: check diff bootstrap

check:
	cd $(ROOT) && $(PYTHON) -m pytest -q apps/cluster-diagnosis/tests
	cd $(ROOT) && $(PYTHON) -m ansiblelint apps/cluster-diagnosis/*.yml
	cd $(ROOT) && kubectl kustomize apps/cluster-diagnosis >/dev/null
	cd $(ROOT) && kubectl kustomize apps/cluster-diagnosis/argocd >/dev/null

diff:
	cd $(ROOT) && $(PYTHON) -m scripts.app_diff --app cluster-diagnosis --package apps/cluster-diagnosis

bootstrap:
	cd $(ROOT) && $(ANSIBLE) apps/cluster-diagnosis/bootstrap.yml

.DEFAULT:
	@printf 'unknown: cluster-diagnosis has no maintained %s operation yet.\n' "$@" >&2
	@exit 2
