SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c
PYTHON ?= soyspray-venv/bin/python
REVISION ?= HEAD
.PHONY: check diff deploy

check:
	$(PYTHON) -m pytest -q apps/external-dns/tests
	$(PYTHON) -m ansiblelint apps/external-dns/*.yml
	kubectl kustomize apps/external-dns/argocd >/dev/null

diff:
	$(PYTHON) -m scripts.app_diff --app external-dns --pushed

deploy:
	$(MAKE) --no-print-directory -f Makefile APP= external-dns EXTERNAL_DNS_REVISION=$(REVISION)

.DEFAULT:
	@printf 'unknown: ExternalDNS has no maintained %s operation yet.\n' "$@" >&2
	@exit 2
