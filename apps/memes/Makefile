include $(dir $(lastword $(MAKEFILE_LIST)))../common.mk
.PHONY: check diff
check:
	cd $(ROOT) && $(PYTHON) -m ruff check apps/memes
	cd $(ROOT) && $(PYTHON) -m ruff format --check apps/memes
	cd $(ROOT) && PYTHONPATH=apps/memes:apps/memes/tests OPENBLAS_NUM_THREADS=4 $(PYTHON) -m pytest -q apps/memes/tests
	cd $(ROOT) && kubectl kustomize apps/memes/manifests >/dev/null
	cd $(ROOT) && kubectl kustomize apps/memes/argocd >/dev/null
	cd $(ROOT)/apps/memes && MEMES_TEST_PYTHON=$(abspath $(shell command -v $(PYTHON))) npm test
	@printf 'Memes checks passed.\n'
diff:
	cd $(ROOT) && $(PYTHON) -m scripts.app_diff --app memes --package apps/memes/manifests
