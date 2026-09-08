include $(dir $(lastword $(MAKEFILE_LIST)))../common.mk
.PHONY: check diff bootstrap restore-check

check:
	cd $(ROOT) && $(PYTHON) -m unittest discover -s apps/node-backup/tests
	cd $(ROOT) && kubectl kustomize apps/node-backup/argocd >/dev/null
	cd $(ROOT) && kubectl kustomize apps/node-backup >/dev/null

diff:
	cd $(ROOT) && $(PYTHON) -m scripts.app_diff --app node-backup --package apps/node-backup

bootstrap:
	cd $(ROOT) && $(ANSIBLE) apps/node-backup/bootstrap.yml --vault-password-file $(HOME)/.config/soyspray/recovery/vault-password

restore-check:
	cd $(ROOT) && $(PYTHON) apps/node-backup/restore.py --snapshot "$(SNAPSHOT)"

.DEFAULT:
	@printf 'unknown: node-backup has no maintained %s operation yet.\n' "$@" >&2
	@exit 2
