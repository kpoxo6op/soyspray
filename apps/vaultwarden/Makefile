include $(dir $(lastword $(MAKEFILE_LIST)))../common.mk
.PHONY: check diff bootstrap restore-check

check:
	cd $(ROOT) && $(PYTHON) -m pytest -q apps/vaultwarden/tests
	cd $(ROOT) && $(PYTHON) -m ansiblelint apps/vaultwarden/*.yml
	cd $(ROOT) && kubectl kustomize apps/vaultwarden/argocd >/dev/null

diff:
	cd $(ROOT) && $(PYTHON) -m scripts.app_diff --app vaultwarden --package apps/vaultwarden/manifests

bootstrap:
	cd $(ROOT) && $(ANSIBLE) apps/vaultwarden/bootstrap.yml

restore-check:
	cd $(ROOT) && $(PYTHON) -m apps.vaultwarden.restore_check

.DEFAULT:
	@printf 'unknown: vaultwarden has no maintained %s operation yet.\n' "$@" >&2
	@exit 2
