include $(dir $(lastword $(MAKEFILE_LIST)))../common.mk

.PHONY: check render diff
check:
	cd $(ROOT) && $(PYTHON) -m pytest -q tests/test_argocd_root.py tests/test_argocd_runtime.py
render:
	cd $(ROOT) && kubectl kustomize apps/argocd/manifests
diff:
	cd $(ROOT) && $(PYTHON) -m scripts.app_diff --app argocd --pushed
