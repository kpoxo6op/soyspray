PYTHON ?= python3

.PHONY: check render diff
check:
	cd ../.. && $(PYTHON) -m pytest -q tests/test_argocd_root.py tests/test_argocd_runtime.py
render:
	kubectl kustomize manifests
diff:
	cd ../.. && $(PYTHON) -m scripts.app_diff --app argocd --pushed
