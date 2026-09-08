include $(dir $(lastword $(MAKEFILE_LIST)))../common.mk
.PHONY: check diff bootstrap smoke

check:
	cd $(ROOT) && $(PYTHON) -m pytest -q apps/cert-manager-config/tests tests/test_argocd_root.py
	cd $(ROOT) && $(PYTHON) -m ansiblelint apps/cert-manager-config/*.yml argocd/bootstrap/repositories.yml roles/apps/authentik/tasks/certificate.yml
	cd $(ROOT) && kubectl kustomize apps/cert-manager-config/argocd >/dev/null

diff:
	cd $(ROOT) && $(PYTHON) -m scripts.app_diff --app cert-manager-config --pushed

bootstrap:
	cd $(ROOT) && $(ANSIBLE) apps/cert-manager-config/bootstrap.yml

smoke:
	@cd $(ROOT) && $(PYTHON) -m apps.cert-manager-config.smoke

.DEFAULT:
	@printf 'unknown: cert-manager-config has no maintained %s operation yet.\n' "$@" >&2
	@exit 2
