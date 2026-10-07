include $(dir $(lastword $(MAKEFILE_LIST)))../common.mk
.PHONY: check diff

check:
	cd $(ROOT) && $(PYTHON) -m pytest -q tests/test_argocd_root.py
	cd $(ROOT) && kubectl kustomize apps/cert-manager/argocd >/dev/null

diff:
	cd $(ROOT) && $(PYTHON) -m scripts.app_diff_sources --app cert-manager
