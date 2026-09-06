include $(dir $(lastword $(MAKEFILE_LIST)))../common.mk
ENABLED ?= true
.PHONY: check diff deploy restore-check

check:
	cd $(ROOT) && $(PYTHON) -m pytest -q apps/vaultwarden/tests
	cd $(ROOT) && $(PYTHON) -m ansiblelint apps/vaultwarden/*.yml
	cd $(ROOT) && kubectl kustomize apps/vaultwarden/argocd >/dev/null

diff:
	cd $(ROOT) && $(PYTHON) -m scripts.app_diff --app vaultwarden --package apps/vaultwarden/manifests

deploy:
	test "$(ENABLED)" = true || { echo 'Retire an adopted app through an explicit operation; this command only deploys.' >&2; exit 1; }
	cd $(ROOT) && $(ANSIBLE) apps/vaultwarden/bootstrap.yml
	cd $(ROOT) && $(ANSIBLE) playbooks/bootstrap-apps.yml -e argocd_revision=$(REVISION) \
		-e argocd_preview_application=$(if $(filter HEAD,$(REVISION)),,vaultwarden)

restore-check:
	cd $(ROOT) && $(PYTHON) -m apps.vaultwarden.restore_check

.DEFAULT:
	@printf 'unknown: vaultwarden has no maintained %s operation yet.\n' "$@" >&2
	@exit 2
