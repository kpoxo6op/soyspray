include $(dir $(lastword $(MAKEFILE_LIST)))../common.mk
.PHONY: check diff

check:
	cd $(ROOT) && $(PYTHON) -m pytest -q apps/headlamp/tests tests/test_argocd_root.py tests/test_sso_headlamp.py
	cd $(ROOT) && kubectl kustomize apps/headlamp/argocd >/dev/null

diff:
	cd $(ROOT) && $(PYTHON) -m scripts.app_diff --app headlamp --pushed

.DEFAULT:
	@printf 'unknown: headlamp has no maintained %s operation yet.\n' "$@" >&2
	@exit 2
