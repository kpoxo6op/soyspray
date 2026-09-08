include $(dir $(lastword $(MAKEFILE_LIST)))../common.mk
.PHONY: check diff bootstrap restore-check

check:
	cd $(ROOT) && $(PYTHON) -m pytest -q apps/obsidian-livesync/tests
	cd $(ROOT) && $(PYTHON) -m ansiblelint apps/obsidian-livesync/*.yml
	cd $(ROOT) && kubectl kustomize apps/obsidian-livesync/argocd >/dev/null

diff:
	cd $(ROOT) && $(PYTHON) -m scripts.app_diff --app obsidian-livesync --package apps/obsidian-livesync/manifests

bootstrap:
	cd $(ROOT) && $(ANSIBLE) apps/obsidian-livesync/bootstrap.yml

restore-check:
	cd $(ROOT) && $(PYTHON) -m apps.obsidian-livesync.restore_check

.DEFAULT:
	@printf 'unknown: obsidian-livesync has no maintained %s operation yet.\n' "$@" >&2
	@exit 2
