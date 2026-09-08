include $(dir $(lastword $(MAKEFILE_LIST)))../common.mk
.PHONY: check diff

check:
	cd $(ROOT) && $(PYTHON) -m pytest -q apps/media-helper/tests tests/test_argocd_root.py tests/test_live_tv.py tests/test_ci_scope.py
	cd $(ROOT) && kubectl kustomize apps/media-helper/argocd >/dev/null

diff:
	cd $(ROOT) && $(PYTHON) -m scripts.app_diff --app media-helper --pushed

.DEFAULT:
	@printf 'unknown: media-helper has no maintained %s operation yet.\n' "$@" >&2
	@exit 2
