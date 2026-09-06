include $(dir $(lastword $(MAKEFILE_LIST)))../common.mk
.PHONY: check diff deploy

check:
	cd $(ROOT) && $(PYTHON) -m pytest -q apps/media-helper/tests tests/test_argocd_root.py tests/test_live_tv.py tests/test_ci_scope.py
	cd $(ROOT) && kubectl kustomize apps/media-helper/argocd >/dev/null

diff:
	cd $(ROOT) && $(PYTHON) -m scripts.app_diff --app media-helper --pushed

deploy:
	cd $(ROOT) && $(ANSIBLE) playbooks/bootstrap-apps.yml -e argocd_revision=$(REVISION) \
		-e argocd_preview_application=$(if $(filter HEAD,$(REVISION)),,media-helper)

.DEFAULT:
	@printf 'unknown: media-helper has no maintained %s operation yet.\n' "$@" >&2
	@exit 2
