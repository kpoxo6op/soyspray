SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c
PYTHON ?= soyspray-venv/bin/python
REVISION ?= HEAD
.PHONY: check diff deploy

check:
	$(PYTHON) -m pytest -q apps/domain-health/tests
	$(PYTHON) -m ansiblelint apps/domain-health/*.yml
	kubectl kustomize apps/domain-health/argocd >/dev/null

diff:
	$(PYTHON) -m scripts.app_diff --app domain-health --package apps/domain-health

deploy:
	$(MAKE) --no-print-directory -f Makefile APP= domain-health DOMAIN_HEALTH_REVISION=$(REVISION)

.DEFAULT:
	@printf 'unknown: domain-health has no maintained %s operation yet.\n' "$@" >&2
	@exit 2
