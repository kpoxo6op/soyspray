include $(dir $(lastword $(MAKEFILE_LIST)))../common.mk
.PHONY: check diff deploy

check:
	cd $(ROOT) && $(PYTHON) -m pytest -q apps/external-dns/tests
	cd $(ROOT) && $(PYTHON) -m ansiblelint apps/external-dns/*.yml
	cd $(ROOT) && kubectl kustomize apps/external-dns/argocd >/dev/null

diff:
	cd $(ROOT) && $(PYTHON) -m scripts.app_diff --app external-dns --pushed

deploy:
	cd $(ROOT) && $(ANSIBLE) apps/external-dns/bootstrap.yml
	cd $(ROOT) && $(ANSIBLE) playbooks/bootstrap-apps.yml -e argocd_revision=$(REVISION) \
		-e argocd_preview_application=$(if $(filter HEAD,$(REVISION)),,external-dns)

.DEFAULT:
	@printf 'unknown: ExternalDNS has no maintained %s operation yet.\n' "$@" >&2
	@exit 2
