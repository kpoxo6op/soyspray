include $(dir $(lastword $(MAKEFILE_LIST)))../common.mk
.PHONY: check diff deploy restore-check

check:
	cd $(ROOT) && $(PYTHON) -m unittest discover -s apps/node-backup/tests
	cd $(ROOT) && kubectl kustomize apps/node-backup/argocd >/dev/null
	cd $(ROOT) && kubectl kustomize apps/node-backup >/dev/null

diff:
	cd $(ROOT) && $(PYTHON) -m scripts.app_diff --app node-backup --package apps/node-backup

deploy:
	cd $(ROOT) && $(ANSIBLE) apps/node-backup/bootstrap.yml --vault-password-file $(HOME)/.config/soyspray/recovery/vault-password
	cd $(ROOT) && $(ANSIBLE) playbooks/bootstrap-apps.yml -e argocd_revision=$(REVISION) \
		-e argocd_preview_application=$(if $(filter HEAD,$(REVISION)),,node-backup)

restore-check:
	cd $(ROOT) && $(PYTHON) apps/node-backup/restore.py --snapshot "$(SNAPSHOT)"

.DEFAULT:
	@printf 'unknown: node-backup has no maintained %s operation yet.\n' "$@" >&2
	@exit 2
