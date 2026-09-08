include $(dir $(lastword $(MAKEFILE_LIST)))../common.mk
.PHONY: check diff bootstrap

check:
	cd $(ROOT) && $(PYTHON) -m pytest -q apps/external-dns/tests
	cd $(ROOT) && $(PYTHON) -m ansiblelint apps/external-dns/*.yml
	cd $(ROOT) && kubectl kustomize apps/external-dns/argocd >/dev/null

diff:
	cd $(ROOT) && $(PYTHON) -m scripts.app_diff --app external-dns --pushed

bootstrap:
	cd $(ROOT) && $(ANSIBLE) apps/external-dns/bootstrap.yml

.DEFAULT:
	@printf 'unknown: ExternalDNS has no maintained %s operation yet.\n' "$@" >&2
	@exit 2
