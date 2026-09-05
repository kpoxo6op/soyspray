SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c
PYTHON ?= soyspray-venv/bin/python
REVISION ?= HEAD
.PHONY: check diff deploy

check:
	$(PYTHON) -m pytest -q apps/cert-manager-config/tests tests/test_argocd_root.py
	$(PYTHON) -m ansiblelint apps/cert-manager-config/*.yml argocd/bootstrap/repositories.yml roles/apps/authentik/tasks/certificate.yml
	kubectl kustomize apps/cert-manager-config/argocd >/dev/null

diff:
	$(PYTHON) -m scripts.app_diff --app cert-manager-config --pushed

deploy:
	$(MAKE) --no-print-directory -f Makefile APP= cert-manager-config CERT_MANAGER_CONFIG_REVISION=$(REVISION)

.DEFAULT:
	@printf 'unknown: cert-manager-config has no maintained %s operation yet.\n' "$@" >&2
	@exit 2
