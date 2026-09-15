include $(dir $(lastword $(MAKEFILE_LIST)))../common.mk
.PHONY: check diff bootstrap

check:
	cd $(ROOT) && $(PYTHON) -m pytest -q apps/gi/tests
	cd $(ROOT) && $(PYTHON) -m ruff check apps/gi/tests
	cd $(ROOT) && $(PYTHON) -m ruff format --check apps/gi/tests
	cd $(ROOT) && kubectl kustomize apps/gi/manifests >/dev/null
	cd $(ROOT) && kubectl kustomize apps/gi/argocd >/dev/null

diff:
	cd $(ROOT) && $(PYTHON) -m scripts.app_diff --app gi

bootstrap:
	cd $(ROOT) && $(ANSIBLE) apps/gi/bootstrap.yml

.DEFAULT:
	@printf 'unknown: gi has no maintained %s operation yet.\n' "$@" >&2
	@exit 2
