include $(dir $(lastword $(MAKEFILE_LIST)))../common.mk
ENABLED ?= true
.PHONY: check diff deploy restore-check

check:
	cd $(ROOT) && $(PYTHON) -m pytest -q apps/obsidian-livesync/tests
	cd $(ROOT) && $(PYTHON) -m ansiblelint apps/obsidian-livesync/*.yml
	cd $(ROOT) && kubectl kustomize apps/obsidian-livesync/argocd >/dev/null

diff:
	cd $(ROOT) && $(PYTHON) -m scripts.app_diff --app obsidian-livesync --package apps/obsidian-livesync/manifests

deploy:
	test "$(ENABLED)" = true || { echo 'Retire an adopted app through an explicit operation; this command only deploys.' >&2; exit 1; }
	cd $(ROOT) && $(ANSIBLE) apps/obsidian-livesync/bootstrap.yml
	cd $(ROOT) && $(ANSIBLE) playbooks/bootstrap-apps.yml -e argocd_revision=$(REVISION) \
		-e argocd_preview_application=$(if $(filter HEAD,$(REVISION)),,obsidian-livesync)

restore-check:
	cd $(ROOT) && $(PYTHON) -m apps.obsidian-livesync.restore_check

.DEFAULT:
	@printf 'unknown: obsidian-livesync has no maintained %s operation yet.\n' "$@" >&2
	@exit 2
